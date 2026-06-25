from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Category, Product, Cart, Order, OrderItem, UserProfile, LoyaltyConfig, LoyaltyWallet, LoyaltyTransaction
from .forms import RegisterForm, ProfileUpdateForm, CheckoutForm
import uuid
import razorpay
import stripe
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from .tasks import (
    send_registration_email,
    send_order_confirmation_email,
    send_payment_notification_email
)

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


def award_points(order):
    """Award exactly 1 loyalty point per purchase."""
    if order.points_earned == 0:
        wallet, _ = LoyaltyWallet.objects.get_or_create(user=order.user)
        order.points_earned = 1
        order.save(update_fields=['points_earned'])
        wallet.earn_points(1, order=order, description=f"1 point earned on Order {order.order_id}")

def home(request):
    categories = Category.objects.all()
    featured_products = Product.objects.filter(is_active=True).order_by('-views_count')[:8]
    latest_products = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    return render(request, 'store/home.html', {
        'categories': categories,
        'featured_products': featured_products,
        'latest_products': latest_products,
    })


def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()

    query = request.GET.get('q', '')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    category_slug = request.GET.get('category', '')
    selected_category = None
    if category_slug:
        selected_category = Category.objects.filter(slug=category_slug).first()
        if selected_category:
            products = products.filter(category=selected_category)

    sort = request.GET.get('sort', '')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    elif sort == 'popular':
        products = products.order_by('-views_count')

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    sort_options = [
        ('', 'Default'),
        ('popular', 'Most Popular'),
        ('newest', 'Newest First'),
        ('price_asc', 'Price: Low to High'),
        ('price_desc', 'Price: High to Low'),
    ]

    return render(request, 'store/products.html', {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'category_slug': category_slug,
        'selected_category': selected_category,
        'sort': sort,
        'sort_options': sort_options,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    product.views_count += 1
    product.save(update_fields=['views_count'])

    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=pk)[:4]

    in_cart = False
    if request.user.is_authenticated:
        in_cart = Cart.objects.filter(user=request.user, product=product).exists()

    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'in_cart': in_cart,
    })


@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    subtotal = sum(item.subtotal for item in cart_items)
    tax = subtotal * 18 / 100
    total = subtotal + tax
    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': round(tax, 2),
        'total': round(total, 2),
    })


@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if not product.in_stock:
        messages.error(request, f'"{product.name}" is currently out of stock.')
        return redirect('product_detail', pk=pk)

    cart_item, created = Cart.objects.get_or_create(
        user=request.user, product=product,
        defaults={'quantity': 1}
    )
    if not created:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'Updated quantity for "{product.name}".')
        else:
            messages.warning(request, f'Cannot add more — only {product.stock} in stock.')
    else:
        messages.success(request, f'"{product.name}" added to cart! 🛒')

    next_url = request.GET.get('next', 'cart')
    return redirect(next_url)


@login_required
def update_cart(request, pk):
    cart_item = get_object_or_404(Cart, pk=pk, user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > 0:
        if quantity <= cart_item.product.stock:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            messages.warning(request, f'Only {cart_item.product.stock} units available.')
    else:
        cart_item.delete()
        messages.info(request, 'Item removed from cart.')
    return redirect('cart')


@login_required
def remove_from_cart(request, pk):
    cart_item = get_object_or_404(Cart, pk=pk, user=request.user)
    name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'"{name}" removed from cart.')
    return redirect('cart')


@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    subtotal = sum(item.subtotal for item in cart_items)
    tax = round(subtotal * 18 / 100, 2)
    total = round(subtotal + tax, 2)

    loyalty_config = LoyaltyConfig.get_solo()
    wallet, _ = LoyaltyWallet.objects.get_or_create(user=request.user)
    available_points = wallet.points
    discount = 0.00
    points_to_redeem = 0

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        
        points_input = request.POST.get('redeem_points', '0')
        try:
            points_input = int(points_input)
        except ValueError:
            points_input = 0
            
        if points_input > 0:
            if points_input > available_points:
                messages.error(request, "You don't have enough points.")
                return redirect('checkout')
            if points_input < loyalty_config.min_redemption_points:
                messages.error(request, f"Minimum points to redeem is {loyalty_config.min_redemption_points}.")
                return redirect('checkout')
                
            discount_value = float(points_input) * float(loyalty_config.point_value_in_currency)
            max_discount = float(total) * (float(loyalty_config.max_redemption_percent) / 100.0)
            
            if discount_value > max_discount:
                discount_value = max_discount
                points_input = int(discount_value / float(loyalty_config.point_value_in_currency))
                
            discount = round(discount_value, 2)
            points_to_redeem = points_input
            total = round(float(total) - discount, 2)

        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = total
            order.discount_amount = discount
            order.points_redeemed = points_to_redeem

            payment_method = form.cleaned_data.get('payment_method')
            
            # We always save as pending initially until stripe webhook or success callback confirms
            order.payment_status = 'Pending'
            order.save()

            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price=item.product.price,
                )
                # Deduct stock
                if item.product.stock >= item.quantity:
                    item.product.stock -= item.quantity
                    item.product.save(update_fields=['stock'])

            if points_to_redeem > 0:
                wallet.redeem_points(points_to_redeem, order=order, description=f"Redeemed on Order {order.order_id}")

            cart_items.delete()

            if payment_method == 'UPI':
                # Setup Razorpay Order
                amount_in_paise = int(total * 100)
                currency = 'INR'
                
                razorpay_order = razorpay_client.order.create({
                    'amount': amount_in_paise,
                    'currency': currency,
                    'receipt': order.order_id,
                    'payment_capture': '1'
                })
                
                # We can store the Razorpay order ID in transaction_id for now
                order.transaction_id = razorpay_order['id']
                order.save(update_fields=['transaction_id'])
                
                context = {
                    'order': order,
                    'razorpay_order_id': razorpay_order['id'],
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                    'amount': amount_in_paise,
                    'currency': currency,
                    'callback_url': request.build_absolute_uri(reverse('payment_callback'))
                }
                return render(request, 'store/payment_razorpay.html', context)

            elif payment_method == 'Card':
                # Setup Stripe Checkout
                host = request.get_host()
                success_url = f"http://{host}{reverse('payment_success', args=[order.order_id])}"
                cancel_url = f"http://{host}{reverse('payment_cancel', args=[order.order_id])}"

                # Construct line items
                line_items = []
                for item in order.items.all():
                    line_items.append({
                        'price_data': {
                            'currency': 'inr', 
                            'unit_amount': int(item.price * 100),
                            'product_data': {
                                'name': item.product_name,
                            },
                        },
                        'quantity': item.quantity,
                    })

                # Add tax as a line item if greater than 0
                if tax > 0:
                    line_items.append({
                        'price_data': {
                            'currency': 'inr',
                            'unit_amount': int(tax * 100),
                            'product_data': {
                                'name': 'Tax',
                            },
                        },
                        'quantity': 1,
                    })

                try:
                    checkout_session = stripe.checkout.Session.create(
                        payment_method_types=['card'],
                        line_items=line_items,
                        mode='payment',
                        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                        cancel_url=cancel_url,
                        client_reference_id=order.order_id,
                    )
                    return redirect(checkout_session.url)
                except Exception as e:
                    messages.error(request, f"Stripe error: {str(e)}")
                    return redirect('checkout')

            
            messages.success(request, f'Order placed successfully! Order ID: {order.order_id}')
            award_points(order)  # Award 1 point for COD orders immediately
            send_order_confirmation_email.delay(request.user.email, order.order_id)
            return redirect('order_confirmation', order_id=order.order_id)
    else:
        initial = {}
        try:
            profile = request.user.userprofile
            initial = {
                'shipping_name': request.user.get_full_name() or request.user.username,
                'shipping_phone': profile.phone,
                'shipping_address': profile.address,
                'shipping_city': profile.city,
                'shipping_state': profile.state,
                'shipping_pincode': profile.pincode,
            }
        except UserProfile.DoesNotExist:
            initial['shipping_name'] = request.user.get_full_name() or request.user.username
        form = CheckoutForm(initial=initial)

    return render(request, 'store/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'discount': discount,
        'total': total,
        'wallet': wallet,
        'loyalty_config': loyalty_config,
    })


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    tracking_steps = ['Pending', 'Processing', 'Shipped', 'Delivered']
    return render(request, 'store/order_confirmation.html', {'order': order, 'tracking_steps': tracking_steps})


@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    session_id = request.GET.get('session_id')
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                order.payment_status = 'Paid'
                order.transaction_id = session_id
                order.save()
                award_points(order)
                send_payment_notification_email.delay(order.user.email, order.order_id, 'Success')
                send_order_confirmation_email.delay(order.user.email, order.order_id)
                messages.success(request, 'Payment successful! Your order is complete.')
        except Exception as e:
            messages.error(request, 'Could not verify payment status.')
            
    return redirect('order_confirmation', order_id=order.order_id)


@login_required
def payment_cancel(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    order.status = 'Cancelled'
    order.payment_status = 'Failed'
    order.save()
    messages.warning(request, 'Payment was cancelled. Your order has been marked as cancelled.')
    return redirect('order_history')


@csrf_exempt
def payment_callback(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
        razorpay_order_id = request.POST.get('razorpay_order_id', '')
        razorpay_signature = request.POST.get('razorpay_signature', '')

        try:
            # Verify the payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            razorpay_client.utility.verify_payment_signature(params_dict)

            # Find the order
            order = get_object_or_404(Order, transaction_id=razorpay_order_id)
            order.payment_status = 'Paid'
            order.status = 'Processing'  # Or whatever makes sense
            order.save()
            award_points(order)
            send_payment_notification_email.delay(order.user.email, order.order_id, 'Success')
            send_order_confirmation_email.delay(order.user.email, order.order_id)

            messages.success(request, 'Payment successful! Your order is complete.')
            return redirect('order_confirmation', order_id=order.order_id)
        except razorpay.errors.SignatureVerificationError:
            messages.error(request, 'Payment verification failed. Please try again.')
            return redirect('order_history')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('order_history')
    else:
        return redirect('home')



@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    tracking_steps = ['Pending', 'Processing', 'Shipped', 'Delivered']
    return render(request, 'store/order_detail.html', {'order': order, 'tracking_steps': tracking_steps})


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            request.user.first_name = d['first_name']
            request.user.last_name = d['last_name']
            request.user.email = d['email']
            request.user.save()
            profile.phone = d['phone']
            profile.address = d['address']
            profile.city = d['city']
            profile.state = d['state']
            profile.pincode = d['pincode']
            profile.save()
            messages.success(request, 'Profile updated successfully! ✅')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': profile.phone,
            'address': profile.address,
            'city': profile.city,
            'state': profile.state,
            'pincode': profile.pincode,
        })

    orders = Order.objects.filter(user=request.user)
    wallet, _ = LoyaltyWallet.objects.get_or_create(user=request.user)
    loyalty_transactions = wallet.transactions.all()[:20]
    return render(request, 'store/profile.html', {
        'form': form,
        'profile': profile,
        'total_orders': orders.count(),
        'delivered': orders.filter(status='Delivered').count(),
        'pending': orders.filter(status__in=['Pending', 'Processing', 'Shipped']).count(),
        'recent_orders': orders[:5],
        'wallet': wallet,
        'loyalty_transactions': loyalty_transactions,
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            phone = form.cleaned_data.get('phone', '')
            UserProfile.objects.create(user=user, phone=phone)
            login(request, user)
            send_registration_email.delay(user.email, user.first_name or user.username)
            messages.success(request, f'Welcome to ShopVerse, {user.first_name}! 🎉')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'store/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
            if user:
                try:
                    if user.userprofile.is_blocked:
                        messages.error(request, 'Your account has been blocked. Contact support.')
                        return render(request, 'store/login.html')
                except UserProfile.DoesNotExist:
                    pass
                login(request, user)
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password.')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
    return render(request, 'store/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def loyalty_view(request):
    wallet, _ = LoyaltyWallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.select_related('order').all()[:20]

    # Determine current tier
    pts = wallet.points
    if pts >= 3000:
        current_tier = 'Platinum'
        next_tier = None
        next_tier_pts = 3000
        tier_progress = 100
    elif pts >= 1500:
        current_tier = 'Gold'
        next_tier = 'Platinum'
        next_tier_pts = 3000
        tier_progress = round((pts - 1500) / (3000 - 1500) * 100)
    elif pts >= 500:
        current_tier = 'Silver'
        next_tier = 'Gold'
        next_tier_pts = 1500
        tier_progress = round((pts - 500) / (1500 - 500) * 100)
    else:
        current_tier = 'Bronze'
        next_tier = 'Silver'
        next_tier_pts = 500
        tier_progress = round(pts / 500 * 100)

    # Simple referral code based on username
    referral_code = f"{request.user.username.upper()}-SV{request.user.pk:04d}"

    return render(request, 'store/loyalty.html', {
        'wallet': wallet,
        'loyalty_transactions': transactions,
        'current_tier': current_tier,
        'next_tier': next_tier,
        'next_tier_pts': next_tier_pts,
        'tier_progress': tier_progress,
        'referral_code': referral_code,
    })

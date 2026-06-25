from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.utils import timezone
from store.models import Product, Category, Order, OrderItem, UserProfile, LoyaltyWallet, LoyaltyConfig
from .forms import ProductForm, CategoryForm, OrderStatusForm, LoyaltyConfigForm
import json
import csv
from datetime import timedelta
from functools import wraps
from store.tasks import send_shipping_update_email, send_delivery_confirmation_email


def admin_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── AUTH ───────────────────────────────────────────────
def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        try:
            user_obj = User.objects.get(email=email, is_staff=True)
            user = authenticate(request, username=user_obj.username, password=password)
            if user and user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Invalid credentials.')
        except User.DoesNotExist:
            messages.error(request, 'Admin account not found.')
    return render(request, 'adminpanel/login.html')


def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')


# ─── DASHBOARD ─────────────────────────────────────────
@admin_login_required
def dashboard(request):
    total_products = Product.objects.count()
    total_customers = User.objects.filter(is_staff=False).count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        payment_status='Paid'
    ).aggregate(t=Sum('total_amount'))['t'] or 0

    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]

    # Last 7 days chart
    today = timezone.localdate()
    dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    sales_data, labels, order_counts = [], [], []
    for d in dates:
        rev = Order.objects.filter(
            created_at__date=d, payment_status='Paid'
        ).aggregate(t=Sum('total_amount'))['t'] or 0
        cnt = Order.objects.filter(created_at__date=d).count()
        sales_data.append(float(rev))
        order_counts.append(cnt)
        labels.append(d.strftime('%b %d'))

    # Top products
    top_products = OrderItem.objects.values(
        'product__name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_rev=Sum('price')
    ).order_by('-total_qty')[:5]

    return render(request, 'adminpanel/dashboard.html', {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'sales_data': json.dumps(sales_data),
        'order_counts': json.dumps(order_counts),
        'labels': json.dumps(labels),
        'top_products': top_products,
    })


# ─── PRODUCTS ──────────────────────────────────────────
@admin_login_required
def product_list(request):
    products = Product.objects.select_related('category').order_by('-created_at')
    query = request.GET.get('q', '')
    if query:
        products = products.filter(name__icontains=query)
    cat_filter = request.GET.get('category', '')
    if cat_filter:
        products = products.filter(category__slug=cat_filter)
    categories = Category.objects.all()
    return render(request, 'adminpanel/products.html', {
        'products': products,
        'categories': categories,
        'query': query,
        'cat_filter': cat_filter,
    })


@admin_login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('admin_products')
    else:
        form = ProductForm()
    return render(request, 'adminpanel/add_edit_product.html', {'form': form, 'action': 'Add'})


@admin_login_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('admin_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'adminpanel/add_edit_product.html', {'form': form, 'action': 'Edit', 'product': product})


@admin_login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted.')
        return redirect('admin_products')
    return render(request, 'adminpanel/confirm_delete.html', {'obj': product, 'type': 'Product'})


# ─── ORDERS ────────────────────────────────────────────
@admin_login_required
def order_list(request):
    orders = Order.objects.select_related('user').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    status_list = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    return render(request, 'adminpanel/orders.html', {
        'orders': orders,
        'status_filter': status_filter,
        'status_list': status_list,
    })


@admin_login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    form = OrderStatusForm(initial={'status': order.status})
    if request.method == 'POST':
        form = OrderStatusForm(request.POST)
        if form.is_valid():
            old_status = order.status
            order.status = form.cleaned_data['status']
            if order.status == 'Cancelled':
                # Restore stock
                for item in order.items.all():
                    if item.product:
                        item.product.stock += item.quantity
                        item.product.save(update_fields=['stock'])
                        
                # Handle Loyalty Points on Cancellation
                if old_status != 'Cancelled':
                    wallet, _ = LoyaltyWallet.objects.get_or_create(user=order.user)
                    if order.points_earned > 0:
                        wallet.deduct_earned_points(order.points_earned, order=order, description=f"Reversed for Cancelled Order {order.order_id}")
                        order.points_earned = 0
                    if order.points_redeemed > 0:
                        wallet.refund_points(order.points_redeemed, order=order, description=f"Refunded for Cancelled Order {order.order_id}")
                        order.points_redeemed = 0
                    order.save(update_fields=['points_earned', 'points_redeemed'])

            order.save()

            if old_status != order.status:
                if order.status == 'Shipped':
                    send_shipping_update_email.delay(order.user.email, order.order_id)
                elif order.status == 'Delivered':
                    send_delivery_confirmation_email.delay(order.user.email, order.order_id)

            messages.success(request, f'Order status updated to {order.status}.')
            return redirect('admin_order_detail', order_id=order_id)
    tracking_steps = ['Pending', 'Processing', 'Shipped', 'Delivered']
    return render(request, 'adminpanel/order_detail.html', {'order': order, 'form': form, 'tracking_steps': tracking_steps})


# ─── USERS ─────────────────────────────────────────────
@admin_login_required
def user_list(request):
    users = User.objects.filter(is_staff=False).select_related('userprofile').order_by('-date_joined')
    query = request.GET.get('q', '')
    if query:
        users = users.filter(
            username__icontains=query
        ) | User.objects.filter(email__icontains=query, is_staff=False)
    for user in users:
        user.order_count = Order.objects.filter(user=user).count()
    return render(request, 'adminpanel/users.html', {'users': users, 'query': query})


@admin_login_required
def toggle_user_block(request, pk):
    user = get_object_or_404(User, pk=pk, is_staff=False)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.is_blocked = not profile.is_blocked
    profile.save()
    status = 'blocked' if profile.is_blocked else 'activated'
    messages.success(request, f'User {user.username} has been {status}.')
    return redirect('admin_users')


@admin_login_required
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk, is_staff=False)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('admin_users')
    return render(request, 'adminpanel/confirm_delete.html', {'obj': user, 'type': 'User'})


# ─── LOYALTY SETTINGS ──────────────────────────────────
@admin_login_required
def loyalty_settings(request):
    config = LoyaltyConfig.get_solo()
    if request.method == 'POST':
        form = LoyaltyConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Loyalty settings updated successfully!')
            return redirect('admin_loyalty_settings')
    else:
        form = LoyaltyConfigForm(instance=config)
    return render(request, 'adminpanel/loyalty_settings.html', {'form': form})


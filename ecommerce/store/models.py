from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return f'https://picsum.photos/seed/product{self.pk}/400/400'


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('UPI', 'UPI Payment'),
        ('Card', 'Credit/Debit Card'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_id = models.CharField(max_length=20, unique=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='COD')
    transaction_id = models.CharField(max_length=50, blank=True)

    # Loyalty Points
    points_earned = models.PositiveIntegerField(default=0)
    points_redeemed = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Shipping Details
    shipping_name = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=15)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_id} by {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"SV{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        colors = {
            'Pending': 'warning',
            'Processing': 'info',
            'Shipped': 'primary',
            'Delivered': 'success',
            'Cancelled': 'danger',
        }
        return colors.get(self.status, 'secondary')

    @property
    def payment_color(self):
        colors = {
            'Pending': 'warning',
            'Paid': 'success',
            'Failed': 'danger',
            'Refunded': 'info',
        }
        return colors.get(self.payment_status, 'secondary')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)  # Store name at time of order
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity

class LoyaltyConfig(models.Model):
    points_per_currency = models.DecimalField(max_digits=10, decimal_places=2, default=200.00, help_text="Amount to spend to earn 1 point")
    min_redemption_points = models.PositiveIntegerField(default=50, help_text="Minimum points required to redeem")
    max_redemption_percent = models.DecimalField(max_digits=5, decimal_places=2, default=50.00, help_text="Max percentage of an order total that can be discounted")
    point_value_in_currency = models.DecimalField(max_digits=10, decimal_places=2, default=1.00, help_text="Currency value of 1 point when redeeming")
    
    class Meta:
        verbose_name = 'Loyalty Configuration'
        verbose_name_plural = 'Loyalty Configuration'

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and LoyaltyConfig.objects.exists():
            return
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj


class LoyaltyWallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='loyalty_wallet')
    points = models.PositiveIntegerField(default=0)
    total_earned = models.PositiveIntegerField(default=0)
    total_redeemed = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.points} Points"

    def earn_points(self, amount, order=None, description=""):
        self.points += amount
        self.total_earned += amount
        self.save()
        LoyaltyTransaction.objects.create(
            wallet=self, order=order, points=amount, transaction_type='Earned', description=description
        )

    def redeem_points(self, amount, order=None, description=""):
        if self.points >= amount:
            self.points -= amount
            self.total_redeemed += amount
            self.save()
            LoyaltyTransaction.objects.create(
                wallet=self, order=order, points=-amount, transaction_type='Redeemed', description=description
            )
            return True
        return False

    def refund_points(self, amount, order=None, description=""):
        self.points += amount
        self.save()
        LoyaltyTransaction.objects.create(
            wallet=self, order=order, points=amount, transaction_type='Refunded', description=description
        )

    def deduct_earned_points(self, amount, order=None, description=""):
        self.points = max(0, self.points - amount)  # Prevent negative points
        self.total_earned = max(0, self.total_earned - amount)
        self.save()
        LoyaltyTransaction.objects.create(
            wallet=self, order=order, points=-amount, transaction_type='Adjusted', description=description
        )


class LoyaltyTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('Earned', 'Earned'),
        ('Redeemed', 'Redeemed'),
        ('Adjusted', 'Adjusted'),
        ('Expired', 'Expired'),
        ('Refunded', 'Refunded'),
    ]

    wallet = models.ForeignKey(LoyaltyWallet, on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='loyalty_transactions')
    points = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.user.username} - {self.transaction_type} {self.points}"

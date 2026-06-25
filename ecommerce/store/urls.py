from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),

    # Checkout & Orders
    path('checkout/', views.checkout, name='checkout'),
    path('payment/success/<str:order_id>/', views.payment_success, name='payment_success'),
    path('payment/cancel/<str:order_id>/', views.payment_cancel, name='payment_cancel'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('order/confirmation/<str:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),

    # Account
    path('profile/', views.profile_view, name='profile'),
    path('loyalty/', views.loyalty_view, name='loyalty'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]

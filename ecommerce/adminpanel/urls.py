from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_login_view, name='admin_login'),
    path('logout/', views.admin_logout_view, name='admin_logout'),
    path('dashboard/', views.dashboard, name='admin_dashboard'),

    # Products
    path('products/', views.product_list, name='admin_products'),
    path('products/add/', views.add_product, name='admin_add_product'),
    path('products/edit/<int:pk>/', views.edit_product, name='admin_edit_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='admin_delete_product'),

    # Orders
    path('orders/', views.order_list, name='admin_orders'),
    path('orders/<str:order_id>/', views.order_detail_view, name='admin_order_detail'),

    # Users
    path('users/', views.user_list, name='admin_users'),
    path('users/toggle/<int:pk>/', views.toggle_user_block, name='admin_toggle_user'),
    path('users/delete/<int:pk>/', views.delete_user, name='admin_delete_user'),

    # Settings
    path('loyalty-settings/', views.loyalty_settings, name='admin_loyalty_settings'),
]

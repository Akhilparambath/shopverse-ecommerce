from django import forms
from store.models import Product, Category, LoyaltyConfig


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'price', 'stock', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class OrderStatusForm(forms.Form):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class LoyaltyConfigForm(forms.ModelForm):
    class Meta:
        model = LoyaltyConfig
        fields = ['points_per_currency', 'min_redemption_points', 'max_redemption_percent', 'point_value_in_currency']
        widgets = {
            'points_per_currency': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_redemption_points': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_redemption_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'point_value_in_currency': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


from django import forms
from .models import Item, Category, Delivery


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            'name', 'description', 'category', 'quantity',
            'price', 'expiring_date', 'vendor'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'expiring_date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'vendor': forms.Select(attrs={'class': 'form-control'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name',
            }),
        }
        labels = {'name': 'Category Name'}


class DeliveryCreateForm(forms.ModelForm):
    """
    Form for manually creating a delivery from a Sale.
    Only the sale selector, shipping address, and phone are editable.
    Customer / total / items are shown via AJAX as read-only info.
    """
    class Meta:
        model = Delivery
        fields = ['sale', 'phone_number', 'location']
        widgets = {
            'sale': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_sale',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. +254712345678',
                'id': 'id_phone_number',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Shipping / delivery address',
                'id': 'id_location',
            }),
        }
        labels = {
            'sale': 'Sale',
            'phone_number': 'Contact Phone',
            'location': 'Delivery Address',
        }


class DeliveryUpdateForm(forms.ModelForm):
    """
    Form for updating delivery contact info and status.
    The sale link is intentionally excluded — it cannot be changed after creation.
    """
    class Meta:
        model = Delivery
        fields = ['status', 'phone_number', 'location', 'email']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. +254712345678',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Delivery address',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'customer@example.com',
            }),
        }
        labels = {
            'status': 'Delivery Status',
            'phone_number': 'Contact Phone',
            'location': 'Delivery Address',
            'email': 'Contact Email',
        }


# Legacy form kept for any existing code that imports DeliveryForm
DeliveryForm = DeliveryUpdateForm

from django import forms
from .models import Item, Category, Delivery


class ItemForm(forms.ModelForm):
    """
    A form for creating or updating an Item in the inventory.
    """
    class Meta:
        model = Item
        fields = [
            'name',
            'description',
            'category',
            'quantity',
            'price',
            'expiring_date',
            'vendor'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2
                }
            ),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01'
                }
            ),
            'expiring_date': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local'
                }
            ),
            'vendor': forms.Select(attrs={'class': 'form-control'}),
        }


class CategoryForm(forms.ModelForm):
    """
    A form for creating or updating category.
    """
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name',
                'aria-label': 'Category Name'
            }),
        }
        labels = {
            'name': 'Category Name',
        }


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = [
            'invoice',
            'customer',
            'item',
            'customer_name',
            'email',
            'phone_number',
            'location',
            'date',
            'is_delivered'
        ]
        widgets = {
            'invoice': forms.Select(attrs={
                'class': 'form-control', 'id': 'id_invoice',
            }),
            'customer': forms.Select(attrs={
                'class': 'form-control', 'id': 'id_customer',
            }),
            'item': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Select item',
                'id': 'id_item',
            }),
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter customer name',
                'id': 'id_customer_name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'customer@example.com',
                'id': 'id_email',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number',
                'id': 'id_phone_number',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter delivery location',
                'id': 'id_location',
            }),
            'date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'placeholder': 'Select delivery date and time',
                'type': 'datetime-local'
            }),
            'is_delivered': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'label': 'Mark as delivered',
            }),
        }

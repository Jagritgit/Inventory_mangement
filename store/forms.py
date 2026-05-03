from django import forms
from .models import Item, Category, Delivery


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            'name', 'sku', 'description', 'category', 'quantity',
            'price', 'cost_price', 'low_stock_threshold',
            'image', 'expiring_date', 'vendor',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SKU-001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
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
    Supports two creation modes:
      - 'sale'   : user picks a Sale; customer details auto-fill via AJAX.
      - 'manual' : no Sale; user enters customer_name, phone, address by hand.

    The `mode` field is a hidden input driven by the JS toggle in the template.
    """

    MODE_SALE   = 'sale'
    MODE_MANUAL = 'manual'

    mode = forms.ChoiceField(
        choices=[('sale', 'From Sale'), ('manual', 'Manual')],
        initial='sale',
        widget=forms.HiddenInput(attrs={'id': 'id_mode'}),
    )

    class Meta:
        model = Delivery
        fields = ['sale', 'customer_name', 'phone_number', 'location']
        widgets = {
            'sale': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_sale',
            }),
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name',
                'id': 'id_customer_name',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 9876543210',
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
            'customer_name': 'Customer Name',
            'phone_number': 'Contact Phone',
            'location': 'Delivery Address',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Both sale and customer_name are optional at the field level;
        # cross-field validation happens in clean().
        self.fields['sale'].required = False
        self.fields['customer_name'].required = False
        self.fields['phone_number'].required = False
        self.fields['location'].required = False

    def clean(self):
        data = super().clean()
        mode = data.get('mode', self.MODE_SALE)
        sale = data.get('sale')
        customer_name = (data.get('customer_name') or '').strip()

        if mode == self.MODE_SALE:
            if not sale:
                self.add_error('sale', 'Please select a sale.')
        else:
            # Manual mode — sale must be empty, customer_name is required
            data['sale'] = None
            if not customer_name:
                self.add_error('customer_name', 'Customer name is required.')

        return data


class DeliveryUpdateForm(forms.ModelForm):
    """
    Form for editing an existing delivery.
    The sale link cannot be changed after creation.
    """
    class Meta:
        model = Delivery
        fields = ['status', 'phone_number', 'location', 'email']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 9876543210',
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


# Legacy alias
DeliveryForm = DeliveryUpdateForm

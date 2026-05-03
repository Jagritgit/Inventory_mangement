from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile, Customer, Vendor


class CreateUserForm(UserCreationForm):
    """Form for creating a new user with an email field."""
    email = forms.EmailField()

    class Meta:
        """Meta options for the CreateUserForm."""
        model = User
        fields = [
            'username',
            'email',
            'password1',
            'password2'
        ]


class UserUpdateForm(forms.ModelForm):
    """Form for updating existing user information."""
    class Meta:
        """Meta options for the UserUpdateForm."""
        model = User
        fields = [
            'username',
            'email'
        ]


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information."""
    class Meta:
        """Meta options for the ProfileUpdateForm."""
        model = Profile
        fields = [
            'telephone',
            'email',
            'first_name',
            'last_name',
            'profile_picture'
        ]


class CustomerForm(forms.ModelForm):
    """Form for creating/updating customer information."""
    class Meta:
        model = Customer
        fields = [
            'first_name',
            'last_name',
            'address',
            'email',
            'phone',
            'loyalty_points'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter address',
                'rows': 3
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'loyalty_points': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter loyalty points'
            }),
        }


class VendorForm(forms.ModelForm):
    """Form for creating/updating vendor information."""
    class Meta:
        model  = Vendor
        fields = ['name', 'company_name', 'phone_number', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Contact person name',
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Company / business name',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 9876543210',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'vendor@example.com',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Full address',
            }),
        }

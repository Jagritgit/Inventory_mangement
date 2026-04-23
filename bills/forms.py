from django import forms
from .models import Bill


class BillForm(forms.ModelForm):
    """ModelForm for Bill with bootstrap styling."""

    class Meta:
        model = Bill
        fields = [
            "vendor", "institution_name", "phone_number", "email",
            "address", "description", "payment_details",
            "item", "quantity", "cost_price", "tax",
            "amount", "status",
        ]
        widgets = {
            "vendor":           forms.Select(attrs={"class": "form-control"}),
            "institution_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number":     forms.NumberInput(attrs={"class": "form-control"}),
            "email":            forms.EmailInput(attrs={"class": "form-control"}),
            "address":          forms.TextInput(attrs={"class": "form-control"}),
            "description":      forms.TextInput(attrs={"class": "form-control"}),
            "payment_details":  forms.TextInput(attrs={"class": "form-control"}),
            "item":             forms.Select(attrs={"class": "form-control"}),
            "quantity":         forms.NumberInput(attrs={"class": "form-control"}),
            "cost_price":       forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "tax":              forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "amount":           forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "status":           forms.Select(attrs={"class": "form-control"}),
        }

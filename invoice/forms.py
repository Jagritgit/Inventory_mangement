from django import forms
from .models import Invoice


class InvoiceHeaderForm(forms.ModelForm):
    """Form for the Invoice header fields only. Items are handled separately."""

    class Meta:
        model = Invoice
        fields = [
            "customer", "customer_name", "contact_number", "customer_email",
            "shipping_address", "due_date", "shipping", "status",
        ]
        widgets = {
            "customer":         forms.Select(attrs={"class": "form-control", "id": "id_customer"}),
            "customer_name":    forms.TextInput(attrs={"class": "form-control", "id": "id_customer_name"}),
            "contact_number":   forms.TextInput(attrs={"class": "form-control", "id": "id_contact_number"}),
            "customer_email":   forms.EmailInput(attrs={"class": "form-control", "id": "id_customer_email"}),
            "shipping_address": forms.TextInput(attrs={"class": "form-control", "id": "id_shipping_address"}),
            "due_date":         forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "shipping":         forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "id": "id_shipping"}),
            "status":           forms.Select(attrs={"class": "form-control"}),
        }

    def clean_shipping(self):
        s = self.cleaned_data.get("shipping") or 0
        if s < 0:
            raise forms.ValidationError("Shipping cannot be negative.")
        return s

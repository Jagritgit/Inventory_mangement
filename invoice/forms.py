from django import forms
from .models import Invoice


class InvoiceForm(forms.ModelForm):
    """ModelForm for Invoice with bootstrap styling."""

    class Meta:
        model = Invoice
        fields = [
            "customer", "customer_name", "contact_number", "due_date",
            "item", "price_per_item", "quantity", "shipping", "status",
        ]
        widgets = {
            "customer":        forms.Select(attrs={"class": "form-control"}),
            "customer_name":   forms.TextInput(attrs={"class": "form-control"}),
            "contact_number":  forms.TextInput(attrs={"class": "form-control"}),
            "due_date":        forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "item":            forms.Select(attrs={"class": "form-control"}),
            "price_per_item":  forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "quantity":        forms.NumberInput(attrs={"class": "form-control", "step": "1"}),
            "shipping":        forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "status":          forms.Select(attrs={"class": "form-control"}),
        }

    def clean_quantity(self):
        q = self.cleaned_data.get("quantity") or 0
        if q < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return q

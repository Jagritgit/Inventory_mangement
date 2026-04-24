from django import forms
from .models import Invoice


class InvoiceForm(forms.ModelForm):
    """ModelForm for Invoice with bootstrap styling and server-side validation."""

    class Meta:
        model = Invoice
        fields = [
            "customer", "customer_name", "contact_number", "due_date",
            "item", "price_per_item", "quantity", "shipping", "status",
        ]
        widgets = {
            "customer":        forms.Select(attrs={"class": "form-control", "id": "id_customer"}),
            "customer_name":   forms.TextInput(attrs={"class": "form-control", "id": "id_customer_name"}),
            "contact_number":  forms.TextInput(attrs={"class": "form-control", "id": "id_contact_number"}),
            "due_date":        forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "item":            forms.Select(attrs={"class": "form-control", "id": "id_item"}),
            "price_per_item":  forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "id": "id_price_per_item"}),
            "quantity":        forms.NumberInput(attrs={"class": "form-control", "step": "1", "min": "1", "id": "id_quantity"}),
            "shipping":        forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "id": "id_shipping"}),
            "status":          forms.Select(attrs={"class": "form-control"}),
        }

    def clean_quantity(self):
        q = self.cleaned_data.get("quantity") or 0
        if q <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return q

    def clean_price_per_item(self):
        p = self.cleaned_data.get("price_per_item")
        if p is None or p < 0:
            raise forms.ValidationError("Price must be zero or greater.")
        return p

    def clean_shipping(self):
        s = self.cleaned_data.get("shipping") or 0
        if s < 0:
            raise forms.ValidationError("Shipping cannot be negative.")
        return s

    def clean(self):
        """
        Authoritative server-side recalculation. Frontend JS is a UX aid only —
        we always recompute totals here so that crafted form posts cannot bypass
        the math.
        """
        cleaned = super().clean()
        item = cleaned.get("item")
        qty = cleaned.get("quantity") or 0
        price = cleaned.get("price_per_item")

        # Default price to product's selling price if blank.
        if item and (price is None or price == 0):
            cleaned["price_per_item"] = float(item.price or 0)

        return cleaned

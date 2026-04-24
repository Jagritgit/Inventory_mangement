from django import forms
from .models import Bill


class BillForm(forms.ModelForm):
    """ModelForm for Bill with bootstrap styling and server-side validation."""

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
            "item":             forms.Select(attrs={"class": "form-control", "id": "id_item"}),
            "quantity":         forms.NumberInput(attrs={"class": "form-control", "min": "0", "id": "id_quantity"}),
            "cost_price":       forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "id": "id_cost_price"}),
            "tax":              forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "id": "id_tax"}),
            "amount":           forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "id": "id_amount"}),
            "status":           forms.Select(attrs={"class": "form-control"}),
        }

    def clean_quantity(self):
        q = self.cleaned_data.get("quantity") or 0
        if q < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return q

    def clean_cost_price(self):
        p = self.cleaned_data.get("cost_price") or 0
        if p < 0:
            raise forms.ValidationError("Cost price cannot be negative.")
        return p

    def clean_tax(self):
        t = self.cleaned_data.get("tax") or 0
        if t < 0:
            raise forms.ValidationError("Tax cannot be negative.")
        return t

    def clean(self):
        """
        Authoritative server-side recalculation:
            amount = (quantity × cost_price) + tax
        Frontend JS is a UX aid only.
        """
        cleaned = super().clean()
        item = cleaned.get("item")
        qty = cleaned.get("quantity") or 0
        cost = cleaned.get("cost_price")
        tax = cleaned.get("tax") or 0

        # Default cost to product's stored cost_price if blank/zero and item set.
        if item and (cost is None or cost == 0):
            cost = float(item.cost_price or 0)
            cleaned["cost_price"] = cost
        cost = cost or 0

        # Always recompute amount on the server so the user can't tamper with it.
        cleaned["amount"] = round(float(qty) * float(cost) + float(tax), 2)
        return cleaned

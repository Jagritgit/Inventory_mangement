from django import forms
from django.forms import inlineformset_factory

from .models import PurchaseOrder, PurchaseOrderItem, PurchaseBill, PurchaseBillItem


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model  = PurchaseOrder
        fields = ['vendor', 'expected_date', 'status', 'notes']
        widgets = {
            'vendor':        forms.Select(attrs={'class': 'form-control'}),
            'expected_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status':        forms.Select(attrs={'class': 'form-control'}),
            'notes':         forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model  = PurchaseOrderItem
        fields = ['product', 'quantity', 'price']
        widgets = {
            'product':  forms.Select(attrs={'class': 'form-control item-product'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control item-qty', 'min': 1}),
            'price':    forms.NumberInput(attrs={'class': 'form-control item-price', 'step': '0.01', 'min': 0}),
        }


PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


# ── Purchase Bill (manual creation) ──────────────────────────────────────────

class PurchaseBillForm(forms.ModelForm):
    class Meta:
        model  = PurchaseBill
        fields = ['vendor', 'notes']
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-control'}),
            'notes':  forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                            'placeholder': 'Optional notes…'}),
        }


class PurchaseBillItemForm(forms.ModelForm):
    class Meta:
        model  = PurchaseBillItem
        fields = ['product', 'quantity', 'cost_price']
        widgets = {
            'product':    forms.Select(attrs={'class': 'form-control item-product'}),
            'quantity':   forms.NumberInput(attrs={'class': 'form-control item-qty',
                                                   'min': 1, 'value': 1}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control item-price',
                                                   'step': '0.01', 'min': 0}),
        }


PurchaseBillItemFormSet = inlineformset_factory(
    PurchaseBill,
    PurchaseBillItem,
    form=PurchaseBillItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)

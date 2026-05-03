from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ('product', 'quantity', 'price')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInline]
    fields = (
        'customer_name', 'contact_number', 'customer_email',
        'shipping_address', 'due_date', 'shipping', 'status',
    )
    list_display = (
        'invoice_number', 'date', 'customer_name', 'contact_number',
        'grand_total', 'status',
    )
    readonly_fields = ()


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'product', 'quantity', 'price')

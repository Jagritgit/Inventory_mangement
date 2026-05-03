from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemInline(admin.TabularInline):
    model  = PurchaseOrderItem
    extra  = 1
    fields = ['product', 'quantity', 'price']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display  = ['order_number', 'vendor', 'status', 'total_amount', 'order_date']
    list_filter   = ['status']
    search_fields = ['order_number', 'vendor__name']
    inlines       = [PurchaseOrderItemInline]

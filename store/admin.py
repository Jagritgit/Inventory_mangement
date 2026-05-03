"""
Module: admin.py

Django admin configurations for managing categories, items, and deliveries.
"""

from django.contrib import admin
from .models import Category, Item, Delivery


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    ordering = ('name',)


class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'quantity', 'price', 'expiring_date', 'vendor'
    )
    search_fields = ('name', 'category__name', 'vendor__name')
    list_filter = ('category', 'vendor')
    ordering = ('name',)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'sale', 'status', 'customer_name',
        'shipped_date', 'delivered_date', 'is_delivered',
    )
    list_filter = ('status', 'is_delivered')
    search_fields = ('customer_name', 'sale__id')
    readonly_fields = ('shipped_date', 'delivered_date')
    ordering = ('-id',)


admin.site.register(Category, CategoryAdmin)
admin.site.register(Item, ItemAdmin)

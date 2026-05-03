"""
Module: models.py

Contains Django models for handling categories, items, and deliveries.
"""

import re

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.forms import model_to_dict
from django_extensions.db.fields import AutoSlugField
from accounts.models import Vendor


class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = AutoSlugField(unique=True, populate_from='name')

    def __str__(self):
        return f"Category: {self.name}"

    class Meta:
        verbose_name_plural = 'Categories'


class Item(models.Model):
    slug = AutoSlugField(unique=True, populate_from='name')
    name = models.CharField(max_length=50)
    sku = models.CharField(max_length=32, unique=True, null=True, blank=True)
    description = models.TextField(max_length=256)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    price = models.FloatField(default=0)
    cost_price = models.FloatField(default=0)

    expiring_date = models.DateTimeField(null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    def __str__(self):
        return (
            f"{self.name} - Category: {self.category}, "
            f"Quantity: {self.quantity}"
        )

    def get_absolute_url(self):
        return reverse('item-detail', kwargs={'slug': self.slug})

    def to_json(self):
        product = model_to_dict(self)
        product['id'] = self.id
        product['text'] = self.name
        product['category'] = self.category.name
        product['quantity'] = 1
        product['total_product'] = 0
        return product

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Items'


DELIVERY_STATUS = [
    ('PENDING',   'Pending'),
    ('SHIPPED',   'Shipped'),
    ('DELIVERED', 'Delivered'),
]


class Delivery(models.Model):
    """
    Represents a delivery linked to a Sale.

    Lifecycle:  PENDING → SHIPPED → DELIVERED
    Auto-created via post_save signal on Sale.
    Manual ad-hoc deliveries leave `sale` as NULL.
    """

    # --- sale link (new) ---
    sale = models.OneToOneField(
        'transactions.Sale',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='delivery',
        help_text="The Sale this delivery fulfils. NULL = manual delivery.",
    )

    # --- lifecycle (new) ---
    status = models.CharField(
        max_length=10,
        choices=DELIVERY_STATUS,
        default='PENDING',
        db_index=True,
    )
    shipped_date = models.DateTimeField(null=True, blank=True)
    delivered_date = models.DateTimeField(null=True, blank=True)

    # --- legacy fields kept for manual deliveries ---
    item = models.ForeignKey(
        Item, blank=True, null=True, on_delete=models.SET_NULL
    )
    invoice = models.ForeignKey(
        'invoice.Invoice', blank=True, null=True,
        on_delete=models.SET_NULL, related_name='deliveries'
    )
    customer = models.ForeignKey(
        'accounts.Customer', blank=True, null=True,
        on_delete=models.SET_NULL, related_name='deliveries'
    )
    customer_name = models.CharField(max_length=60, blank=True, null=True)
    email = models.EmailField(max_length=120, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateTimeField(null=True, blank=True)
    is_delivered = models.BooleanField(default=False, verbose_name='Is Delivered')

    class Meta:
        ordering = ['-id']

    # ── Indian phone helpers ──────────────────────────────────
    _PHONE_RE = re.compile(r'^[6-9]\d{9}$')

    def clean(self):
        super().clean()
        raw = (self.phone_number or '').strip()
        if not raw:
            return
        # Strip +91 or 91 prefix so we always validate the bare 10-digit number
        if raw.startswith('+91'):
            raw = raw[3:]
        elif raw.startswith('91') and len(raw) == 12:
            raw = raw[2:]
        if not self._PHONE_RE.match(raw):
            raise ValidationError({
                'phone_number': (
                    'Enter a valid 10-digit Indian mobile number '
                    '(starts with 6–9). Example: 9876543210'
                )
            })
        # Store the normalised 10-digit form so save() can prepend +91 once
        self.phone_number = raw

    def save(self, *args, **kwargs):
        raw = (self.phone_number or '').strip()
        if raw and not raw.startswith('+'):
            # Bare 10-digit number — prepend Indian country code
            self.phone_number = '+91' + raw
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        return {
            'PENDING':   'warning',
            'SHIPPED':   'primary',
            'DELIVERED': 'success',
        }.get(self.status, 'secondary')

    def __str__(self):
        if self.sale_id:
            return f"Delivery for Sale #{self.sale_id} [{self.status}]"
        return (
            f"Delivery of {self.item} to {self.customer_name} "
            f"[{self.status}]"
        )

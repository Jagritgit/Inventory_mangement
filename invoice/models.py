from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django_extensions.db.fields import AutoSlugField

from store.models import Item
from accounts.models import Customer


INVOICE_STATUS = [
    ("PAID", "Paid"),
    ("PENDING", "Pending"),
    ("CANCELLED", "Cancelled"),
]


class Invoice(models.Model):
    """
    Invoice (Sales side): money to RECEIVE from a customer.
    Reduces stock on create. Only Paid invoices contribute to revenue.
    """

    slug = AutoSlugField(unique=True, populate_from='date')
    invoice_number = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text="Auto-generated INV-YYYY-NNNN."
    )
    date = models.DateTimeField(auto_now=True, verbose_name='Date')
    due_date = models.DateField(null=True, blank=True)

    # Customer linkage. Keep customer_name string for display fallback / legacy rows.
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoices"
    )
    customer_name = models.CharField(max_length=60)
    contact_number = models.CharField(max_length=20)
    customer_email = models.EmailField(max_length=120, blank=True, null=True)
    shipping_address = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="Shipping Address"
    )

    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    price_per_item = models.FloatField(verbose_name='Price Per Item (₹)')
    quantity = models.FloatField(default=0.00)
    shipping = models.FloatField(verbose_name='Shipping & Handling', default=0.0)

    total = models.FloatField(verbose_name='Subtotal (₹)', editable=False, default=0)
    grand_total = models.FloatField(verbose_name='Grand Total (₹)', editable=False, default=0)

    status = models.CharField(
        max_length=10, choices=INVOICE_STATUS, default="PENDING"
    )

    class Meta:
        ordering = ["-id"]

    # ---------- numbering ----------
    @staticmethod
    def _next_invoice_number():
        year = timezone.now().year
        prefix = f"INV-{year}-"
        last = (
            Invoice.objects.filter(invoice_number__startswith=prefix)
            .order_by("-invoice_number").first()
        )
        if last and last.invoice_number:
            try:
                seq = int(last.invoice_number.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    # ---------- save with stock logic ----------
    def save(self, *args, **kwargs):
        """
        Stock logic:
          - On create (status != Cancelled): reduce stock by quantity, validate.
          - On update: reverse the previously-applied delta, then re-apply
            based on the new quantity/status.
          - Cancelled invoices never hold stock.
        """
        self.total = round(float(self.quantity) * float(self.price_per_item), 2)
        self.grand_total = round(self.total + float(self.shipping or 0), 2)
        if not self.invoice_number:
            self.invoice_number = self._next_invoice_number()

        with transaction.atomic():
            # Read previous state if updating
            if self.pk:
                prev = Invoice.objects.select_for_update().get(pk=self.pk)
                prev_qty = float(prev.quantity)
                prev_status = prev.status
                prev_item_id = prev.item_id
            else:
                prev_qty = 0.0
                prev_status = None
                prev_item_id = None

            new_qty = float(self.quantity)
            new_status = self.status

            # Compute stock changes per item
            item_deltas = {}  # item_id -> delta to apply (positive = restore)
            # Reverse previous reservation if it was non-cancelled
            if self.pk and prev_status != "CANCELLED":
                item_deltas[prev_item_id] = item_deltas.get(prev_item_id, 0) + prev_qty
            # Apply new reservation if non-cancelled
            if new_status != "CANCELLED":
                item_deltas[self.item_id] = item_deltas.get(self.item_id, 0) - new_qty

            for item_id, delta in item_deltas.items():
                if delta == 0:
                    continue
                item = Item.objects.select_for_update().get(pk=item_id)
                new_stock = item.quantity + int(delta)
                if new_stock < 0:
                    raise ValueError(
                        f"Insufficient stock for {item.name}: "
                        f"available {item.quantity}, requested {-int(delta)}."
                    )
                item.quantity = new_stock
                item.save()

            super().save(*args, **kwargs)

    # ---------- delete restores stock ----------
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.status != "CANCELLED" and self.item_id:
                item = Item.objects.select_for_update().get(pk=self.item_id)
                item.quantity += int(float(self.quantity))
                item.save()
            return super().delete(*args, **kwargs)

    @property
    def status_color(self):
        return {"PAID": "success", "PENDING": "warning", "CANCELLED": "danger"}.get(
            self.status, "secondary"
        )

    def __str__(self):
        return self.invoice_number or self.slug

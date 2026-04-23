from django.db import models, transaction
from django.utils import timezone
from autoslug import AutoSlugField

from store.models import Item
from accounts.models import Vendor


BILL_STATUS = [
    ("PAID", "Paid"),
    ("PENDING", "Pending"),
]


class Bill(models.Model):
    """
    Bill (Purchase side): money to PAY a supplier. Increases stock on create.
    Contributes to expenses regardless of status (expense is incurred when
    stock is received).
    """

    slug = AutoSlugField(unique=True, populate_from='date')
    bill_number = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text="Auto-generated BILL-YYYY-NNNN."
    )
    date = models.DateTimeField(auto_now_add=True, verbose_name='Date')

    # Vendor linkage. Keep institution_name as fallback for legacy/non-vendor bills.
    vendor = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bills"
    )
    institution_name = models.CharField(max_length=60)
    phone_number = models.PositiveBigIntegerField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    payment_details = models.CharField(max_length=255)

    # Optional product linkage. When `item` is set the bill behaves as a
    # purchase order and adjusts stock automatically.
    item = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bills"
    )
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.FloatField(default=0)
    tax = models.FloatField(default=0, help_text="GST / input tax (₹)")

    amount = models.FloatField(verbose_name='Total Amount Owing (₹)')
    status = models.CharField(
        max_length=10, choices=BILL_STATUS, default="PENDING"
    )

    class Meta:
        ordering = ["-id"]

    @staticmethod
    def _next_bill_number():
        year = timezone.now().year
        prefix = f"BILL-{year}-"
        last = (
            Bill.objects.filter(bill_number__startswith=prefix)
            .order_by("-bill_number").first()
        )
        if last and last.bill_number:
            try:
                seq = int(last.bill_number.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    def save(self, *args, **kwargs):
        """
        Stock logic:
          - On create with `item` set: increase Item.quantity by `quantity`.
          - On update with `item` set: reverse old delta then apply new.
          - On delete: reverse old delta if any.
        """
        if not self.bill_number:
            self.bill_number = self._next_bill_number()

        with transaction.atomic():
            prev_item_id = None
            prev_qty = 0
            if self.pk:
                prev = Bill.objects.select_for_update().get(pk=self.pk)
                prev_item_id = prev.item_id
                prev_qty = prev.quantity

            deltas = {}
            if prev_item_id and prev_qty:
                deltas[prev_item_id] = deltas.get(prev_item_id, 0) - prev_qty
            if self.item_id and self.quantity:
                deltas[self.item_id] = deltas.get(self.item_id, 0) + int(self.quantity)

            for item_id, delta in deltas.items():
                if delta == 0:
                    continue
                it = Item.objects.select_for_update().get(pk=item_id)
                new_stock = it.quantity + int(delta)
                if new_stock < 0:
                    raise ValueError(
                        f"Cannot reduce {it.name} below zero "
                        f"(would become {new_stock})."
                    )
                it.quantity = new_stock
                it.save()

            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.item_id and self.quantity:
                it = Item.objects.select_for_update().get(pk=self.item_id)
                new_stock = it.quantity - int(self.quantity)
                # If selling drove stock low we still allow the delete but clamp at 0.
                it.quantity = max(0, new_stock)
                it.save()
            return super().delete(*args, **kwargs)

    @property
    def status_color(self):
        return {"PAID": "success", "PENDING": "warning"}.get(self.status, "secondary")

    def __str__(self):
        return self.bill_number or self.institution_name

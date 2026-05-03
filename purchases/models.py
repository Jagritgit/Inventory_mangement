from django.db import models
from django.utils import timezone
from autoslug import AutoSlugField

from accounts.models import Vendor
from store.models import Item

PO_STATUS = [
    ('PENDING',  'Pending'),
    ('RECEIVED', 'Received'),
]


class PurchaseOrder(models.Model):
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    slug         = AutoSlugField(unique=True, populate_from='order_number')
    vendor       = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_orders'
    )
    order_date   = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(max_length=10, choices=PO_STATUS, default='PENDING')
    notes        = models.TextField(blank=True, null=True, max_length=500)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_updated = models.BooleanField(
        default=False,
        help_text='True after stock has been incremented on marking as Received.'
    )

    class Meta:
        ordering            = ['-order_date']
        verbose_name        = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'

    @staticmethod
    def _next_order_number():
        year   = timezone.now().year
        prefix = f"PO-{year}-"
        last   = (
            PurchaseOrder.objects
            .filter(order_number__startswith=prefix)
            .order_by('-order_number')
            .first()
        )
        if last and last.order_number:
            try:
                seq = int(last.order_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._next_order_number()
        super().save(*args, **kwargs)

    def recalculate_total(self):
        total = sum(i.line_total for i in self.items.all())
        PurchaseOrder.objects.filter(pk=self.pk).update(total_amount=total)
        self.total_amount = total

    @property
    def status_color(self):
        return {
            'PENDING':  'warning',
            'RECEIVED': 'success',
        }.get(self.status, 'secondary')

    def __str__(self):
        return self.order_number or f"PO-{self.pk}"


class PurchaseOrderItem(models.Model):
    order          = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product        = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='po_items')
    quantity       = models.PositiveIntegerField(default=1)
    price_per_item = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Price Per Item (₹)'
    )

    @property
    def line_total(self):
        return self.price_per_item * self.quantity

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"


# ── Purchase Bills ────────────────────────────────────────────────────────────

PBILL_STATUS = [
    ('UNPAID', 'Unpaid'),
    ('PAID',   'Paid'),
]


class PurchaseBill(models.Model):
    """
    A vendor invoice created from a PurchaseOrder.
    purchase_order=None only for legacy/manual entries.
    """
    bill_number    = models.CharField(max_length=25, unique=True, blank=True)
    slug           = AutoSlugField(unique=True, populate_from='bill_number')
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='purchase_bills'
    )
    vendor         = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='purchase_bills'
    )
    bill_date      = models.DateTimeField(auto_now_add=True)
    total_amount   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status         = models.CharField(max_length=10, choices=PBILL_STATUS, default='UNPAID')
    notes          = models.TextField(blank=True, null=True, max_length=500)

    class Meta:
        ordering            = ['-bill_date']
        verbose_name        = 'Purchase Bill'
        verbose_name_plural = 'Purchase Bills'

    @staticmethod
    def _next_bill_number():
        year   = timezone.now().year
        prefix = f"PBILL-{year}-"
        last   = (
            PurchaseBill.objects
            .filter(bill_number__startswith=prefix)
            .order_by('-bill_number')
            .first()
        )
        if last and last.bill_number:
            try:
                seq = int(last.bill_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    def save(self, *args, **kwargs):
        if not self.bill_number:
            self.bill_number = self._next_bill_number()
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        return {'PAID': 'success', 'UNPAID': 'danger'}.get(self.status, 'secondary')

    def __str__(self):
        return self.bill_number or f"PBill-{self.pk}"


class PurchaseBillItem(models.Model):
    bill       = models.ForeignKey(PurchaseBill, on_delete=models.CASCADE, related_name='items')
    product    = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, related_name='purchase_bill_items')
    quantity   = models.PositiveIntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Unit Cost (₹)')

    @property
    def total_price(self):
        return self.cost_price * self.quantity

    def __str__(self):
        name = self.product.name if self.product else '—'
        return f"{name} × {self.quantity}"

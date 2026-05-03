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
    Supports multiple products via InvoiceItem.
    Stock is managed in the view layer, not here.
    Revenue is tracked via Sale only — invoices do NOT update revenue.

    The optional `sale` FK links this invoice to the POS Sale it was generated
    from. Manual invoices leave this NULL.
    """

    slug = AutoSlugField(unique=True, populate_from='date')
    invoice_number = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text="Auto-generated INV-YYYY-NNNN."
    )
    date = models.DateTimeField(auto_now=True, verbose_name='Date')
    due_date = models.DateField(null=True, blank=True)

    # Optional link to a POS Sale. NULL = manual invoice.
    sale = models.OneToOneField(
        'transactions.Sale',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice',
        help_text="The POS Sale this invoice was generated from, if any.",
    )

    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invoices"
    )
    customer_name = models.CharField(max_length=60)
    contact_number = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(max_length=120, blank=True, null=True)
    shipping_address = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="Shipping Address"
    )

    shipping = models.FloatField(verbose_name='Shipping & Handling', default=0.0)
    grand_total = models.FloatField(verbose_name='Grand Total (₹)', default=0)

    status = models.CharField(
        max_length=10, choices=INVOICE_STATUS, default="PENDING"
    )

    class Meta:
        ordering = ["-id"]

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

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._next_invoice_number()
        super().save(*args, **kwargs)

    def recompute_total(self):
        """Recalculate grand_total from all InvoiceItems and shipping, then save."""
        subtotal = sum(item.line_total for item in self.items.all())
        self.grand_total = round(subtotal + float(self.shipping or 0), 2)
        Invoice.objects.filter(pk=self.pk).update(grand_total=self.grand_total)

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def status_color(self):
        return {"PAID": "success", "PENDING": "warning", "CANCELLED": "danger"}.get(
            self.status, "secondary"
        )

    def __str__(self):
        return self.invoice_number or self.slug


class InvoiceItem(models.Model):
    """
    A single line item on an Invoice.
    One Invoice can have many InvoiceItems (one per product).
    """

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name='invoice_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        return float(self.quantity) * float(self.price)

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

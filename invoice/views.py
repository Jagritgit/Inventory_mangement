from datetime import timedelta
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, DeleteView, ListView
from django.db import transaction
from django.db.models import Q

from store.models import Item
from .models import Invoice, InvoiceItem
from .forms import InvoiceHeaderForm


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "invoice/invoicelist.html"
    context_object_name = "invoices"
    paginate_by = 15

    SORT_MAP = {
        "date_desc":   "-date",
        "date_asc":    "date",
        "amount_desc": "-grand_total",
        "amount_asc":  "grand_total",
    }

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("items__product").select_related("customer")

        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q)
                | Q(customer_name__icontains=q)
                | Q(customer__first_name__icontains=q)
                | Q(customer__last_name__icontains=q)
            )

        status = self.request.GET.get("status")
        if status in {"PAID", "PENDING", "CANCELLED"}:
            qs = qs.filter(status=status)

        date_filter = self.request.GET.get("date")
        now = timezone.now()
        if date_filter == "today":
            qs = qs.filter(date__date=now.date())
        elif date_filter == "week":
            qs = qs.filter(date__gte=now - timedelta(days=7))
        elif date_filter == "month":
            qs = qs.filter(date__gte=now - timedelta(days=30))

        sort = self.request.GET.get("sort", "date_desc")
        qs = qs.order_by(self.SORT_MAP.get(sort, "-date"))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["date"] = self.request.GET.get("date", "")
        ctx["sort"] = self.request.GET.get("sort", "date_desc")
        return ctx


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "invoice/invoicedetail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("items__product")


def _parse_items(post):
    """
    Extract parallel lists of product_id / quantity / price from POST data.
    Returns a list of dicts, skipping rows with no product selected.
    """
    product_ids = post.getlist("product_id[]")
    quantities  = post.getlist("quantity[]")
    prices      = post.getlist("price[]")

    items = []
    for pid, qty, prc in zip(product_ids, quantities, prices):
        pid = pid.strip()
        if not pid:
            continue
        try:
            qty = int(qty)
            prc = float(prc)
        except (ValueError, TypeError):
            continue
        if qty <= 0 or prc < 0:
            continue
        items.append({"product_id": int(pid), "quantity": qty, "price": prc})
    return items


def _apply_stock(invoice, item_rows, restore=False):
    """
    Deduct or restore stock for a list of item rows.
    Does nothing when the invoice is CANCELLED.
    Raises ValueError on insufficient stock when deducting.
    """
    if invoice.status == "CANCELLED":
        return
    sign = 1 if restore else -1
    for row in item_rows:
        product = Item.objects.select_for_update().get(pk=row["product_id"])
        new_qty = product.quantity + sign * row["quantity"]
        if new_qty < 0:
            raise ValueError(
                f"Insufficient stock for '{product.name}': "
                f"available {product.quantity}, requested {row['quantity']}."
            )
        product.quantity = new_qty
        product.save()


@login_required
def invoice_create(request):
    all_products = Item.objects.order_by("name")
    errors = []

    if request.method == "POST":
        form = InvoiceHeaderForm(request.POST)
        item_rows = _parse_items(request.POST)

        if not item_rows:
            errors.append("Add at least one product line.")

        if form.is_valid() and not errors:
            try:
                with transaction.atomic():
                    invoice = form.save()
                    _apply_stock(invoice, item_rows, restore=False)
                    for row in item_rows:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            product_id=row["product_id"],
                            quantity=row["quantity"],
                            price=row["price"],
                        )
                    invoice.recompute_total()
                return redirect("invoicelist")
            except ValueError as e:
                errors.append(str(e))
    else:
        form = InvoiceHeaderForm()

    return render(request, "invoice/invoice_form.html", {
        "form": form,
        "all_products": all_products,
        "errors": errors,
        "editing": False,
    })


@login_required
def invoice_update(request, slug):
    invoice = get_object_or_404(Invoice, slug=slug)
    all_products = Item.objects.order_by("name")
    existing_items = list(invoice.items.select_related("product").all())
    errors = []

    if request.method == "POST":
        form = InvoiceHeaderForm(request.POST, instance=invoice)
        item_rows = _parse_items(request.POST)

        if not item_rows:
            errors.append("Add at least one product line.")

        if form.is_valid() and not errors:
            try:
                with transaction.atomic():
                    old_status = Invoice.objects.select_for_update().get(pk=invoice.pk).status
                    old_rows = [
                        {"product_id": ii.product_id, "quantity": ii.quantity}
                        for ii in existing_items
                    ]
                    old_invoice_stub = type("Stub", (), {"status": old_status})()
                    _apply_stock(old_invoice_stub, old_rows, restore=True)

                    invoice = form.save()
                    invoice.items.all().delete()

                    _apply_stock(invoice, item_rows, restore=False)
                    for row in item_rows:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            product_id=row["product_id"],
                            quantity=row["quantity"],
                            price=row["price"],
                        )
                    invoice.recompute_total()
                return redirect("invoicelist")
            except ValueError as e:
                errors.append(str(e))
    else:
        form = InvoiceHeaderForm(instance=invoice)

    return render(request, "invoice/invoice_form.html", {
        "form": form,
        "all_products": all_products,
        "existing_items": existing_items,
        "errors": errors,
        "editing": True,
        "invoice": invoice,
    })


class InvoiceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Invoice
    template_name = "invoice/invoicedelete.html"
    success_url = reverse_lazy("invoicelist")

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        invoice = self.get_object()
        with transaction.atomic():
            if invoice.status != "CANCELLED":
                rows = [
                    {"product_id": ii.product_id, "quantity": ii.quantity}
                    for ii in invoice.items.all()
                ]
                _apply_stock(invoice, rows, restore=True)
        return super().form_valid(form)

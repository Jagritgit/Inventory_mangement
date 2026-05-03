from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)

from .models import PurchaseOrder, PurchaseBill, PurchaseBillItem
from .forms import PurchaseOrderForm, PurchaseOrderItemFormSet
from store.models import Item


# ── Purchase Orders ───────────────────────────────────────────────────────────

class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model               = PurchaseOrder
    template_name       = 'purchases/po_list.html'
    context_object_name = 'orders'
    paginate_by         = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('vendor')
        q  = self.request.GET.get('q')
        if q:
            qs = qs.filter(order_number__icontains=q) | qs.filter(vendor__name__icontains=q)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q']              = self.request.GET.get('q', '')
        ctx['status']         = self.request.GET.get('status', '')
        ctx['status_choices'] = PurchaseOrder._meta.get_field('status').choices
        return ctx


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model               = PurchaseOrder
    template_name       = 'purchases/po_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related('vendor')
            .prefetch_related('items__product')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Pass existing bill (if any) to template so we can show View Bill link
        try:
            ctx['existing_bill'] = self.object.purchase_bill
        except PurchaseBill.DoesNotExist:
            ctx['existing_bill'] = None
        return ctx


class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    model         = PurchaseOrder
    form_class    = PurchaseOrderForm
    template_name = 'purchases/po_form.html'
    success_url   = reverse_lazy('purchase-order-list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'New Purchase Order'
        if self.request.POST:
            ctx['item_formset'] = PurchaseOrderItemFormSet(self.request.POST)
        else:
            ctx['item_formset'] = PurchaseOrderItemFormSet()
        return ctx

    def form_valid(self, form):
        ctx          = self.get_context_data()
        item_formset = ctx['item_formset']
        if item_formset.is_valid():
            self.object = form.save()
            item_formset.instance = self.object
            item_formset.save()
            self.object.recalculate_total()
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))


class PurchaseOrderUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model         = PurchaseOrder
    form_class    = PurchaseOrderForm
    template_name = 'purchases/po_form.html'
    success_url   = reverse_lazy('purchase-order-list')

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit {self.object.order_number}'
        if self.request.POST:
            ctx['item_formset'] = PurchaseOrderItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            ctx['item_formset'] = PurchaseOrderItemFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        ctx          = self.get_context_data()
        item_formset = ctx['item_formset']
        if item_formset.is_valid():
            self.object = form.save()
            item_formset.instance = self.object
            item_formset.save()
            self.object.recalculate_total()
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))


class PurchaseOrderDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model         = PurchaseOrder
    template_name = 'purchases/po_confirm_delete.html'
    success_url   = reverse_lazy('purchase-order-list')

    def test_func(self):
        return self.request.user.is_superuser


class MarkReceivedView(LoginRequiredMixin, View):
    """
    POST-only. Increments product stocks, bumps vendor.total_paid,
    marks order RECEIVED. Idempotent via stock_updated flag.
    """

    def post(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)

        if order.stock_updated:
            messages.warning(
                request,
                f"{order.order_number} was already marked as received — no changes made."
            )
            return redirect('purchase-order-detail', slug=order.slug)

        with transaction.atomic():
            for line in order.items.select_related('product'):
                line.product.quantity += line.quantity
                line.product.save(update_fields=['quantity'])

            if order.vendor_id:
                from accounts.models import Vendor as VendorModel
                vendor = VendorModel.objects.select_for_update().get(pk=order.vendor_id)
                vendor.total_paid = (vendor.total_paid or 0) + order.total_amount
                vendor.save(update_fields=['total_paid'])

            order.status        = 'RECEIVED'
            order.stock_updated = True
            order.save(update_fields=['status', 'stock_updated'])

        item_count = order.items.count()
        messages.success(
            request,
            f"{order.order_number} marked as Received. "
            f"Stock updated for {item_count} product{'s' if item_count != 1 else ''}."
        )
        return redirect('purchase-order-detail', slug=order.slug)


# ── Purchase Bills ────────────────────────────────────────────────────────────

class PurchaseBillListView(LoginRequiredMixin, ListView):
    model               = PurchaseBill
    template_name       = 'purchases/purchase_bill_list.html'
    context_object_name = 'bills'
    paginate_by         = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('vendor', 'purchase_order')
        q  = self.request.GET.get('q')
        if q:
            qs = qs.filter(bill_number__icontains=q) | qs.filter(vendor__name__icontains=q)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q']              = self.request.GET.get('q', '')
        ctx['status']         = self.request.GET.get('status', '')
        ctx['status_choices'] = PurchaseBill._meta.get_field('status').choices
        return ctx


class PurchaseBillDetailView(LoginRequiredMixin, DetailView):
    model               = PurchaseBill
    template_name       = 'purchases/purchase_bill_detail.html'
    context_object_name = 'bill'

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related('vendor', 'purchase_order')
            .prefetch_related('items__product')
        )


class CreatePurchaseBillView(LoginRequiredMixin, View):
    """
    POST-only. Creates a PurchaseBill from a PurchaseOrder in one click.
    - Copies all line items with their unit costs.
    - Updates each product's cost_price to the purchased price.
    - Idempotent: if a bill already exists, redirects to it.
    """

    def post(self, request, pk):
        order = get_object_or_404(
            PurchaseOrder.objects.prefetch_related('items__product'), pk=pk
        )

        # Idempotency guard
        try:
            existing = order.purchase_bill
            messages.info(request, f"Bill {existing.bill_number} already exists for {order.order_number}.")
            return redirect('purchase-bill-detail', slug=existing.slug)
        except PurchaseBill.DoesNotExist:
            pass

        with transaction.atomic():
            bill = PurchaseBill.objects.create(
                purchase_order=order,
                vendor=order.vendor,
                total_amount=order.total_amount,
            )

            for line in order.items.all():
                PurchaseBillItem.objects.create(
                    bill=bill,
                    product=line.product,
                    quantity=line.quantity,
                    cost_price=line.price,
                )
                # Update product's recorded cost price to the latest purchase price
                if line.product_id:
                    Item.objects.filter(pk=line.product_id).update(cost_price=line.price)

        messages.success(
            request,
            f"Bill {bill.bill_number} created from {order.order_number}. "
            f"Cost prices updated for {order.items.count()} product(s)."
        )
        return redirect('purchase-bill-detail', slug=bill.slug)


class ToggleBillStatusView(LoginRequiredMixin, View):
    """POST-only. Flips bill status between UNPAID ↔ PAID."""

    def post(self, request, pk):
        bill = get_object_or_404(PurchaseBill, pk=pk)
        bill.status = 'PAID' if bill.status == 'UNPAID' else 'UNPAID'
        bill.save(update_fields=['status'])
        messages.success(request, f"{bill.bill_number} marked as {bill.get_status_display()}.")
        return redirect('purchase-bill-detail', slug=bill.slug)

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)

from .models import PurchaseOrder
from .forms import PurchaseOrderForm, PurchaseOrderItemFormSet


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
    POST-only action view. On first call:
      1. Increments each product's stock by ordered quantity.
      2. Adds order total to vendor.total_paid.
      3. Sets status = RECEIVED and stock_updated = True.
    Idempotent: does nothing if already marked received.
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
            # 1. Increase each product's stock
            for line in order.items.select_related('product'):
                line.product.quantity += line.quantity
                line.product.save(update_fields=['quantity'])

            # 2. Bump vendor.total_paid
            if order.vendor_id:
                from accounts.models import Vendor as VendorModel
                vendor = VendorModel.objects.select_for_update().get(pk=order.vendor_id)
                vendor.total_paid = (vendor.total_paid or 0) + order.total_amount
                vendor.save(update_fields=['total_paid'])

            # 3. Mark the order
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

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
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
        ctx['q']      = self.request.GET.get('q', '')
        ctx['status'] = self.request.GET.get('status', '')
        ctx['status_choices'] = PurchaseOrder._meta.get_field('status').choices
        return ctx


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model               = PurchaseOrder
    template_name       = 'purchases/po_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return super().get_queryset().select_related('vendor').prefetch_related('items__product')


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
        ctx         = self.get_context_data()
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
            ctx['item_formset'] = PurchaseOrderItemFormSet(self.request.POST, instance=self.object)
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

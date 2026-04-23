from datetime import timedelta
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView
from django.db.models import Q

from .models import Invoice
from .forms import InvoiceForm


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "invoice/invoicelist.html"
    context_object_name = "invoices"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related("item", "customer")

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

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["date"] = self.request.GET.get("date", "")
        return ctx


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "invoice/invoicedetail.html"
    context_object_name = "invoice"


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice/invoice_form.html"
    success_url = reverse_lazy("invoicelist")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoice/invoice_form.html"
    success_url = reverse_lazy("invoicelist")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class InvoiceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Invoice
    template_name = "invoice/invoicedelete.html"
    success_url = reverse_lazy("invoicelist")

    def test_func(self):
        return self.request.user.is_superuser

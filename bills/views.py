from datetime import timedelta
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView
from django.db.models import Q

from .models import Bill
from .forms import BillForm


class BillListView(LoginRequiredMixin, ListView):
    model = Bill
    template_name = "bills/bill_list.html"
    context_object_name = "bills"
    paginate_by = 15

    SORT_MAP = {
        "date_desc":   "-date",
        "date_asc":    "date",
        "amount_desc": "-amount",
        "amount_asc":  "amount",
    }

    def get_queryset(self):
        qs = super().get_queryset().select_related("vendor", "item")

        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(bill_number__icontains=q)
                | Q(institution_name__icontains=q)
                | Q(vendor__name__icontains=q)
            )

        status = self.request.GET.get("status")
        if status in {"PAID", "PENDING"}:
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


class BillDetailView(LoginRequiredMixin, DetailView):
    model = Bill
    template_name = "bills/billdetail.html"
    context_object_name = "bill"


class BillCreateView(LoginRequiredMixin, CreateView):
    model = Bill
    form_class = BillForm
    template_name = "bills/bill_form.html"
    success_url = reverse_lazy("bill_list")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class BillUpdateView(LoginRequiredMixin, UpdateView):
    model = Bill
    form_class = BillForm
    template_name = "bills/bill_form.html"
    success_url = reverse_lazy("bill_list")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class BillDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Bill
    template_name = "bills/billdelete.html"
    success_url = reverse_lazy("bill_list")

    def test_func(self):
        return self.request.user.is_superuser

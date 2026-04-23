"""
Module: store.views

Contains Django views for managing items, profiles,
and deliveries in the store application.

Classes handle product listing, creation, updating,
deletion, and delivery management.
The module integrates with Django's authentication
and querying functionalities.
"""

# Standard library imports
import operator
from functools import reduce

# Django core imports
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum

# Authentication and permissions
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

# Class-based views
from django.views.generic import (
    DetailView, CreateView, UpdateView, DeleteView, ListView
)
from django.views.generic.edit import FormMixin

# Third-party packages
from django_tables2 import SingleTableView
import django_tables2 as tables
from django_tables2.export.views import ExportMixin

# Local app imports
from accounts.models import Profile, Vendor
from transactions.models import Sale
from .models import Category, Item, Delivery
from .forms import ItemForm, CategoryForm, DeliveryForm
from .tables import ItemTable


@login_required
def revenue_view(request):
    """
    Revenue page with daily/weekly/monthly grouping.

    NOTE: The Sale model has no `status` field — every persisted Sale row is
    a completed transaction (it ran inside an atomic block that already
    decremented stock). If a status field is ever added, filter here.
    """
    from decimal import Decimal, ROUND_HALF_UP
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
    from transactions.models import Sale

    period = request.GET.get("period", "daily")
    trunc_map = {
        "daily": TruncDay("date_added"),
        "weekly": TruncWeek("date_added"),
        "monthly": TruncMonth("date_added"),
    }
    trunc = trunc_map.get(period, TruncDay("date_added"))

    rows_qs = (
        Sale.objects
        .annotate(bucket=trunc)
        .values("bucket")
        .annotate(revenue=Sum("grand_total"), sales_count=Count("id"))
        .order_by("-bucket")  # Latest first
    )

    q = Decimal("0.01")
    rows = [
        {
            "bucket": r["bucket"],
            "revenue": Decimal(str(r["revenue"] or 0)).quantize(q, ROUND_HALF_UP),
            "sales_count": r["sales_count"],
        }
        for r in rows_qs
    ]

    total = sum((r["revenue"] for r in rows), Decimal("0.00")).quantize(q)

    return render(request, "store/revenue.html", {
        "period": period,
        "rows": rows,
        "total_revenue": total,
    })


@login_required
def dashboard(request):
    from decimal import Decimal, ROUND_HALF_UP
    from django.db.models import Sum, Count, F, FloatField, ExpressionWrapper
    from transactions.models import Sale, SaleDetail

    def money(value):
        """Round any numeric to 2 decimal places for display."""
        if value is None:
            return Decimal("0.00")
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Basic data
    profiles = Profile.objects.all()
    items = Item.objects.all()

    total_items = (
        Item.objects.aggregate(Sum("quantity")).get("quantity__sum") or 0
    )

    items_count = items.count()
    profiles_count = profiles.count()

    # Deliveries
    completed_deliveries = Delivery.objects.filter(is_delivered=True).count()
    pending_deliveries = Delivery.objects.filter(is_delivered=False).count()

    # -----------------------------
    # 💰 TOTAL REVENUE
    # -----------------------------
    total_revenue = money(
        Sale.objects.aggregate(total=Sum("grand_total")).get("total")
    )

    # -----------------------------
    # 💰 TOTAL PROFIT (FIXED)
    # -----------------------------
    total_profit = money(
        SaleDetail.objects.aggregate(
            profit=Sum(
                ExpressionWrapper(
                    F("quantity") * (F("price") - F("item__cost_price")),
                    output_field=FloatField()
                )
            )
        ).get("profit")
    )

    # -----------------------------
    # 🔥 TOP PRODUCT
    # -----------------------------
    top = (
        SaleDetail.objects
        .values('item__name')
        .annotate(total=Sum('quantity'))
        .order_by('-total')
        .first()
    )

    top_product = top['item__name'] if top else None

    # -----------------------------
    # 🔥 RECENT PRODUCT
    # -----------------------------
    recent = (
        SaleDetail.objects
        .select_related('item')
        .order_by('-id')
        .first()
    )

    recent_product = recent.item.name if recent else None

    # -----------------------------
    # CATEGORY CHART
    # -----------------------------
    category_counts_qs = Category.objects.annotate(
        item_count=Count("item")
    ).values("name", "item_count")

    categories = [cat["name"] for cat in category_counts_qs]
    category_counts = [cat["item_count"] for cat in category_counts_qs]

    # -----------------------------
    # SALES CHART
    # -----------------------------
    sale_dates = (
        Sale.objects.values("date_added__date")
        .annotate(total_sales=Sum("grand_total"))
        .order_by("date_added__date")
    )

    sale_dates_labels = [
        date["date_added__date"].strftime("%Y-%m-%d")
        for date in sale_dates
    ]

    sale_dates_values = [
        float(date["total_sales"]) for date in sale_dates
    ]

    # -----------------------------
    # FINAL CONTEXT
    # -----------------------------
    context = {
        "items": items,
        "profiles": profiles,
        "profiles_count": profiles_count,
        "items_count": items_count,
        "total_items": total_items,
        "vendors": Vendor.objects.all(),

        "completed_deliveries": completed_deliveries,
        "pending_deliveries": pending_deliveries,

        "sales": Sale.objects.all(),

        # 🔥 IMPORTANT
        "total_revenue": total_revenue,
        "total_profit": total_profit,

        "top_product": top_product,
        "recent_product": recent_product,

        # Charts
        "categories": categories,
        "category_counts": category_counts,
        "sale_dates_labels": sale_dates_labels,
        "sale_dates_values": sale_dates_values,
    }

    return render(request, "store/dashboard.html", context)


class ProductListView(LoginRequiredMixin, ExportMixin, tables.SingleTableView):
    model = Item
    table_class = ItemTable
    template_name = "store/productslist.html"
    context_object_name = "items"
    paginate_by = 10
    SingleTableView.table_pagination = False

    def get_queryset(self):
        queryset = super().get_queryset()
        order = self.request.GET.get('order', 'old')

        if order == 'new':
            return queryset.order_by('-id')

        elif order == 'high':
            return queryset.order_by('-price')

        elif order == 'low':
            return queryset.order_by('price')

        else:  # default = oldest
            return queryset.order_by('id')


class ItemSearchListView(ProductListView):
    """
    View class to search and display a filtered list of items.

    Attributes:
    - paginate_by: Number of items per page for pagination.
    """

    paginate_by = 10

    def get_queryset(self):
        result = super(ItemSearchListView, self).get_queryset()

        query = self.request.GET.get("q")
        if query:
            query_list = query.split()
            result = result.filter(
                reduce(
                    operator.and_, (Q(name__icontains=q) for q in query_list)
                )
            )
        return result


class ProductDetailView(LoginRequiredMixin, FormMixin, DetailView):
    """
    View class to display detailed information about a product.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    """

    model = Item
    template_name = "store/productdetail.html"

    def get_success_url(self):
        return reverse("product-detail", kwargs={"slug": self.object.slug})


class ProductCreateView(LoginRequiredMixin, CreateView):
    """
    View class to create a new product.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    - form_class: The form class used for data input.
    - success_url: The URL to redirect to upon successful form submission.
    """

    model = Item
    template_name = "store/productcreate.html"
    form_class = ItemForm
    success_url = "/products"

    def test_func(self):
        try:
            return int(self.request.POST.get("quantity", 0)) >= 1
        except (TypeError, ValueError):
            return False


class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View class to update product information.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    - fields: The fields to be updated.
    - success_url: The URL to redirect to upon successful form submission.
    """

    model = Item
    template_name = "store/productupdate.html"
    form_class = ItemForm
    success_url = "/products"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View class to delete a product.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    - success_url: The URL to redirect to upon successful deletion.
    """

    model = Item
    template_name = "store/productdelete.html"
    success_url = "/products"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class DeliveryListView(LoginRequiredMixin, ExportMixin, tables.SingleTableView):
    model = Delivery
    template_name = "store/deliveries.html"
    context_object_name = "deliveries"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        # SEARCH
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(customer_name__icontains=query)

        # FILTER / SORT
        order = self.request.GET.get("order", "old")

        if order == "new":
            queryset = queryset.order_by("-id")

        elif order == "delivered":
            queryset = queryset.filter(is_delivered=True).order_by("-id")

        elif order == "pending":
            queryset = queryset.filter(is_delivered=False).order_by("-id")

        else:
            queryset = queryset.order_by("id")

        return queryset


class DeliverySearchListView(DeliveryListView):
    """
    View class to search and display a filtered list of deliveries.

    Attributes:
    - paginate_by: Number of items per page for pagination.
    """

    paginate_by = 10

    def get_queryset(self):
        result = super(DeliverySearchListView, self).get_queryset()

        query = self.request.GET.get("q")
        if query:
            query_list = query.split()
            result = result.filter(
                reduce(
                    operator.
                    and_, (Q(customer_name__icontains=q) for q in query_list)
                )
            )
        return result


class DeliveryDetailView(LoginRequiredMixin, DetailView):
    """
    View class to display detailed information about a delivery.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    """

    model = Delivery
    template_name = "store/deliverydetail.html"


class DeliveryCreateView(LoginRequiredMixin, CreateView):
    """
    View class to create a new delivery.

    Attributes:
    - model: The model associated with the view.
    - fields: The fields to be included in the form.
    - template_name: The HTML template used for rendering the view.
    - success_url: The URL to redirect to upon successful form submission.
    """

    model = Delivery
    form_class = DeliveryForm
    template_name = "store/delivery_form.html"
    success_url = "/deliveries"


class DeliveryUpdateView(LoginRequiredMixin, UpdateView):
    """
    View class to update delivery information.

    Attributes:
    - model: The model associated with the view.
    - fields: The fields to be updated.
    - template_name: The HTML template used for rendering the view.
    - success_url: The URL to redirect to upon successful form submission.
    """

    model = Delivery
    form_class = DeliveryForm
    template_name = "store/delivery_form.html"
    success_url = "/deliveries"


class DeliveryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View class to delete a delivery.

    Attributes:
    - model: The model associated with the view.
    - template_name: The HTML template used for rendering the view.
    - success_url: The URL to redirect to upon successful deletion.
    """

    model = Delivery
    template_name = "store/deliverydelete.html"
    success_url = "/deliveries"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        else:
            return False


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'store/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10
    login_url = 'login'


class CategoryDetailView(LoginRequiredMixin, DetailView):
    model = Category
    template_name = 'store/category_detail.html'
    context_object_name = 'category'
    login_url = 'login'


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    template_name = 'store/category_form.html'
    form_class = CategoryForm
    login_url = 'login'

    def get_success_url(self):
        return reverse_lazy('category-detail', kwargs={'pk': self.object.pk})


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    template_name = 'store/category_form.html'
    form_class = CategoryForm
    login_url = 'login'

    def get_success_url(self):
        return reverse_lazy('category-detail', kwargs={'pk': self.object.pk})


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'store/category_confirm_delete.html'
    context_object_name = 'category'
    success_url = reverse_lazy('category-list')
    login_url = 'login'


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


@csrf_exempt
@require_POST
@login_required
def get_items_ajax_view(request):
    if is_ajax(request):
        try:
            term = request.POST.get("term", "")
            data = []

            items = Item.objects.filter(name__icontains=term)
            for item in items[:10]:
                data.append(item.to_json())

            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Not an AJAX request'}, status=400)
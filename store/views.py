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
from django.shortcuts import render, redirect, get_object_or_404
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
from .forms import ItemForm, CategoryForm, DeliveryCreateForm, DeliveryUpdateForm
from .tables import ItemTable


@login_required
def vendor_detail_json(request, pk):
    """Return Vendor contact details as JSON for the bill form auto-fill."""
    try:
        v = Vendor.objects.only(
            "id", "name", "phone_number", "email", "address"
        ).get(pk=pk)
    except Vendor.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    return JsonResponse({
        "id": v.id,
        "name": v.name,
        "phone_number": v.phone_number or "",
        "email": v.email or "",
        "address": v.address or "",
    })


@login_required
def invoice_detail_json(request, pk):
    """
    Return Invoice + linked Customer details for delivery form auto-fill.
    """
    from invoice.models import Invoice
    try:
        inv = (
            Invoice.objects.select_related("customer")
            .prefetch_related("items__product")
            .get(pk=pk)
        )
    except Invoice.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    cust = inv.customer
    first_item = inv.items.first()
    return JsonResponse({
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "customer_id": cust.id if cust else None,
        "customer_name": (
            cust.get_full_name() if cust else (inv.customer_name or "")
        ),
        "email": (cust.email if cust else "") or inv.customer_email or "",
        "phone": (
            (cust.phone if cust else "") or inv.contact_number or ""
        ),
        "address": (
            inv.shipping_address
            or (cust.address if cust else "")
            or ""
        ),
        "item_id": first_item.product_id if first_item else None,
        "item_name": first_item.product.name if first_item else "",
    })


@login_required
def customer_detail_json(request, pk):
    """Return Customer contact details as JSON for the invoice form auto-fill."""
    from accounts.models import Customer
    try:
        c = Customer.objects.only(
            "id", "first_name", "last_name", "email", "phone", "address"
        ).get(pk=pk)
    except Customer.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    return JsonResponse({
        "id": c.id,
        "name": c.get_full_name(),
        "email": c.email or "",
        "phone": c.phone or "",
        "address": c.address or "",
    })


@login_required
def item_pricing_view(request, pk):
    """
    Lightweight JSON endpoint returning an Item's selling + cost prices and
    available stock. Used by the invoice/bill forms to auto-fill price on
    product selection.
    """
    try:
        item = Item.objects.only(
            "id", "name", "price", "cost_price", "quantity"
        ).get(pk=pk)
    except Item.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    return JsonResponse({
        "id": item.id,
        "name": item.name,
        "price": float(item.price or 0),
        "cost_price": float(item.cost_price or 0),
        "quantity_in_stock": int(item.quantity or 0),
    })


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
    from invoice.models import Invoice
    from bills.models import Bill

    sales_revenue = money(
        Sale.objects.aggregate(total=Sum("grand_total")).get("total")
    )
    paid_invoice_revenue = money(
        Invoice.objects.filter(status="PAID")
        .aggregate(total=Sum("grand_total")).get("total")
    )
    total_revenue = money(sales_revenue + paid_invoice_revenue)

    total_expenses = money(
        Bill.objects.filter(status="PAID")
        .aggregate(total=Sum("amount")).get("total")
    )

    pending_invoices_count = Invoice.objects.filter(status="PENDING").count()
    pending_bills_count = Bill.objects.filter(status="PENDING").count()
    pending_invoices_total = money(
        Invoice.objects.filter(status="PENDING")
        .aggregate(total=Sum("grand_total")).get("total")
    )
    pending_bills_total = money(
        Bill.objects.filter(status="PENDING")
        .aggregate(total=Sum("amount")).get("total")
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
    # SALES CHART (revenue + quantity per day)
    # -----------------------------
    from transactions.models import SaleDetail as _SD
    daily_stats = (
        _SD.objects
        .values("sale__date_added__date")
        .annotate(
            daily_revenue=Sum("total_detail"),
            daily_qty=Sum("quantity"),
        )
        .order_by("sale__date_added__date")
    )

    sale_dates_labels    = [d["sale__date_added__date"].strftime("%Y-%m-%d") for d in daily_stats]
    sale_dates_values    = [float(d["daily_revenue"] or 0) for d in daily_stats]
    sale_dates_quantities = [int(d["daily_qty"] or 0) for d in daily_stats]

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
        "total_expenses": total_expenses,
        "sales_revenue": sales_revenue,
        "paid_invoice_revenue": paid_invoice_revenue,
        "pending_invoices_count": pending_invoices_count,
        "pending_bills_count": pending_bills_count,
        "pending_invoices_total": pending_invoices_total,
        "pending_bills_total": pending_bills_total,

        "top_product": top_product,
        "recent_product": recent_product,

        # Charts
        "categories": categories,
        "category_counts": category_counts,
        "sale_dates_labels": sale_dates_labels,
        "sale_dates_values": sale_dates_values,
        "sale_dates_quantities": sale_dates_quantities,
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

    def _latest_purchase_price(self):
        """Return the price from the most-recent Purchase for this product, or None."""
        from transactions.models import Purchase
        latest = Purchase.objects.filter(item=self.object).order_by('-order_date').first()
        return latest.price if latest else None

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Only auto-fill when the form hasn't been submitted yet (GET request),
        # so we don't override what the user just typed on a failed POST.
        if self.request.method == 'GET':
            latest_price = self._latest_purchase_price()
            if latest_price is not None and not form.initial.get('cost_price'):
                form.fields['cost_price'].initial = latest_price
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['latest_purchase_price'] = self._latest_purchase_price()
        return ctx


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
        queryset = super().get_queryset().select_related(
            "sale__customer", "customer", "item"
        )

        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(
                Q(customer_name__icontains=query)
                | Q(sale__customer__first_name__icontains=query)
                | Q(sale__customer__last_name__icontains=query)
            )

        order = self.request.GET.get("order", "new")

        if order == "delivered":
            queryset = queryset.filter(status="DELIVERED").order_by("-id")
        elif order == "shipped":
            queryset = queryset.filter(status="SHIPPED").order_by("-id")
        elif order == "pending":
            queryset = queryset.filter(status="PENDING").order_by("-id")
        else:
            queryset = queryset.order_by("-id")

        return queryset


class DeliverySearchListView(DeliveryListView):
    paginate_by = 10

    def get_queryset(self):
        result = super().get_queryset()
        query = self.request.GET.get("q")
        if query:
            query_list = query.split()
            result = result.filter(
                reduce(operator.and_, (Q(customer_name__icontains=q) for q in query_list))
            )
        return result


class DeliveryDetailView(LoginRequiredMixin, DetailView):
    model = Delivery
    template_name = "store/deliverydetail.html"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "sale__customer", "sale__invoice", "customer", "item"
        ).prefetch_related("sale__saledetail_set__item")


class DeliveryCreateView(LoginRequiredMixin, CreateView):
    model = Delivery
    form_class = DeliveryCreateForm
    template_name = "store/delivery_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Sale dropdown only shows sales that don't already have a delivery
        taken_ids = Delivery.objects.filter(
            sale__isnull=False
        ).values_list('sale_id', flat=True)
        form.fields['sale'].queryset = (
            Sale.objects.exclude(id__in=taken_ids)
            .select_related('customer')
            .order_by('-id')
        )
        form.fields['sale'].empty_label = '— Select a sale —'
        return form

    def form_valid(self, form):
        from django.contrib import messages
        delivery = form.save(commit=False)
        delivery.status = 'PENDING'
        mode = form.cleaned_data.get('mode', 'sale')

        if mode == 'sale':
            sale = delivery.sale
            # Server-side duplicate guard
            if Delivery.objects.filter(sale=sale).exists():
                form.add_error('sale', 'A delivery already exists for this sale.')
                return self.form_invalid(form)
            # Copy customer details from the linked sale
            customer = sale.customer if sale else None
            if customer:
                if not delivery.phone_number:
                    delivery.phone_number = getattr(customer, 'phone', '') or None
                if not delivery.location:
                    delivery.location = getattr(customer, 'address', '') or ''
                delivery.customer = customer
                delivery.customer_name = customer.get_full_name()
                delivery.email = getattr(customer, 'email', '') or ''
            delivery.save()
            messages.success(
                self.request,
                f'Delivery #{delivery.id} created for Sale #{sale.id}.'
            )
        else:
            # Manual mode — no sale link
            delivery.sale = None
            delivery.save()
            messages.success(
                self.request,
                f'Manual delivery #{delivery.id} created for {delivery.customer_name or "customer"}.'
            )

        return redirect('delivery-detail', pk=delivery.pk)


class DeliveryUpdateView(LoginRequiredMixin, UpdateView):
    model = Delivery
    form_class = DeliveryUpdateForm
    template_name = "store/deliveryupdate.html"

    def get_success_url(self):
        return reverse('delivery-detail', kwargs={'pk': self.object.pk})


class DeliveryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Delivery
    template_name = "store/deliverydelete.html"
    success_url = "/deliveries"

    def test_func(self):
        return self.request.user.is_superuser


@login_required
def sale_details_json(request, pk):
    """
    AJAX endpoint — returns Sale data for the delivery create form auto-fill.
    GET /api/sale/<pk>/details/
    """
    from transactions.models import Sale
    try:
        sale = (
            Sale.objects
            .select_related('customer')
            .prefetch_related('saledetail_set__item')
            .get(pk=pk)
        )
    except Sale.DoesNotExist:
        return JsonResponse({'error': 'Sale not found'}, status=404)

    # Duplicate guard
    already_exists = Delivery.objects.filter(sale=sale).exists()

    customer = sale.customer
    items = [
        {
            'name': d.item.name,
            'quantity': d.quantity,
            'price': str(d.price),
            'total': str(d.total_detail),
        }
        for d in sale.saledetail_set.all()
    ]

    return JsonResponse({
        'sale_id': sale.id,
        'customer_name': customer.get_full_name() if customer else '',
        'customer_email': (customer.email or '') if customer else '',
        'customer_phone': (customer.phone or '') if customer else '',
        'customer_address': (customer.address or '') if customer else '',
        'grand_total': str(sale.grand_total),
        'date': sale.date_added.strftime('%Y-%m-%d %H:%M'),
        'items': items,
        'already_has_delivery': already_exists,
    })


@login_required
def mark_as_shipped(request, pk):
    """Set delivery status → SHIPPED and record shipped_date."""
    from django.utils import timezone as tz
    delivery = get_object_or_404(Delivery, pk=pk)
    if delivery.status == 'PENDING':
        delivery.status = 'SHIPPED'
        delivery.shipped_date = tz.now()
        delivery.save(update_fields=['status', 'shipped_date'])
    return redirect('delivery-detail', pk=pk)


@login_required
def mark_as_delivered(request, pk):
    """Set delivery status → DELIVERED and record delivered_date."""
    from django.utils import timezone as tz
    delivery = get_object_or_404(Delivery, pk=pk)
    if delivery.status in ('PENDING', 'SHIPPED'):
        delivery.status = 'DELIVERED'
        delivery.is_delivered = True
        delivery.delivered_date = tz.now()
        delivery.save(update_fields=['status', 'is_delivered', 'delivered_date'])
    return redirect('delivery-detail', pk=pk)


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
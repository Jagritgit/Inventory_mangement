# Standard library imports
import json
import logging

# Django core imports
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.shortcuts import render
from django.db import transaction

# Class-based views
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# Authentication and permissions
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required

# Third-party packages
from openpyxl import Workbook

# Local app imports
from store.models import Item
from accounts.models import Customer
from .models import Sale, Purchase, SaleDetail
from .forms import PurchaseForm


logger = logging.getLogger(__name__)


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def export_sales_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Sales'

    columns = [
        'ID', 'Date', 'Customer', 'Sub Total',
        'Grand Total', 'Tax Amount', 'Tax Percentage',
        'Amount Paid', 'Amount Change'
    ]
    worksheet.append(columns)

    sales = Sale.objects.all()

    for sale in sales:
        if sale.date_added.tzinfo is not None:
            date_added = sale.date_added.replace(tzinfo=None)
        else:
            date_added = sale.date_added

        worksheet.append([
            sale.id,
            date_added,
            sale.customer.phone,
            float(sale.sub_total),
            float(sale.grand_total),
            float(sale.tax_amount),
            sale.tax_percentage,
            float(sale.amount_paid),
            float(sale.amount_change)
        ])

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = 'attachment; filename=sales.xlsx'
    workbook.save(response)
    return response


def export_purchases_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Purchases'

    columns = [
        'ID', 'Item', 'Description', 'Vendor', 'Order Date',
        'Delivery Date', 'Quantity', 'Delivery Status',
        'Price per item (Ksh)', 'Total Value'
    ]
    worksheet.append(columns)

    purchases = Purchase.objects.all()

    for purchase in purchases:
        # BUG FIX #3: Original code crashed when delivery_date was None
        # (NullPointerError calling .tzinfo on None). Fixed with a None check.
        order_date = purchase.order_date
        if order_date and order_date.tzinfo is not None:
            order_date = order_date.replace(tzinfo=None)

        delivery_date = purchase.delivery_date
        if delivery_date and delivery_date.tzinfo is not None:
            delivery_date = delivery_date.replace(tzinfo=None)

        worksheet.append([
            purchase.id,
            purchase.item.name,
            purchase.description,
            purchase.vendor.name,
            order_date,
            delivery_date,
            purchase.quantity,
            purchase.get_delivery_status_display(),
            float(purchase.price),
            float(purchase.total_value)
        ])

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = 'attachment; filename=purchases.xlsx'
    workbook.save(response)
    return response


class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = "transactions/sales_list.html"
    context_object_name = "sales"
    paginate_by = 10

    def get_queryset(self):
        order = self.request.GET.get('order', 'old')  # 👈 DEFAULT OLD

        if order == 'new':
            return Sale.objects.all().order_by('-date_added')

        elif order == 'high':
            return Sale.objects.all().order_by('-grand_total')

        elif order == 'low':
            return Sale.objects.all().order_by('grand_total')

        else:  # default
            return Sale.objects.all().order_by('date_added')


class SaleDetailView(LoginRequiredMixin, DetailView):
    """
    View to display details of a specific sale.
    """
    model = Sale
    template_name = "transactions/saledetail.html"

@login_required
def SaleCreateView(request):
    context = {
        "active_icon": "sales",
        "customers": [c.to_select2() for c in Customer.objects.all()],
        "products": Item.objects.all()   # ✅ FIX
    }

    if request.method == 'POST':
        if is_ajax(request=request):
            try:
                data = json.loads(request.body)

                sale_attributes = {
                    "customer": Customer.objects.get(id=int(data['customer'])),
                    "sub_total": float(data["sub_total"]),
                    "grand_total": float(data["grand_total"]),
                    "tax_amount": float(data.get("tax_amount", 0.0)),
                    "tax_percentage": float(data.get("tax_percentage", 0.0)),
                    "amount_paid": float(data["amount_paid"]),
                    "amount_change": float(data["amount_change"]),
                }

                items = data.get("items", [])

                with transaction.atomic():
                    new_sale = Sale.objects.create(**sale_attributes)

                    for item in items:
                        item_instance = Item.objects.select_for_update().get(
                            id=int(item["id"])
                        )
                        quantity = int(float(item["quantity"]))

                        if quantity <= 0:
                            raise ValueError(
                                f"Quantity for {item_instance.name} must be positive."
                            )
                        if item_instance.quantity < quantity:
                            raise ValueError(
                                f"Insufficient stock for {item_instance.name}: "
                                f"requested {quantity}, available {item_instance.quantity}."
                            )

                        SaleDetail.objects.create(
                            sale=new_sale,
                            item=item_instance,
                            price=float(item["price"]),
                            quantity=quantity,
                            total_detail=float(item["total_item"])
                        )

                        item_instance.quantity -= quantity
                        item_instance.save()

                return JsonResponse({
                    'status': 'success',
                    'redirect': '/transactions/sales/'
                })

            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)

    return render(request, "transactions/sale_create.html", context=context)



class SaleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View to delete a sale.
    """
    model = Sale
    template_name = "transactions/saledelete.html"

    def get_success_url(self):
        return reverse("saleslist")

    def test_func(self):
        return self.request.user.is_superuser


class PurchaseListView(LoginRequiredMixin, ListView):
    """
    View to list all purchases with pagination.
    """
    model = Purchase
    template_name = "transactions/purchases_list.html"
    context_object_name = "purchases"
    paginate_by = 10


class PurchaseDetailView(LoginRequiredMixin, DetailView):
    """
    View to display details of a specific purchase.
    """
    model = Purchase
    template_name = "transactions/purchasedetail.html"


class PurchaseCreateView(LoginRequiredMixin, CreateView):
    """
    View to create a new purchase.
    """
    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"

    def get_success_url(self):
        return reverse("purchaseslist")


class PurchaseUpdateView(LoginRequiredMixin, UpdateView):
    """
    View to update an existing purchase.
    """
    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"

    def get_success_url(self):
        return reverse("purchaseslist")


class PurchaseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View to delete a purchase.
    """
    model = Purchase
    template_name = "transactions/purchasedelete.html"

    def get_success_url(self):
        return reverse("purchaseslist")

    def test_func(self):
        return self.request.user.is_superuser

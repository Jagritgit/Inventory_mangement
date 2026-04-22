# =========================
# IMPORTS
# =========================
import json
import logging
from decimal import Decimal

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.db import transaction

from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from openpyxl import Workbook

from store.models import Item
from accounts.models import Customer
from .models import Sale, Purchase, SaleDetail
from .forms import PurchaseForm

logger = logging.getLogger(__name__)


# =========================
# 🔍 AJAX CHECK
# =========================
def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


# =========================
# 🔍 GET ITEMS (IMPORTANT)
# =========================
def get_items(request):
    term = request.POST.get('term', '')

    items = Item.objects.filter(name__icontains=term)[:10]

    data = []
    for item in items:
        data.append({
            'id': item.id,
            'text': item.name,
            'price': float(item.price)
        })

    return JsonResponse(data, safe=False)


# =========================
# 📊 SALES LIST
# =========================
class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = "transactions/sales_list.html"
    context_object_name = "sales"
    paginate_by = 10
    ordering = ['-date_added']


# =========================
# 📄 SALE DETAIL
# =========================
class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = "transactions/saledetail.html"


# =========================
# ➕ CREATE SALE
# =========================
def SaleCreateView(request):
    context = {
        "active_icon": "sales",
        "customers": [c.to_select2() for c in Customer.objects.all()]
    }

    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            required_fields = [
                'customer', 'sub_total', 'grand_total',
                'amount_paid', 'amount_change', 'items'
            ]

            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Missing field: {field}'
                    }, status=400)

            customer = Customer.objects.get(id=int(data['customer']))

            with transaction.atomic():

                sale = Sale.objects.create(
                    customer=customer,
                    sub_total=Decimal(data['sub_total']),
                    grand_total=Decimal(data['grand_total']),
                    tax_amount=Decimal(data.get('tax_amount', 0)),
                    tax_percentage=Decimal(data.get('tax_percentage', 0)),
                    amount_paid=Decimal(data['amount_paid']),
                    amount_change=Decimal(data['amount_change']),
                )

                for item in data['items']:
                    item_obj = Item.objects.get(id=int(item['id']))
                    qty = int(item['quantity'])

                    if item_obj.quantity < qty:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Not enough stock for {item_obj.name}'
                        }, status=400)

                    SaleDetail.objects.create(
                        sale=sale,
                        item=item_obj,
                        price=Decimal(item['price']),
                        quantity=qty,
                        total_detail=Decimal(item['total_item'])
                    )

                    item_obj.quantity -= qty
                    item_obj.save()

            return JsonResponse({
                'status': 'success',
                'redirect': reverse('saleslist')
            })

        except Exception as e:
            logger.error(e)
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return render(request, "transactions/sale_create.html", context)


# =========================
# ❌ DELETE SALE
# =========================
class SaleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Sale
    template_name = "transactions/saledelete.html"

    def get_success_url(self):
        return reverse("saleslist")

    def test_func(self):
        return self.request.user.is_superuser


# =========================
# 📦 PURCHASE LIST
# =========================
class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    template_name = "transactions/purchases_list.html"
    context_object_name = "purchases"
    paginate_by = 10


# =========================
# 📄 PURCHASE DETAIL
# =========================
class PurchaseDetailView(LoginRequiredMixin, DetailView):
    model = Purchase
    template_name = "transactions/purchasedetail.html"


# =========================
# ➕ CREATE PURCHASE
# =========================
class PurchaseCreateView(LoginRequiredMixin, CreateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"

    def get_success_url(self):
        return reverse("purchaseslist")


# =========================
# ✏️ UPDATE PURCHASE
# =========================
class PurchaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"

    def get_success_url(self):
        return reverse("purchaseslist")


# =========================
# ❌ DELETE PURCHASE
# =========================
class PurchaseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Purchase
    template_name = "transactions/purchasedelete.html"

    def get_success_url(self):
        return reverse("purchaseslist")

    def test_func(self):
        return self.request.user.is_superuser


# =========================
# 📤 EXPORT SALES
# =========================
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

    for sale in Sale.objects.all():
        worksheet.append([
            sale.id,
            sale.date_added.replace(tzinfo=None),
            sale.customer,
            sale.sub_total,
            sale.grand_total,
            sale.tax_amount,
            sale.tax_percentage,
            sale.amount_paid,
            sale.amount_change
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=sales.xlsx'

    workbook.save(response)
    return response


# =========================
# 📤 EXPORT PURCHASES
# =========================
def export_purchases_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Purchases'

    columns = [
        'ID', 'Item', 'Vendor', 'Quantity',
        'Price', 'Total Value'
    ]
    worksheet.append(columns)

    for purchase in Purchase.objects.all():
        worksheet.append([
            purchase.id,
            purchase.item.name,
            purchase.vendor.name,
            purchase.quantity,
            purchase.price,
            purchase.total_value
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=purchases.xlsx'

    workbook.save(response)
    return response

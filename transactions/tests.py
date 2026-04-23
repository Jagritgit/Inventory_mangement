import json

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Customer, Vendor
from store.models import Category, Item
from transactions.models import Sale, SaleDetail, Purchase


def make_item(qty=10, price=5, cost=2, name="Widget"):
    cat = Category.objects.create(name=f"cat-{name}")
    vendor = Vendor.objects.create(name=f"vend-{name}")
    return Item.objects.create(
        name=name, description="x", category=cat, vendor=vendor,
        quantity=qty, price=price, cost_price=cost,
    )


class PurchaseStockTests(TestCase):
    """Phase 6 — business logic: stock increases on purchase, exactly once."""

    def test_purchase_increases_stock_once(self):
        item = make_item(qty=5, name="A")
        vendor = item.vendor
        Purchase.objects.create(
            item=item, vendor=vendor, quantity=3, price=2,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 8)

    def test_purchase_update_does_not_double_stock(self):
        # Regression for previous double-increment bug (signals + save()).
        item = make_item(qty=5, name="B")
        vendor = item.vendor
        p = Purchase.objects.create(
            item=item, vendor=vendor, quantity=3, price=2,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 8)

        # Updating an existing purchase must NOT increase stock again.
        p.price = 4
        p.save()
        item.refresh_from_db()
        self.assertEqual(item.quantity, 8)

    def test_purchase_total_value_computed(self):
        item = make_item(name="C")
        p = Purchase.objects.create(
            item=item, vendor=item.vendor, quantity=4, price=2.5,
        )
        self.assertEqual(float(p.total_value), 10.0)


class SaleModelTests(TestCase):
    def test_sum_products(self):
        item = make_item(qty=20, name="S1")
        cust = Customer.objects.create(first_name="C")
        sale = Sale.objects.create(
            customer=cust, sub_total=10, grand_total=10,
            amount_paid=10, amount_change=0,
        )
        SaleDetail.objects.create(
            sale=sale, item=item, price=5, quantity=2, total_detail=10
        )
        SaleDetail.objects.create(
            sale=sale, item=item, price=5, quantity=3, total_detail=15
        )
        self.assertEqual(sale.sum_products(), 5)


class SaleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw12345!")
        self.client.login(username="u", password="pw12345!")

    def test_sales_list_ok(self):
        resp = self.client.get(reverse("saleslist"))
        self.assertEqual(resp.status_code, 200)

    def test_sale_create_get_renders(self):
        resp = self.client.get(reverse("sale-create"))
        self.assertEqual(resp.status_code, 200)

    def _post_sale(self, item, customer, quantity):
        return self.client.post(
            reverse("sale-create"),
            data=json.dumps({
                "customer": customer.id,
                "sub_total": str(item.price * quantity),
                "grand_total": str(item.price * quantity),
                "tax_amount": "0",
                "tax_percentage": "0",
                "amount_paid": str(item.price * quantity),
                "amount_change": "0",
                "items": [{
                    "id": item.id,
                    "price": str(item.price),
                    "quantity": str(quantity),
                    "total_item": str(item.price * quantity),
                }],
            }),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_sale_creation_reduces_stock(self):
        item = make_item(qty=10, price=5, name="StockTest")
        customer = Customer.objects.create(first_name="J")
        resp = self._post_sale(item, customer, 4)
        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 6)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(SaleDetail.objects.count(), 1)

    def test_sale_rejects_insufficient_stock(self):
        item = make_item(qty=2, price=5, name="LowStock")
        customer = Customer.objects.create(first_name="J")
        resp = self._post_sale(item, customer, 5)
        self.assertEqual(resp.status_code, 500)
        item.refresh_from_db()
        # Atomic transaction must roll back: stock unchanged, no sale persisted.
        self.assertEqual(item.quantity, 2)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(SaleDetail.objects.count(), 0)


class PurchaseViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("p", password="pw12345!")
        self.client.login(username="p", password="pw12345!")

    def test_purchases_list_ok(self):
        resp = self.client.get(reverse("purchaseslist"))
        self.assertEqual(resp.status_code, 200)

    def test_purchase_create_post(self):
        item = make_item(qty=1, name="PV")
        resp = self.client.post(reverse("purchase-create"), {
            "item": item.id, "vendor": item.vendor.id,
            "quantity": 5, "price": "1.00",
            "delivery_status": "P", "description": "x",
        })
        self.assertIn(resp.status_code, (200, 302))
        self.assertEqual(Purchase.objects.count(), 1)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 6)


class IntegrationFlowTests(TestCase):
    """Full workflow: add product → purchase increases stock → sale reduces stock."""

    def test_full_inventory_flow(self):
        user = User.objects.create_user("flow", password="pw12345!")
        self.client.login(username="flow", password="pw12345!")

        cat = Category.objects.create(name="FlowCat")
        vendor = Vendor.objects.create(name="FlowVendor")
        customer = Customer.objects.create(first_name="FlowC")

        # 1. Create product (qty 0)
        resp = self.client.post(reverse("product-create"), {
            "name": "FlowItem", "description": "x",
            "category": cat.id, "quantity": 0, "price": 10,
            "vendor": vendor.id,
        })
        self.assertIn(resp.status_code, (200, 302))
        item = Item.objects.get(name="FlowItem")
        self.assertEqual(item.quantity, 0)

        # 2. Purchase increases stock to 7
        Purchase.objects.create(
            item=item, vendor=vendor, quantity=7, price=5,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 7)

        # 3. Sell 3 → stock = 4
        resp = self.client.post(
            reverse("sale-create"),
            data=json.dumps({
                "customer": customer.id,
                "sub_total": "30", "grand_total": "30",
                "tax_amount": "0", "tax_percentage": "0",
                "amount_paid": "30", "amount_change": "0",
                "items": [{
                    "id": item.id, "price": "10",
                    "quantity": "3", "total_item": "30",
                }],
            }),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)


class ExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("e", password="pw12345!")
        self.client.login(username="e", password="pw12345!")

    def test_export_sales_xlsx(self):
        resp = self.client.get(reverse("sales-export"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("spreadsheet", resp["Content-Type"])

    def test_export_purchases_xlsx_with_null_dates(self):
        # Regression for #3: crashed when delivery_date was None.
        item = make_item(name="EX")
        Purchase.objects.create(
            item=item, vendor=item.vendor, quantity=1, price=1,
            delivery_date=None,
        )
        resp = self.client.get(reverse("purchases-export"))
        self.assertEqual(resp.status_code, 200)

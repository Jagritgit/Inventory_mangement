from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Vendor
from store.models import Category, Item
from invoice.models import Invoice


class InvoiceModelTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="C")
        vendor = Vendor.objects.create(name="V")
        self.item = Item.objects.create(
            name="Inv", description="x", category=cat, vendor=vendor,
            quantity=10, price=5,
        )

    def test_totals_computed_on_save(self):
        inv = Invoice.objects.create(
            customer_name="John", contact_number="555",
            item=self.item, price_per_item=10.0, quantity=3, shipping=2.0,
        )
        self.assertEqual(inv.total, 30.0)
        self.assertEqual(inv.grand_total, 32.0)

    def test_totals_recompute_on_update(self):
        inv = Invoice.objects.create(
            customer_name="J", contact_number="1",
            item=self.item, price_per_item=2.0, quantity=2, shipping=1.0,
        )
        inv.quantity = 5
        inv.save()
        self.assertEqual(inv.total, 10.0)
        self.assertEqual(inv.grand_total, 11.0)


class InvoiceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw12345!")
        self.client.login(username="u", password="pw12345!")

    def test_invoice_list_ok(self):
        resp = self.client.get(reverse("invoicelist"))
        self.assertEqual(resp.status_code, 200)

    def test_invoice_create_get(self):
        resp = self.client.get(reverse("invoice-create"))
        self.assertEqual(resp.status_code, 200)

    def test_invoice_list_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("invoicelist"))
        self.assertEqual(resp.status_code, 302)

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

    def test_invoice_number_auto_generated(self):
        inv1 = Invoice.objects.create(
            customer_name="A", contact_number="1",
            item=self.item, price_per_item=1.0, quantity=1, shipping=0,
        )
        inv2 = Invoice.objects.create(
            customer_name="B", contact_number="2",
            item=self.item, price_per_item=1.0, quantity=1, shipping=0,
        )
        self.assertTrue(inv1.invoice_number.startswith("INV-"))
        n1 = int(inv1.invoice_number.split("-")[-1])
        n2 = int(inv2.invoice_number.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_invoice_decrements_stock(self):
        start = self.item.quantity
        Invoice.objects.create(
            customer_name="X", contact_number="1",
            item=self.item, price_per_item=2.0, quantity=3, shipping=0,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, start - 3)

    def test_invoice_overstock_raises(self):
        with self.assertRaises(ValueError):
            Invoice.objects.create(
                customer_name="O", contact_number="1",
                item=self.item, price_per_item=1.0,
                quantity=self.item.quantity + 999, shipping=0,
            )

    def test_invoice_delete_restores_stock(self):
        start = self.item.quantity
        inv = Invoice.objects.create(
            customer_name="D", contact_number="1",
            item=self.item, price_per_item=2.0, quantity=2, shipping=0,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, start - 2)
        inv.delete()
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, start)

    def test_invoice_update_reverses_old_delta(self):
        start = self.item.quantity
        inv = Invoice.objects.create(
            customer_name="U", contact_number="1",
            item=self.item, price_per_item=1.0, quantity=2, shipping=0,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, start - 2)
        inv.quantity = 5
        inv.save()
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, start - 5)

    def test_invoice_default_status_pending(self):
        inv = Invoice.objects.create(
            customer_name="S", contact_number="1",
            item=self.item, price_per_item=1.0, quantity=1, shipping=0,
        )
        self.assertEqual(inv.status, "PENDING")


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

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

    def test_form_recomputes_total_on_save(self):
        """Backend must compute total = qty * price + shipping regardless of any
        client-side hint."""
        from invoice.forms import InvoiceForm
        f = InvoiceForm(data={
            "customer_name": "Z", "contact_number": "1",
            "item": self.item.id,
            "price_per_item": "10.00", "quantity": 2, "shipping": "1.50",
            "status": "PENDING",
        })
        self.assertTrue(f.is_valid(), f.errors)
        inv = f.save()
        self.assertEqual(inv.total, 20.0)
        self.assertEqual(inv.grand_total, 21.5)

    def test_form_rejects_zero_quantity(self):
        from invoice.forms import InvoiceForm
        f = InvoiceForm(data={
            "customer_name": "Z", "contact_number": "1",
            "item": self.item.id,
            "price_per_item": "10.00", "quantity": 0, "shipping": "0",
            "status": "PENDING",
        })
        self.assertFalse(f.is_valid())
        self.assertIn("quantity", f.errors)

    def test_form_rejects_negative_price(self):
        from invoice.forms import InvoiceForm
        f = InvoiceForm(data={
            "customer_name": "Z", "contact_number": "1",
            "item": self.item.id,
            "price_per_item": "-1.00", "quantity": 1, "shipping": "0",
            "status": "PENDING",
        })
        self.assertFalse(f.is_valid())

    def test_pricing_endpoint(self):
        u = User.objects.create_user("api", password="pw12345!")
        self.client.login(username="api", password="pw12345!")
        resp = self.client.get(f"/api/item/{self.item.id}/pricing/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["price"], 5.0)
        self.assertIn("cost_price", data)
        self.assertIn("quantity_in_stock", data)

    def test_customer_autofill_endpoint(self):
        from accounts.models import Customer
        cust = Customer.objects.create(
            first_name="Ramesh", last_name="Iyer",
            email="r@x.com", phone="9876543210", address="MG Road",
        )
        User.objects.create_user("a", password="pw12345!")
        self.client.login(username="a", password="pw12345!")
        resp = self.client.get(f"/get-customer/{cust.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "Ramesh Iyer")
        self.assertEqual(data["phone"], "9876543210")
        self.assertEqual(data["email"], "r@x.com")
        self.assertEqual(data["address"], "MG Road")

    def test_vendor_autofill_endpoint(self):
        v = Vendor.objects.create(
            name="Acme Supplies", phone_number=9988776655,
            email="acme@x.com", address="Pune",
        )
        User.objects.create_user("b", password="pw12345!")
        self.client.login(username="b", password="pw12345!")
        resp = self.client.get(f"/get-vendor/{v.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "Acme Supplies")
        self.assertEqual(data["phone_number"], 9988776655)
        self.assertEqual(data["email"], "acme@x.com")
        self.assertEqual(data["address"], "Pune")

    def test_autofill_endpoints_require_login(self):
        from accounts.models import Customer
        cust = Customer.objects.create(first_name="X")
        v = Vendor.objects.create(name="Y")
        # Logged out from previous tests
        self.client.logout()
        self.assertEqual(self.client.get(f"/get-customer/{cust.id}/").status_code, 302)
        self.assertEqual(self.client.get(f"/get-vendor/{v.id}/").status_code, 302)

    def test_invoice_autofill_endpoint_with_linked_customer(self):
        """`/get-invoice/<id>/` returns customer details from FK + invoice fallback."""
        from accounts.models import Customer
        cust = Customer.objects.create(
            first_name="Anjali", last_name="Sharma",
            email="anjali@x.com", phone="9000011111", address="42 Brigade Rd",
        )
        inv = Invoice.objects.create(
            customer=cust,
            customer_name="Anjali Sharma", contact_number="9000011111",
            shipping_address="42 Brigade Rd, Bangalore",
            item=self.item, price_per_item=10.0, quantity=2, shipping=5,
        )
        User.objects.create_user("inv1", password="pw12345!")
        self.client.login(username="inv1", password="pw12345!")
        resp = self.client.get(f"/get-invoice/{inv.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["customer_id"], cust.id)
        self.assertEqual(data["customer_name"], "Anjali Sharma")
        self.assertEqual(data["email"], "anjali@x.com")
        self.assertEqual(data["phone"], "9000011111")
        # shipping_address takes precedence over customer.address
        self.assertEqual(data["address"], "42 Brigade Rd, Bangalore")
        self.assertEqual(data["item_id"], self.item.id)

    def test_invoice_autofill_endpoint_without_customer_fk(self):
        """Falls back to invoice's own customer_name/contact when no FK set."""
        inv = Invoice.objects.create(
            customer_name="Walk In", contact_number="9123456789",
            customer_email="walkin@x.com",
            item=self.item, price_per_item=1.0, quantity=1, shipping=0,
        )
        User.objects.create_user("inv2", password="pw12345!")
        self.client.login(username="inv2", password="pw12345!")
        data = self.client.get(f"/get-invoice/{inv.id}/").json()
        self.assertIsNone(data["customer_id"])
        self.assertEqual(data["customer_name"], "Walk In")
        self.assertEqual(data["email"], "walkin@x.com")
        self.assertEqual(data["phone"], "9123456789")

    def test_invoice_autofill_endpoint_requires_login(self):
        inv = Invoice.objects.create(
            customer_name="X", contact_number="1",
            item=self.item, price_per_item=1.0, quantity=1, shipping=0,
        )
        self.client.logout()
        self.assertEqual(
            self.client.get(f"/get-invoice/{inv.id}/").status_code, 302
        )

    def test_invoice_form_accepts_email_and_shipping_address(self):
        """InvoiceForm persists the new customer_email and shipping_address fields."""
        from invoice.forms import InvoiceForm
        form = InvoiceForm(data={
            "customer_name": "Ravi Kumar",
            "contact_number": "9999999999",
            "customer_email": "ravi@x.com",
            "shipping_address": "Plot 7, Sector 21",
            "item": self.item.id,
            "price_per_item": 10.0,
            "quantity": 1,
            "shipping": 0,
            "status": "PENDING",
        })
        self.assertTrue(form.is_valid(), form.errors)
        inv = form.save()
        self.assertEqual(inv.customer_email, "ravi@x.com")
        self.assertEqual(inv.shipping_address, "Plot 7, Sector 21")

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

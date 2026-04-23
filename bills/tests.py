from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from bills.models import Bill
from store.models import Item, Category
from accounts.models import Vendor


class BillModelTests(TestCase):
    def test_create_with_required_fields(self):
        b = Bill.objects.create(
            institution_name="Power Co",
            payment_details="Bank transfer",
            amount=125.50,
        )
        self.assertTrue(b.bill_number.startswith("BILL-"))
        self.assertEqual(b.status, "PENDING")
        self.assertTrue(b.slug)

    def test_status_toggle(self):
        b = Bill.objects.create(
            institution_name="Water", payment_details="x", amount=10
        )
        b.status = "PAID"
        b.save()
        b.refresh_from_db()
        self.assertEqual(b.status, "PAID")

    def test_bill_number_increments(self):
        b1 = Bill.objects.create(
            institution_name="A", payment_details="x", amount=10
        )
        b2 = Bill.objects.create(
            institution_name="B", payment_details="x", amount=20
        )
        n1 = int(b1.bill_number.split("-")[-1])
        n2 = int(b2.bill_number.split("-")[-1])
        self.assertEqual(n2, n1 + 1)

    def test_bill_with_item_increases_stock(self):
        cat = Category.objects.create(name="Cat")
        item = Item.objects.create(
            name="Widget", category=cat, quantity=5, price=10, cost_price=5
        )
        Bill.objects.create(
            institution_name="V", payment_details="x", amount=50,
            item=item, quantity=10, cost_price=5,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 15)

    def test_bill_delete_reduces_stock(self):
        cat = Category.objects.create(name="Cat2")
        item = Item.objects.create(
            name="Gadget", category=cat, quantity=0, price=10, cost_price=5
        )
        b = Bill.objects.create(
            institution_name="V", payment_details="x", amount=20,
            item=item, quantity=4, cost_price=5,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)
        b.delete()
        item.refresh_from_db()
        self.assertEqual(item.quantity, 0)


class BillViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw12345!")
        self.client.login(username="u", password="pw12345!")

    def test_list_ok(self):
        resp = self.client.get(reverse("bill_list"))
        self.assertEqual(resp.status_code, 200)

    def test_create_get(self):
        resp = self.client.get(reverse("bill_create"))
        self.assertEqual(resp.status_code, 200)

    def test_create_post(self):
        resp = self.client.post(reverse("bill_create"), {
            "institution_name": "ISP",
            "phone_number": 1234567890,
            "email": "a@b.com",
            "address": "x",
            "description": "Internet",
            "payment_details": "card",
            "quantity": 0,
            "cost_price": 0,
            "tax": 0,
            "amount": "50.00",
            "status": "PENDING",
        })
        self.assertIn(resp.status_code, (200, 302))
        self.assertTrue(Bill.objects.filter(institution_name="ISP").exists())

    def test_list_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("bill_list"))
        self.assertEqual(resp.status_code, 302)

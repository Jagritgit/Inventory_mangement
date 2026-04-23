from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from bills.models import Bill


class BillModelTests(TestCase):
    def test_create_with_required_fields(self):
        b = Bill.objects.create(
            institution_name="Power Co",
            payment_details="Bank transfer",
            amount=125.50,
        )
        self.assertEqual(str(b), "Power Co")
        self.assertFalse(b.status)
        self.assertTrue(b.slug)

    def test_status_toggle(self):
        b = Bill.objects.create(
            institution_name="Water", payment_details="x", amount=10
        )
        b.status = True
        b.save()
        b.refresh_from_db()
        self.assertTrue(b.status)


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
            "amount": "50.00",
            "status": False,
        })
        self.assertIn(resp.status_code, (200, 302))
        self.assertTrue(Bill.objects.filter(institution_name="ISP").exists())

    def test_list_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("bill_list"))
        self.assertEqual(resp.status_code, 302)

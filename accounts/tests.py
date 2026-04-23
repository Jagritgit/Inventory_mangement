from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Customer, Vendor, Profile


class CustomerModelTests(TestCase):
    def test_str_handles_missing_last_name(self):
        # Regression: previously raised TypeError when last_name was None.
        c = Customer.objects.create(first_name="Solo")
        self.assertEqual(str(c), "Solo")

    def test_full_name_with_last(self):
        c = Customer.objects.create(first_name="Ada", last_name="Lovelace")
        self.assertEqual(c.get_full_name(), "Ada Lovelace")

    def test_to_select2_shape(self):
        c = Customer.objects.create(first_name="X")
        self.assertEqual(set(c.to_select2().keys()), {"label", "value"})


class VendorModelTests(TestCase):
    def test_create_and_slug(self):
        v = Vendor.objects.create(name="Acme Corp")
        self.assertTrue(v.slug)
        self.assertEqual(str(v), "Acme Corp")


class ProfileSignalTests(TestCase):
    def test_profile_auto_created_for_user(self):
        # Tests the post_save signal in accounts/signals.py
        u = User.objects.create_user("newbie", password="pw12345!")
        self.assertTrue(Profile.objects.filter(user=u).exists())


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pw12345!")

    def test_login_success(self):
        ok = self.client.login(username="alice", password="pw12345!")
        self.assertTrue(ok)

    def test_login_wrong_password(self):
        ok = self.client.login(username="alice", password="wrong")
        self.assertFalse(ok)

    def test_login_page_renders(self):
        resp = self.client.get(reverse("user-login"))
        self.assertEqual(resp.status_code, 200)

    def test_logout_redirects(self):
        self.client.login(username="alice", password="pw12345!")
        # Django 5 LogoutView only accepts POST.
        resp = self.client.post(reverse("user-logout"))
        self.assertIn(resp.status_code, (200, 302))

    def test_protected_dashboard_redirects_when_anonymous(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)


class CustomerCRUDViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("carl", password="pw12345!")
        self.client.login(username="carl", password="pw12345!")

    def test_customer_list_ok(self):
        resp = self.client.get(reverse("customer_list"))
        self.assertEqual(resp.status_code, 200)

    def test_customer_create_and_delete(self):
        resp = self.client.post(reverse("customer_create"), {
            "first_name": "Jane", "last_name": "Doe",
            "address": "1 Main St", "email": "j@x.com",
            "phone": "555", "loyalty_points": 0,
        })
        self.assertIn(resp.status_code, (200, 302))
        c = Customer.objects.get(first_name="Jane")
        resp = self.client.post(
            reverse("customer_delete", kwargs={"pk": c.pk})
        )
        self.assertIn(resp.status_code, (200, 302))
        self.assertFalse(Customer.objects.filter(pk=c.pk).exists())


class VendorCRUDViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("dee", password="pw12345!")
        self.client.login(username="dee", password="pw12345!")

    def test_vendor_list_ok(self):
        resp = self.client.get(reverse("vendor-list"))
        self.assertEqual(resp.status_code, 200)

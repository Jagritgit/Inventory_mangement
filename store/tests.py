from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Vendor
from store.models import Category, Item, Delivery
from store.forms import ItemForm, CategoryForm


class CategoryModelTests(TestCase):
    def test_category_str_and_slug(self):
        c = Category.objects.create(name="Beverages")
        self.assertIn("Beverages", str(c))
        self.assertTrue(c.slug)


class ItemModelTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Snacks")
        self.vendor = Vendor.objects.create(name="Acme")

    def test_item_creation_defaults(self):
        item = Item.objects.create(
            name="Chips", description="x", category=self.cat, vendor=self.vendor
        )
        self.assertEqual(item.quantity, 0)
        self.assertEqual(item.price, 0)
        self.assertEqual(item.cost_price, 0)
        self.assertTrue(item.slug)
        self.assertIn("Chips", str(item))

    def test_item_to_json_contains_required_keys(self):
        item = Item.objects.create(
            name="Soda", description="x", category=self.cat,
            vendor=self.vendor, quantity=5, price=10
        )
        data = item.to_json()
        for key in ("id", "text", "category", "quantity", "total_product"):
            self.assertIn(key, data)
        self.assertEqual(data["text"], "Soda")
        self.assertEqual(data["category"], "Snacks")


class ItemFormTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="A")
        self.vendor = Vendor.objects.create(name="V")

    def test_required_fields(self):
        form = ItemForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_valid_form(self):
        form = ItemForm(data={
            "name": "Bread", "description": "fresh",
            "category": self.cat.id, "quantity": 5, "price": 1.50,
            "vendor": self.vendor.id,
        })
        self.assertTrue(form.is_valid(), form.errors)


class CategoryFormTests(TestCase):
    def test_invalid_when_empty(self):
        self.assertFalse(CategoryForm(data={}).is_valid())

    def test_valid(self):
        self.assertTrue(CategoryForm(data={"name": "Books"}).is_valid())


class StoreViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("alice", password="pw12345!")
        self.cat = Category.objects.create(name="Tools")
        self.vendor = Vendor.objects.create(name="Vend")

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_ok_when_logged_in(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_handles_empty_db(self):
        # Regression: total_items aggregate returned None; template iterating
        # categories must still render.
        self.client.login(username="alice", password="pw12345!")
        Category.objects.all().delete()
        Item.objects.all().delete()
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_product_list_requires_login(self):
        resp = self.client.get(reverse("productslist"))
        self.assertEqual(resp.status_code, 302)

    def test_product_list_ok(self):
        Item.objects.create(
            name="Hammer", description="x", category=self.cat,
            vendor=self.vendor, quantity=3, price=9
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("productslist"))
        self.assertEqual(resp.status_code, 200)

    def test_product_create_view_get(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("product-create"))
        self.assertEqual(resp.status_code, 200)

    def test_product_create_post_creates_item(self):
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.post(reverse("product-create"), {
            "name": "Saw", "description": "tool",
            "category": self.cat.id, "quantity": 4, "price": 12.5,
            "vendor": self.vendor.id,
        })
        self.assertIn(resp.status_code, (200, 302))
        self.assertTrue(Item.objects.filter(name="Saw").exists())

    def test_product_update_requires_superuser(self):
        item = Item.objects.create(
            name="Drill", description="x", category=self.cat,
            vendor=self.vendor, quantity=1, price=5
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(
            reverse("product-update", kwargs={"slug": item.slug})
        )
        self.assertEqual(resp.status_code, 403)

    def test_item_search_filters(self):
        Item.objects.create(
            name="WidgetX", description="x", category=self.cat,
            vendor=self.vendor, quantity=1, price=1
        )
        Item.objects.create(
            name="Other", description="x", category=self.cat,
            vendor=self.vendor, quantity=1, price=1
        )
        self.client.login(username="alice", password="pw12345!")
        resp = self.client.get(reverse("item_search_list_view"), {"q": "Widget"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "WidgetX")
        self.assertNotContains(resp, "Other")


class CategoryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bob", password="pw12345!")
        self.client.login(username="bob", password="pw12345!")

    def test_category_create_post(self):
        resp = self.client.post(reverse("category-create"), {"name": "New Cat"})
        self.assertIn(resp.status_code, (200, 302))
        self.assertTrue(Category.objects.filter(name="New Cat").exists())

    def test_category_list_ok(self):
        resp = self.client.get(reverse("category-list"))
        self.assertEqual(resp.status_code, 200)


class DeliveryModelTests(TestCase):
    def test_delivery_create(self):
        from django.utils import timezone
        cat = Category.objects.create(name="C")
        vendor = Vendor.objects.create(name="V")
        item = Item.objects.create(
            name="I", description="x", category=cat, vendor=vendor
        )
        d = Delivery.objects.create(
            item=item, customer_name="Joe", date=timezone.now()
        )
        self.assertFalse(d.is_delivered)
        self.assertIn("Joe", str(d))

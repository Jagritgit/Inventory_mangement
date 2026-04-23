"""
Seed the database with realistic Indian-market sample data.

Usage:
    python manage.py migrate
    python manage.py seed_data
    python manage.py seed_data --flush   # wipe sample data first
"""
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from accounts.models import Vendor, Customer
from store.models import Category, Item, Delivery
from transactions.models import Sale, SaleDetail


ADMIN_USERNAME = "jagrit"
ADMIN_PASSWORD = "JK810jkup"
ADMIN_EMAIL = "jagrit@example.com"

CATEGORIES = [
    "Electronics", "Accessories", "Appliances", "Furniture",
    "Stationery", "FMCG", "Clothing", "Hardware & Tools",
]

VENDORS = [
    ("Sharma Traders",       9876543210, "Karol Bagh, New Delhi"),
    ("Gupta Electronics",    9823456712, "Lamington Road, Mumbai"),
    ("Reddy Supplies",       9849123456, "Ameerpet, Hyderabad"),
    ("Patel Distributors",   9879012345, "C G Road, Ahmedabad"),
    ("Khan Hardware Store",  9812345678, "Chandni Chowk, Delhi"),
    ("Iyer Wholesale",       9840012345, "T Nagar, Chennai"),
]

CUSTOMERS = [
    ("Rahul",  "Sharma", "rahul.sharma@example.in",  "9810011001"),
    ("Priya",  "Reddy",  "priya.reddy@example.in",   "9849022002"),
    ("Amit",   "Patel",  "amit.patel@example.in",    "9879033003"),
    ("Sneha",  "Verma",  "sneha.verma@example.in",   "9820044004"),
    ("Arjun",  "Mehta",  "arjun.mehta@example.in",   "9811055005"),
    ("Kavya",  "Iyer",   "kavya.iyer@example.in",    "9840066006"),
    ("Rohit",  "Singh",  "rohit.singh@example.in",   "9830077007"),
    ("Anjali", "Nair",   "anjali.nair@example.in",   "9847088008"),
]

# (name, category, sku, cost_price, price, qty, low_stock_threshold)
PRODUCTS = [
    ("Redmi Note 13",        "Electronics", "MOB-RDM-013",  12000, 15999, 25, 5),
    ("Samsung Galaxy M14",   "Electronics", "MOB-SMG-M14",  10500, 13499, 18, 5),
    ("HP 15s Laptop",        "Electronics", "LAP-HP-015S",  38000, 45990, 8,  3),
    ("Dell Inspiron 3520",   "Electronics", "LAP-DL-3520",  41000, 49990, 6,  3),
    ("Boat Rockerz 450",     "Accessories", "ACC-BT-R450",  900,   1499,  40, 10),
    ("USB-C Charger 25W",    "Accessories", "ACC-CHG-25W",  450,   799,   60, 15),
    ("Bajaj Mixer Grinder",  "Appliances",  "APL-BJ-MX01",  2200,  3299,  15, 4),
    ("Prestige Iron Box",    "Appliances",  "APL-PR-IRN1",  650,   999,   22, 5),
    ("Nilkamal Plastic Chair","Furniture",  "FRN-NK-CHR1",  550,   899,   30, 8),
    ("Godrej Office Table",  "Furniture",   "FRN-GJ-TBL1",  3800,  5499,  5,  2),
    ("Classmate Notebook",   "Stationery",  "STN-CM-NB01",  35,    60,    200,30),
    ("Reynolds Pen (10 pk)", "Stationery",  "STN-RY-PN10",  80,    120,   150,25),
    ("Parle-G Biscuit Pack", "FMCG",        "FMG-PG-BSC1",  8,     12,    500,50),
    ("Lay's Magic Masala",   "FMCG",        "FMG-LY-MSL1",  15,    20,    300,40),
    ("Levi's Slim Jeans",    "Clothing",    "CLT-LV-JNS1",  1500,  2499,  20, 5),
    ("US Polo T-Shirt",      "Clothing",    "CLT-USP-TS1",  600,   999,   35, 8),
    ("Stanley Hammer",       "Hardware & Tools", "HWT-ST-HMR1", 350, 549, 18, 5),
    ("Bosch Drill Machine",  "Hardware & Tools", "HWT-BS-DRL1", 2900,3999,10, 3),
]


class Command(BaseCommand):
    help = "Seed the database with Indian-market sample data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete existing sample data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["flush"]:
            self.stdout.write(self.style.WARNING("Flushing sample data..."))
            SaleDetail.objects.all().delete()
            Sale.objects.all().delete()
            Delivery.objects.all().delete()
            Item.objects.all().delete()
            Category.objects.all().delete()
            Vendor.objects.all().delete()
            Customer.objects.all().delete()

        self._create_admin()
        cats = self._create_categories()
        vendors = self._create_vendors()
        customers = self._create_customers()
        items = self._create_products(cats, vendors)
        sales = self._create_sales(customers, items)
        self._create_deliveries(sales, items)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Admin: {ADMIN_USERNAME} / {ADMIN_PASSWORD}"
        ))

    def _create_admin(self):
        user, created = User.objects.get_or_create(
            username=ADMIN_USERNAME,
            defaults={"email": ADMIN_EMAIL, "is_staff": True, "is_superuser": True},
        )
        user.is_staff = True
        user.is_superuser = True
        user.email = ADMIN_EMAIL
        user.set_password(ADMIN_PASSWORD)
        user.save()
        self.stdout.write(
            f"  admin {'created' if created else 'updated'}: {ADMIN_USERNAME}"
        )

    def _create_categories(self):
        cats = {}
        for name in CATEGORIES:
            cats[name], _ = Category.objects.get_or_create(name=name)
        self.stdout.write(f"  categories: {len(cats)}")
        return cats

    def _create_vendors(self):
        vendors = []
        for name, phone, address in VENDORS:
            v, _ = Vendor.objects.get_or_create(
                name=name,
                defaults={"phone_number": phone, "address": address},
            )
            v.phone_number = phone
            v.address = address
            v.save()
            vendors.append(v)
        self.stdout.write(f"  vendors: {len(vendors)}")
        return vendors

    def _create_customers(self):
        customers = []
        for first, last, email, phone in CUSTOMERS:
            c, _ = Customer.objects.get_or_create(
                first_name=first, last_name=last,
                defaults={"email": email, "phone": phone, "address": "India"},
            )
            customers.append(c)
        self.stdout.write(f"  customers: {len(customers)}")
        return customers

    def _create_products(self, cats, vendors):
        items = []
        for name, cat_name, sku, cost, price, qty, threshold in PRODUCTS:
            item, _ = Item.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "description": f"{name} - sample stock for demo.",
                    "category": cats[cat_name],
                    "vendor": random.choice(vendors),
                    "quantity": qty,
                    "price": price,
                    "cost_price": cost,
                    "low_stock_threshold": threshold,
                },
            )
            # Sync values if item already existed.
            item.name = name
            item.category = cats[cat_name]
            item.quantity = qty
            item.price = price
            item.cost_price = cost
            item.low_stock_threshold = threshold
            item.save()
            items.append(item)
        self.stdout.write(f"  products: {len(items)}")
        return items

    def _create_sales(self, customers, items):
        """Create sample sales; reduce stock; never go negative."""
        sales = []
        random.seed(42)
        for _ in range(8):
            customer = random.choice(customers)
            chosen = random.sample(items, k=random.randint(1, 3))

            sub_total = Decimal("0.00")
            details = []
            for item in chosen:
                if item.quantity <= 0:
                    continue
                qty = random.randint(1, min(3, item.quantity))
                line_total = Decimal(str(item.price)) * qty
                sub_total += line_total
                details.append((item, qty, line_total))

            if not details:
                continue

            tax_pct = 18.0  # GST
            tax_amount = (sub_total * Decimal("0.18")).quantize(Decimal("0.01"))
            grand_total = sub_total + tax_amount

            sale = Sale.objects.create(
                customer=customer,
                sub_total=sub_total,
                grand_total=grand_total,
                tax_amount=tax_amount,
                tax_percentage=tax_pct,
                amount_paid=grand_total,
                amount_change=Decimal("0.00"),
            )
            for item, qty, line_total in details:
                SaleDetail.objects.create(
                    sale=sale, item=item,
                    price=Decimal(str(item.price)),
                    quantity=qty, total_detail=line_total,
                )
                # Phase 4 logic requirement: prevent negative stock.
                item.quantity = max(0, item.quantity - qty)
                item.save()
            sales.append(sale)

        self.stdout.write(f"  sales: {len(sales)}")
        return sales

    def _create_deliveries(self, sales, items):
        """Create deliveries linked to sale items (Pending / Delivered)."""
        deliveries = 0
        now = timezone.now()
        for sale in sales:
            for detail in sale.saledetail_set.all():
                Delivery.objects.create(
                    item=detail.item,
                    customer_name=sale.customer.get_full_name(),
                    phone_number=None,
                    location=random.choice([
                        "Mumbai", "Delhi", "Hyderabad",
                        "Bengaluru", "Chennai", "Pune",
                    ]),
                    date=now,
                    is_delivered=random.choice([True, False]),
                )
                deliveries += 1
        self.stdout.write(f"  deliveries: {deliveries}")

# Django core imports
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

# Local app imports
from .views import (
    # Purchases
    PurchaseListView,
    PurchaseDetailView,
    PurchaseCreateView,
    PurchaseUpdateView,
    PurchaseDeleteView,

    # Sales
    SaleListView,
    SaleDetailView,
    SaleCreateView,
    SaleDeleteView,

    # Export
    export_sales_to_excel,
    export_purchases_to_excel,

    # 🔍 IMPORTANT (for item search)
    get_items
)

urlpatterns = [

    # =========================
    # 🔍 ITEM SEARCH (CRITICAL)
    # =========================
    path('get-items/', get_items, name='get_items'),

    # =========================
    # 📦 PURCHASES
    # =========================
    path('purchases/', PurchaseListView.as_view(), name='purchaseslist'),
    path('purchases/create/', PurchaseCreateView.as_view(), name='purchase-create'),
    path('purchases/<int:pk>/', PurchaseDetailView.as_view(), name='purchase-detail'),
    path('purchases/<int:pk>/update/', PurchaseUpdateView.as_view(), name='purchase-update'),
    path('purchases/<int:pk>/delete/', PurchaseDeleteView.as_view(), name='purchase-delete'),

    # =========================
    # 🧾 SALES
    # =========================
    path('sales/', SaleListView.as_view(), name='saleslist'),
    path('sales/create/', SaleCreateView, name='sale-create'),
    path('sales/<int:pk>/', SaleDetailView.as_view(), name='sale-detail'),
    path('sales/<int:pk>/delete/', SaleDeleteView.as_view(), name='sale-delete'),

    # =========================
    # 📤 EXPORT
    # =========================
    path('sales/export/', export_sales_to_excel, name='sales-export'),
    path('purchases/export/', export_purchases_to_excel, name='purchases-export'),
]

# Static media files (development only)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
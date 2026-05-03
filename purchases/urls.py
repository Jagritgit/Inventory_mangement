from django.urls import path
from .views import (
    PurchaseOrderListView,
    PurchaseOrderDetailView,
    PurchaseOrderCreateView,
    PurchaseOrderUpdateView,
    PurchaseOrderDeleteView,
    MarkReceivedView,
    PurchaseBillListView,
    PurchaseBillDetailView,
    CreatePurchaseBillView,
    ManualPurchaseBillCreateView,
    ToggleBillStatusView,
)

urlpatterns = [
    # ── Purchase Bills (static prefixes MUST precede <slug:slug>) ──────────
    path('bills/',                        PurchaseBillListView.as_view(),         name='purchase-bill-list'),
    path('bills/new/',                    ManualPurchaseBillCreateView.as_view(), name='purchase-bill-manual-create'),
    path('bills/<slug:slug>/',            PurchaseBillDetailView.as_view(),       name='purchase-bill-detail'),
    path('bills/<int:pk>/toggle-status/', ToggleBillStatusView.as_view(),         name='purchase-bill-toggle-status'),

    # ── Purchase Orders ─────────────────────────────────────────────────────
    path('',                        PurchaseOrderListView.as_view(),   name='purchase-order-list'),
    path('new/',                    PurchaseOrderCreateView.as_view(), name='purchase-order-create'),
    path('<int:pk>/delete/',        PurchaseOrderDeleteView.as_view(), name='purchase-order-delete'),
    path('<int:pk>/mark-received/', MarkReceivedView.as_view(),        name='purchase-order-mark-received'),
    path('<int:pk>/create-bill/',   CreatePurchaseBillView.as_view(),  name='purchase-bill-create'),
    # slug patterns last — catch-alls within this prefix
    path('<slug:slug>/',            PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('<slug:slug>/edit/',       PurchaseOrderUpdateView.as_view(), name='purchase-order-update'),
]

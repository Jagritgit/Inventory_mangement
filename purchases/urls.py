from django.urls import path
from .views import (
    PurchaseOrderListView,
    PurchaseOrderDetailView,
    PurchaseOrderCreateView,
    PurchaseOrderUpdateView,
    PurchaseOrderDeleteView,
    MarkReceivedView,
)

urlpatterns = [
    path('',                         PurchaseOrderListView.as_view(),   name='purchase-order-list'),
    path('new/',                     PurchaseOrderCreateView.as_view(), name='purchase-order-create'),
    path('<slug:slug>/',             PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('<slug:slug>/edit/',        PurchaseOrderUpdateView.as_view(), name='purchase-order-update'),
    path('<int:pk>/delete/',         PurchaseOrderDeleteView.as_view(), name='purchase-order-delete'),
    path('<int:pk>/mark-received/',  MarkReceivedView.as_view(),        name='purchase-order-mark-received'),
]

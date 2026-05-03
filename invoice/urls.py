from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    InvoiceListView,
    InvoiceDetailView,
    InvoiceDeleteView,
    invoice_create,
    invoice_update,
    create_invoice_from_sale,
)

urlpatterns = [
    path('invoices/',                          InvoiceListView.as_view(),   name='invoicelist'),
    path('invoice/<slug:slug>/',               InvoiceDetailView.as_view(), name='invoice-detail'),
    path('new-invoice/',                       invoice_create,              name='invoice-create'),
    path('invoice/<slug:slug>/update/',        invoice_update,              name='invoice-update'),
    path('invoice/<int:pk>/delete/',           InvoiceDeleteView.as_view(), name='invoice-delete'),
    path('invoice/from-sale/<int:sale_id>/',   create_invoice_from_sale,    name='invoice-from-sale'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

import django_tables2 as tables
from .models import Invoice


class InvoiceTable(tables.Table):
    class Meta:
        model = Invoice
        template_name = "django_tables2/semantic.html"
        fields = ('invoice_number', 'date', 'customer_name', 'contact_number', 'grand_total', 'status')
        order_by = 'date'

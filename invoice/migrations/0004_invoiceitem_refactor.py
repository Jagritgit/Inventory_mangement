from django.db import migrations, models
import django.db.models.deletion


def migrate_single_item_to_invoiceitem(apps, schema_editor):
    """Convert each existing Invoice's single item into an InvoiceItem row."""
    Invoice = apps.get_model('invoice', 'Invoice')
    InvoiceItem = apps.get_model('invoice', 'InvoiceItem')

    for inv in Invoice.objects.all():
        if inv.item_id:
            qty = max(1, int(float(inv.quantity or 1)))
            price = float(inv.price_per_item or 0)
            InvoiceItem.objects.create(
                invoice=inv,
                product_id=inv.item_id,
                quantity=qty,
                price=price,
            )
            subtotal = qty * price
            grand = round(subtotal + float(inv.shipping or 0), 2)
            Invoice.objects.filter(pk=inv.pk).update(grand_total=grand)


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '0003_invoice_customer_email_invoice_shipping_address'),
        ('store', '0004_delivery_customer_delivery_email_delivery_invoice_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('invoice', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='invoice.invoice',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='invoice_items',
                    to='store.item',
                )),
            ],
            options={'ordering': ['id']},
        ),
        migrations.RunPython(migrate_single_item_to_invoiceitem, migrations.RunPython.noop),
        migrations.RemoveField(model_name='invoice', name='item'),
        migrations.RemoveField(model_name='invoice', name='price_per_item'),
        migrations.RemoveField(model_name='invoice', name='quantity'),
        migrations.RemoveField(model_name='invoice', name='total'),
    ]

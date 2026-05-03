from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '0004_invoiceitem_refactor'),
        ('transactions', '0003_alter_purchase_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='sale',
            field=models.OneToOneField(
                blank=True,
                help_text='The POS Sale this invoice was generated from, if any.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invoice',
                to='transactions.sale',
            ),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='contact_number',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]

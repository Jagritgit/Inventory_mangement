from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_delivery_customer_delivery_email_delivery_invoice_and_more'),
        ('transactions', '0003_alter_purchase_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='delivery',
            name='sale',
            field=models.OneToOneField(
                blank=True,
                help_text='The Sale this delivery fulfils. NULL = manual delivery.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='delivery',
                to='transactions.sale',
            ),
        ),
        migrations.AddField(
            model_name='delivery',
            name='status',
            field=models.CharField(
                choices=[('PENDING', 'Pending'), ('SHIPPED', 'Shipped'), ('DELIVERED', 'Delivered')],
                db_index=True,
                default='PENDING',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='delivery',
            name='shipped_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='delivery',
            name='delivered_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='delivery',
            name='date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='delivery',
            options={'ordering': ['-id']},
        ),
    ]

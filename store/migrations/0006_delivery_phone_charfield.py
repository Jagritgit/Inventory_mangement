from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0005_delivery_sale_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='phone_number',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]

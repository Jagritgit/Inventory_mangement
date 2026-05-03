from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0004_alter_purchasebill_purchase_order'),
    ]

    operations = [
        # Rename price → price_per_item (no data loss, no default needed)
        migrations.RenameField(
            model_name='purchaseorderitem',
            old_name='price',
            new_name='price_per_item',
        ),
        # Drop expected_date (nullable, safe to remove)
        migrations.RemoveField(
            model_name='purchaseorder',
            name='expected_date',
        ),
    ]

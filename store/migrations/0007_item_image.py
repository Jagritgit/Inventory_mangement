from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_delivery_phone_charfield'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='image',
            field=models.ImageField(
                blank=True, null=True,
                upload_to='products/',
                help_text='Product image (optional). JPG / PNG / WebP.'
            ),
        ),
    ]

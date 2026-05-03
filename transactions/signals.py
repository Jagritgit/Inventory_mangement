from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Purchase, Sale


@receiver(post_save, sender=Purchase)
def update_item_quantity(sender, instance, created, **kwargs):
    """
    Increment item stock only when a new Purchase is created.
    Not on updates — avoids double-increment.
    """
    if created:
        instance.item.quantity += instance.quantity
        instance.item.save()


@receiver(post_save, sender=Sale)
def auto_create_delivery(sender, instance, created, **kwargs):
    """
    Automatically create a Delivery record in PENDING status
    whenever a new Sale is saved.

    Duplicate guard: does nothing if a Delivery already exists for this Sale.
    Revenue logic is NOT touched here.
    """
    if not created:
        return

    from store.models import Delivery

    if Delivery.objects.filter(sale=instance).exists():
        return

    customer = instance.customer
    Delivery.objects.create(
        sale=instance,
        customer=customer,
        customer_name=customer.get_full_name() if customer else "",
        email=getattr(customer, 'email', '') or "",
        phone_number=None,
        location=getattr(customer, 'address', '') or "",
        status='PENDING',
    )

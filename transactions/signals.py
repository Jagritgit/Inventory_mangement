from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Purchase


# BUG FIX #2: The original signal ALSO incremented item.quantity on every
# post_save (including updates), AND models.py save() did the same — resulting
# in stock being doubled on every save. Now the signal correctly only runs
# on `created=True` (new purchases), and models.py save() no longer touches
# item quantity at all.
@receiver(post_save, sender=Purchase)
def update_item_quantity(sender, instance, created, **kwargs):
    """
    Signal to update item quantity only when a NEW purchase is created.
    """
    if created:
        instance.item.quantity += instance.quantity
        instance.item.save()

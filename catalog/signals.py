from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Book


@receiver(post_save, sender=Book)
def assign_queue_on_stock_change(sender, instance, created, **kwargs):
    if created or instance.available_copies <= 0:
        return
    from loans.models import Loan
    Loan.assign_free_copies(instance)

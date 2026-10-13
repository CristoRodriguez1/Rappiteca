from django.db.models.signals import post_save
from django.dispatch import receiver

from loans.models import Loan


@receiver(post_save, sender=Loan)
def apply_fine_on_return(sender, instance, created, **kwargs):
    """
    FR-23/FR-24: when the admin marks a late loan as returned, the fine is
    calculated with the real return date and applied right away, even if
    the daily calculate_fines command has not run yet.
    """
    if created or instance.status != Loan.STATUS_RETURNED:
        return
    from .services import apply_fine
    apply_fine(instance)

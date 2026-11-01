from decimal import Decimal

from django.db import models

from accounts.models import User
from loans.models import Loan


# FR-23 Calculate fine / FR-24 Apply fine
class Fine(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
    ]

    # One fine per loan: while the loan stays overdue the same record is
    # recalculated, so the user never gets duplicated charges for one book.
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='fine')
    # FR-24: the fine is applied to the user's account through this relation.
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fines')

    days_overdue = models.PositiveIntegerField(default=0)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # True once the book was returned: the amount stops growing.
    is_final = models.BooleanField(default=False)

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']

    @property
    def due_date(self):
        from .services import loan_due_date
        return loan_due_date(self.loan)

    def __str__(self):
        return f'{self.user.email} - {self.loan.book.title}: {self.amount} [{self.status}]'

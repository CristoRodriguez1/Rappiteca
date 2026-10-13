"""
FR-23 Calculate fine
IF a loan becomes overdue THEN THE Rappiteca system SHOULD automatically
calculate the corresponding fine based on the number of overdue days.

FR-24 Apply fine
IF a fine has been calculated for a user THEN THE Rappiteca system SHOULD
apply the fine to the user's account within 3 seconds.
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from loans.models import Loan

from .models import Fine

# Same loan period used by Loan.due_date: 14 days, plus 14 more per renewal.
LOAN_PERIOD_DAYS = 14

# Amount charged per overdue day. Can be overridden with FINE_DAILY_RATE in settings.
DEFAULT_DAILY_RATE = Decimal('1000.00')


def get_daily_rate():
    return Decimal(str(getattr(settings, 'FINE_DAILY_RATE', DEFAULT_DAILY_RATE)))


def loan_due_date(loan):
    """
    Due date of a loan, also for loans that were already returned
    (Loan.due_date only works while the loan is borrowed).
    """
    if not loan.pickup_date:
        return None
    return loan.pickup_date + timedelta(days=LOAN_PERIOD_DAYS * (1 + loan.renewals))


def calculate_fine(loan, today=None):
    """
    FR-23: returns (days_overdue, amount) for a loan.

    Overdue days are counted until today for borrowed loans, and until the
    return date for returned loans. A loan that is not late gives (0, 0).
    """
    due = loan_due_date(loan)
    if due is None or loan.status not in (Loan.STATUS_BORROWED, Loan.STATUS_RETURNED):
        return 0, Decimal('0.00')

    if loan.status == Loan.STATUS_RETURNED and loan.return_date:
        end_date = timezone.localdate(loan.return_date)
    else:
        end_date = today or timezone.localdate()

    days_overdue = (end_date - timezone.localdate(due)).days
    if days_overdue <= 0:
        return 0, Decimal('0.00')

    amount = (get_daily_rate() * days_overdue).quantize(Decimal('0.01'))
    return days_overdue, amount


def apply_fine(loan, today=None):
    """
    FR-24: calculates the fine of a loan and applies it to the user's account.

    Creates the Fine the first time the loan is late and updates it on later
    runs while the book is still out. Paid or final fines are not touched.
    Returns the Fine, or None if the loan is not overdue.
    """
    days_overdue, amount = calculate_fine(loan, today=today)
    if days_overdue == 0:
        return None

    with transaction.atomic():
        fine = Fine.objects.select_for_update().filter(loan=loan).first()

        if fine is None:
            fine = Fine.objects.create(
                loan=loan,
                user=loan.user,
                days_overdue=days_overdue,
                daily_rate=get_daily_rate(),
                amount=amount,
                is_final=loan.status == Loan.STATUS_RETURNED,
            )
            return fine

        if fine.status == Fine.STATUS_PAID or fine.is_final:
            return fine

        fine.days_overdue = days_overdue
        fine.amount = (fine.daily_rate * days_overdue).quantize(Decimal('0.01'))
        fine.is_final = loan.status == Loan.STATUS_RETURNED
        fine.save()
        return fine


def apply_overdue_fines(today=None):
    """
    Applies fines to every borrowed loan that is past its due date.
    Returns the list of fines created or updated.
    """
    fines = []
    loans = Loan.objects.filter(
        status=Loan.STATUS_BORROWED,
        pickup_date__isnull=False,
    ).select_related('user', 'book')

    for loan in loans:
        fine = apply_fine(loan, today=today)
        if fine is not None:
            fines.append(fine)
    return fines


def user_pending_fines_total(user):
    """FR-24: total pending amount on a user's account."""
    total = Fine.objects.filter(user=user, status=Fine.STATUS_PENDING).aggregate(
        total=Sum('amount')
    )['total']
    return total or Decimal('0.00')

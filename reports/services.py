"""
FR-31 Most borrowed books
IF an administrator requests the most-borrowed-books report THEN THE Rappiteca
system SHOULD generate and display the report within 5 seconds.

FR-32 Overdue fines report
IF an administrator requests the overdue rates report THEN THE Rappiteca
system SHOULD generate and display the report within 5 seconds.

Both reports are built with aggregate queries (one GROUP BY per table) so the
time does not grow with one query per book or per user.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from catalog.models import Book
from fines.models import Fine
from fines.services import calculate_fine
from loans.models import Loan

# Periods the admin can pick in both reports: value -> (label, days or None = all time)
PERIODS = {
    '30': ('Last 30 days', 30),
    '90': ('Last 90 days', 90),
    '365': ('Last 12 months', 365),
    'all': ('All time', None),
}
DEFAULT_PERIOD = 'all'

# A loan only counts as "borrowed" once the book left the library.
# Reservations that were never picked up or were cancelled do not count.
BORROWED_STATUSES = (Loan.STATUS_BORROWED, Loan.STATUS_RETURNED)


def clean_period(value):
    return value if value in PERIODS else DEFAULT_PERIOD


def period_start(period, now=None):
    days = PERIODS[clean_period(period)][1]
    if days is None:
        return None
    return (now or timezone.now()) - timedelta(days=days)


def _percent(part, total):
    if not total:
        return 0.0
    return round(part * 100.0 / total, 1)


# ---------------------------------------------------------------------------
# FR-31 Most borrowed books
# ---------------------------------------------------------------------------

def most_borrowed_books(period=DEFAULT_PERIOD, limit=10):
    """
    Returns the books ordered by how many times they were borrowed in the period.

    Each row has: book, times_borrowed, borrowers (distinct users), currently_out,
    share (% of all borrows in the period) and bar (width 0-100 relative to the top book).
    """
    start = period_start(period)
    loan_filter = Q(loans__status__in=BORROWED_STATUSES)
    if start is not None:
        loan_filter &= Q(loans__pickup_date__gte=start)

    books = (
        Book.objects
        .annotate(
            times_borrowed=Count('loans', filter=loan_filter),
            borrowers=Count('loans__user', filter=loan_filter, distinct=True),
            currently_out=Count('loans', filter=Q(loans__status=Loan.STATUS_BORROWED)),
        )
        .filter(times_borrowed__gt=0)
        .order_by('-times_borrowed', '-borrowers', 'title')
    )

    total_borrows = sum(b.times_borrowed for b in books)
    top = books[:limit]
    max_count = top[0].times_borrowed if top else 0

    rows = []
    for position, book in enumerate(top, start=1):
        rows.append({
            'rank': position,
            'book': book,
            'times_borrowed': book.times_borrowed,
            'borrowers': book.borrowers,
            'currently_out': book.currently_out,
            'share': _percent(book.times_borrowed, total_borrows),
            'bar': round(book.times_borrowed * 100 / max_count) if max_count else 0,
        })

    # Borrows grouped by category, to see which kind of book moves the most
    categories = {}
    for book in books:
        name = book.category or 'Uncategorized'
        categories[name] = categories.get(name, 0) + book.times_borrowed
    category_rows = [
        {'name': name, 'count': count, 'share': _percent(count, total_borrows)}
        for name, count in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
    ]

    return {
        'rows': rows,
        'categories': category_rows,
        'total_borrows': total_borrows,
        'books_with_borrows': len(books),
        'total_books': Book.objects.count(),
    }


# ---------------------------------------------------------------------------
# FR-32 Overdue fines report
# ---------------------------------------------------------------------------

def overdue_fines_report(period=DEFAULT_PERIOD, today=None):
    """
    Overdue rate of the loans picked up in the period and the state of their fines.

    - overdue rate = loans that went past their due date / loans that were picked up
    - fines are grouped by status (pending, awaiting confirmation, paid)
    """
    start = period_start(period)

    loans = Loan.objects.filter(
        status__in=BORROWED_STATUSES, pickup_date__isnull=False,
    ).select_related('user', 'book')
    if start is not None:
        loans = loans.filter(pickup_date__gte=start)

    total_loans = 0
    overdue_loans = 0
    overdue_now = []          # still out and late
    by_category = {}

    for loan in loans:
        days_overdue, amount = calculate_fine(loan, today=today)
        total_loans += 1
        category = loan.book.category or 'Uncategorized'
        stats = by_category.setdefault(category, {'name': category, 'loans': 0, 'overdue': 0})
        stats['loans'] += 1
        if days_overdue > 0:
            overdue_loans += 1
            stats['overdue'] += 1
            if loan.status == Loan.STATUS_BORROWED:
                overdue_now.append({'loan': loan, 'days_overdue': days_overdue, 'amount': amount})

    for stats in by_category.values():
        stats['rate'] = _percent(stats['overdue'], stats['loans'])
    category_rows = sorted(by_category.values(), key=lambda s: (-s['rate'], -s['overdue'], s['name']))
    overdue_now.sort(key=lambda row: -row['days_overdue'])

    fines = Fine.objects.all()
    if start is not None:
        fines = fines.filter(loan__pickup_date__gte=start)

    def _sum(queryset):
        return queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    pending_total = _sum(fines.filter(status=Fine.STATUS_PENDING))
    requested_total = _sum(fines.filter(status=Fine.STATUS_PAYMENT_REQUESTED))
    paid_total = _sum(fines.filter(status=Fine.STATUS_PAID))
    fined_total = pending_total + requested_total + paid_total

    # Users with the highest amount still to pay (pending + awaiting confirmation)
    top_debtors = (
        fines.exclude(status=Fine.STATUS_PAID)
        .values('user__id', 'user__name', 'user__last_name', 'user__email')
        .annotate(owed=Sum('amount'), fines_count=Count('id'))
        .order_by('-owed')[:10]
    )

    return {
        'total_loans': total_loans,
        'overdue_loans': overdue_loans,
        'on_time_loans': total_loans - overdue_loans,
        'overdue_rate': _percent(overdue_loans, total_loans),
        'on_time_rate': _percent(total_loans - overdue_loans, total_loans),
        'categories': category_rows,
        'overdue_now': overdue_now,
        'fines_count': fines.count(),
        'fined_total': fined_total,
        'pending_total': pending_total,
        'requested_total': requested_total,
        'paid_total': paid_total,
        'collection_rate': _percent(float(paid_total), float(fined_total)),
        'top_debtors': list(top_debtors),
    }

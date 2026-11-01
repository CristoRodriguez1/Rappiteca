"""
FR-28 Users information.

IF an administrator selects a registered user THEN THE Rappiteca system SHOULD
display the user's profile information within 3 seconds.
"""

from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from fines.models import Fine
from loans.models import Loan

from .fr21_profile import ROLE_LABELS
from .models import User

RECENT_LOANS_LIMIT = 10


def _is_admin(request):
    return request.session.get('user_role') == 'adm'


def admin_user_list(request):
    """
    FR-28: Admin page to select a registered user, with a search by name or email.
    """
    if not _is_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    search_term = request.GET.get('q', '').strip()
    users = User.objects.annotate(
        active_loans=Count(
            'loans',
            filter=Q(loans__status__in=[Loan.STATUS_RESERVED, Loan.STATUS_BORROWED]),
        ),
    ).order_by(Lower('name'), Lower('last_name'))

    if search_term:
        users = users.filter(
            Q(name__icontains=search_term)
            | Q(last_name__icontains=search_term)
            | Q(email__icontains=search_term)
        )

    rows = [
        {
            'user': user,
            'full_name': f'{user.name} {user.last_name}'.strip(),
            'role_label': ROLE_LABELS.get(user.role, user.role),
        }
        for user in users
    ]

    context = {
        'rows': rows,
        'searchTerm': search_term,
    }
    return render(request, 'fr28_admin_users.html', context)


def admin_user_detail(request, user_id):
    """
    FR-28: Show the selected user's profile information and a summary of their
    loans and fines.
    """
    if not _is_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    user = get_object_or_404(User, id=user_id)

    loans = Loan.objects.filter(user=user).select_related('book').order_by('-reservation_date')
    active_loans = [
        loan for loan in loans
        if loan.status in (Loan.STATUS_RESERVED, Loan.STATUS_BORROWED)
    ]
    now = timezone.now()
    overdue_count = sum(
        1 for loan in active_loans
        if loan.status == Loan.STATUS_BORROWED and loan.due_date and loan.due_date < now
    )

    unpaid_fines = Fine.objects.filter(user=user).exclude(status=Fine.STATUS_PAID)
    unpaid_total = unpaid_fines.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    context = {
        'profile_user': user,
        'full_name': f'{user.name} {user.last_name}'.strip(),
        'initials': f'{user.name[:1]}{user.last_name[:1]}'.upper(),
        'role_label': ROLE_LABELS.get(user.role, user.role),
        'active_loans': active_loans,
        'total_loans': len(loans),
        'overdue_count': overdue_count,
        'unpaid_fines_count': unpaid_fines.count(),
        'unpaid_total': unpaid_total,
        'recent_loans': loans[:RECENT_LOANS_LIMIT],
        'now': now,
    }
    return render(request, 'fr28_admin_user_detail.html', context)

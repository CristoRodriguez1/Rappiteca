"""
FR-23/FR-24: admin page that lists the fines applied to users' accounts.
"""

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render

from .models import Fine
from .services import apply_overdue_fines


def _is_admin(request):
    return request.session.get('user_role') == 'adm'


def admin_fine_list(request):
    if not _is_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    # Bring fines of books that are still out up to date before showing them,
    # so the page is correct even if the daily command has not run yet.
    apply_overdue_fines()

    fines = Fine.objects.select_related('user', 'loan', 'loan__book').order_by('status', '-amount')
    pending_total = fines.filter(status=Fine.STATUS_PENDING).aggregate(total=Sum('amount'))['total']

    return render(request, 'fines_admin_list.html', {
        'fines': fines,
        'pending_total': pending_total or 0,
    })

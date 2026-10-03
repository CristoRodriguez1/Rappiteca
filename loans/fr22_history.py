"""
FR-22 User loan history.

IF a user accesses their loan history section THEN THE Rappiteca system SHOULD
display the user's complete loan history within 3 seconds.
"""

from django.contrib import messages
from django.shortcuts import redirect, render

from .models import Loan
from .views import _usuario_actual


def loan_history(request):
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in to view your loan history.')
        return redirect('login')

    if current_user.role == 'adm':
        messages.error(request, 'Administrators cannot have loans.')
        return redirect('home')

    # Unlike FR-13 (My loans), returned and cancelled loans are included.
    loans = list(
        Loan.objects.select_related('book')
        .filter(user=current_user)
        .order_by('-reservation_date')
    )

    contexto = {
        'current_user': current_user,
        'loans': loans,
        'total_count': len(loans),
        'returned_count': sum(1 for loan in loans if loan.status == Loan.STATUS_RETURNED),
    }
    return render(request, 'fr22_loan_history.html', contexto)

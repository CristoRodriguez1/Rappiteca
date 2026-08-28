from django.shortcuts import render, redirect
from django.contrib import messages

from accounts.models import User
from .models import Loan


def _usuario_actual(request):
    current_user = None
    user_id = request.session.get('user_id')

    if user_id:
        try:
            current_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # Session points to a user that no longer exists — clear it out.
            request.session.flush()

    return current_user


def user_loans(request):
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'Debes iniciar sesión para ver tus préstamos.')
        return redirect('login')
    
    if current_user.role == 'adm':
        messages.error(request, 'Los administradores no pueden tener préstamos.')
        return redirect('home')

    loans = Loan.objects.select_related('book').filter(
        user=current_user
    ).exclude(
        estado__in=[Loan.ESTADO_DEVUELTO, Loan.ESTADO_CANCELADO]
    ).order_by('-fecha_reserva')

    contexto = {
        'current_user': current_user,
        'loans': loans,
    }
    return render(request, 'user_loans.html', contexto)

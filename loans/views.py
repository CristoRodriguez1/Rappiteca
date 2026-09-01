from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST

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
        status__in=[Loan.STATUS_RETURNED, Loan.STATUS_CANCELLED]
    ).order_by('-reservation_date')

    contexto = {
        'current_user': current_user,
        'loans': loans,
    }
    return render(request, 'user_loans.html', contexto)


@require_POST
def devolver_libro(request, loan_id):
    """
    Book Return.
    IF a user selects an active loan and confirms the return THEN the system
    SHALL register the return and update the book's availability status.
    """
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'Debes iniciar sesión para devolver un libro.')
        return redirect('login')

    # get_object_or_404 con user=current_user evita que alguien devuelva
    # préstamos de otro usuario adivinando el id en la URL.
    loan = get_object_or_404(Loan, id=loan_id, user=current_user)

    try:
        loan.mark_returned()
        messages.success(request, f'Devolviste "{loan.book.title}". ¡Gracias!')
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, 'message') else str(e))

    return redirect('user_loans')


@require_POST
def renovar_prestamo(request, loan_id):
    """
    Book Renewal.
    IF a user selects an active loan and requests a renewal THEN the system
    SHALL extend the loan's due date.
    """
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'Debes iniciar sesión para renovar un préstamo.')
        return redirect('login')

    loan = get_object_or_404(Loan, id=loan_id, user=current_user)

    try:
        loan.renew()
        messages.success(request, f'Renovaste "{loan.book.title}". Nueva fecha de entrega: {loan.due_date:%d/%m/%Y}.')
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, 'message') else str(e))

    return redirect('user_loans')

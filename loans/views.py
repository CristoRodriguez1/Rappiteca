from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import User
from catalog.models import Book
from .models import Loan, WaitlistEntry


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


def _volver(request, default='home'):
    target = request.POST.get('next')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(default)

# FR-13 User loan section
def user_loans(request):
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in to view your loans.')
        return redirect('login')
    
    if current_user.role == 'adm':
        messages.error(request, 'Administrators cannot have loans.')
        return redirect('home')

    loans = Loan.objects.select_related('book').filter(
        user=current_user
    ).exclude(
        status__in=[Loan.STATUS_RETURNED, Loan.STATUS_CANCELLED]
    ).order_by('-reservation_date')

    queue_entries = WaitlistEntry.objects.select_related('book').filter(
        user=current_user,
        status=WaitlistEntry.STATUS_WAITING,
    )

    contexto = {
        'current_user': current_user,
        'loans': loans,
        'queue_entries': queue_entries,
    }
    return render(request, 'user_loans.html', contexto)

# FR-11 Book return (revisado: el usuario solicita, el admin confirma)
@require_POST
def solicitar_devolucion(request, loan_id):
    """
    Book Return — user side.
    The user requests the return; an admin confirms it via the admin
    panel (marcar_devuelto), which is the only path that updates the
    book's availability.
    """
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in to request a return.')
        return redirect('login')

    loan = get_object_or_404(Loan, id=loan_id, user=current_user)

    try:
        loan.request_return()
        messages.success(
            request,
            f'You requested the return of "{loan.book.title}". '
            f'An admin will confirm it when you drop off the book.',
        )
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, 'message') else str(e))

    return redirect('user_loans')

# FR-12 Book renewal
@require_POST
def renovar_prestamo(request, loan_id):
    """
    Book Renewal.
    IF a user selects an active loan and requests a renewal THEN the system
    SHALL extend the loan's due date.
    """
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in to renew a loan.')
        return redirect('login')

    loan = get_object_or_404(Loan, id=loan_id, user=current_user)

    try:
        loan.renew()
        messages.success(request, f'You renewed "{loan.book.title}". New due date: {loan.due_date:%d/%m/%Y}.')
    except ValidationError as e:
        messages.error(request, e.message if hasattr(e, 'message') else str(e))

    return redirect('user_loans')


# FR-17 Reserve unavailable book
@require_POST
def unirse_cola(request, book_id):
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in to join the queue.')
        return redirect('login')
    if current_user.role == 'adm':
        messages.error(request, 'Administrators cannot join queues.')
        return redirect('home')

    book = get_object_or_404(Book, id=book_id)
    try:
        entry = WaitlistEntry.join(current_user, book)
        messages.success(
            request,
            f'You joined the queue for "{book.title}". Your position: #{entry.position}.',
        )
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
    return _volver(request)


@require_POST
def salir_cola(request, entry_id):
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in.')
        return redirect('login')

    entry = get_object_or_404(WaitlistEntry, id=entry_id, user=current_user)
    try:
        entry.leave()
        messages.success(request, f'You left the queue for "{entry.book.title}".')
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
    return _volver(request, default='user_loans')

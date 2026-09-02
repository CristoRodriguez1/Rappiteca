"""
FR-16 Display borrowers information requirement.

IF an administrator selects a book THEN THE Rappiteca system SHALL display the
current borrower's information within 3 seconds.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from loans.models import Loan

from .models import Book


def _is_admin(request):
    return request.session.get('user_role') == 'adm'


def admin_book_borrower_list(request):
    """
    FR-16: Admin page to select a book and view its current borrower(s).
    """
    if not _is_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    books = Book.objects.all().order_by('title')

    return render(request, 'fr16_admin_book_borrowers.html', {'books': books})


def admin_book_borrower_detail(request, book_id):
    """
    FR-16: Show current borrower information for the selected book.
    """
    if not _is_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    book = get_object_or_404(Book, id=book_id)

    # FIX: `estado` y `fecha_reserva` son @property de Python, no campos
    # reales del modelo — .filter()/.order_by() necesitan los campos reales
    # (`status`, `reservation_date`). Las properties sí funcionan bien más
    # abajo, una vez que `loan` ya es una instancia cargada en memoria.
    active_loans = (
        Loan.objects.filter(
            book=book,
            status__in=[Loan.STATUS_RESERVED, Loan.STATUS_BORROWED],
        )
        .select_related('user')
        .order_by('-reservation_date')
    )

    borrowers = []
    for loan in active_loans:
        status_label = 'Reserved' if loan.status == Loan.STATUS_RESERVED else 'Checked out'
        borrowers.append({
            'loan': loan,
            'full_name': f'{loan.user.name} {loan.user.last_name}'.strip(),
            'email': loan.user.email,
            'status_label': status_label,
            'reserved_on': loan.reservation_date,
            'picked_up_on': loan.pickup_date,
            'due_date': loan.due_date,
        })

    context = {
        'book': book,
        'borrowers': borrowers,
        'has_borrowers': bool(borrowers),
        'estado_publico': book.estado_publico(),
        'estado_publico_label': book.ESTADO_PUBLICO_LABELS[book.estado_publico()],
    }
    return render(request, 'fr16_admin_book_borrower_detail.html', context)

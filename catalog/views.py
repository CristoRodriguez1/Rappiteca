from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.models import User
from .forms import BookForm
from .models import Book, BookAvailabilityAlert
from loans.models import Loan, WaitlistEntry
 
 
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
 
 
# ---------- Home + public search ----------
 
def home(request):
    current_user = _usuario_actual(request)
 
    search_term = request.GET.get('q')
    books = Book.objects.all()
    if search_term:
        books = books.filter(
            Q(title__icontains=search_term)
            | Q(author__icontains=search_term)
            | Q(isbn__icontains=search_term)
            | Q(category__icontains=search_term)
        )
 
    resultados = []
    for book in books:
        # Computed once per book: `estado_publico` hits the DB.
        estado_publico = book.estado_publico()
        info = {
            'book': book,
            'estado': book.estado_display(),
            'estado_publico': estado_publico,
            'estado_publico_label': book.ESTADO_PUBLICO_LABELS[estado_publico],
            'loan_activo': None,
            'entrada_cola': None,
            'availability_alert': None,
        }
        if current_user:
            info['loan_activo'] = Loan.objects.filter(
                user=current_user,
                book=book,
                status__in=[Loan.STATUS_RESERVED, Loan.STATUS_BORROWED],
            ).first()
            info['entrada_cola'] = WaitlistEntry.objects.filter(
                user=current_user,
                book=book,
                status=WaitlistEntry.STATUS_WAITING,
            ).first()
            info['availability_alert'] = BookAvailabilityAlert.objects.filter(
                user=current_user,
                book=book,
                is_active=True
            ).first()
        resultados.append(info)
 
    contexto = {
        'current_user': current_user,
        'searchTerm': search_term,
        'resultados': resultados,
        'busqueda_activa': bool(search_term),
        'busqueda_vacia': bool(search_term) and not books.exists(),
    }
    return render(request, 'home.html', contexto)
 
 
# ---------- Public book detail ----------

def detalle_libro(request, book_id):
    current_user = _usuario_actual(request)
    book = get_object_or_404(Book, id=book_id)

    estado_publico = book.estado_publico()

    loan_activo = None
    entrada_cola = None
    availability_alert = None
    if current_user:
        # FIX: `estado` es una @property de Python, no un campo real del
        # modelo — filtrar por ella tira FieldError. Se usa `status`
        # (el campo real) con los valores en inglés.
        loan_activo = Loan.objects.filter(
            user=current_user,
            book=book,
            status__in=[Loan.STATUS_RESERVED, Loan.STATUS_BORROWED],
        ).first()
        entrada_cola = WaitlistEntry.objects.filter(
            user=current_user,
            book=book,
            status=WaitlistEntry.STATUS_WAITING,
        ).first()
        availability_alert = BookAvailabilityAlert.objects.filter(
            user=current_user,
            book=book,
            is_active=True
        ).first()

    contexto = {
        'current_user': current_user,
        'book': book,
        'estado_publico': estado_publico,
        'estado_publico_label': book.ESTADO_PUBLICO_LABELS[estado_publico],
        'loan_activo': loan_activo,
        'entrada_cola': entrada_cola,
        'availability_alert': availability_alert,
    }
    return render(request, 'book_detail.html', contexto)


# ---------- User action: reserve ----------
 
def reservar_libro(request, book_id):
    if request.method != 'POST':
        return redirect('home')
 
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in to reserve a book.')
        return redirect('login')
 
    book = get_object_or_404(Book, id=book_id)
    try:
        Loan.reservar(current_user, book)
        messages.success(request, f'You reserved "{book.title}". Stop by the library to pick it up.')
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
 
    return redirect(f"/?q={request.POST.get('q', '')}")


# ---------- Availability Alert Management ----------

def set_availability_alert(request, book_id):
    """User requests to be notified when a book becomes available."""
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in to set availability alerts.')
        return redirect('login')

    book = get_object_or_404(Book, id=book_id)
    
    # Check if book is available (user should reserve directly instead)
    if book.esta_disponible:
        messages.warning(request, f'"{book.title}" is currently available. You can reserve it directly.')
        return redirect('detalle_libro', book_id=book.id)
    
    # Check if user already has an alert for this book
    existing_alert = BookAvailabilityAlert.objects.filter(
        user=current_user,
        book=book
    ).first()
    
    if existing_alert:
        if existing_alert.is_active:
            messages.info(request, f'You already have an availability alert set for "{book.title}".')
        else:
            existing_alert.is_active = True
            existing_alert.save()
            messages.success(request, f'Your availability alert for "{book.title}" has been reactivated.')
    else:
        BookAvailabilityAlert.objects.create(
            user=current_user,
            book=book
        )
        messages.success(request, f'You will be notified when "{book.title}" becomes available.')
    
    return redirect('detalle_libro', book_id=book.id)


def remove_availability_alert(request, book_id):
    """User removes their availability alert for a book."""
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in to manage availability alerts.')
        return redirect('login')

    book = get_object_or_404(Book, id=book_id)
    
    alert = BookAvailabilityAlert.objects.filter(
        user=current_user,
        book=book
    ).first()
    
    if alert:
        alert.delete()
        messages.success(request, f'Availability alert removed for "{book.title}".')
    else:
        messages.warning(request, f'You don\'t have an availability alert for "{book.title}".')
    
    return redirect('detalle_libro', book_id=book.id)


def toggle_availability_alert(request, book_id):
    """Toggle availability alert for a book (AJAX endpoint)."""
    current_user = _usuario_actual(request)
    if not current_user:
        return JsonResponse({'success': False, 'error': 'Not logged in'}, status=401)

    book = get_object_or_404(Book, id=book_id)
    
    alert = BookAvailabilityAlert.objects.filter(
        user=current_user,
        book=book
    ).first()
    
    if alert:
        if alert.is_active:
            alert.is_active = False
            alert.save()
            return JsonResponse({'success': True, 'active': False})
        else:
            alert.is_active = True
            alert.save()
            return JsonResponse({'success': True, 'active': True})
    else:
        # Create new alert
        BookAvailabilityAlert.objects.create(
            user=current_user,
            book=book,
            is_active=True
        )
        return JsonResponse({'success': True, 'active': True})
 
 
# ---------- User action: cancel your own reservation ----------
 
# FR-18 Cancel reservation
def cancelar_reserva(request, loan_id):
    if request.method != 'POST':
        return redirect('home')
 
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'You must be logged in.')
        return redirect('login')
 
    loan = get_object_or_404(Loan, id=loan_id)
 
    # Only the owner of the reservation can cancel it.
    if loan.user_id != current_user.id:
        messages.error(request, 'You cannot cancel this reservation.')
        return redirect('home')
 
    try:
        loan.cancelar_reserva()
        messages.success(request, f'You cancelled the reservation for "{loan.book.title}".')
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
 
    return _volver(request, default='user_loans')
 
 
# ---------- Admin panel ----------
 
def _es_admin(request):
    return request.session.get('user_role') == 'adm'
 
 
def gestionar_loans(request):
    if not _es_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    loans = Loan.objects.select_related('user', 'book').exclude(
        status__in=[Loan.STATUS_RETURNED, Loan.STATUS_CANCELLED]
    ).order_by('-return_requested', '-reservation_date')

    return render(request, 'admin_prestamos.html', {'loans': loans})


# ---------- Admin panel: inventory ----------

def ver_inventario(request):
    if not _es_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    libros = Book.objects.all().order_by('title')

    return render(request, 'admin_inventario.html', {'libros': libros})


def eliminar_libro(request, book_id):
    """Admin: remove a book from inventory (hard delete from the DB)."""
    if request.method != 'POST':
        return redirect('ver_inventario')

    if not _es_admin(request):
        messages.error(request, 'You do not have permission.')
        return redirect('home')

    book = get_object_or_404(Book, id=book_id)

    activos = Loan.objects.filter(
        book=book,
        status__in=[Loan.STATUS_RESERVED, Loan.STATUS_BORROWED],
    ).exists()
    if activos:
        messages.error(
            request,
            f'Cannot remove "{book.title}": it has active reservations or loans.',
        )
        return redirect('ver_inventario')

    titulo = book.title
    book.delete()
    messages.success(request, f'Removed "{titulo}" from inventory.')
    return redirect('ver_inventario')


# ---------- Admin panel: add book to inventory ----------

def agregar_libro(request):
    if not _es_admin(request):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'"{book.title}" was added to inventory.')
            return redirect('ver_inventario')
    else:
        form = BookForm()

    return render(request, 'admin_agregar_libro.html', {'form': form})


def marcar_recogido(request, loan_id):
    """Admin marks that the user has picked up the book (reserved -> checked out)."""
    if request.method != 'POST':
        return redirect('gestionar_prestamos')

    if not _es_admin(request):
        messages.error(request, 'You do not have permission.')
        return redirect('home')

    loan = get_object_or_404(Loan, id=loan_id)
    try:
        loan.mark_picked_up()
        messages.success(request, f'"{loan.book.title}" marked as checked out.')
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
    return redirect('gestionar_prestamos')


def marcar_devuelto(request, loan_id):
    if request.method != 'POST':
        return redirect('gestionar_prestamos')

    if not _es_admin(request):
        messages.error(request, 'You do not have permission.')
        return redirect('home')

    loan = get_object_or_404(Loan, id=loan_id)
    try:
        loan.mark_returned()
        messages.success(request, f'"{loan.book.title}" marked as returned.')
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
    return redirect('gestionar_prestamos')

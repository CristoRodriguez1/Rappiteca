from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q

from accounts.models import User
from .forms import BookForm
from .models import Book
from loans.models import Loan
 
 
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
 
 
# ---------- Home + búsqueda pública ----------
 
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
        # Se calcula una sola vez por libro: `estado_publico` consulta la DB.
        estado_publico = book.estado_publico()
        info = {
            'book': book,
            'estado': book.estado_display(),
            'estado_publico': estado_publico,
            'estado_publico_label': book.ESTADO_PUBLICO_LABELS[estado_publico],
            'loan_activo': None,
        }
        if current_user:
            info['loan_activo'] = Loan.objects.filter(
                user=current_user,
                book=book,
                estado__in=[Loan.ESTADO_RESERVADO, Loan.ESTADO_PRESTADO],
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
 
 
# ---------- Detalle público de un libro ----------

def detalle_libro(request, book_id):
    current_user = _usuario_actual(request)
    book = get_object_or_404(Book, id=book_id)

    estado_publico = book.estado_publico()

    loan_activo = None
    if current_user:
        loan_activo = Loan.objects.filter(
            user=current_user,
            book=book,
            estado__in=[Loan.ESTADO_RESERVADO, Loan.ESTADO_PRESTADO],
        ).first()

    contexto = {
        'current_user': current_user,
        'book': book,
        'estado_publico': estado_publico,
        'estado_publico_label': book.ESTADO_PUBLICO_LABELS[estado_publico],
        'loan_activo': loan_activo,
    }
    return render(request, 'book_detail.html', contexto)


# ---------- Acción del usuario: reservar ----------
 
def reservar_libro(request, book_id):
    if request.method != 'POST':
        return redirect('home')
 
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'Debes iniciar sesión para reservar un libro.')
        return redirect('login')
 
    book = get_object_or_404(Book, id=book_id)
    try:
        Loan.reservar(current_user, book)
        messages.success(request, f'Reservaste "{book.title}". Pásate por la biblioteca a recogerlo.')
    except ValidationError as e:
        messages.error(request, str(e))
 
    return redirect(f"/?q={request.POST.get('q', '')}")
 
 
# ---------- Acción del usuario: cancelar una reserva propia ----------
 
def cancelar_reserva(request, loan_id):
    if request.method != 'POST':
        return redirect('home')
 
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'Debes iniciar sesión.')
        return redirect('login')
 
    loan = get_object_or_404(Loan, id=loan_id)
 
    # Solo el dueño de la reserva puede cancelarla.
    if loan.user_id != current_user.id:
        messages.error(request, 'No puedes cancelar esta reserva.')
        return redirect('home')
 
    try:
        loan.cancelar_reserva()
        messages.success(request, f'Cancelaste la reserva de "{loan.book.title}".')
    except ValidationError as e:
        messages.error(request, str(e))
 
    return redirect(f"/?q={request.POST.get('q', '')}")
 
 
# ---------- Panel de administrador ----------
 
def _es_admin(request):
    return request.session.get('user_role') == 'adm'
 
 
def gestionar_loans(request):
    if not _es_admin(request):
        messages.error(request, 'No tienes permisos para ver esta página.')
        return redirect('home')

    loans = Loan.objects.select_related('user', 'book').exclude(
        estado__in=[Loan.ESTADO_DEVUELTO, Loan.ESTADO_CANCELADO]
    ).order_by('-fecha_reserva')

    return render(request, 'admin_prestamos.html', {'loans': loans})


# ---------- Panel de administrador: inventario ----------

def ver_inventario(request):
    if not _es_admin(request):
        messages.error(request, 'No tienes permisos para ver esta página.')
        return redirect('home')

    libros = Book.objects.all().order_by('title')

    return render(request, 'admin_inventario.html', {'libros': libros})


def eliminar_libro(request, book_id):
    """Admin: quitar un libro del inventario (borrado real en la DB)."""
    if request.method != 'POST':
        return redirect('ver_inventario')

    if not _es_admin(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('home')

    book = get_object_or_404(Book, id=book_id)

    activos = Loan.objects.filter(
        book=book,
        estado__in=[Loan.ESTADO_RESERVADO, Loan.ESTADO_PRESTADO],
    ).exists()
    if activos:
        messages.error(
            request,
            f'No se puede quitar "{book.title}": tiene reservas o préstamos activos.',
        )
        return redirect('ver_inventario')

    titulo = book.title
    book.delete()
    messages.success(request, f'Se quitó "{titulo}" del inventario.')
    return redirect('ver_inventario')


# ---------- Panel de administrador: agregar libro al inventario ----------

def agregar_libro(request):
    if not _es_admin(request):
        messages.error(request, 'No tienes permisos para ver esta página.')
        return redirect('home')

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'"{book.title}" se agregó al inventario.')
            return redirect('ver_inventario')
    else:
        form = BookForm()

    return render(request, 'admin_agregar_libro.html', {'form': form})


def marcar_recogido(request, loan_id):
    """Admin marca que el usuario ya recogió el libro (reservado → prestado)."""
    if request.method != 'POST':
        return redirect('gestionar_prestamos')

    if not _es_admin(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('home')

    loan = get_object_or_404(Loan, id=loan_id)
    try:
        loan.marcar_recogido()
        messages.success(request, f'"{loan.book.title}" marcado como prestado.')
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect('gestionar_prestamos')


def marcar_devuelto(request, loan_id):
    if request.method != 'POST':
        return redirect('gestionar_prestamos')

    if not _es_admin(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('home')

    loan = get_object_or_404(Loan, id=loan_id)
    try:
        loan.marcar_devuelto()
        messages.success(request, f'"{loan.book.title}" marcado como devuelto.')
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect('gestionar_prestamos')


# ---------- Acción del usuario: confirmar que ya recogió el libro ----------

def confirmar_recogida(request, loan_id):
    """
    El propio usuario indica que ya recogió el libro.
    Pasa de reservado → prestado y deja de poder cancelar.
    """
    if request.method != 'POST':
        return redirect('home')

    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'Debes iniciar sesión.')
        return redirect('login')

    loan = get_object_or_404(Loan, id=loan_id)

    if loan.user_id != current_user.id:
        messages.error(request, 'No puedes confirmar la recogida de este préstamo.')
        return redirect('home')

    try:
        loan.marcar_recogido()
        messages.success(
            request,
            f'Confirmaste la recogida de "{loan.book.title}". Ya no puedes cancelar.',
        )
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect(f"/?q={request.POST.get('q', '')}")
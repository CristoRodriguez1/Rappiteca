from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
 
from accounts.models import User
from .models import Book, Prestamo
 
 
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
        books = books.filter(title__icontains=search_term)  # amplía a author/isbn si quieres
 
    resultados = []
    for book in books:
        info = {
            'book': book,
            'estado': book.estado_display(),
            'prestamo_activo': None,
        }
        if current_user:
            info['prestamo_activo'] = Prestamo.objects.filter(
                user=current_user,
                book=book,
                estado__in=[Prestamo.ESTADO_RESERVADO, Prestamo.ESTADO_PRESTADO],
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
        Prestamo.reservar(current_user, book)
        messages.success(request, f'Reservaste "{book.title}". Pásate por la biblioteca a recogerlo.')
    except ValidationError as e:
        messages.error(request, str(e))
 
    return redirect(f"/?q={request.POST.get('q', '')}")
 
 
# ---------- Acción del usuario: cancelar una reserva propia ----------
 
def cancelar_reserva(request, prestamo_id):
    if request.method != 'POST':
        return redirect('home')
 
    current_user = _usuario_actual(request)
    if not current_user:
        messages.error(request, 'Debes iniciar sesión.')
        return redirect('login')
 
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
 
    # Solo el dueño de la reserva puede cancelarla.
    if prestamo.user_id != current_user.id:
        messages.error(request, 'No puedes cancelar esta reserva.')
        return redirect('home')
 
    try:
        prestamo.cancelar_reserva()
        messages.success(request, f'Cancelaste la reserva de "{prestamo.book.title}".')
    except ValidationError as e:
        messages.error(request, str(e))
 
    return redirect(f"/?q={request.POST.get('q', '')}")
 
 
# ---------- Panel de administrador ----------
 
def _es_admin(request):
    return request.session.get('user_role') == 'adm'
 
 
def gestionar_prestamos(request):
    if not _es_admin(request):
        messages.error(request, 'No tienes permisos para ver esta página.')
        return redirect('home')

    prestamos = Prestamo.objects.select_related('user', 'book').exclude(
        estado__in=[Prestamo.ESTADO_DEVUELTO, Prestamo.ESTADO_CANCELADO]
    ).order_by('-fecha_reserva')

    return render(request, 'admin_prestamos.html', {'prestamos': prestamos})


# ---------- Panel de administrador: inventario (solo lectura) ----------

def ver_inventario(request):
    if not _es_admin(request):
        messages.error(request, 'No tienes permisos para ver esta página.')
        return redirect('home')

    libros = Book.objects.all().order_by('title')

    return render(request, 'admin_inventario.html', {'libros': libros})
 
 
def marcar_recogido(request, prestamo_id):
    if not _es_admin(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('home')
 
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    try:
        prestamo.marcar_recogido()
        messages.success(request, f'"{prestamo.book.title}" marcado como prestado.')
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect('gestionar_prestamos')
 
 
def marcar_devuelto(request, prestamo_id):
    if not _es_admin(request):
        messages.error(request, 'No tienes permisos.')
        return redirect('home')
 
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    try:
        prestamo.marcar_devuelto()
        messages.success(request, f'"{prestamo.book.title}" marcado como devuelto.')
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect('gestionar_prestamos')
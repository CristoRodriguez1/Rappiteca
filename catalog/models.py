from django.db import models
from django.core.exceptions import ValidationError

from accounts.models import User


class Book(models.Model):
    title = models.CharField(max_length=150)
    author = models.CharField(max_length=150)
    isbn = models.CharField(max_length=20, unique=True, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=500, blank=True)
    image = models.ImageField(upload_to='catalog/images/', blank=True, null=True)

    total_copies = models.PositiveIntegerField(default=1)
    # Copias que NO están ni reservadas ni prestadas ahora mismo.
    # Baja al reservar Y al prestar; sube al cancelar reserva o al devolver.
    available_copies = models.PositiveIntegerField(default=1)

    # Estados que ve el público en el catálogo y en el detalle del libro.
    ESTADO_DISPONIBLE = 'available'
    ESTADO_PRESTADO = 'borrowed'
    ESTADO_RESERVADO = 'reserved'

    ESTADO_PUBLICO_LABELS = {
        ESTADO_DISPONIBLE: 'Available',
        ESTADO_PRESTADO: 'Borrowed',
        ESTADO_RESERVADO: 'Reserved',
    }

    def __str__(self):
        return f'{self.title} ({self.available_copies}/{self.total_copies})'

    @property
    def esta_disponible(self):
        return self.available_copies > 0

    def estado_display(self):
        return 'Disponible' if self.esta_disponible else 'No disponible actualmente'

    def estado_publico(self):
        """
        Estado real del libro para mostrar al usuario: disponible, prestado o reservado.

        `estado_display` solo distingue disponible/no disponible; acá separamos los dos
        motivos por los que un libro puede no estar disponible, porque para el usuario
        no es lo mismo que el libro esté fuera de la biblioteca a que esté esperando
        a que alguien lo recoja.
        """
        if self.esta_disponible:
            return self.ESTADO_DISPONIBLE

        # Sin copias libres: si alguna está fuera de la biblioteca, pesa "prestado";
        # si todas están apartadas sin recoger, es "reservado".
        hay_prestadas = self.prestamos.filter(estado=Prestamo.ESTADO_PRESTADO).exists()
        return self.ESTADO_PRESTADO if hay_prestadas else self.ESTADO_RESERVADO

    def estado_publico_display(self):
        """Etiqueta legible del estado público, para usar directo en plantillas."""
        return self.ESTADO_PUBLICO_LABELS[self.estado_publico()]


class Prestamo(models.Model):
    ESTADO_RESERVADO = 'reservado'
    ESTADO_PRESTADO = 'prestado'
    ESTADO_DEVUELTO = 'devuelto'
    ESTADO_CANCELADO = 'cancelado'

    ESTADO_CHOICES = [
        (ESTADO_RESERVADO, 'Reservado (pendiente de recoger)'),
        (ESTADO_PRESTADO, 'Prestado (fuera de la biblioteca)'),
        (ESTADO_DEVUELTO, 'Devuelto'),
        (ESTADO_CANCELADO, 'Cancelado'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prestamos')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='prestamos')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ESTADO_RESERVADO)

    fecha_reserva = models.DateTimeField(auto_now_add=True)
    fecha_recogida = models.DateTimeField(blank=True, null=True)
    fecha_devolucion = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'{self.book.title} -> {self.user.email} [{self.estado}]'

    @classmethod
    def reservar(cls, user, book):
        if not book.esta_disponible:
            raise ValidationError('No hay copias disponibles para reservar.')
        book.available_copies -= 1
        book.save()
        return cls.objects.create(user=user, book=book, estado=cls.ESTADO_RESERVADO)

    def marcar_recogido(self):
        if self.estado != self.ESTADO_RESERVADO:
            raise ValidationError('Solo una reserva pendiente puede pasar a préstamo.')
        from django.utils import timezone
        self.estado = self.ESTADO_PRESTADO
        self.fecha_recogida = timezone.now()
        self.save()

    def marcar_devuelto(self):
        if self.estado not in (self.ESTADO_RESERVADO, self.ESTADO_PRESTADO):
            raise ValidationError('Este préstamo/reserva ya está cerrado.')
        from django.utils import timezone
        self.estado = self.ESTADO_DEVUELTO
        self.fecha_devolucion = timezone.now()
        self.save()

        self.book.available_copies += 1
        self.book.save()

    def cancelar_reserva(self):
        if self.estado != self.ESTADO_RESERVADO:
            raise ValidationError('Solo se puede cancelar una reserva pendiente.')
        self.estado = self.ESTADO_CANCELADO
        self.save()

        self.book.available_copies += 1
        self.book.save()

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

    def __str__(self):
        return f'{self.title} ({self.available_copies}/{self.total_copies})'

    @property
    def esta_disponible(self):
        return self.available_copies > 0

    def estado_display(self):
        return 'Disponible' if self.esta_disponible else 'No disponible actualmente'


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

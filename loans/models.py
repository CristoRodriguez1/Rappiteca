from django.db import models
from django.core.exceptions import ValidationError

from accounts.models import User

# Create your models here.
class Loan(models.Model):
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
    book = models.ForeignKey('catalog.Book', on_delete=models.CASCADE, related_name='prestamos')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ESTADO_RESERVADO)

    fecha_reserva = models.DateTimeField(auto_now_add=True)
    fecha_recogida = models.DateTimeField(blank=True, null=True)
    fecha_devolucion = models.DateTimeField(blank=True, null=True)

    MAX_RENOVACIONES = 2
    renovaciones = models.PositiveIntegerField(default=0)

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
        # Solo un préstamo activo (ya recogido) puede devolverse. Una reserva que
        # nunca se recogió se cancela con `cancelar_reserva()`, no se "devuelve".
        if self.estado != self.ESTADO_PRESTADO:
            raise ValidationError('Solo un préstamo activo (prestado) puede marcarse como devuelto.')
        from django.utils import timezone
        self.estado = self.ESTADO_DEVUELTO
        self.fecha_devolucion = timezone.now()
        self.save()

        self.book.available_copies += 1
        self.book.save()

    def renovar(self):
        """
        Book Renewal.
        IF a user selects an active loan and requests a renewal THEN the system
        SHALL extend the loan's due date (hasta MAX_RENOVACIONES veces).
        """
        if self.estado != self.ESTADO_PRESTADO:
            raise ValidationError('Solo un préstamo activo (prestado) puede renovarse.')
        if self.renovaciones >= self.MAX_RENOVACIONES:
            raise ValidationError(f'Ya alcanzaste el máximo de {self.MAX_RENOVACIONES} renovaciones para este préstamo.')

        self.renovaciones += 1
        self.save()

    def cancelar_reserva(self):
        if self.estado != self.ESTADO_RESERVADO:
            raise ValidationError('Solo se puede cancelar una reserva pendiente.')
        self.estado = self.ESTADO_CANCELADO
        self.save()

        self.book.available_copies += 1
        self.book.save()

    @property
    def due_date(self):
        """
        Calculate due date: 14 days from pickup date for borrowed books,
        plus 14 more days per renovation (renovar() extiende desde el
        due_date actual, no desde la fecha de hoy).
        """
        from datetime import timedelta
        if self.estado == self.ESTADO_PRESTADO and self.fecha_recogida:
            return self.fecha_recogida + timedelta(days=14 * (1 + self.renovaciones))
        return None

    @property
    def puede_renovar(self):
        return self.estado == self.ESTADO_PRESTADO and self.renovaciones < self.MAX_RENOVACIONES

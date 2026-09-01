from django.db import models
from django.core.exceptions import ValidationError

from accounts.models import User

# Create your models here.
class Loan(models.Model):
    STATUS_RESERVED = 'reserved'
    STATUS_BORROWED = 'borrowed'
    STATUS_RETURNED = 'returned'
    STATUS_CANCELLED = 'cancelled'

    # Backwards compatibility constants
    ESTADO_RESERVADO = STATUS_RESERVED
    ESTADO_PRESTADO = STATUS_BORROWED
    ESTADO_DEVUELTO = STATUS_RETURNED
    ESTADO_CANCELADO = STATUS_CANCELLED

    STATUS_CHOICES = [
        (STATUS_RESERVED, 'Reserved (pending pickup)'),
        (STATUS_BORROWED, 'Borrowed (checked out)'),
        (STATUS_RETURNED, 'Returned'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    ESTADO_CHOICES = STATUS_CHOICES

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    book = models.ForeignKey('catalog.Book', on_delete=models.CASCADE, related_name='loans')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_RESERVED)

    reservation_date = models.DateTimeField(auto_now_add=True)
    pickup_date = models.DateTimeField(blank=True, null=True)
    return_date = models.DateTimeField(blank=True, null=True)

    MAX_RENEWALS = 2
    renewals = models.PositiveIntegerField(default=0)

    # Backwards compatibility properties
    @property
    def estado(self):
        return self.status

    @estado.setter
    def estado(self, value):
        self.status = value

    @property
    def fecha_reserva(self):
        return self.reservation_date

    @property
    def fecha_recogida(self):
        return self.pickup_date

    @fecha_recogida.setter
    def fecha_recogida(self, value):
        self.pickup_date = value

    @property
    def fecha_devolucion(self):
        return self.return_date

    @fecha_devolucion.setter
    def fecha_devolucion(self, value):
        self.return_date = value

    @property
    def renovaciones(self):
        return self.renewals

    @renovaciones.setter
    def renovaciones(self, value):
        self.renewals = value

    def __str__(self):
        return f'{self.book.title} -> {self.user.email} [{self.status}]'

    @classmethod
    def reserve(cls, user, book):
        if not book.esta_disponible:
            raise ValidationError('No hay copias disponibles para reservar.')
        book.available_copies -= 1
        book.save()
        return cls.objects.create(user=user, book=book, status=cls.STATUS_RESERVED)

    @classmethod
    def reservar(cls, user, book):
        return cls.reserve(user, book)

    def mark_picked_up(self):
        if self.status != self.STATUS_RESERVED:
            raise ValidationError('Solo una reserva pendiente puede pasar a préstamo.')
        from django.utils import timezone
        self.status = self.STATUS_BORROWED
        self.pickup_date = timezone.now()
        self.save()

    def marcar_recogido(self):
        return self.mark_picked_up()

    def mark_returned(self):
        if self.status != self.STATUS_BORROWED:
            raise ValidationError('Solo un préstamo activo (prestado) puede marcarse como devuelto.')
        from django.utils import timezone
        self.status = self.STATUS_RETURNED
        self.return_date = timezone.now()
        self.save()

        self.book.available_copies += 1
        self.book.save()

    def marcar_devuelto(self):
        return self.mark_returned()

    def renew(self):
        """
        Book Renewal.
        IF a user selects an active loan and requests a renewal THEN the system
        SHALL extend the loan's due date (up to MAX_RENEWALS times).
        """
        if self.status != self.STATUS_BORROWED:
            raise ValidationError('Solo un préstamo activo (prestado) puede renovarse.')
        if self.renewals >= self.MAX_RENEWALS:
            raise ValidationError(f'Ya alcanzaste el máximo de {self.MAX_RENEWALS} renovaciones para este préstamo.')

        self.renewals += 1
        self.save()

    def renovar(self):
        return self.renew()

    def cancel_reservation(self):
        if self.status != self.STATUS_RESERVED:
            raise ValidationError('Solo se puede cancelar una reserva pendiente.')
        self.status = self.STATUS_CANCELLED
        self.save()

        self.book.available_copies += 1
        self.book.save()

    def cancelar_reserva(self):
        return self.cancel_reservation()

    @property
    def due_date(self):
        """
        Calculate due date: 14 days from pickup date for borrowed books,
        plus 14 more days per renewal.
        """
        from datetime import timedelta
        if self.status == self.STATUS_BORROWED and self.pickup_date:
            return self.pickup_date + timedelta(days=14 * (1 + self.renewals))
        return None

    @property
    def can_renew(self):
        return self.status == self.STATUS_BORROWED and self.renewals < self.MAX_RENEWALS

    @property
    def puede_renovar(self):
        return self.can_renew

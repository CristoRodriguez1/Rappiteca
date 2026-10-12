from datetime import timedelta

from django.db import models, transaction
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import User, Notification

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

    RESERVATION_HOLD_HOURS = 48

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    book = models.ForeignKey('catalog.Book', on_delete=models.CASCADE, related_name='loans')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_RESERVED)

    reservation_date = models.DateTimeField(auto_now_add=True)
    pickup_date = models.DateTimeField(blank=True, null=True)
    return_date = models.DateTimeField(blank=True, null=True)

    MAX_RENEWALS = 2
    renewals = models.PositiveIntegerField(default=0)

    # FR-11 (revisado): el usuario solicita la devolución, pero solo el admin
    # la confirma vía mark_returned(). Esto evita que el usuario actualice
    # la disponibilidad del libro sin que nadie de la biblioteca lo verifique.
    return_requested = models.BooleanField(default=False)

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
        with transaction.atomic():
            locked_book = book.__class__.objects.select_for_update().get(pk=book.pk)
            if not locked_book.esta_disponible:
                raise ValidationError('No copies available to reserve.')
            book.__class__.objects.filter(pk=book.pk).update(
                available_copies=F('available_copies') - 1
            )
            book.refresh_from_db(fields=['available_copies'])
            return cls.objects.create(user=user, book=book, status=cls.STATUS_RESERVED)

    @classmethod
    def reservar(cls, user, book):
        return cls.reserve(user, book)

    @classmethod
    def _assign_entry(cls, entry, book):
        loan = cls.objects.create(user=entry.user, book=book, status=cls.STATUS_RESERVED)
        entry.status = WaitlistEntry.STATUS_FULFILLED
        entry.save()
        Notification.objects.create(
            user=entry.user,
            notification_type=Notification.TYPE_RESERVATION_READY,
            title='Your book is ready for pickup',
            message=(
                f'"{book.title}" is now reserved for you. Please pick it up at '
                f'{book.location or "the library"} within {cls.RESERVATION_HOLD_HOURS} hours.'
            ),
            related_loan_id=loan.id,
        )
        return loan

    @classmethod
    def _release_copy(cls, book):
        from catalog.models import BookAvailabilityAlert
        from django.core.mail import send_mail
        from django.conf import settings
        
        with transaction.atomic():
            entry = (
                WaitlistEntry.objects.select_for_update()
                .select_related('user')
                .filter(book=book, status=WaitlistEntry.STATUS_WAITING)
                .order_by('created_at')
                .first()
            )

            if entry is None:
                # No waitlist entries, increment available copies first
                book.__class__.objects.filter(pk=book.pk).update(
                    available_copies=F('available_copies') + 1
                )
                book.refresh_from_db(fields=['available_copies'])
                
                # Now notify users who requested availability alerts
                if book.available_copies > 0:
                    cls._notify_availability_alerts(book)
                return None

            return cls._assign_entry(entry, book)
    
    @classmethod
    def _notify_availability_alerts(cls, book):
        """Notify users who requested availability alerts when a book becomes available."""
        from catalog.models import BookAvailabilityAlert
        
        alerts = BookAvailabilityAlert.objects.filter(
            book=book,
            is_active=True
        ).select_related('user')
        
        for alert in alerts:
            # Create in-app notification
            Notification.objects.create(
                user=alert.user,
                notification_type=Notification.TYPE_BOOK_AVAILABLE,
                title=f'Available: "{book.title}"',
                message=f'Good news! "{book.title}" is now available for reservation. '
                        f'There are {book.available_copies} copy/copies available.',
                related_book_id=book.id
            )
            
            # Send email notification
            try:
                email_subject = f'Book Available: "{book.title}"'
                email_message = f'Hello {alert.user.name},\n\n'
                email_message += f'Great news! The book you requested is now available:\n\n'
                email_message += f'Title: {book.title}\n'
                email_message += f'Author: {book.author}\n'
                email_message += f'Available copies: {book.available_copies}\n\n'
                email_message += f'You can now reserve this book before someone else does.\n\n'
                email_message += f'Visit the catalog to reserve: http://localhost:8000/\n\n'
                email_message += f'Best regards,\n'
                email_message += f'Rappiteca Team'
                
                send_mail(
                    subject=email_subject,
                    message=email_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[alert.user.email],
                    fail_silently=False,
                )
            except Exception as e:
                # Still keep the in-app notification even if email fails
                pass

    @classmethod
    def assign_free_copies(cls, book):
        with transaction.atomic():
            locked_book = book.__class__.objects.select_for_update().get(pk=book.pk)
            entries = list(
                WaitlistEntry.objects.select_for_update()
                .select_related('user')
                .filter(book=book, status=WaitlistEntry.STATUS_WAITING)
                .order_by('created_at')[:locked_book.available_copies]
            )
            for entry in entries:
                cls._assign_entry(entry, locked_book)
            if entries:
                book.__class__.objects.filter(pk=book.pk).update(
                    available_copies=F('available_copies') - len(entries)
                )
                book.refresh_from_db(fields=['available_copies'])
            return len(entries)

    def mark_picked_up(self):
        if self.status != self.STATUS_RESERVED:
            raise ValidationError('Only a pending reservation can become a loan.')
        self.status = self.STATUS_BORROWED
        self.pickup_date = timezone.now()
        self.save()

    def marcar_recogido(self):
        return self.mark_picked_up()

    def request_return(self):
        """
        FR-11 (revisado): el usuario indica que va a devolver el libro.
        No toca available_copies — eso solo lo hace mark_returned(),
        disparado por el admin cuando el libro llega físicamente.
        """
        if self.status != self.STATUS_BORROWED:
            raise ValidationError('Only an active (checked-out) loan can have a return requested.')
        if self.return_requested:
            raise ValidationError('You already requested the return of this loan.')

        self.return_requested = True
        self.save()

    def mark_returned(self):
        with transaction.atomic():
            if self.status != self.STATUS_BORROWED:
                raise ValidationError('Only an active (checked-out) loan can be marked as returned.')
            self.status = self.STATUS_RETURNED
            self.return_date = timezone.now()
            self.return_requested = False
            self.save()
            Loan._release_copy(self.book)

    def marcar_devuelto(self):
        return self.mark_returned()

    def renew(self):
        """
        Book Renewal.
        IF a user selects an active loan and requests a renewal THEN the system
        SHALL extend the loan's due date (up to MAX_RENEWALS times).
        """
        if self.status != self.STATUS_BORROWED:
            raise ValidationError('Only an active (checked-out) loan can be renewed.')
        if self.renewals >= self.MAX_RENEWALS:
            raise ValidationError(f'You have reached the maximum of {self.MAX_RENEWALS} renewals for this loan.')

        self.renewals += 1
        self.save()

    def renovar(self):
        return self.renew()

    # FR-18 Cancel reservation
    def cancel_reservation(self):
        with transaction.atomic():
            if self.status != self.STATUS_RESERVED:
                raise ValidationError('Only a pending reservation can be cancelled.')
            self.status = self.STATUS_CANCELLED
            self.save()
            Loan._release_copy(self.book)

    def cancelar_reserva(self):
        return self.cancel_reservation()

    def expire(self):
        with transaction.atomic():
            if self.status != self.STATUS_RESERVED:
                raise ValidationError('Only a pending reservation can expire.')
            self.status = self.STATUS_CANCELLED
            self.save()
            Notification.objects.create(
                user=self.user,
                notification_type=Notification.TYPE_RESERVATION_EXPIRED,
                title='Your reservation expired',
                message=(
                    f'Your reservation for "{self.book.title}" was cancelled because it was not '
                    f'picked up within {self.RESERVATION_HOLD_HOURS} hours.'
                ),
                related_loan_id=self.id,
            )
            Loan._release_copy(self.book)

    @classmethod
    def expire_stale_reservations(cls):
        cutoff = timezone.now() - timedelta(hours=cls.RESERVATION_HOLD_HOURS)
        stale = cls.objects.select_related('book', 'user').filter(
            status=cls.STATUS_RESERVED,
            reservation_date__lt=cutoff,
        )
        expired = 0
        for loan in stale:
            try:
                loan.expire()
                expired += 1
            except ValidationError:
                continue
        return expired

    @property
    def pickup_deadline(self):
        if self.status == self.STATUS_RESERVED:
            return self.reservation_date + timedelta(hours=self.RESERVATION_HOLD_HOURS)
        return None

    @property
    def due_date(self):
        """
        Calculate due date: 14 days from pickup date for borrowed books,
        plus 14 more days per renewal.
        """
        if self.status == self.STATUS_BORROWED and self.pickup_date:
            return self.pickup_date + timedelta(days=14 * (1 + self.renewals))
        return None

    @property
    def can_renew(self):
        return self.status == self.STATUS_BORROWED and self.renewals < self.MAX_RENEWALS

    @property
    def puede_renovar(self):
        return self.can_renew


# FR-17 Reserve unavailable book
class WaitlistEntry(models.Model):
    STATUS_WAITING = 'waiting'
    STATUS_FULFILLED = 'fulfilled'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_WAITING, 'Waiting'),
        (STATUS_FULFILLED, 'Fulfilled'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waitlist_entries')
    book = models.ForeignKey('catalog.Book', on_delete=models.CASCADE, related_name='waitlist_entries')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_WAITING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'book'],
                condition=Q(status='waiting'),
                name='unique_waiting_entry_per_user_book',
            )
        ]

    def __str__(self):
        return f'{self.user.email} waiting for {self.book.title} [{self.status}]'

    @classmethod
    def join(cls, user, book):
        with transaction.atomic():
            locked_book = book.__class__.objects.select_for_update().get(pk=book.pk)
            if locked_book.available_copies > 0:
                raise ValidationError('This book has copies available, you can reserve it directly.')
            if cls.objects.filter(user=user, book=book, status=cls.STATUS_WAITING).exists():
                raise ValidationError('You are already in the queue for this book.')
            if Loan.objects.filter(
                user=user,
                book=book,
                status__in=[Loan.STATUS_RESERVED, Loan.STATUS_BORROWED],
            ).exists():
                raise ValidationError('You already have this book reserved or borrowed.')
            return cls.objects.create(user=user, book=book)

    def leave(self):
        if self.status != self.STATUS_WAITING:
            raise ValidationError('You are not waiting in this queue.')
        self.status = self.STATUS_CANCELLED
        self.save()

    @property
    def position(self):
        if self.status != self.STATUS_WAITING:
            return None
        return WaitlistEntry.objects.filter(
            book=self.book,
            status=self.STATUS_WAITING,
            created_at__lt=self.created_at,
        ).count() + 1

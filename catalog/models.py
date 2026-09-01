from django.db import models
from django.core.exceptions import ValidationError

from accounts.models import User
from loans.models import Loan

class Book(models.Model):
    title = models.CharField(max_length=150)
    author = models.CharField(max_length=150)
    isbn = models.CharField(max_length=20, unique=True, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True)
    # Ubicación física en la biblioteca (estante, sala, piso…), para que el usuario
    # sepa dónde encontrarlo cuando vaya a recogerlo.
    location = models.CharField(max_length=100, blank=True)
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
        hay_prestadas = (
            self.loans.filter(status=Loan.STATUS_BORROWED).exists()
            if hasattr(self, 'loans')
            else self.prestamos.filter(status=Loan.STATUS_BORROWED).exists()
        )
        return self.ESTADO_PRESTADO if hay_prestadas else self.ESTADO_RESERVADO

    def estado_publico_display(self):
        """Etiqueta legible del estado público, para usar directo en plantillas."""
        return self.ESTADO_PUBLICO_LABELS[self.estado_publico()]

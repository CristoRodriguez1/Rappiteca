"""
Carga libros de ejemplo para poder ver los tres estados del catálogo (FR-09)
y la pantalla de detalle (FR-10) sin tener que crearlos a mano.

Uso:
    python manage.py seed_demo

Se puede correr varias veces: los libros que ya existan se omiten.
"""

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from accounts.models import User
from catalog.models import Book
from loans.models import Loan

# Usuario al que se le asignan las reservas/préstamos de ejemplo. Solo se crea
# si no hay ningún estudiante en la base de datos.
LECTOR_DEMO = {
    'name': 'Lector',
    'last_name': 'Demo',
    'email': 'lector.demo@rappiteca.edu',
    'password': 'demo12345',
}

# (título, autor, categoría, ubicación, copias, escenario)
# escenario: None = queda libre | 'reservado' = apartado sin recoger | 'prestado' = recogido
LIBROS_DEMO = [
    ('Cien años de soledad', 'Gabriel García Márquez', 'Novela',
     'Estante A1 — Sala 1', 2, None),
    ('El Aleph', 'Jorge Luis Borges', 'Cuento',
     'Estante A2 — Sala 1', 3, 'prestado'),
    ('Rayuela', 'Julio Cortázar', 'Novela',
     'Estante B3 — Sala 2', 1, 'reservado'),
    ('Pedro Páramo', 'Juan Rulfo', 'Novela',
     'Estante B1 — Sala 2', 1, 'prestado'),
]


class Command(BaseCommand):
    help = 'Crea libros de ejemplo que cubren los estados disponible, reservado y prestado.'

    def handle(self, *args, **options):
        lector = self._obtener_lector()

        creados = 0
        for titulo, autor, categoria, ubicacion, copias, escenario in LIBROS_DEMO:
            if Book.objects.filter(title=titulo).exists():
                self.stdout.write(f'  ya existe, se omite:  {titulo}')
                continue

            book = Book.objects.create(
                title=titulo,
                author=autor,
                category=categoria,
                location=ubicacion,
                description=f'Ejemplar de demostración de «{titulo}».',
                total_copies=copias,
                available_copies=copias,
            )

            # Los estados se generan con los métodos del modelo, no escribiendo
            # `available_copies` a mano, para que los datos queden consistentes
            # con la lógica real de préstamos.
            if escenario == 'reservado':
                Loan.reservar(lector, book)
            elif escenario == 'prestado':
                Loan.reservar(lector, book).marcar_recogido()

            book.refresh_from_db()
            creados += 1
            self.stdout.write(
                f'  creado: {titulo}  '
                f'({book.available_copies}/{book.total_copies}) '
                f'-> {book.estado_publico_display()}'
            )

        self.stdout.write('')
        if creados:
            self.stdout.write(self.style.SUCCESS(
                f'Listo: {creados} libro(s) de ejemplo agregados. '
                f'Las reservas quedaron a nombre de {lector.email}.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                'No se creó nada: los libros de ejemplo ya estaban en la base de datos.'
            ))

    def _obtener_lector(self):
        """Devuelve un estudiante al que asignarle los préstamos de ejemplo."""
        lector = User.objects.filter(role='stu').first()
        if lector:
            return lector

        lector = User.objects.create(
            name=LECTOR_DEMO['name'],
            last_name=LECTOR_DEMO['last_name'],
            email=LECTOR_DEMO['email'],
            password=make_password(LECTOR_DEMO['password']),
            role='stu',
        )
        self.stdout.write(
            f'  no había estudiantes: se creó {lector.email} '
            f'(contraseña: {LECTOR_DEMO["password"]})'
        )
        return lector

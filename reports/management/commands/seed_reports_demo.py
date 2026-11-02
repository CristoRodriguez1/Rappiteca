"""
Loads a history of example loans so the Reports tab (FR-31 / FR-32) has data
to show. The database (db.sqlite3) is not in the repository, so every
environment (local or server) needs this command to show the reports.

What it creates:
- 6 reader accounts (they cannot log in: their password is unusable).
- 8 books in different categories, each borrowed a different number of times
  in the last months (FR-31: there is a clear ranking).
- Some loans returned late, two books still out and overdue, and fines in the
  three states: pending, awaiting confirmation and paid (FR-32).

Usage:
    python manage.py seed_reports_demo

It can be run several times: if the demo books already exist it does nothing.
"""

from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import Book
from fines.models import Fine
from fines.services import apply_fine
from loans.models import Loan

DEMO_READERS = [
    ('Laura', 'Restrepo', 'laura.restrepo.demo@rappiteca.edu'),
    ('Andrés', 'Gómez', 'andres.gomez.demo@rappiteca.edu'),
    ('Valentina', 'Ríos', 'valentina.rios.demo@rappiteca.edu'),
    ('Santiago', 'Muñoz', 'santiago.munoz.demo@rappiteca.edu'),
    ('Camila', 'Torres', 'camila.torres.demo@rappiteca.edu'),
    ('Mateo', 'Zapata', 'mateo.zapata.demo@rappiteca.edu'),
]

# (title, author, category, isbn, times borrowed)
DEMO_BOOKS = [
    ('La vorágine', 'José Eustasio Rivera', 'Novela', '9780000031001', 8),
    ('El principito', 'Antoine de Saint-Exupéry', 'Infantil', '9780000031002', 7),
    ('Clean Code', 'Robert C. Martin', 'Tecnología', '9780000031003', 6),
    ('Sapiens', 'Yuval Noah Harari', 'Historia', '9780000031004', 5),
    ('Cálculo de una variable', 'James Stewart', 'Matemáticas', '9780000031005', 4),
    ('María', 'Jorge Isaacs', 'Novela', '9780000031006', 3),
    ('Breve historia del tiempo', 'Stephen Hawking', 'Ciencia', '9780000031007', 2),
    ('1984', 'George Orwell', 'Novela', '9780000031008', 1),
]

# Books whose last loan is still out and already overdue: (isbn, days since pickup)
STILL_OUT_OVERDUE = {'9780000031001': 22, '9780000031003': 19}
# Book whose last loan is still out but on time
STILL_OUT_ON_TIME = {'9780000031002': 5}

LOAN_DAYS = 14


class Command(BaseCommand):
    help = 'Create an example loan history for the Reports tab (FR-31 / FR-32)'

    @transaction.atomic
    def handle(self, *args, **options):
        if Book.objects.filter(isbn=DEMO_BOOKS[0][3]).exists():
            self.stdout.write('Demo data for reports already exists. Nothing to do.')
            return

        readers = []
        for name, last_name, email in DEMO_READERS:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create(
                    name=name, last_name=last_name, email=email,
                    password=make_password(None), role='stu',
                )
            readers.append(user)

        now = timezone.now()
        created_loans = 0
        late_returns = []

        for book_index, (title, author, category, isbn, times) in enumerate(DEMO_BOOKS):
            out_now = 1 if isbn in STILL_OUT_OVERDUE or isbn in STILL_OUT_ON_TIME else 0
            book = Book.objects.create(
                title=title, author=author, category=category, isbn=isbn,
                location='Demo shelf', total_copies=2, available_copies=2 - out_now,
                description=f'Demo copy of "{title}".',
            )

            for i in range(times):
                reader = readers[(book_index + i) % len(readers)]
                is_last = i == times - 1

                if is_last and isbn in STILL_OUT_OVERDUE:
                    pickup = now - timedelta(days=STILL_OUT_OVERDUE[isbn])
                    returned = None
                elif is_last and isbn in STILL_OUT_ON_TIME:
                    pickup = now - timedelta(days=STILL_OUT_ON_TIME[isbn])
                    returned = None
                else:
                    # Older loans spread over the last ~10 months
                    pickup = now - timedelta(days=30 + i * 34 + book_index * 4)
                    # Roughly one in three is returned late (2 to 9 days)
                    late_days = 2 + (i + book_index) % 8 if (i + book_index) % 3 == 0 else 0
                    kept = LOAN_DAYS + late_days if late_days else 7 + (i % 6)
                    returned = pickup + timedelta(days=kept)

                loan = Loan.objects.create(
                    user=reader, book=book,
                    status=Loan.STATUS_RETURNED if returned else Loan.STATUS_BORROWED,
                    pickup_date=pickup, return_date=returned,
                )
                # Make the reservation date match the story instead of "today"
                Loan.objects.filter(pk=loan.pk).update(reservation_date=pickup - timedelta(days=1))
                created_loans += 1

                fine = apply_fine(loan)
                if fine is not None and returned:
                    late_returns.append(fine)

        # Older late returns: most were paid, one is waiting for confirmation,
        # the rest stay pending so the report shows the three states.
        late_returns.sort(key=lambda f: f.loan.pickup_date)
        for index, fine in enumerate(late_returns):
            if index == len(late_returns) - 1:
                continue  # most recent one stays pending
            if index % 3 == 2:
                fine.status = Fine.STATUS_PAYMENT_REQUESTED
                fine.payment_requested_at = fine.loan.return_date + timedelta(days=1)
            elif index % 3 == 0:
                fine.status = Fine.STATUS_PAID
                fine.payment_method = 'in_person'
                fine.payment_confirmed_at = fine.loan.return_date + timedelta(days=2)
            fine.save()

        self.stdout.write(self.style.SUCCESS(
            f'Done: {len(DEMO_BOOKS)} books, {created_loans} loans, '
            f'{Fine.objects.filter(loan__book__isbn__startswith="978000003100").count()} fines. '
            'Log in as an admin and open the Reports tab.'
        ))

"""
Loads example loans with an overdue date so the Fines tab (FR-23/FR-24)
has something to show without waiting 14 days.

- "El túnel": still borrowed and 6 days overdue -> fine to pay, still growing.
- "Ficciones": returned 8 days late -> fine to pay, final.

Usage:
    python manage.py seed_fines_demo

It can be run several times: books that already exist are skipped.
"""

from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from catalog.models import Book
from loans.models import Loan
from fines.services import apply_fine

DEMO_USER = {
    'name': 'Lector',
    'last_name': 'Demo',
    'email': 'lector.demo@rappiteca.edu',
    'password': 'demo12345',
}

# (title, author, category, isbn, days since pickup, days since return or None)
DEMO_LOANS = [
    ('El túnel', 'Ernesto Sabato', 'Novela', '9780000023001', 20, None),
    ('Ficciones', 'Jorge Luis Borges', 'Cuento', '9780000023002', 25, 3),
]


class Command(BaseCommand):
    help = 'Create example overdue loans with fines (FR-23/FR-24)'

    def handle(self, *args, **options):
        user = User.objects.filter(email=DEMO_USER['email']).first()
        if user is None:
            user = User.objects.create(
                name=DEMO_USER['name'],
                last_name=DEMO_USER['last_name'],
                email=DEMO_USER['email'],
                password=make_password(DEMO_USER['password']),
                role='stu',
            )

        now = timezone.now()
        for title, author, category, isbn, days_since_pickup, days_since_return in DEMO_LOANS:
            if Book.objects.filter(isbn=isbn).exists():
                self.stdout.write(f'  skipped: {title} (already exists)')
                continue

            book = Book.objects.create(
                title=title,
                author=author,
                category=category,
                isbn=isbn,
                location='Demo shelf',
                total_copies=1,
                available_copies=0 if days_since_return is None else 1,
            )
            loan = Loan.objects.create(user=user, book=book, status=Loan.STATUS_BORROWED)
            loan.pickup_date = now - timedelta(days=days_since_pickup)
            if days_since_return is not None:
                loan.status = Loan.STATUS_RETURNED
                loan.return_date = now - timedelta(days=days_since_return)
            loan.save()

            fine = apply_fine(loan)
            self.stdout.write(self.style.WARNING(
                f'  created: {title} -> {user.email}: {fine.days_overdue} day(s) overdue, fine {fine.amount}'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'Done. Log in as an admin and open the Fines tab. Demo user: {user.email}'
        ))

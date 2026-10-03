import time

from django.test import Client, TestCase
from django.utils import timezone

from accounts.models import User
from catalog.models import Book

from .models import Loan


class FR22LoanHistoryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            name='Ana',
            last_name='Gomez',
            email='ana.gomez@example.com',
            password='secret123',
            role='stu',
        )
        self.other_user = User.objects.create(
            name='Luis',
            last_name='Perez',
            email='luis.perez@example.com',
            password='secret123',
            role='stu',
        )

        statuses = {
            'Reserved Book': Loan.STATUS_RESERVED,
            'Borrowed Book': Loan.STATUS_BORROWED,
            'Returned Book': Loan.STATUS_RETURNED,
            'Cancelled Book': Loan.STATUS_CANCELLED,
        }
        for i, (title, status) in enumerate(statuses.items()):
            book = Book.objects.create(
                title=title,
                author='Test Author',
                isbn=f'978000000000{i}',
                total_copies=1,
                available_copies=1,
            )
            Loan.objects.create(
                user=self.user,
                book=book,
                status=status,
                pickup_date=timezone.now() if status in (Loan.STATUS_BORROWED, Loan.STATUS_RETURNED) else None,
                return_date=timezone.now() if status == Loan.STATUS_RETURNED else None,
            )

        other_book = Book.objects.create(
            title='Someone Elses Book',
            author='Other Author',
            isbn='9780000000099',
            total_copies=1,
            available_copies=0,
        )
        Loan.objects.create(user=self.other_user, book=other_book, status=Loan.STATUS_RETURNED)

    def _login(self, user):
        session = self.client.session
        session['user_id'] = user.id
        session['user_role'] = user.role
        session.save()

    def test_fr22_history_displays_complete_loan_history_within_three_seconds(self):
        self._login(self.user)

        start = time.monotonic()
        response = self.client.get('/loans/historial/')
        elapsed = time.monotonic() - start

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['loans']), 4)
        for title in ('Reserved Book', 'Borrowed Book', 'Returned Book', 'Cancelled Book'):
            self.assertContains(response, title)
        self.assertLess(elapsed, 3.0)

    def test_fr22_history_includes_loans_hidden_from_my_loans(self):
        self._login(self.user)

        my_loans = self.client.get('/loans/mis-prestamos/')
        history = self.client.get('/loans/historial/')

        self.assertNotContains(my_loans, 'Returned Book')
        self.assertNotContains(my_loans, 'Cancelled Book')
        self.assertContains(history, 'Returned Book')
        self.assertContains(history, 'Cancelled Book')

    def test_fr22_history_only_shows_current_users_loans(self):
        self._login(self.user)

        response = self.client.get('/loans/historial/')

        self.assertNotContains(response, 'Someone Elses Book')

    def test_fr22_history_shows_empty_state_without_loans(self):
        new_user = User.objects.create(
            name='New',
            last_name='User',
            email='new.user@example.com',
            password='secret123',
            role='stu',
        )
        self._login(new_user)

        response = self.client.get('/loans/historial/')

        self.assertEqual(len(response.context['loans']), 0)
        self.assertContains(response, "You haven't borrowed or reserved any books yet.")

    def test_fr22_history_requires_login(self):
        response = self.client.get('/loans/historial/')

        self.assertRedirects(response, '/login/', fetch_redirect_response=False)

    def test_fr22_history_redirects_administrators(self):
        admin = User.objects.create(
            name='Admin',
            last_name='Root',
            email='admin@example.com',
            password='secret123',
            role='adm',
        )
        self._login(admin)

        response = self.client.get('/loans/historial/')

        self.assertRedirects(response, '/', fetch_redirect_response=False)

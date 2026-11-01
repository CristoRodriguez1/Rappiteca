import time
from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase
from django.utils import timezone

from catalog.models import Book
from fines.models import Fine
from loans.models import Loan

from .models import User


class FR28UsersInformationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create(
            name='Admin', last_name='User', email='admin@example.com',
            password='secret123', role='adm',
        )
        self.student = User.objects.create(
            name='Jane', last_name='Doe', email='jane.doe@example.com',
            password='secret123', role='stu',
        )
        self.other = User.objects.create(
            name='Bob', last_name='Smith', email='bob@example.com',
            password='secret123', role='stu',
        )
        self.book = Book.objects.create(
            title='Dune', author='Frank Herbert', total_copies=3, available_copies=1,
        )
        self.returned_book = Book.objects.create(
            title='Foundation', author='Isaac Asimov', total_copies=1, available_copies=1,
        )

        # One overdue loan (picked up 20 days ago, due after 14), one reservation
        # and one returned loan with an unpaid fine.
        self.overdue_loan = Loan.objects.create(
            user=self.student, book=self.book, status=Loan.STATUS_BORROWED,
            pickup_date=timezone.now() - timedelta(days=20),
        )
        Loan.objects.create(user=self.student, book=self.book, status=Loan.STATUS_RESERVED)
        returned_loan = Loan.objects.create(
            user=self.student, book=self.returned_book, status=Loan.STATUS_RETURNED,
            pickup_date=timezone.now() - timedelta(days=30),
            return_date=timezone.now() - timedelta(days=10),
        )
        Fine.objects.create(
            loan=returned_loan, user=self.student, days_overdue=6,
            daily_rate=Decimal('1000.00'), amount=Decimal('6000.00'),
        )

    def _login(self, user):
        session = self.client.session
        session['user_id'] = user.id
        session['user_role'] = user.role
        session.save()

    def test_fr28_non_admin_cannot_view_user_list(self):
        self._login(self.student)
        response = self.client.get('/admin-users/')
        self.assertRedirects(response, '/')

    def test_fr28_anonymous_cannot_view_user_detail(self):
        response = self.client.get(f'/admin-users/{self.student.id}/')
        self.assertRedirects(response, '/')

    def test_fr28_admin_sees_all_registered_users(self):
        self._login(self.admin)
        response = self.client.get('/admin-users/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'jane.doe@example.com')
        self.assertContains(response, 'bob@example.com')
        self.assertContains(response, 'admin@example.com')

    def test_fr28_user_list_counts_active_loans(self):
        self._login(self.admin)
        response = self.client.get('/admin-users/')
        rows = {row['user'].email: row['user'].active_loans for row in response.context['rows']}
        self.assertEqual(rows['jane.doe@example.com'], 2)
        self.assertEqual(rows['bob@example.com'], 0)

    def test_fr28_search_by_name_or_email(self):
        self._login(self.admin)
        response = self.client.get('/admin-users/', {'q': 'doe'})
        self.assertEqual([row['user'] for row in response.context['rows']], [self.student])

        response = self.client.get('/admin-users/', {'q': 'bob@'})
        self.assertEqual([row['user'] for row in response.context['rows']], [self.other])

        response = self.client.get('/admin-users/', {'q': 'nobody'})
        self.assertContains(response, 'No users match')

    def test_fr28_admin_sees_user_profile_information(self):
        self._login(self.admin)
        response = self.client.get(f'/admin-users/{self.student.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane Doe')
        self.assertContains(response, 'jane.doe@example.com')
        self.assertContains(response, 'Student')

    def test_fr28_detail_shows_account_summary(self):
        self._login(self.admin)
        response = self.client.get(f'/admin-users/{self.student.id}/')
        self.assertEqual(len(response.context['active_loans']), 2)
        self.assertEqual(response.context['overdue_count'], 1)
        self.assertEqual(response.context['total_loans'], 3)
        self.assertEqual(response.context['unpaid_total'], Decimal('6000.00'))
        self.assertContains(response, 'Overdue')

    def test_fr28_paid_fines_are_not_counted(self):
        Fine.objects.filter(user=self.student).update(status=Fine.STATUS_PAID)
        self._login(self.admin)
        response = self.client.get(f'/admin-users/{self.student.id}/')
        self.assertEqual(response.context['unpaid_total'], Decimal('0.00'))

    def test_fr28_user_without_loans(self):
        self._login(self.admin)
        response = self.client.get(f'/admin-users/{self.other.id}/')
        self.assertContains(response, 'This user has no loans yet.')

    def test_fr28_unknown_user_returns_404(self):
        self._login(self.admin)
        response = self.client.get('/admin-users/99999/')
        self.assertEqual(response.status_code, 404)

    def test_fr28_users_tab_in_admin_panel(self):
        self._login(self.admin)
        response = self.client.get('/admin-prestamos/')
        self.assertContains(response, 'href="/admin-users/"')

    def test_fr28_responds_within_3_seconds(self):
        self._login(self.admin)
        start = time.perf_counter()
        response = self.client.get(f'/admin-users/{self.student.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertLess(time.perf_counter() - start, 3)

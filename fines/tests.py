import time
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from catalog.models import Book
from loans.models import Loan

from .models import Fine
from .services import apply_fine, calculate_fine, user_pending_fines_total


@override_settings(FINE_DAILY_RATE=Decimal('1000.00'))
class FR23FR24FineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name='Ana',
            last_name='Gomez',
            email='ana.gomez@example.com',
            password='secret123',
            role='stu',
        )
        self.book = Book.objects.create(
            title='Fine Book',
            author='Test Author',
            isbn='9780000000100',
            total_copies=1,
            available_copies=0,
        )

    def _loan(self, days_since_pickup, renewals=0, status=Loan.STATUS_BORROWED):
        loan = Loan.objects.create(user=self.user, book=self.book, status=status, renewals=renewals)
        loan.pickup_date = timezone.now() - timedelta(days=days_since_pickup)
        loan.save()
        return loan

    # ---------- FR-23 Calculate fine ----------

    def test_loan_not_overdue_has_no_fine(self):
        loan = self._loan(days_since_pickup=10)
        self.assertEqual(calculate_fine(loan), (0, Decimal('0.00')))
        self.assertIsNone(apply_fine(loan))
        self.assertFalse(Fine.objects.exists())

    def test_fine_is_based_on_overdue_days(self):
        loan = self._loan(days_since_pickup=19)  # due after 14 days -> 5 days late
        days, amount = calculate_fine(loan)
        self.assertEqual(days, 5)
        self.assertEqual(amount, Decimal('5000.00'))

    def test_renewals_extend_due_date_before_fining(self):
        loan = self._loan(days_since_pickup=20, renewals=1)  # due after 28 days
        self.assertEqual(calculate_fine(loan), (0, Decimal('0.00')))

    def test_reserved_loan_is_never_fined(self):
        loan = Loan.objects.create(user=self.user, book=self.book)
        self.assertEqual(calculate_fine(loan), (0, Decimal('0.00')))

    # ---------- FR-24 Apply fine ----------

    def test_fine_is_applied_to_user_account(self):
        loan = self._loan(days_since_pickup=17)
        fine = apply_fine(loan)
        self.assertEqual(fine.user, self.user)
        self.assertEqual(fine.status, Fine.STATUS_PENDING)
        self.assertEqual(list(self.user.fines.all()), [fine])
        self.assertEqual(user_pending_fines_total(self.user), Decimal('3000.00'))

    def test_fine_is_applied_within_3_seconds(self):
        loan = self._loan(days_since_pickup=17)
        start = time.perf_counter()
        apply_fine(loan)
        self.assertLess(time.perf_counter() - start, 3)

    def test_recalculating_updates_the_same_fine(self):
        loan = self._loan(days_since_pickup=17)
        apply_fine(loan)
        apply_fine(loan, today=timezone.localdate() + timedelta(days=2))
        self.assertEqual(Fine.objects.count(), 1)
        fine = Fine.objects.get()
        self.assertEqual(fine.days_overdue, 5)
        self.assertEqual(fine.amount, Decimal('5000.00'))

    def test_paid_fine_is_not_changed(self):
        loan = self._loan(days_since_pickup=17)
        fine = apply_fine(loan)
        fine.status = Fine.STATUS_PAID
        fine.save()
        apply_fine(loan, today=timezone.localdate() + timedelta(days=10))
        fine.refresh_from_db()
        self.assertEqual(fine.amount, Decimal('3000.00'))

    def test_returning_late_book_applies_final_fine(self):
        loan = self._loan(days_since_pickup=16)
        loan.mark_returned()
        fine = Fine.objects.get(loan=loan)
        self.assertTrue(fine.is_final)
        self.assertEqual(fine.days_overdue, 2)

        # Once returned, the fine no longer grows.
        apply_fine(loan, today=timezone.localdate() + timedelta(days=30))
        fine.refresh_from_db()
        self.assertEqual(fine.days_overdue, 2)

    def test_returning_on_time_applies_no_fine(self):
        loan = self._loan(days_since_pickup=5)
        loan.mark_returned()
        self.assertFalse(Fine.objects.exists())

    def test_command_applies_fines_to_overdue_loans(self):
        self._loan(days_since_pickup=18)
        out = StringIO()
        call_command('calculate_fines', stdout=out)
        self.assertEqual(Fine.objects.count(), 1)
        self.assertIn('Fines applied or updated: 1', out.getvalue())


@override_settings(FINE_DAILY_RATE=Decimal('1000.00'))
class FinesAdminTabTests(TestCase):
    def setUp(self):
        User.objects.create(
            name='Admin', last_name='Demo', email='admin@example.com',
            password='secret123', role='adm',
        )

    def _login(self, role):
        session = self.client.session
        session['user_id'] = User.objects.get(email='admin@example.com').id
        session['user_role'] = role
        session.save()

    def test_non_admin_is_redirected(self):
        response = self.client.get('/admin-fines/')
        self.assertRedirects(response, '/')

    def test_admin_sees_overdue_book_with_fine(self):
        call_command('seed_fines_demo', stdout=StringIO())
        self._login('adm')
        response = self.client.get('/admin-fines/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El túnel')
        self.assertContains(response, 'Ficciones')
        self.assertContains(response, 'To pay')
        self.assertEqual(Fine.objects.count(), 2)

    def test_fines_tab_appears_in_admin_panel(self):
        self._login('adm')
        response = self.client.get('/admin-prestamos/')
        self.assertContains(response, 'href="/admin-fines/"')

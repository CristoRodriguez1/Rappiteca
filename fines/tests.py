import time
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Notification, User
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


@override_settings(FINE_DAILY_RATE=Decimal('1000.00'))
class FR25FinePaymentStatusTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(
            name='Admin', last_name='User', email='admin@example.com',
            password='secret123', role='adm',
        )
        self.user = User.objects.create(
            name='Ana', last_name='Gomez', email='ana.gomez@example.com',
            password='secret123', role='stu',
        )
        self.other = User.objects.create(
            name='Bob', last_name='Smith', email='bob@example.com',
            password='secret123', role='stu',
        )
        book = Book.objects.create(title='Dune', author='Frank Herbert', total_copies=3, available_copies=1)
        other_book = Book.objects.create(title='Ficciones', author='Borges', total_copies=1, available_copies=0)
        self.loan = Loan.objects.create(
            user=self.user, book=book, status=Loan.STATUS_BORROWED,
            pickup_date=timezone.now() - timedelta(days=20),
        )
        Loan.objects.create(
            user=self.other, book=other_book, status=Loan.STATUS_BORROWED,
            pickup_date=timezone.now() - timedelta(days=20),
        )

    def _login(self, user):
        session = self.client.session
        session['user_id'] = user.id
        session['user_role'] = user.role
        session.save()

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get('/my-fines/')
        self.assertRedirects(response, '/login/')

    def test_user_sees_only_their_own_fines(self):
        self._login(self.user)
        response = self.client.get('/my-fines/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dune')
        self.assertNotContains(response, 'Ficciones')
        self.assertEqual(response.context['pending_total'], Decimal('6000.00'))

    def test_admin_sees_all_fines(self):
        self._login(self.admin)
        response = self.client.get('/admin-fines/')
        self.assertContains(response, 'Dune')
        self.assertContains(response, 'Ficciones')
        self.assertEqual(response.context['pending_total'], Decimal('12000.00'))

    def test_payment_status_goes_from_pending_to_paid(self):
        apply_fine(self.loan)
        fine = Fine.objects.get(loan=self.loan)

        self._login(self.user)
        response = self.client.get('/my-fines/')
        self.assertContains(response, 'To pay')

        self.client.get(f'/request-payment/{fine.id}/')
        fine.refresh_from_db()
        self.assertEqual(fine.status, Fine.STATUS_PAYMENT_REQUESTED)
        response = self.client.get('/my-fines/')
        self.assertContains(response, 'Awaiting confirmation')

        self._login(self.admin)
        self.client.get(f'/confirm-payment/{fine.id}/')
        fine.refresh_from_db()
        self.assertEqual(fine.status, Fine.STATUS_PAID)
        self.assertEqual(fine.confirmed_by, self.admin)

        self._login(self.user)
        response = self.client.get('/my-fines/')
        self.assertEqual(response.context['paid_total'], Decimal('6000.00'))

    def test_user_cannot_request_payment_of_another_users_fine(self):
        other_fine = apply_fine(Loan.objects.get(user=self.other))
        self._login(self.user)
        response = self.client.get(f'/request-payment/{other_fine.id}/')
        self.assertEqual(response.status_code, 404)

    def test_fines_pages_load_within_3_seconds(self):
        for user, url in ((self.user, '/my-fines/'), (self.admin, '/admin-fines/')):
            self._login(user)
            start = time.perf_counter()
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertLess(time.perf_counter() - start, 3)


@override_settings(FINE_DAILY_RATE=Decimal('1000.00'))
class FR26FineNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name='Ana', last_name='Gomez', email='ana.gomez@example.com',
            password='secret123', role='stu',
        )
        self.book = Book.objects.create(title='Dune', author='Frank Herbert', total_copies=1, available_copies=0)
        self.loan = Loan.objects.create(
            user=self.user, book=self.book, status=Loan.STATUS_BORROWED,
            pickup_date=timezone.now() - timedelta(days=30),
        )

    def _fine_notifications(self, fine):
        return Notification.objects.filter(
            user=self.user,
            notification_type=Notification.TYPE_FINE_APPLIED,
            related_fine_id=fine.id,
        )

    def test_user_is_notified_when_fine_is_applied(self):
        fine = apply_fine(self.loan)
        notification = self._fine_notifications(fine).get()
        self.assertIn('Fine Applied', notification.title)
        self.assertIn('Dune', notification.title)
        self.assertIn(str(fine.amount), notification.message)
        self.assertEqual(notification.related_loan_id, self.loan.id)
        self.assertFalse(notification.is_read)

    def test_no_notification_when_loan_is_not_overdue(self):
        self.loan.pickup_date = timezone.now()
        self.loan.save()
        apply_fine(self.loan)
        self.assertFalse(Notification.objects.filter(user=self.user).exists())

    def test_update_within_24_hours_does_not_repeat_notification(self):
        fine = apply_fine(self.loan)
        self.loan.pickup_date = timezone.now() - timedelta(days=35)
        self.loan.save()
        apply_fine(self.loan)
        self.assertEqual(self._fine_notifications(fine).count(), 1)

    def test_update_after_24_hours_sends_updated_notification(self):
        fine = apply_fine(self.loan)
        self._fine_notifications(fine).update(created_at=timezone.now() - timedelta(hours=25))
        self.loan.pickup_date = timezone.now() - timedelta(days=35)
        self.loan.save()
        apply_fine(self.loan)

        latest = self._fine_notifications(fine).order_by('-created_at').first()
        self.assertEqual(self._fine_notifications(fine).count(), 2)
        self.assertIn('Fine Updated', latest.title)

    def test_notification_appears_in_notifications_page(self):
        apply_fine(self.loan)
        session = self.client.session
        session['user_id'] = self.user.id
        session['user_role'] = self.user.role
        session.save()
        response = self.client.get('/accounts/notifications/')
        self.assertContains(response, 'Fine Applied')

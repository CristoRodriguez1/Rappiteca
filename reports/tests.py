import time
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from catalog.models import Book
from fines.models import Fine
from loans.models import Loan

from .services import most_borrowed_books, overdue_fines_report


@override_settings(FINE_DAILY_RATE=Decimal('1000.00'))
class ReportsTestBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create(name='Ada', last_name='Admin', email='ada@example.com',
                                         password='x', role='adm')
        self.ana = User.objects.create(name='Ana', last_name='Gomez', email='ana@example.com',
                                       password='x', role='stu')
        self.leo = User.objects.create(name='Leo', last_name='Diaz', email='leo@example.com',
                                       password='x', role='stu')
        self.popular = Book.objects.create(title='Popular', author='A', category='Novela',
                                           isbn='9780000099001', total_copies=3, available_copies=3)
        self.rare = Book.objects.create(title='Rare', author='B', category='Ciencia',
                                        isbn='9780000099002', total_copies=1, available_copies=1)
        self.unused = Book.objects.create(title='Unused', author='C', category='Novela',
                                          isbn='9780000099003', total_copies=1, available_copies=1)

    def loan(self, user, book, days_ago, kept=None, status=None):
        now = timezone.now()
        pickup = now - timedelta(days=days_ago)
        returned = pickup + timedelta(days=kept) if kept is not None else None
        return Loan.objects.create(
            user=user, book=book,
            status=status or (Loan.STATUS_RETURNED if returned else Loan.STATUS_BORROWED),
            pickup_date=pickup, return_date=returned,
        )

    def login_admin(self):
        session = self.client.session
        session['user_id'] = self.admin.id
        session['user_role'] = 'adm'
        session.save()


class FR31MostBorrowedTests(ReportsTestBase):
    def test_ranking_counts_only_picked_up_loans(self):
        self.loan(self.ana, self.popular, 40, kept=7)
        self.loan(self.leo, self.popular, 20, kept=7)
        self.loan(self.ana, self.popular, 3)
        self.loan(self.ana, self.rare, 10, kept=5)
        # Reservations and cancellations are not borrows
        Loan.objects.create(user=self.leo, book=self.rare, status=Loan.STATUS_RESERVED)
        Loan.objects.create(user=self.leo, book=self.rare, status=Loan.STATUS_CANCELLED)

        report = most_borrowed_books()
        rows = report['rows']
        self.assertEqual([r['book'].title for r in rows], ['Popular', 'Rare'])
        self.assertEqual(rows[0]['times_borrowed'], 3)
        self.assertEqual(rows[0]['borrowers'], 2)
        self.assertEqual(rows[0]['currently_out'], 1)
        self.assertEqual(rows[0]['bar'], 100)
        self.assertEqual(report['total_borrows'], 4)
        self.assertEqual(report['books_with_borrows'], 2)

    def test_period_filter(self):
        self.loan(self.ana, self.rare, 200, kept=5)
        self.loan(self.ana, self.popular, 10, kept=5)
        rows = most_borrowed_books(period='30')['rows']
        self.assertEqual([r['book'].title for r in rows], ['Popular'])

    def test_page_requires_admin(self):
        response = self.client.get(reverse('reports_most_borrowed'))
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_page_renders_within_5_seconds(self):
        self.loan(self.ana, self.popular, 10, kept=5)
        self.login_admin()
        started = time.perf_counter()
        response = self.client.get(reverse('reports_most_borrowed'), {'period': '90'})
        self.assertLess(time.perf_counter() - started, 5)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Popular')
        self.assertContains(response, 'FR-31')

    def test_csv_export(self):
        self.loan(self.ana, self.popular, 10, kept=5)
        self.login_admin()
        response = self.client.get(reverse('reports_most_borrowed'), {'export': 'csv'})
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('Popular', response.content.decode())


@override_settings(FINE_DAILY_RATE=Decimal('1000.00'))
class FR32OverdueFinesTests(ReportsTestBase):
    def test_overdue_rate_and_fines(self):
        self.loan(self.ana, self.popular, 60, kept=7)            # on time
        late = self.loan(self.leo, self.popular, 40, kept=20)    # 6 days late, returned
        self.loan(self.ana, self.rare, 18)                       # 4 days late, still out
        from fines.services import apply_fine
        fine = apply_fine(late)
        fine.status = Fine.STATUS_PAID
        fine.save()

        report = overdue_fines_report()
        self.assertEqual(report['total_loans'], 3)
        self.assertEqual(report['overdue_loans'], 2)
        self.assertEqual(report['overdue_rate'], 66.7)
        self.assertEqual(len(report['overdue_now']), 1)
        self.assertEqual(report['overdue_now'][0]['days_overdue'], 4)
        self.assertEqual(report['paid_total'], Decimal('6000.00'))
        rates = {c['name']: c['rate'] for c in report['categories']}
        self.assertEqual(rates, {'Ciencia': 100.0, 'Novela': 50.0})

    def test_page_applies_fines_and_shows_debtors(self):
        self.loan(self.ana, self.rare, 18)  # 4 days late, still out
        self.login_admin()
        started = time.perf_counter()
        response = self.client.get(reverse('reports_overdue_fines'))
        self.assertLess(time.perf_counter() - started, 5)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Fine.objects.filter(user=self.ana).exists())
        self.assertContains(response, 'ana@example.com')
        self.assertContains(response, 'FR-32')

    def test_empty_report(self):
        self.login_admin()
        response = self.client.get(reverse('reports_overdue_fines'), {'period': '30'})
        self.assertContains(response, 'No loans were picked up in this period.')

    def test_page_requires_admin(self):
        response = self.client.get(reverse('reports_overdue_fines'))
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)


class SeedReportsDemoTests(TestCase):
    def test_seed_is_idempotent_and_fills_both_reports(self):
        call_command('seed_reports_demo', stdout=StringIO())
        call_command('seed_reports_demo', stdout=StringIO())
        self.assertEqual(Book.objects.filter(isbn__startswith='978000003100').count(), 8)
        top = most_borrowed_books()['rows'][0]
        self.assertEqual(top['book'].title, 'La vorágine')
        report = overdue_fines_report()
        self.assertGreater(report['overdue_rate'], 0)
        self.assertEqual(len(report['overdue_now']), 2)
        self.assertGreater(report['paid_total'], 0)
        self.assertGreater(report['requested_total'], 0)
        self.assertGreater(report['pending_total'], 0)

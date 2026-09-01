import time

from django.test import Client, TestCase
from django.utils import timezone

from accounts.models import User
from loans.models import Loan

from .models import Book


class FR16BorrowerDisplayTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create(
            name='Admin',
            last_name='User',
            email='admin@example.com',
            password='secret123',
            role='adm',
        )
        self.borrower = User.objects.create(
            name='Jane',
            last_name='Doe',
            email='jane.doe@example.com',
            password='secret123',
            role='stu',
        )
        self.book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            isbn='9780000000001',
            total_copies=1,
            available_copies=0,
        )
        self.loan = Loan.objects.create(
            user=self.borrower,
            book=self.book,
            estado=Loan.ESTADO_PRESTADO,
            fecha_recogida=timezone.now(),
        )

    def _login_admin(self):
        session = self.client.session
        session['user_id'] = self.admin.id
        session['user_role'] = self.admin.role
        session.save()

    def test_fr16_non_admin_cannot_view_borrower_detail(self):
        response = self.client.get(f'/admin-book-borrowers/{self.book.id}/')
        self.assertEqual(response.status_code, 302)

    def test_fr16_admin_sees_borrower_information_within_three_seconds(self):
        self._login_admin()

        start = time.monotonic()
        response = self.client.get(f'/admin-book-borrowers/{self.book.id}/')
        elapsed = time.monotonic() - start

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane Doe')
        self.assertContains(response, 'jane.doe@example.com')
        self.assertContains(response, 'Checked out')
        self.assertLess(elapsed, 3.0)

    def test_fr16_admin_book_list_links_to_detail(self):
        self._login_admin()

        response = self.client.get('/admin-book-borrowers/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View borrower')
        self.assertContains(response, self.book.title)

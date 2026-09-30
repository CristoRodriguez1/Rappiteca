import time

from django.test import Client, TestCase

from .models import User


class FR21ProfileDisplayTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            name='Ana',
            last_name='Gomez',
            email='ana.gomez@example.com',
            password='secret123',
            role='stu',
        )

    def _login(self, user):
        session = self.client.session
        session['user_id'] = user.id
        session['user_role'] = user.role
        session.save()

    def test_fr21_profile_displays_personal_information_within_three_seconds(self):
        self._login(self.user)

        start = time.monotonic()
        response = self.client.get('/accounts/profile/')
        elapsed = time.monotonic() - start

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Gomez')
        self.assertContains(response, 'ana.gomez@example.com')
        self.assertContains(response, 'Student')
        self.assertLess(elapsed, 3.0)

    def test_fr21_profile_shows_administrator_role(self):
        admin = User.objects.create(
            name='Admin',
            last_name='Root',
            email='admin@example.com',
            password='secret123',
            role='adm',
        )
        self._login(admin)

        response = self.client.get('/accounts/profile/')

        self.assertContains(response, 'Administrator')
        self.assertContains(response, 'admin@example.com')

    def test_fr21_profile_does_not_expose_password(self):
        self._login(self.user)

        response = self.client.get('/accounts/profile/')

        self.assertNotContains(response, 'secret123')

    def test_fr21_profile_requires_login(self):
        response = self.client.get('/accounts/profile/')

        self.assertRedirects(response, '/login/', fetch_redirect_response=False)

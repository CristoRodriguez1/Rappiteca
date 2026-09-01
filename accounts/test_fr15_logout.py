import time

from django.test import Client, TestCase

from .models import User


class FR15LogoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            name='Test',
            last_name='User',
            email='test.user@example.com',
            password='secret123',
            role='stu',
        )

    def test_fr15_confirm_end_session_clears_session_within_three_seconds(self):
        session = self.client.session
        session['user_id'] = self.user.id
        session['user_role'] = self.user.role
        session.save()

        start = time.monotonic()
        response = self.client.post('/accounts/end-session/confirm/')
        elapsed = time.monotonic() - start

        self.assertEqual(response.status_code, 302)
        self.assertNotIn('user_id', self.client.session)
        self.assertNotIn('user_role', self.client.session)
        self.assertLess(elapsed, 3.0)

    def test_fr15_existing_logout_endpoint_still_ends_session(self):
        session = self.client.session
        session['user_id'] = self.user.id
        session['user_role'] = self.user.role
        session.save()

        response = self.client.get('/logout/')

        self.assertEqual(response.status_code, 302)
        self.assertNotIn('user_id', self.client.session)

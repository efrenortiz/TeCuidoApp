from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class HomeViewTests(TestCase):
    def test_login_redirects_to_a_working_home_page(self):
        User.objects.create_user(
            email="home@example.com", password="s3cure-pass!", email_verified=True
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "home@example.com", "password": "s3cure-pass!"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], "/")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)

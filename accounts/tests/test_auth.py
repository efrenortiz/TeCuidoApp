from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import User


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.password = "s3cure-pass!"
        self.user = User.objects.create_user(
            email="user@example.com", password=self.password, email_verified=True
        )

    def test_login_with_correct_credentials_succeeds(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "user@example.com", "password": self.password},
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_incorrect_password_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "user@example.com", "password": "wrong-password"},
        )
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_with_inactive_user_fails(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "user@example.com", "password": self.password},
        )
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_with_unverified_email_fails(self):
        unverified = User.objects.create_user(
            email="unverified@example.com", password=self.password
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "unverified@example.com", "password": self.password},
        )
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, "verificar tu correo")
        self.assertFalse(unverified.email_verified)

    def test_logout_clears_session(self):
        self.client.login(username="user@example.com", password=self.password)
        response = self.client.post(reverse("accounts:logout"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.password = "s3cure-pass!"
        self.user = User.objects.create_user(email="user@example.com", password=self.password)
        self.client.login(username="user@example.com", password=self.password)

    def test_password_change_updates_password(self):
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": self.password,
                "new_password1": "another-s3cure-pass!",
                "new_password2": "another-s3cure-pass!",
            },
        )
        self.assertRedirects(response, reverse("accounts:password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("another-s3cure-pass!"))


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="s3cure-pass!")

    def test_password_reset_sends_email(self):
        self.client.post(reverse("accounts:password_reset"), {"email": "user@example.com"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("user@example.com", mail.outbox[0].to)

    def test_password_reset_confirm_sets_new_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # Django's PasswordResetConfirmView redirects a valid (uid, token) GET
        # to an internal "set-password" URL backed by the session; the POST
        # with the new password must target that redirected URL, not the
        # original emailed one (posting there again just redirects again).
        first_url = reverse(
            "accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token}
        )
        get_response = self.client.get(first_url, follow=True)
        set_password_url = get_response.redirect_chain[-1][0]

        response = self.client.post(
            set_password_url,
            {"new_password1": "brand-new-pass!", "new_password2": "brand-new-pass!"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brand-new-pass!"))

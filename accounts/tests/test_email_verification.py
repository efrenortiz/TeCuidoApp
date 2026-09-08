import time

from django.test import TestCase, override_settings

from accounts.models import User
from accounts.services import email_verification


class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="s3cure-pass!")

    def test_valid_token_verifies_user(self):
        token = email_verification.generate_email_verification_token(self.user)
        verified = email_verification.verify_email_token(token)
        self.assertEqual(verified.pk, self.user.pk)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_invalid_token_is_rejected(self):
        with self.assertRaises(email_verification.InvalidVerificationToken):
            email_verification.verify_email_token("not-a-real-token")

    def test_reusing_a_token_after_verification_is_rejected(self):
        token = email_verification.generate_email_verification_token(self.user)
        email_verification.verify_email_token(token)

        with self.assertRaises(email_verification.EmailAlreadyVerified):
            email_verification.verify_email_token(token)

    @override_settings(EMAIL_VERIFICATION_TTL_HOURS=1 / 3600)  # 1 second
    def test_expired_token_is_rejected(self):
        token = email_verification.generate_email_verification_token(self.user)
        time.sleep(1.5)
        with self.assertRaises(email_verification.VerificationTokenExpired):
            email_verification.verify_email_token(token)

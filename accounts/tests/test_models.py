from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Person, User


class UserModelTests(TestCase):
    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(email="  Test@Example.COM ", password="s3cure-pass!")
        self.assertEqual(user.email, "test@example.com")

    def test_create_user_hashes_password(self):
        user = User.objects.create_user(email="a@example.com", password="s3cure-pass!")
        self.assertNotEqual(user.password, "s3cure-pass!")
        self.assertTrue(user.check_password("s3cure-pass!"))

    def test_email_is_unique_at_db_level(self):
        User.objects.create_user(email="dup@example.com", password="s3cure-pass!")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create(email="dup@example.com", password="whatever")

    def test_email_uniqueness_is_case_insensitive(self):
        User.objects.create_user(email="dup2@example.com", password="s3cure-pass!")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(email="Dup2@Example.com", password="s3cure-pass!")

    def test_direct_save_also_normalizes_email(self):
        # Covers paths that bypass the manager (e.g. the Django admin form,
        # which calls user.save() directly).
        user = User(email="  Mixed@Example.COM  ")
        user.set_password("s3cure-pass!")
        user.save()
        self.assertEqual(user.email, "mixed@example.com")

    def test_login_matches_stored_email_case_insensitively(self):
        User.objects.create_user(email="caselogin@example.com", password="s3cure-pass!")
        found = User.objects.get_by_natural_key("CaseLogin@Example.com")
        self.assertEqual(found.email, "caselogin@example.com")

    def test_email_verified_defaults_false(self):
        user = User.objects.create_user(email="b@example.com", password="s3cure-pass!")
        self.assertFalse(user.email_verified)

    def test_is_active_defaults_true(self):
        user = User.objects.create_user(email="c@example.com", password="s3cure-pass!")
        self.assertTrue(user.is_active)

    def test_create_superuser_sets_flags(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="s3cure-pass!")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.email_verified)


class PersonModelTests(TestCase):
    def test_person_can_exist_without_a_user(self):
        person = Person.objects.create(
            first_name="Ana", last_name_paterno="Lopez", birth_date=date(2015, 1, 1)
        )
        self.assertIsNone(person.user)

    def test_person_str_is_full_name(self):
        person = Person.objects.create(
            first_name="Ana", last_name_paterno="Lopez", last_name_materno="Diaz",
            birth_date=date(1990, 1, 1),
        )
        self.assertEqual(str(person), "Ana Lopez Diaz")

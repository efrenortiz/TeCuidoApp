from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from accounts.models import Person, User
from accounts.roles import ADMINISTRATOR, DOCTOR, PATIENT, RESPONSIBLE, has_role, user_roles
from doctors.models import Doctor
from patients.models import Patient, Responsible


def _make_person(email, first_name):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1)
    )


class RoleDerivationTests(TestCase):
    def test_anonymous_user_has_no_roles(self):
        self.assertEqual(user_roles(AnonymousUser()), [])

    def test_plain_user_without_profile_has_no_roles(self):
        user = User.objects.create_user(email="plain@example.com", password="s3cure-pass!")
        self.assertEqual(user_roles(user), [])

    def test_superuser_has_administrator_role(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="s3cure-pass!")
        self.assertTrue(has_role(admin, ADMINISTRATOR))

    def test_doctor_profile_grants_doctor_role(self):
        person = _make_person("doc@example.com", "Doc")
        Doctor.objects.create(person=person)
        self.assertTrue(has_role(person.user, DOCTOR))

    def test_patient_profile_grants_patient_role(self):
        person = _make_person("pat@example.com", "Pat")
        Patient.objects.create(person=person, sex=Patient.Sex.FEMALE)
        self.assertTrue(has_role(person.user, PATIENT))

    def test_responsible_profile_grants_responsible_role(self):
        person = _make_person("resp@example.com", "Resp")
        Responsible.objects.create(person=person)
        self.assertTrue(has_role(person.user, RESPONSIBLE))

    def test_person_can_hold_patient_and_responsible_roles_simultaneously(self):
        person = _make_person("both@example.com", "Both")
        Patient.objects.create(person=person, sex=Patient.Sex.FEMALE)
        Responsible.objects.create(person=person)

        roles = user_roles(person.user)
        self.assertIn(PATIENT, roles)
        self.assertIn(RESPONSIBLE, roles)

from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Person, User
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor


def _make_doctor(email):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user, first_name="Doc", last_name_paterno="Tor", birth_date=date(1980, 1, 1)
    )
    return Doctor.objects.create(person=person)


class ClinicModelTests(TestCase):
    def test_clinic_defaults_to_active(self):
        clinic = Clinic.objects.create(name="Consultorio Centro")
        self.assertTrue(clinic.is_active)
        self.assertEqual(str(clinic), "Consultorio Centro")

    def test_clinic_can_be_deactivated(self):
        clinic = Clinic.objects.create(name="Consultorio Norte")
        clinic.is_active = False
        clinic.save(update_fields=["is_active"])
        clinic.refresh_from_db()
        self.assertFalse(clinic.is_active)


class DoctorClinicModelTests(TestCase):
    def test_doctor_can_be_assigned_to_a_clinic(self):
        doctor = _make_doctor("doc-clinic@example.com")
        clinic = Clinic.objects.create(name="Consultorio Sur")
        relation = DoctorClinic.objects.create(doctor=doctor, clinic=clinic)
        self.assertTrue(relation.is_active)

    def test_duplicate_doctor_clinic_pair_is_rejected(self):
        doctor = _make_doctor("doc-clinic2@example.com")
        clinic = Clinic.objects.create(name="Consultorio Sur")
        DoctorClinic.objects.create(doctor=doctor, clinic=clinic)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DoctorClinic.objects.create(doctor=doctor, clinic=clinic)

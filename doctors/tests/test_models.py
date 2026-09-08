from datetime import date

from django.test import TestCase

from accounts.models import Person, User
from doctors.models import Doctor


class DoctorModelTests(TestCase):
    def test_doctor_is_tied_to_a_person(self):
        user = User.objects.create_user(email="doc@example.com", password="s3cure-pass!")
        person = Person.objects.create(
            user=user, first_name="Doc", last_name_paterno="Tor", birth_date=date(1980, 1, 1)
        )
        doctor = Doctor.objects.create(person=person)

        self.assertEqual(doctor.person, person)
        self.assertTrue(doctor.is_active)
        self.assertEqual(str(doctor), str(person))

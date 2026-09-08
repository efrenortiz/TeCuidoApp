from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Person, User
from doctors.models import Doctor
from patients.models import DoctorPatientRelationship, Patient


def _make_doctor(email, first_name="Doc"):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Tor", birth_date=date(1980, 1, 1)
    )
    return Doctor.objects.create(person=person)


def _make_patient(email, first_name="Pat", phone=""):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user,
        first_name=first_name,
        last_name_paterno="Test",
        birth_date=date(1990, 1, 1),
        phone=phone,
    )
    return Patient.objects.create(person=person, sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT)


class PatientListViewTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("doc@example.com")
        self.client.login(username="doc@example.com", password="s3cure-pass!")

    def test_non_doctor_is_forbidden(self):
        User.objects.create_user(email="plain@example.com", password="s3cure-pass!")
        self.client.logout()
        self.client.login(username="plain@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("patients:patient_list"))
        self.assertEqual(response.status_code, 403)

    def test_lists_only_active_related_patients(self):
        related = _make_patient("related@example.com", "Maria")
        unrelated = _make_patient("unrelated@example.com", "Ana")
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=related)

        response = self.client.get(reverse("patients:patient_list"))

        self.assertContains(response, "Maria")
        self.assertNotContains(response, "Ana Test")

    def test_empty_state_when_no_patients(self):
        response = self.client.get(reverse("patients:patient_list"))
        self.assertContains(response, "No hay pacientes registrados")

    def test_search_filters_by_name(self):
        maria = _make_patient("maria@example.com", "Maria", phone="5551234567")
        luisa = _make_patient("luisa@example.com", "Luisa", phone="5559876543")
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=maria)
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=luisa)

        response = self.client.get(reverse("patients:patient_list"), {"q": "Maria"})

        self.assertContains(response, "Maria")
        self.assertNotContains(response, "Luisa Test")


class PatientProfileViewTests(TestCase):
    def setUp(self):
        self.patient = _make_patient("me@example.com", "Selfie")
        self.client.login(username="me@example.com", password="s3cure-pass!")

    def test_non_patient_is_forbidden(self):
        User.objects.create_user(email="plain2@example.com", password="s3cure-pass!")
        self.client.logout()
        self.client.login(username="plain2@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("patients:my_profile"))
        self.assertEqual(response.status_code, 403)

    def test_get_prefills_current_data(self):
        response = self.client.get(reverse("patients:my_profile"))
        self.assertContains(response, "Selfie")
        self.assertContains(response, self.patient.person.user.email)

    def test_post_updates_person_and_patient_fields(self):
        response = self.client.post(
            reverse("patients:my_profile"),
            {
                "first_name": "Nuevo Nombre",
                "last_name_paterno": "Test",
                "last_name_materno": "",
                "birth_date": "1990-01-01",
                "phone": "5550001111",
                "alternative_phone": "",
                "street": "",
                "exterior_number": "",
                "neighborhood": "",
                "postal_code": "",
                "municipality": "",
                "state": "",
                "country": "",
                "curp": "",
                "nationality": "",
                "sex": "F",
                "emergency_contact_name": "",
                "emergency_contact_phone": "",
                "blood_type": "",
                "allergies": "Penicilina",
                "chronic_conditions": "",
                "current_medications": "",
                "surgical_history": "",
                "relevant_hospitalizations": "",
            },
        )
        self.assertRedirects(response, reverse("patients:my_profile"))
        self.patient.person.refresh_from_db()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.person.first_name, "Nuevo Nombre")
        self.assertEqual(self.patient.allergies, "Penicilina")

    def test_email_field_is_not_present_and_cannot_be_changed(self):
        response = self.client.get(reverse("patients:my_profile"))
        self.assertNotContains(response, 'name="email"')

        original_email = self.patient.person.user.email
        self.client.post(
            reverse("patients:my_profile"),
            {
                "email": "hijacked@example.com",
                "first_name": "Selfie",
                "last_name_paterno": "Test",
                "last_name_materno": "",
                "birth_date": "1990-01-01",
                "sex": "F",
            },
        )
        self.patient.person.user.refresh_from_db()
        self.assertEqual(self.patient.person.user.email, original_email)

from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Person, User
from patients.models import Patient


def _make_patient(email, first_name="Pat"):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1)
    )
    return Patient.objects.create(person=person, sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT)


class PatientDetailViewObjectPermissionTests(TestCase):
    """DoD §22.8: 'Modificar un identificador en una URL no debe conceder
    acceso a un objeto no autorizado.'"""

    def test_patient_can_view_their_own_detail_url(self):
        patient = _make_patient("owner@example.com")
        self.client.login(username="owner@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("patients:patient_detail", args=[patient.pk]))
        self.assertEqual(response.status_code, 200)

    def test_incrementing_the_id_in_the_url_does_not_grant_access(self):
        patient_a = _make_patient("owner-a@example.com", "A")
        patient_b = _make_patient("owner-b@example.com", "B")
        self.client.login(username="owner-a@example.com", password="s3cure-pass!")

        response = self.client.get(reverse("patients:patient_detail", args=[patient_b.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(patient_a.pk, patient_b.pk)

    def test_anonymous_user_is_redirected_to_login(self):
        patient = _make_patient("owner-c@example.com", "C")
        response = self.client.get(reverse("patients:patient_detail", args=[patient.pk]))
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_id_returns_404(self):
        patient = _make_patient("owner-d@example.com", "D")
        self.client.login(username="owner-d@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("patients:patient_detail", args=[999999]))
        self.assertEqual(response.status_code, 404)

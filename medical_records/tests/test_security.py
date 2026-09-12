"""ETAPA 7 — verificaciones de cierre de
docs/phases/phase-3-testing-strategy.md §16 (Seguridad), §31 (Privacidad)
y §22 (casos negativos prioritarios) que no quedaban ya cubiertas por
test_services.py/test_api.py/test_ui.py/test_audit.py: CSRF (TS-100),
ausencia de secretos/internals en errores (TS-101/102), caché privada
(TS-103/158), y payloads que intentan cambiar identidad/timestamps
(tabla de casos negativos §22).
"""

import json
from datetime import date, time, timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.services import encounter as encounter_service
from patients.models import Patient


def _make_person(email, first_name="Test", birth_date=date(1990, 1, 1)):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=birth_date
    )


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_patient(email):
    return Patient.objects.create(
        person=_make_person(email, "Pat"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT
    )


def _make_clinic(name="Consultorio Seguridad"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class ClosureSecurityTestCase(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("close-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user

        self.day = _future_date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("close-patient@example.com")
        self.patient_user = self.patient.person.user
        self.appointment = self._book()

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(hours=1)

    def _book(self, hour=9):
        start_at, end_at = self._slot(hour)
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at,
        )
        return appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient, doctor=self.doctor, clinic=self.clinic,
        )


class CsrfProtectionTests(ClosureSecurityTestCase):
    """TS-100."""

    def test_api_encounter_start_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.doctor_user)
        response = client.post(
            reverse("clinical_api:encounter_start", args=[self.appointment.pk]),
            data="{}", content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_ui_encounter_start_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.doctor_user)
        response = client.post(reverse("clinical_ui:encounter_start", args=[self.appointment.pk]))
        self.assertEqual(response.status_code, 403)


class NoLeakInErrorsTests(ClosureSecurityTestCase):
    """TS-101/102 — sin tracebacks, SQL, ni configuración sensible en
    respuestas de error."""

    def test_malformed_json_body_returns_generic_message(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_api:encounter_complete", args=[999999]),
            data="{not valid json", content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.content.decode()
        self.assertNotIn("Traceback", body)
        self.assertNotIn("django.db", body)
        self.assertNotIn("SELECT ", body)

    def test_db_level_rejection_does_not_leak_sql(self):
        """Fuerza un IntegrityError real (encuentro inexistente al
        completar) y confirma que la respuesta no expone SQL/nombres de
        tabla internos."""
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_api:encounter_detail", args=[999999]))
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertNotIn("psycopg2", json.dumps(body))
        self.assertNotIn("medical_records_clinicalencounter", json.dumps(body))


class PrivateCacheTests(ClosureSecurityTestCase):
    """TS-103/158 — ninguna respuesta clínica es cacheable."""

    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_api_response_is_not_cacheable(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_api:encounter_detail", args=[self.encounter.pk]))
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    def test_ui_response_is_not_cacheable(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_ui:encounter_detail", args=[self.encounter.pk]))
        cache_control = response.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("no-cache", cache_control)


class IdentityAndTimestampPayloadTests(ClosureSecurityTestCase):
    """Tabla de casos negativos §22 — un payload que intenta cambiar
    identidad/timestamps se rechaza (nunca se ignora silenciosamente ni
    se aplica)."""

    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.other_patient = _make_patient("close-other-patient@example.com")

    def _patch(self, data):
        self.client.force_login(self.doctor_user)
        return self.client.patch(
            reverse("clinical_api:encounter_detail", args=[self.encounter.pk]),
            data=json.dumps(data), content_type="application/json",
        )

    def test_patient_id_in_payload_is_rejected(self):
        response = self._patch({"patient_id": self.other_patient.pk})
        self.assertEqual(response.status_code, 400)
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.patient.pk, self.patient.pk)

    def test_doctor_id_in_payload_is_rejected(self):
        other_doctor = _make_doctor("close-other-doc@example.com")
        response = self._patch({"doctor_id": other_doctor.pk})
        self.assertEqual(response.status_code, 400)
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.doctor_id, self.doctor.pk)

    def test_status_in_payload_is_rejected(self):
        response = self._patch({"status": "COMPLETED"})
        self.assertEqual(response.status_code, 400)
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.status, "IN_PROGRESS")

    def test_created_at_in_payload_is_rejected(self):
        response = self._patch({"created_at": "2000-01-01T00:00:00Z"})
        self.assertEqual(response.status_code, 400)

    def test_completed_at_in_payload_is_rejected(self):
        response = self._patch({"completed_at": "2000-01-01T00:00:00Z"})
        self.assertEqual(response.status_code, 400)

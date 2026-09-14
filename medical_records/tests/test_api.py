"""ETAPA 4 — API (Gate 4): happy path, validación, permisos, IDOR, estados
inválidos, concurrencia (a nivel de shape de respuesta — la corrección
real ya está probada en test_concurrency.py), errores, idempotencia,
shape de respuestas, no fuga de información clínica.
"""

import json
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.models import ClinicalEncounter, MedicalRecord
from medical_records.services import encounter as encounter_service
from patients.models import DoctorPatientRelationship, Patient


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


def _make_clinic(name="Consultorio API Clínica"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


VALID_PAYLOAD = {
    "motivo_consulta": "Dolor abdominal de 3 días de evolución",
    "padecimiento_actual": "Inicia hace 3 días con dolor difuso, sin fiebre",
    "exploracion_fisica": "Abdomen blando, depresible, doloroso a la palpación en FID",
    "evaluacion_diagnostico": "Probable apendicitis, se solicita USG",
    "plan_indicaciones": "Referencia a urgencias para valoración quirúrgica",
}


class ClinicalApiTestCase(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("capi-doc@example.com")
        self.other_doctor = _make_doctor("capi-other-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        DoctorClinic.objects.create(doctor=self.other_doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.other_doctor_user = self.other_doctor.person.user

        self.day = _future_date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )

        self.patient = _make_patient("capi-patient@example.com")
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

    def _post_json(self, url, data=None, **extra):
        return self.client.post(url, data=json.dumps(data or {}), content_type="application/json", **extra)

    def _patch_json(self, url, data, **extra):
        return self.client.patch(url, data=json.dumps(data), content_type="application/json", **extra)

    def _start_url(self, appointment=None):
        return reverse("clinical_api:encounter_start", args=[(appointment or self.appointment).pk])

    def _encounter_url(self, encounter):
        return reverse("clinical_api:encounter_detail", args=[encounter.pk])

    def _complete_url(self, encounter):
        return reverse("clinical_api:encounter_complete", args=[encounter.pk])

    def _medical_record_url(self, patient=None):
        return reverse("clinical_api:medical_record_detail", args=[(patient or self.patient).pk])

    def _history_url(self, patient=None):
        return reverse("clinical_api:patient_encounter_history", args=[(patient or self.patient).pk])


class AuthenticationTests(ClinicalApiTestCase):
    def test_unauthenticated_request_returns_401(self):
        response = self._post_json(self._start_url())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "AUTHENTICATION_REQUIRED")

    def test_inactive_user_is_denied(self):
        """API-015 — Django's `ModelBackend.get_user` resolves an
        inactive user's session back to `AnonymousUser`, so this is
        indistinguishable from an unauthenticated request."""
        self.doctor_user.is_active = False
        self.doctor_user.save()
        self.client.force_login(self.doctor_user)
        response = self._post_json(self._start_url())
        self.assertEqual(response.status_code, 401)


class EncounterStartApiTests(ClinicalApiTestCase):
    def test_happy_path_returns_201(self):
        self.client.force_login(self.doctor_user)
        response = self._post_json(self._start_url())
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["status"], "IN_PROGRESS")
        self.assertEqual(body["appointment_id"], self.appointment.pk)
        self.assertEqual(body["patient_id"], self.patient.pk)
        self.assertEqual(body["doctor_id"], self.doctor.pk)
        self.assertIn("clinical", body)
        self.assertEqual(body["clinical"]["motivo_consulta"], "")
        self.assertIsNone(body["completed_at"])

    def test_idempotent_repeat_returns_200(self):
        self.client.force_login(self.doctor_user)
        first = self._post_json(self._start_url())
        self.assertEqual(first.status_code, 201)
        second = self._post_json(self._start_url())
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["id"], first.json()["id"])
        self.assertEqual(ClinicalEncounter.objects.filter(appointment=self.appointment).count(), 1)

    def test_unassigned_doctor_gets_403(self):
        self.client.force_login(self.other_doctor_user)
        response = self._post_json(self._start_url())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "CLINICAL_ACCESS_DENIED")

    def test_patient_cannot_start(self):
        self.client.force_login(self.patient_user)
        response = self._post_json(self._start_url())
        self.assertEqual(response.status_code, 403)

    def test_unknown_appointment_returns_404(self):
        self.client.force_login(self.doctor_user)
        response = self._post_json(reverse("clinical_api:encounter_start", args=[999999]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "RESOURCE_NOT_FOUND")

    def test_cancelled_appointment_returns_409(self):
        appointment = self._book(hour=10)
        appointment_service.cancel_appointment(actor=self.doctor_user, appointment=appointment, reason="DOCTOR_REQUEST")
        self.client.force_login(self.doctor_user)
        response = self._post_json(self._start_url(appointment))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "APPOINTMENT_STATE_INVALID")


class EncounterDetailApiTests(ClinicalApiTestCase):
    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_assigned_doctor_can_read(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._encounter_url(self.encounter))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.encounter.pk)

    def test_unrelated_doctor_gets_404_not_403(self):
        """IDOR (API-037/API-165) — un actor sin autorización recibe el
        mismo 404 que un recurso inexistente, nunca revela que el
        encuentro existe."""
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(self._encounter_url(self.encounter))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "CLINICAL_RESOURCE_NOT_FOUND")

    def test_nonexistent_encounter_returns_same_404_shape(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_api:encounter_detail", args=[999999]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "CLINICAL_RESOURCE_NOT_FOUND")

    def test_get_does_not_mutate_updated_at(self):
        before = self.encounter.updated_at
        self.client.force_login(self.doctor_user)
        self.client.get(self._encounter_url(self.encounter))
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.updated_at, before)


class EncounterSaveApiTests(ClinicalApiTestCase):
    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_partial_save_happy_path(self):
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._encounter_url(self.encounter), {"motivo_consulta": "Dolor abdominal"})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["clinical"]["motivo_consulta"], "Dolor abdominal")

    def test_save_on_nonexistent_encounter_returns_404_not_500(self):
        """TS-155 — un id inexistente nunca debe producir un 500."""
        self.client.force_login(self.doctor_user)
        response = self._patch_json(
            reverse("clinical_api:encounter_detail", args=[999999]), {"motivo_consulta": "x"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "CLINICAL_RESOURCE_NOT_FOUND")

    def test_decimal_fields_round_trip_as_json_numbers(self):
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._encounter_url(self.encounter), {"peso": "65.5", "talla": 165})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["clinical"]
        self.assertEqual(body["peso"], 65.5)
        self.assertEqual(body["talla"], 165.0)

    def test_non_positive_weight_is_400(self):
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._encounter_url(self.encounter), {"peso": "0"})
        self.assertEqual(response.status_code, 400)

    def test_unknown_field_is_400(self):
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._encounter_url(self.encounter), {"diagnostico_cie10": "K35"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_status_field_is_rejected_as_unknown(self):
        """API-052/API-120 — `status` no se acepta como entrada general."""
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._encounter_url(self.encounter), {"status": "COMPLETED"})
        self.assertEqual(response.status_code, 400)

    def test_placeholder_content_is_422(self):
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._encounter_url(self.encounter), {"motivo_consulta": "N/A"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PLACEHOLDER_CONTENT")
        self.assertEqual(response.json()["error"]["details"]["fields"], ["reason_for_visit"])

    def test_unassigned_doctor_gets_403(self):
        self.client.force_login(self.other_doctor_user)
        response = self._patch_json(self._encounter_url(self.encounter), {"motivo_consulta": "x"})
        self.assertEqual(response.status_code, 403)

    def test_save_after_completion_is_409(self):
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data={
            "reason_for_visit": "a", "present_illness": "b", "physical_exam": "c",
            "assessment": "d", "plan": "e",
        })
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._encounter_url(self.encounter), {"motivo_consulta": "tarde"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "ENCOUNTER_COMPLETED")


class EncounterCompleteApiTests(ClinicalApiTestCase):
    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_happy_path_returns_200_completed(self):
        self.client.force_login(self.doctor_user)
        response = self._post_json(self._complete_url(self.encounter), VALID_PAYLOAD)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["status"], "COMPLETED")
        self.assertIsNotNone(body["completed_at"])
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_complete_on_nonexistent_encounter_returns_404_not_500(self):
        """TS-155 — un id inexistente nunca debe producir un 500."""
        self.client.force_login(self.doctor_user)
        response = self._post_json(
            reverse("clinical_api:encounter_complete", args=[999999]), VALID_PAYLOAD,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "CLINICAL_RESOURCE_NOT_FOUND")

    def test_missing_required_fields_returns_422_with_field_list(self):
        incomplete = {k: v for k, v in VALID_PAYLOAD.items() if k not in ("padecimiento_actual", "plan_indicaciones")}
        self.client.force_login(self.doctor_user)
        response = self._post_json(self._complete_url(self.encounter), incomplete)
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "REQUIRED_CLINICAL_CONTENT")
        self.assertCountEqual(body["error"]["details"]["fields"], ["present_illness", "plan"])

    def test_idempotent_repeat_returns_200(self):
        self.client.force_login(self.doctor_user)
        first = self._post_json(self._complete_url(self.encounter), VALID_PAYLOAD)
        second = self._post_json(self._complete_url(self.encounter), VALID_PAYLOAD)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["completed_at"], second.json()["completed_at"])

    def test_repeat_with_different_content_is_409(self):
        self.client.force_login(self.doctor_user)
        self._post_json(self._complete_url(self.encounter), VALID_PAYLOAD)
        different = dict(VALID_PAYLOAD, plan_indicaciones="Plan modificado tras el cierre")
        response = self._post_json(self._complete_url(self.encounter), different)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "ENCOUNTER_COMPLETED")

    def test_unassigned_doctor_gets_403(self):
        self.client.force_login(self.other_doctor_user)
        response = self._post_json(self._complete_url(self.encounter), VALID_PAYLOAD)
        self.assertEqual(response.status_code, 403)


class MedicalRecordApiTests(ClinicalApiTestCase):
    def test_no_record_yet_returns_404(self):
        """API-070/API-073/D-005 — el GET nunca crea, y ausencia se
        traduce a 404."""
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._medical_record_url())
        self.assertEqual(response.status_code, 404)
        self.assertFalse(MedicalRecord.objects.filter(patient=self.patient).exists())

    def test_happy_path_after_lazy_creation(self):
        """P-009/P-010 — una sola cita atendida no basta para lectura
        longitudinal; se agrega la relación activa explícitamente."""
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._medical_record_url())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["patient_id"], self.patient.pk)
        self.assertEqual(body["family_history"], "")

    def test_unrelated_doctor_denied(self):
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(self._medical_record_url())
        self.assertEqual(response.status_code, 403)

    def test_update_happy_path(self):
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.doctor_user)
        response = self._patch_json(
            self._medical_record_url(), {"family_history": "Madre con diabetes mellitus tipo 2"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["family_history"], "Madre con diabetes mellitus tipo 2")

    def test_update_unknown_field_is_400(self):
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._medical_record_url(), {"id": 999})
        self.assertEqual(response.status_code, 400)

    def test_update_before_lazy_creation_is_404(self):
        """API-095 — el PATCH no crea el expediente silenciosamente."""
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.client.force_login(self.doctor_user)
        response = self._patch_json(self._medical_record_url(), {"family_history": "x"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(MedicalRecord.objects.filter(patient=self.patient).exists())

    def test_unknown_patient_returns_404(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_api:medical_record_detail", args=[999999]))
        self.assertEqual(response.status_code, 404)


class PatientEncounterHistoryApiTests(ClinicalApiTestCase):
    def setUp(self):
        super().setUp()
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.completed = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.completed, data={
            "reason_for_visit": "a", "present_illness": "b", "physical_exam": "c",
            "assessment": "d", "plan": "e",
        })
        self.in_progress = encounter_service.start_encounter(actor=self.doctor_user, appointment=self._book(hour=10))

    def test_doctor_sees_paginated_history(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._history_url())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(len(body["results"]), 2)
        self.assertIn("next", body)
        self.assertIn("previous", body)

    def test_patient_sees_only_completed_in_history(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(self._history_url())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["id"], self.completed.pk)

    def test_unrelated_doctor_denied(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(self._history_url())
        self.assertEqual(response.status_code, 403)

    def test_page_size_is_respected(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._history_url() + "?page_size=1")
        body = response.json()
        self.assertEqual(len(body["results"]), 1)
        self.assertIsNotNone(body["next"])

    def test_invalid_ordering_is_400(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._history_url() + "?ordering=doctor__id")
        self.assertEqual(response.status_code, 400)


class NoClinicalContentLeakTests(ClinicalApiTestCase):
    """"No fuga de información clínica" — un actor no autorizado nunca
    recibe contenido clínico, ni siquiera dentro de un mensaje de error."""

    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter,
            data={"reason_for_visit": "Información clínica sensible del paciente"},
        )

    def test_unauthorized_read_response_never_contains_clinical_text(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(self._encounter_url(self.encounter))
        self.assertNotIn(b"Informaci\xc3\xb3n cl\xc3\xadnica sensible", response.content)

    def test_unauthorized_history_response_never_contains_clinical_text(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(self._history_url())
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"Informaci\xc3\xb3n cl\xc3\xadnica sensible", response.content)

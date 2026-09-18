import json
from datetime import date, time, timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from appointments.services import availability as availability_service
from care_requests.models import CareRequest
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import Patient

_MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R>>endobj\ntrailer<</Root 1 0 R>>"
)


def _make_person(email, first_name="Test"):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1)
    )


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_patient(email):
    return Patient.objects.create(
        person=_make_person(email, "Pat"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT
    )


def _make_clinic(name="Consultorio CareRequest API"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class CareRequestApiTestCase(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("cr-api-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(
            doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=30
        )
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic, date=self.day,
            start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("cr-api-patient@example.com")
        self.patient_user = self.patient.person.user
        self.url = reverse("care_requests_api:care_request_create")

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(minutes=30)

    def _payload(self, hour=9, **overrides):
        start_at, end_at = self._slot(hour=hour)
        payload = {
            "doctor_id": self.doctor.pk,
            "clinic_id": self.clinic.pk,
            "start": start_at.isoformat(),
            "end": end_at.isoformat(),
            "motivo": "Dolor abdominal",
        }
        payload.update(overrides)
        return payload


class CreateCareRequestApiTests(CareRequestApiTestCase):
    def test_requires_authentication(self):
        response = self.client.post(self.url, data=self._payload())
        self.assertEqual(response.status_code, 401)

    def test_patient_creates_care_request(self):
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=self._payload())
        self.assertEqual(response.status_code, 201, response.content)
        body = json.loads(response.content)
        self.assertEqual(body["status"], CareRequest.Status.CONVERTIDA)
        self.assertIsNotNone(body["appointment_id"])
        self.assertEqual(body["clinical_document_ids"], [])
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_missing_motivo_is_400(self):
        self.client.force_login(self.patient_user)
        payload = self._payload()
        del payload["motivo"]
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 400)

    def test_whitespace_only_motivo_is_400(self):
        # `_require_field` (api.py) trata " " como truthy y lo deja pasar
        # a `care_request_service.create()` — la regla de dominio (motivo
        # nunca vacío después de normalizar) debe rechazarla ahí, no en el
        # frontend/form.
        self.client.force_login(self.patient_user)
        payload = self._payload(motivo="   \t  ")
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CareRequest.objects.exists())

    def test_slot_conflict_is_409(self):
        self.client.force_login(self.patient_user)
        self.client.post(self.url, data=self._payload(hour=9))
        other_patient = _make_patient("cr-api-other@example.com")
        self.client.force_login(other_patient.person.user)
        response = self.client.post(self.url, data=self._payload(hour=9))
        self.assertEqual(response.status_code, 409)

    def test_idempotency_replay_returns_201_with_same_body(self):
        self.client.force_login(self.patient_user)
        payload = self._payload()
        first = self.client.post(self.url, data=payload, HTTP_IDEMPOTENCY_KEY="api-key-1")
        second = self.client.post(self.url, data=payload, HTTP_IDEMPOTENCY_KEY="api-key-1")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(json.loads(first.content), json.loads(second.content))
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_double_submit_produces_a_single_business_operation(self):
        """Prompt 02 (2026-09-18) §7: la protección real de doble envío no
        es solo "el botón queda deshabilitado" (eso solo cubre un doble
        clic dentro de la misma pestaña) — es que el cliente ahora genera
        y reenvía la misma `Idempotency-Key` (`crypto.randomUUID()`,
        `static/js/care-request.js::selectSlot`) para dos solicitudes HTTP
        reales del mismo intento (p. ej. doble tap, o dos pestañas antes
        de que la primera responda). Se simulan aquí las DOS peticiones
        HTTP reales con la misma clave con forma de UUID, exactamente como
        las enviaría el navegador."""
        import uuid

        self.client.force_login(self.patient_user)
        payload = self._payload()
        key = str(uuid.uuid4())
        first = self.client.post(self.url, data=payload, HTTP_IDEMPOTENCY_KEY=key)
        second = self.client.post(self.url, data=payload, HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(json.loads(first.content), json.loads(second.content))
        # "Una sola operación de negocio" — no solo una CareRequest, sino
        # también una sola Appointment (nunca dos citas reales por un
        # doble envío).
        self.assertEqual(CareRequest.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_fourth_request_in_an_hour_is_429(self):
        self.client.force_login(self.patient_user)
        for hour in (9, 10, 11):
            response = self.client.post(self.url, data=self._payload(hour=hour))
            self.assertEqual(response.status_code, 201)
        response = self.client.post(self.url, data=self._payload(hour=12))
        self.assertEqual(response.status_code, 429)

    def test_attachment_is_uploaded_and_associated(self):
        self.client.force_login(self.patient_user)
        payload = self._payload()
        payload["attachments"] = SimpleUploadedFile(
            "resultado.pdf", _MINIMAL_PDF, content_type="application/pdf"
        )
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 201, response.content)
        body = json.loads(response.content)
        self.assertEqual(len(body["clinical_document_ids"]), 1)

    def test_start_equal_to_end_is_400(self):
        self.client.force_login(self.patient_user)
        start_at, _ = self._slot()
        payload = self._payload()
        payload["end"] = start_at.isoformat()
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CareRequest.objects.exists())

    def test_start_after_end_is_400(self):
        self.client.force_login(self.patient_user)
        start_at, end_at = self._slot()
        payload = self._payload()
        payload["start"] = end_at.isoformat()
        payload["end"] = start_at.isoformat()
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CareRequest.objects.exists())

    def test_multipart_with_attachment_succeeds(self):
        """`docs/design/care-request-api-contracts.md` §5/§8: el endpoint
        siempre es `multipart/form-data`, con o sin adjuntos — esta prueba
        cubre explícitamente el caso CON adjunto real."""
        self.client.force_login(self.patient_user)
        payload = self._payload()
        payload["attachments"] = SimpleUploadedFile(
            "resultado.pdf", _MINIMAL_PDF, content_type="application/pdf"
        )
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 201, response.content)

    def test_json_content_type_is_rejected_explicitly(self):
        """`care-request-api-contracts.md` §5 (corrección 2026-09-18): el
        endpoint exige `multipart/form-data` explícitamente — un
        `application/json` se rechaza con un mensaje claro sobre el
        Content-Type, no con un `400` engañoso de "campo faltante" (ese
        era el comportamiento anterior a esta ronda: `request.POST` vacío
        producía un error sobre `doctor_id`, sin mencionar la causa real)."""
        self.client.force_login(self.patient_user)
        response = self.client.post(
            self.url, data=json.dumps(self._payload()), content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertIn("multipart/form-data", body["error"]["message"])
        self.assertFalse(CareRequest.objects.exists())

    def test_urlencoded_content_type_is_rejected(self):
        """`application/x-www-form-urlencoded` también puebla
        `request.POST` (Django lo parsea igual que multipart), pero no es
        el formato real que usa el cliente (`FormData`, siempre multipart)
        ni soporta adjuntos — se rechaza explícitamente en vez de
        aceptarse "por accidente"."""
        self.client.force_login(self.patient_user)
        payload = self._payload()
        body = "&".join(f"{k}={v}" for k, v in payload.items())
        response = self.client.post(
            self.url, data=body, content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CareRequest.objects.exists())

    def test_invalid_attachment_type_is_400(self):
        self.client.force_login(self.patient_user)
        payload = self._payload()
        payload["attachments"] = SimpleUploadedFile(
            "archivo.pdf", b"not a real pdf", content_type="application/pdf"
        )
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CareRequest.objects.exists())

    def test_attachment_over_10mb_is_400(self):
        self.client.force_login(self.patient_user)
        oversized = _MINIMAL_PDF + b"0" * (10 * 1024 * 1024 + 1)
        payload = self._payload()
        payload["attachments"] = SimpleUploadedFile(
            "grande.pdf", oversized, content_type="application/pdf"
        )
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CareRequest.objects.exists())

    def test_more_than_5_attachments_is_400(self):
        self.client.force_login(self.patient_user)
        payload = self._payload()
        response = self.client.post(
            self.url,
            data={
                **payload,
                "attachments": [
                    SimpleUploadedFile(f"a{i}.pdf", _MINIMAL_PDF, content_type="application/pdf")
                    for i in range(6)
                ],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CareRequest.objects.exists())

    def test_idempotency_conflict_is_409(self):
        self.client.force_login(self.patient_user)
        self.client.post(self.url, data=self._payload(), HTTP_IDEMPOTENCY_KEY="conflict-key")
        response = self.client.post(
            self.url, data=self._payload(motivo="Otro motivo distinto"),
            HTTP_IDEMPOTENCY_KEY="conflict-key",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_unexpected_exception_returns_generic_500_without_internals(self):
        """§7/§11.1: una excepción no anticipada no debe filtrar `motivo`,
        rutas privadas ni traceback — se simula con `DEBUG=False` (el
        modo real de producción) y un cliente que no vuelve a lanzar la
        excepción en el proceso de test, para observar la respuesta HTTP
        real que vería un cliente externo."""
        leaking_client = Client(raise_request_exception=False)
        leaking_client.force_login(self.patient_user)
        secret_detail = "motivo=Dolor abdominal /private/storage/secret-path"
        with mock.patch(
            "care_requests.api.care_request_service.create",
            side_effect=RuntimeError(secret_detail),
        ):
            with override_settings(DEBUG=False):
                response = leaking_client.post(self.url, data=self._payload())
        self.assertEqual(response.status_code, 500)
        body = response.content.decode(errors="ignore")
        self.assertNotIn(secret_detail, body)
        self.assertNotIn("Dolor abdominal", body)
        self.assertNotIn("/private/storage", body)
        self.assertNotIn("Traceback", body)

    def test_responsible_without_relationship_is_rejected(self):
        # Sin ResponsiblePatientRelationship ACTIVE, CareRequestService
        # rechaza en su propia capa de autorización (`_resolve_patient`)
        # con `CareRequestPermissionDenied` -> 403 (`NOT_AUTHORIZED`) — no
        # se deja caer el caso en el rechazo de disponibilidad/reserva de
        # Agenda (`docs/design/care-request-permissions.md` §4).
        from patients.models import Responsible

        responsible = Responsible.objects.create(person=_make_person("cr-api-resp@example.com", "Resp"))
        self.client.force_login(responsible.person.user)
        payload = self._payload()
        payload["patient_id"] = self.patient.pk
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CareRequest.objects.exists())


class CacheControlTests(CareRequestApiTestCase):
    """`Cache-Control: no-store` en TODA respuesta del endpoint —
    política clínica de no-cache (`care-request-api-contracts.md` §12.1).
    Antes de esta ronda, el header solo se fijaba en la ruta de éxito: las
    tres cláusulas `except` de `CareRequestJsonApiView.dispatch` retornaban
    directamente sin pasar por la línea que lo asigna. Un test por código
    de estado representativo, para no depender de que un test de otra
    categoría "de paso" incluya la aserción."""

    def test_no_store_on_success_201(self):
        self.client.force_login(self.patient_user)
        response = self.client.post(self.url, data=self._payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_no_store_on_400(self):
        self.client.force_login(self.patient_user)
        payload = self._payload()
        del payload["motivo"]
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_no_store_on_401(self):
        response = self.client.post(self.url, data=self._payload())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_no_store_on_403(self):
        from patients.models import Responsible

        responsible = Responsible.objects.create(person=_make_person("cr-cache-resp@example.com", "Resp"))
        self.client.force_login(responsible.person.user)
        payload = self._payload()
        payload["patient_id"] = self.patient.pk
        response = self.client.post(self.url, data=payload)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_no_store_on_409(self):
        self.client.force_login(self.patient_user)
        self.client.post(self.url, data=self._payload(hour=9))
        other_patient = _make_patient("cr-cache-other@example.com")
        self.client.force_login(other_patient.person.user)
        response = self.client.post(self.url, data=self._payload(hour=9))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_no_store_on_429(self):
        self.client.force_login(self.patient_user)
        for hour in (9, 10, 11):
            self.client.post(self.url, data=self._payload(hour=hour))
        response = self.client.post(self.url, data=self._payload(hour=12))
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_no_store_on_500(self):
        leaking_client = Client(raise_request_exception=False)
        leaking_client.force_login(self.patient_user)
        with mock.patch(
            "care_requests.api.care_request_service.create", side_effect=RuntimeError("boom"),
        ):
            with override_settings(DEBUG=False):
                response = leaking_client.post(self.url, data=self._payload())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response["Cache-Control"], "no-store")

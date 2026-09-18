from datetime import date, time, timedelta
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from appointments.services import availability as availability_service
from care_requests.models import CareRequest
from care_requests.services import care_request as care_request_service
from care_requests.services.exceptions import (
    CareRequestConflict,
    CareRequestPermissionDenied,
    CareRequestRateLimitExceeded,
    CareRequestValidationError,
)
from clinical_documents.models import ClinicalDocument
from clinical_documents.services import document as document_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.services.exceptions import DocumentValidationError
from patients.models import Patient, Responsible, ResponsiblePatientRelationship

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


def _make_responsible(email):
    return Responsible.objects.create(person=_make_person(email, "Resp"))


def _make_clinic(name="Consultorio CareRequest"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class CareRequestServiceTestCase(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("cr-svc-doc@example.com")
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
        self.patient = _make_patient("cr-svc-patient@example.com")
        self.patient_user = self.patient.person.user

    def _slot(self, hour=9):
        """Mismo horario que devolvería `get_available_slots()` para ese
        `hour` — se construye con `combine_local` (la misma función que
        Agenda usa internamente) para no depender de en qué tzinfo llegan
        los datetimes leídos de PostgreSQL (ver `test_slot_matches_agenda_
        get_available_slots` para la verificación end-to-end real)."""
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(minutes=30)

    def _create(self, **overrides):
        start_at, end_at = overrides.pop("_slot", None) or self._slot()
        defaults = dict(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Dolor abdominal",
        )
        defaults.update(overrides)
        return care_request_service.create(**defaults)


class HappyPathTests(CareRequestServiceTestCase):
    def test_patient_creates_care_request_for_self(self):
        result = self._create()
        self.assertEqual(result.status, CareRequest.Status.CONVERTIDA)
        care_request = CareRequest.objects.get(pk=result.care_request_id)
        self.assertEqual(care_request.patient_id, self.patient.pk)
        self.assertIsNone(care_request.responsible_id)
        self.assertEqual(care_request.appointment_id, result.appointment_id)
        appointment = Appointment.objects.get(pk=result.appointment_id)
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)
        self.assertEqual(appointment.patient_id, self.patient.pk)
        self.assertEqual(result.clinical_document_ids, [])

    def test_responsible_with_active_relationship_creates_for_patient(self):
        responsible = _make_responsible("cr-svc-resp@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible, patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        start_at, end_at = self._slot()
        result = care_request_service.create(
            actor=responsible.person.user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", patient_id=self.patient.pk,
        )
        care_request = CareRequest.objects.get(pk=result.care_request_id)
        self.assertEqual(care_request.responsible_id, responsible.pk)
        self.assertEqual(care_request.patient_id, self.patient.pk)

    def test_responsible_without_relationship_is_rejected(self):
        """Sin ninguna `ResponsiblePatientRelationship` — CareRequest debe
        rechazar en su propia capa de autorización (`_resolve_patient`),
        no dejar caer el caso en el rechazo posterior de Agenda
        (`docs/design/care-request-permissions.md` §4)."""
        responsible = _make_responsible("cr-svc-resp-no-rel@example.com")
        start_at, end_at = self._slot()
        with self.assertRaises(CareRequestPermissionDenied):
            care_request_service.create(
                actor=responsible.person.user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control", patient_id=self.patient.pk,
            )
        self.assertFalse(CareRequest.objects.exists())

    def test_responsible_with_inactive_relationship_is_rejected(self):
        """Combinación actor/patient/responsible inválida: la relación
        existe pero no está `ACTIVE` (p. ej. fue desactivada) — debe
        rechazarse igual que si no existiera ninguna relación."""
        responsible = _make_responsible("cr-svc-resp-inactive@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible, patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.INACTIVE,
            deactivated_at=dj_timezone.now(), deactivation_reason="Prueba",
        )
        start_at, end_at = self._slot()
        with self.assertRaises(CareRequestPermissionDenied):
            care_request_service.create(
                actor=responsible.person.user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control", patient_id=self.patient.pk,
            )
        self.assertFalse(CareRequest.objects.exists())
        self.assertFalse(Appointment.objects.exists())

    def test_responsible_without_patient_id_is_rejected(self):
        responsible = _make_responsible("cr-svc-resp-no-pid@example.com")
        start_at, end_at = self._slot()
        with self.assertRaises(CareRequestValidationError):
            care_request_service.create(
                actor=responsible.person.user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control",
            )

    def test_patient_with_mismatched_patient_id_is_rejected(self):
        other_patient = _make_patient("cr-svc-other-patient@example.com")
        start_at, end_at = self._slot()
        with self.assertRaises(CareRequestPermissionDenied):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control", patient_id=other_patient.pk,
            )
        self.assertFalse(CareRequest.objects.exists())

    def test_slot_from_get_available_slots_is_accepted_as_is(self):
        """Integración real con Agenda (D2): el `start`/`end` que devuelve
        `get_available_slots()` se usa tal cual, sin transformación."""
        slots = availability_service.get_available_slots(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic, date=self.day,
        )
        free_slot = next(s for s in slots if s["status"] == "AVAILABLE")
        result = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=free_slot["start"], end_at=free_slot["end"], motivo="Control",
        )
        appointment = Appointment.objects.get(pk=result.appointment_id)
        self.assertEqual(appointment.start_at, free_slot["start"])
        self.assertEqual(appointment.end_at, free_slot["end"])

    def test_doctor_cannot_initiate_a_care_request(self):
        start_at, end_at = self._slot()
        with self.assertRaises(CareRequestPermissionDenied):
            care_request_service.create(
                actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control",
            )


class IntervalValidationTests(CareRequestServiceTestCase):
    """`docs/design/care-request-api-contracts.md` §6.1: `start_at >=
    end_at` debe rechazarse como error de entrada controlado ANTES de
    intentar persistir — nunca como `IntegrityError` crudo de la
    `CheckConstraint` (`care_request_start_before_end`), que permanece
    como defensa en profundidad, sin cambios."""

    def test_start_equal_to_end_is_rejected(self):
        start_at, _ = self._slot()
        with self.assertRaises(CareRequestValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=start_at, motivo="Control",
            )
        self.assertFalse(CareRequest.objects.exists())

    def test_start_after_end_is_rejected(self):
        start_at, end_at = self._slot()
        with self.assertRaises(CareRequestValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=end_at, end_at=start_at, motivo="Control",
            )
        self.assertFalse(CareRequest.objects.exists())

class MotivoValidationTests(CareRequestServiceTestCase):
    """`docs/design/care-request-domain.md` invariante 1: `motivo` nunca
    puede estar vacío en una creación válida — regla de dominio, aplicada en
    el servicio independientemente de cualquier validación de frontend."""

    def test_empty_motivo_is_rejected(self):
        start_at, end_at = self._slot()
        with self.assertRaises(CareRequestValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="",
            )
        self.assertFalse(CareRequest.objects.exists())

    def test_whitespace_only_motivo_is_rejected(self):
        start_at, end_at = self._slot()
        for whitespace_value in (" ", "   ", "\t", "\n", " \t\n "):
            with self.assertRaises(CareRequestValidationError):
                care_request_service.create(
                    actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                    start_at=start_at, end_at=end_at, motivo=whitespace_value,
                )
        self.assertFalse(CareRequest.objects.exists())

    def test_valid_motivo_is_normalized_and_accepted(self):
        start_at, end_at = self._slot()
        result = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="  Dolor abdominal  ",
        )
        care_request = CareRequest.objects.get(pk=result.care_request_id)
        self.assertEqual(care_request.motivo, "Dolor abdominal")


class FailureRollbackTests(CareRequestServiceTestCase):
    def test_slot_conflict_persists_nothing(self):
        self._create()
        with self.assertRaises(Exception):
            self._create(_slot=self._slot())
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_invalid_attachment_rolls_back_everything(self):
        start_at, end_at = self._slot()
        with self.assertRaises(DocumentValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control",
                attachments=[(b"not a real pdf", "archivo.pdf")],
            )
        self.assertFalse(CareRequest.objects.exists())
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(ClinicalDocument.objects.exists())

    def test_first_attachment_file_is_deleted_when_second_attachment_fails(self):
        """Compensación de archivos (docs/design/care-request-service-contracts.md
        §12): el primer adjunto SÍ llega a escribirse en disco (pasa su
        propia validación); el segundo falla y dispara el rollback — el
        archivo del primero debe desaparecer físicamente, no solo su fila
        de `ClinicalDocument`."""
        start_at, end_at = self._slot()
        storage_root = Path(settings.CLINICAL_DOCUMENTS_STORAGE_ROOT)
        files_before = set(storage_root.rglob("*")) if storage_root.exists() else set()

        with self.assertRaises(DocumentValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control",
                attachments=[(_MINIMAL_PDF, "valido.pdf"), (b"not a real pdf", "invalido.pdf")],
            )

        self.assertFalse(CareRequest.objects.exists())
        self.assertFalse(ClinicalDocument.objects.exists())
        files_after = set(storage_root.rglob("*")) if storage_root.exists() else set()
        self.assertEqual(files_before, files_after)

    def test_too_many_attachments_rejected_before_any_write(self):
        start_at, end_at = self._slot()
        attachments = [(_MINIMAL_PDF, f"a{i}.pdf") for i in range(6)]
        with self.assertRaises(CareRequestValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control", attachments=attachments,
            )
        self.assertFalse(CareRequest.objects.exists())


class AttachmentTests(CareRequestServiceTestCase):
    def test_attachment_is_associated_to_appointment_not_care_request(self):
        start_at, end_at = self._slot()
        result = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            attachments=[(_MINIMAL_PDF, "estudio.pdf")],
        )
        document = ClinicalDocument.objects.get(pk=result.clinical_document_ids[0])
        self.assertEqual(document.appointment_id, result.appointment_id)
        self.assertEqual(document.origin, ClinicalDocument.Origin.UPLOADED)

    def test_clinical_document_ids_is_persisted_on_conversion(self):
        """Hallazgo B (auditoría 2026-09-18): la identidad de adjuntos se
        fija en `CareRequest.clinical_document_ids` en el momento de la
        conversión, no se recalcula después."""
        start_at, end_at = self._slot()
        result = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            attachments=[(_MINIMAL_PDF, "estudio.pdf")],
        )
        care_request = CareRequest.objects.get(pk=result.care_request_id)
        self.assertEqual(care_request.clinical_document_ids, result.clinical_document_ids)
        self.assertEqual(len(care_request.clinical_document_ids), 1)

    def test_document_added_later_by_another_flow_does_not_contaminate_identity(self):
        """Hallazgo B, casos 6/9 (auditoría 2026-09-18): un `ClinicalDocument`
        agregado DESPUÉS a la misma `Appointment`, por otro flujo (aquí,
        `document_service.upload()` invocado directamente, simulando una
        operación ajena a `CareRequestService`), no debe alterar la
        identidad de adjuntos de la `CareRequest` original."""
        start_at, end_at = self._slot()
        key = "contamination-key"
        original = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            attachments=[(_MINIMAL_PDF, "estudio.pdf")], idempotency_key=key,
        )
        care_request = CareRequest.objects.get(pk=original.care_request_id)
        appointment = Appointment.objects.get(pk=original.appointment_id)

        # "Otro flujo": sube un ClinicalDocument directamente a la misma
        # Appointment, sin pasar por CareRequestService.
        extra_document = document_service.upload(
            actor=self.patient_user, patient=self.patient, content=_MINIMAL_PDF,
            original_filename="ajeno.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
            appointment=appointment,
        )
        self.assertEqual(
            ClinicalDocument.objects.filter(appointment_id=appointment.pk).count(), 2,
        )

        # Caso 6/7: la identidad de la CareRequest original no cambió —
        # replay del mismo actor/key/datos sigue siendo replay, no conflict.
        replay = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            attachments=[(_MINIMAL_PDF, "estudio.pdf")], idempotency_key=key,
        )
        self.assertEqual(replay, original)

        # Caso 8: el resultado del replay conserva EXACTAMENTE los IDs
        # originales — nunca incluye el documento ajeno.
        self.assertEqual(replay.clinical_document_ids, original.clinical_document_ids)
        self.assertNotIn(extra_document.pk, replay.clinical_document_ids)

        # La fila persistida tampoco cambió.
        care_request.refresh_from_db()
        self.assertEqual(care_request.clinical_document_ids, original.clinical_document_ids)
        self.assertNotIn(extra_document.pk, care_request.clinical_document_ids)


class IdempotencyTests(CareRequestServiceTestCase):
    """Identidad lógica de la operación (`docs/design/care-request-
    service-contracts.md` §7/§13): `(created_by, idempotency_key)` +
    paciente/médico/consultorio/intervalo/motivo/padecimiento/descripcion/
    huella de adjuntos. Cualquier divergencia en cualquiera de esos campos
    es `CareRequestConflict`, nunca un replay silencioso."""

    def test_first_request_with_key_succeeds_and_persists_key(self):
        start_at, end_at = self._slot()
        result = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", idempotency_key="first-key",
        )
        self.assertEqual(result.status, CareRequest.Status.CONVERTIDA)
        care_request = CareRequest.objects.get(pk=result.care_request_id)
        self.assertEqual(care_request.idempotency_key, "first-key")

    def test_replay_returns_same_result_without_creating_duplicates(self):
        start_at, end_at = self._slot()
        first = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", idempotency_key="abc-123",
        )
        second = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", idempotency_key="abc-123",
        )
        self.assertEqual(first, second)
        self.assertEqual(CareRequest.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_same_key_different_slot_is_conflict(self):
        start_at, end_at = self._slot()
        care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", idempotency_key="abc-456",
        )
        other_start, other_end = self._slot(hour=10)
        with self.assertRaises(CareRequestConflict):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=other_start, end_at=other_end, motivo="Control",
                idempotency_key="abc-456",
            )
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_same_key_different_motivo_is_conflict(self):
        """Ejemplo del contrato: mismo `key`, `motivo="Dolor abdominal"` vs.
        `motivo="Sangrado"` → conflict, nunca replay."""
        start_at, end_at = self._slot()
        care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Dolor abdominal",
            idempotency_key="motivo-key",
        )
        with self.assertRaises(CareRequestConflict):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Sangrado",
                idempotency_key="motivo-key",
            )
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_same_key_different_padecimiento_is_conflict(self):
        start_at, end_at = self._slot()
        care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", padecimiento="Hipertensión",
            idempotency_key="padecimiento-key",
        )
        with self.assertRaises(CareRequestConflict):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control", padecimiento="Diabetes",
                idempotency_key="padecimiento-key",
            )
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_same_key_different_descripcion_is_conflict(self):
        start_at, end_at = self._slot()
        care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", descripcion="Inicio hace 3 días",
            idempotency_key="descripcion-key",
        )
        with self.assertRaises(CareRequestConflict):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control", descripcion="Inicio hoy",
                idempotency_key="descripcion-key",
            )
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_same_key_same_filename_same_size_different_bytes_is_conflict(self):
        """Caso adversarial obligatorio (auditoría de idempotencia): mismo
        actor, misma Idempotency-Key, mismo paciente/médico/consultorio/
        intervalo/motivo/padecimiento/descripcion, mismo nombre de archivo,
        misma longitud en bytes — pero contenido binario distinto. Nombre
        + tamaño NUNCA son identidad suficiente por sí solos; la regla
        exige comparación byte a byte (`_attachments_are_identical`,
        `care-request-service-contracts.md` §7.1)."""
        start_at, end_at = self._slot()
        original_bytes = _MINIMAL_PDF + b"A" * 32
        tampered_bytes = _MINIMAL_PDF + b"B" * 32
        self.assertEqual(len(original_bytes), len(tampered_bytes))
        self.assertNotEqual(original_bytes, tampered_bytes)

        care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            padecimiento="Hipertensión", descripcion="Inicio hace 3 días",
            attachments=[(original_bytes, "estudio.pdf")], idempotency_key="attach-bytes-key",
        )
        with self.assertRaises(CareRequestConflict):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control",
                padecimiento="Hipertensión", descripcion="Inicio hace 3 días",
                attachments=[(tampered_bytes, "estudio.pdf")], idempotency_key="attach-bytes-key",
            )
        self.assertEqual(CareRequest.objects.count(), 1)
        self.assertEqual(ClinicalDocument.objects.count(), 1)

    def test_same_key_incompatible_attachments_is_conflict(self):
        """Distinto número de adjuntos ya basta para ser incompatible,
        antes de siquiera comparar nombre/tamaño/contenido."""
        start_at, end_at = self._slot()
        care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            attachments=[(_MINIMAL_PDF, "estudio.pdf")], idempotency_key="attach-key",
        )
        with self.assertRaises(CareRequestConflict):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control",
                attachments=[], idempotency_key="attach-key",
            )
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_same_key_different_attachment_size_is_conflict(self):
        """Mismo nombre de archivo, tamaño distinto (mismo número de
        adjuntos) — se detecta por metadatos, sin necesidad de leer el
        contenido binario (`_attachments_are_identical` corta temprano
        cuando el tamaño ya difiere)."""
        start_at, end_at = self._slot()
        care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            attachments=[(_MINIMAL_PDF, "estudio.pdf")], idempotency_key="attach-size-key",
        )
        bigger_pdf = _MINIMAL_PDF + b"0" * 64
        with self.assertRaises(CareRequestConflict):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control",
                attachments=[(bigger_pdf, "estudio.pdf")], idempotency_key="attach-size-key",
            )
        self.assertEqual(CareRequest.objects.count(), 1)

    def test_same_key_same_attachments_is_a_real_replay(self):
        """Mismos adjuntos (nombre + tamaño + contenido byte a byte
        idénticos) → replay real, sin duplicar el `ClinicalDocument`."""
        start_at, end_at = self._slot()
        first = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            attachments=[(_MINIMAL_PDF, "estudio.pdf")], idempotency_key="attach-replay-key",
        )
        second = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
            attachments=[(_MINIMAL_PDF, "estudio.pdf")], idempotency_key="attach-replay-key",
        )
        self.assertEqual(first, second)
        self.assertEqual(ClinicalDocument.objects.count(), 1)

    def test_without_idempotency_key_each_request_is_independent(self):
        """Sin `idempotency_key`, no hay deduplicación alguna — cada
        solicitud, aunque sea idéntica, crea su propia `CareRequest`."""
        start_at, end_at = self._slot(hour=9)
        other_start, other_end = self._slot(hour=10)
        first = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control",
        )
        second = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=other_start, end_at=other_end, motivo="Control",
        )
        self.assertNotEqual(first.care_request_id, second.care_request_id)
        self.assertEqual(CareRequest.objects.count(), 2)

    def test_integrity_error_is_recovered_via_savepoint_requery_and_replay(self):
        """Fuerza el camino de defensa en profundidad (`docs/design/
        care-request-service-contracts.md` §7): simula que el re-check
        autoritativo, bajo el lock del actor, no ve una CareRequest ya
        comprometida con la misma `(created_by, idempotency_key)` — el
        `UniqueConstraint` dispara `IntegrityError` dentro del SAVEPOINT
        propio de `CareRequest.objects.create()`. Se captura sin dejar la
        transacción exterior en rollback-only (se sigue consultando y
        operando con éxito después), se re-consulta —esta vez sin el
        parche— y se resuelve como replay."""
        start_at, end_at = self._slot()
        key = "forced-integrity-error"
        original = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", idempotency_key=key,
        )

        real_filter = CareRequest.objects.filter
        calls = {"n": 0}

        def blind_once_then_real(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return CareRequest.objects.none()
            return real_filter(*args, **kwargs)

        with mock.patch.object(CareRequest.objects, "filter", side_effect=blind_once_then_real):
            replay = care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control", idempotency_key=key,
            )

        self.assertEqual(replay.care_request_id, original.care_request_id)
        self.assertEqual(CareRequest.objects.count(), 1)
        self.assertGreaterEqual(calls["n"], 2)

    def test_failed_attempt_does_not_reserve_the_key(self):
        start_at, end_at = self._slot()
        with self.assertRaises(DocumentValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="Control", idempotency_key="retry-key",
                attachments=[(b"not a real pdf", "archivo.pdf")],
            )
        self.assertFalse(CareRequest.objects.exists())
        # El reintento con la misma clave debe ejecutar la operación completa,
        # no encontrarla "reservada".
        result = care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", idempotency_key="retry-key",
        )
        self.assertEqual(result.status, CareRequest.Status.CONVERTIDA)

    def test_invalid_request_with_existing_key_is_400_not_replay_or_conflict(self):
        """Decisión confirmada (`care-request-service-contracts.md` §3.1,
        auditoría de idempotencia 2026-09-18): la validación de entrada
        (intervalo, `motivo`) se ejecuta SIEMPRE antes del lock/re-check de
        idempotencia, incluso cuando la clave ya tiene una CareRequest
        comprometida. Mismo patrón exacto que el precedente ya existente
        `appointments.services.appointment.reschedule_appointment`
        (`_require_valid_reason(reason)` se llama antes de cualquier
        chequeo de idempotencia). Una solicitud estructuralmente inválida
        nunca llega a compararse contra un registro existente: no es un
        replay (los datos no coinciden con nada válido) ni un conflicto de
        idempotencia (el problema es la solicitud en sí, no una
        reutilización de clave) — es `400`, con el mismo código de
        validación de siempre."""
        start_at, end_at = self._slot()
        care_request_service.create(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at, motivo="Control", idempotency_key="reused-key",
        )
        with self.assertRaises(CareRequestValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at, motivo="   ", idempotency_key="reused-key",
            )
        with self.assertRaises(CareRequestValidationError):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=end_at, end_at=start_at, motivo="Control", idempotency_key="reused-key",
            )
        # La CareRequest original sigue intacta — el rechazo de la
        # solicitud inválida no la afectó ni creó una segunda fila.
        self.assertEqual(CareRequest.objects.count(), 1)


class RateLimitTests(CareRequestServiceTestCase):
    def test_third_request_succeeds_fourth_is_rejected(self):
        for hour in (9, 10, 11):
            self._create(_slot=self._slot(hour=hour))
        with self.assertRaises(CareRequestRateLimitExceeded):
            self._create(_slot=self._slot(hour=12))
        self.assertEqual(CareRequest.objects.count(), 3)

    def test_valid_replay_after_reaching_limit_is_not_rejected(self):
        start_at, end_at = self._slot(hour=9)
        for hour, key in ((9, "k1"), (10, "k2"), (11, "k3")):
            self._create(_slot=self._slot(hour=hour), idempotency_key=key)
        # Reintento exacto de la primera solicitud — debe hacer replay, no
        # contar contra el límite ni ser rechazado por él.
        replay = self._create(_slot=(start_at, end_at), idempotency_key="k1")
        self.assertEqual(CareRequest.objects.count(), 3)
        self.assertEqual(replay.status, CareRequest.Status.CONVERTIDA)

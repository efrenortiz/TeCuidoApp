from django.test import TestCase
from django.utils import timezone as dj_timezone

from clinical_documents.models import ClinicalDocument
from medical_records.services.exceptions import (
    DocumentConflict,
    DocumentImmutableResource,
    DocumentInvalidState,
    DocumentNotFound,
    DocumentPermissionDenied,
    DocumentValidationError,
)
from medical_records.testing import ClinicalEncounterFixture
from prescriptions.models import Prescription
from prescriptions.services import prescription as prescription_service

VALID_ITEM = {
    "medication_name": "Paracetamol", "dose": "500", "dose_unit": "mg",
    "route": "Oral", "frequency": "c/8h", "instructions": "Con alimentos",
}


class IssuePrescriptionTests(ClinicalEncounterFixture, TestCase):
    def test_assigned_doctor_can_issue(self):
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        self.assertEqual(prescription.status, Prescription.Status.ISSUED)
        self.assertEqual(prescription.patient, self.patient)
        self.assertEqual(prescription.doctor, self.doctor)
        self.assertEqual(prescription.items.count(), 1)

    def test_issue_generates_pdf_document_atomically(self):
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        document = ClinicalDocument.objects.get(prescription=prescription)
        self.assertEqual(document.origin, ClinicalDocument.Origin.GENERATED)
        self.assertEqual(document.document_type, ClinicalDocument.DocumentType.PRESCRIPTION)
        self.assertIsNone(document.status)
        self.assertGreater(document.size_bytes, 0)
        self.assertEqual(document.mime_type, "application/pdf")

    def test_unassigned_doctor_cannot_issue(self):
        with self.assertRaises(DocumentPermissionDenied):
            prescription_service.issue(
                actor=self.other_doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
            )
        self.assertFalse(Prescription.objects.exists())

    def test_issue_without_items_rejected(self):
        with self.assertRaises(DocumentValidationError):
            prescription_service.issue(actor=self.doctor_user, clinical_encounter=self.encounter, items=[])

    def test_issue_with_missing_required_field_rejected(self):
        with self.assertRaises(DocumentValidationError):
            prescription_service.issue(
                actor=self.doctor_user, clinical_encounter=self.encounter,
                items=[{"medication_name": "X", "dose": "1", "route": "Oral"}],
            )

    def test_double_issue_with_same_idempotency_key_returns_same_prescription(self):
        first = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM], idempotency_key="k1",
        )
        second = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM], idempotency_key="k1",
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Prescription.objects.count(), 1)

    def test_reused_idempotency_key_for_different_encounter_conflicts(self):
        prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM], idempotency_key="k2",
        )
        appointment2 = self._book(hour=10)
        from medical_records.services import encounter as encounter_service
        encounter2 = encounter_service.start_encounter(actor=self.doctor_user, appointment=appointment2)
        with self.assertRaises(DocumentConflict):
            prescription_service.issue(
                actor=self.doctor_user, clinical_encounter=encounter2, items=[VALID_ITEM], idempotency_key="k2",
            )


class ReadPrescriptionTests(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )

    def test_assigned_doctor_can_read(self):
        fetched = prescription_service.get(actor=self.doctor_user, prescription_id=self.prescription.pk)
        self.assertEqual(fetched.pk, self.prescription.pk)

    def test_patient_can_read_own_prescription(self):
        fetched = prescription_service.get(actor=self.patient_user, prescription_id=self.prescription.pk)
        self.assertEqual(fetched.pk, self.prescription.pk)

    def test_unrelated_doctor_cannot_read(self):
        with self.assertRaises(DocumentNotFound):
            prescription_service.get(actor=self.other_doctor_user, prescription_id=self.prescription.pk)

    def test_unrelated_doctor_cannot_list_for_patient(self):
        with self.assertRaises(DocumentPermissionDenied):
            prescription_service.list_for_patient(actor=self.other_doctor_user, patient=self.patient)

    def test_assigned_doctor_without_active_relationship_cannot_list_full_history(self):
        """P-009/P-010 (Fase 3) preservado por ADR-028: estar asignado al
        encuentro que originó UNA receta concreta (ya cubierto por
        `test_assigned_doctor_can_read`) no equivale a acceso al historial
        documental COMPLETO del paciente — eso exige relación activa."""
        with self.assertRaises(DocumentPermissionDenied):
            prescription_service.list_for_patient(actor=self.doctor_user, patient=self.patient)

    def test_patient_can_list_own_prescriptions(self):
        results = list(prescription_service.list_for_patient(actor=self.patient_user, patient=self.patient))
        self.assertEqual(len(results), 1)

    def test_doctor_with_active_relationship_can_list_full_history(self):
        from patients.models import DoctorPatientRelationship
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        results = list(prescription_service.list_for_patient(actor=self.doctor_user, patient=self.patient))
        self.assertEqual(len(results), 1)


class VersionAndVoidPrescriptionTests(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )

    def test_create_version_supersedes_previous(self):
        new_version = prescription_service.create_version(
            actor=self.doctor_user, prescription_id=self.prescription.pk,
            items=[{**VALID_ITEM, "dose": "1000"}], reason="Ajuste de dosis",
        )
        self.assertEqual(new_version.version_number, 2)
        self.assertEqual(new_version.previous_version_id, self.prescription.pk)
        self.assertTrue(new_version.is_current_version)
        self.prescription.refresh_from_db()
        self.assertFalse(self.prescription.is_current_version)
        # cada versión tiene su propio documento generado
        self.assertEqual(ClinicalDocument.objects.filter(prescription=new_version).count(), 1)
        self.assertEqual(ClinicalDocument.objects.filter(prescription=self.prescription).count(), 1)

    def test_cannot_version_a_superseded_version(self):
        prescription_service.create_version(
            actor=self.doctor_user, prescription_id=self.prescription.pk, items=[VALID_ITEM], reason="v2",
        )
        with self.assertRaises(DocumentImmutableResource):
            prescription_service.create_version(
                actor=self.doctor_user, prescription_id=self.prescription.pk, items=[VALID_ITEM], reason="v3-invalida",
            )

    def test_unauthorized_actor_cannot_version(self):
        with self.assertRaises(DocumentPermissionDenied):
            prescription_service.create_version(
                actor=self.other_doctor_user, prescription_id=self.prescription.pk, items=[VALID_ITEM], reason="x",
            )

    def test_void_requires_reason_trace(self):
        voided = prescription_service.void(actor=self.doctor_user, prescription_id=self.prescription.pk, reason="Error de captura")
        self.assertEqual(voided.status, Prescription.Status.VOIDED)
        self.assertIsNotNone(voided.voided_at)
        self.assertEqual(voided.voided_by, self.doctor)

    def test_repeated_void_with_same_reason_is_idempotent(self):
        prescription_service.void(actor=self.doctor_user, prescription_id=self.prescription.pk, reason="Motivo A")
        result = prescription_service.void(actor=self.doctor_user, prescription_id=self.prescription.pk, reason="Motivo A")
        self.assertEqual(result.void_reason, "Motivo A")

    def test_repeated_void_with_different_reason_is_rejected(self):
        prescription_service.void(actor=self.doctor_user, prescription_id=self.prescription.pk, reason="Motivo A")
        with self.assertRaises(DocumentInvalidState):
            prescription_service.void(actor=self.doctor_user, prescription_id=self.prescription.pk, reason="Motivo B")

    def test_unauthorized_actor_cannot_void(self):
        with self.assertRaises(DocumentPermissionDenied):
            prescription_service.void(actor=self.other_doctor_user, prescription_id=self.prescription.pk, reason="x")

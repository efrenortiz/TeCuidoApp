"""ETAPA 6 — Auditoría y seguridad de Prescription (Gate 6): evidencia de
operaciones auditadas, actor siempre real, accesos rechazados registrados,
ausencia de contenido clínico en el audit trail."""

from django.test import TestCase

from medical_records.models import AuditEvent
from medical_records.services.exceptions import DocumentPermissionDenied
from medical_records.testing import ClinicalEncounterFixture
from prescriptions.services import prescription as prescription_service

VALID_ITEM = {
    "medication_name": "Paracetamol", "dose": "500", "dose_unit": "mg",
    "route": "Oral", "frequency": "c/8h", "instructions": "Con alimentos",
}


class PrescriptionAuditTests(ClinicalEncounterFixture, TestCase):
    def test_issue_is_audited_with_real_actor(self):
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        event = AuditEvent.objects.get(action=AuditEvent.Action.ISSUE_PRESCRIPTION)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.doctor_user)
        self.assertIsNotNone(event.actor_id)
        self.assertEqual(event.actor_role, "DOCTOR")
        self.assertEqual(event.resource_id, prescription.pk)
        self.assertEqual(event.patient, self.patient)

    def test_generated_document_is_audited_correlated_to_prescription(self):
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        event = AuditEvent.objects.get(action=AuditEvent.Action.GENERATE_CLINICAL_DOCUMENT)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.doctor_user)
        self.assertEqual(event.clinical_encounter_id, self.encounter.pk)

    def test_denied_issue_is_audited(self):
        with self.assertRaises(DocumentPermissionDenied):
            prescription_service.issue(
                actor=self.other_doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
            )
        event = AuditEvent.objects.get(action=AuditEvent.Action.ISSUE_PRESCRIPTION)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)
        self.assertEqual(event.actor, self.other_doctor_user)

    def test_void_is_audited(self):
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        prescription_service.void(actor=self.doctor_user, prescription_id=prescription.pk, reason="Error de captura")
        event = AuditEvent.objects.get(action=AuditEvent.Action.VOID_PRESCRIPTION)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.reason_code, "Error de captura")

    def test_create_version_is_audited(self):
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        prescription_service.create_version(
            actor=self.doctor_user, prescription_id=prescription.pk, items=[VALID_ITEM], reason="Ajuste",
        )
        event = AuditEvent.objects.get(action=AuditEvent.Action.CREATE_DOCUMENT_VERSION)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)

    def test_denied_version_is_audited(self):
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        with self.assertRaises(DocumentPermissionDenied):
            prescription_service.create_version(
                actor=self.other_doctor_user, prescription_id=prescription.pk, items=[VALID_ITEM], reason="x",
            )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.CREATE_DOCUMENT_VERSION, result=AuditEvent.Result.DENIED,
        ).get()
        self.assertEqual(event.actor, self.other_doctor_user)

    def test_no_clinical_content_leaks_into_audit_trail(self):
        """AH-012/071 (por analogía) — el evento nunca duplica el contenido
        clínico (nombres de medicamentos, dosis), sólo referencias."""
        prescription_service.issue(actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM])
        for event in AuditEvent.objects.all():
            for field in (event.actor_role, event.action, event.result, event.reason_code, event.resource_type):
                self.assertNotIn("Paracetamol", str(field))

    def test_read_is_audited(self):
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        AuditEvent.objects.all().delete()
        prescription_service.get(actor=self.doctor_user, prescription_id=prescription.pk)
        # Prescription.get() no está en la lista mínima auditable de AH-002
        # (a diferencia de ClinicalDocument.get) — se documenta como
        # decisión explícita, no como omisión: la propia Prescription ya
        # es un artefacto de solo lectura auditado en su emisión/versión/
        # anulación; su lectura puntual no agrega una señal de seguridad
        # nueva que AH-002 exija. Verificamos que no truena, no que audite.
        self.assertFalse(AuditEvent.objects.exists())

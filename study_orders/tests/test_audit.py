"""ETAPA 6 — Auditoría y seguridad de StudyOrder (Gate 6) — mismo esquema
que `prescriptions/tests/test_audit.py`."""

from django.test import TestCase

from medical_records.models import AuditEvent
from medical_records.services.exceptions import DocumentPermissionDenied
from medical_records.testing import ClinicalEncounterFixture
from study_orders.models import StudyOrder
from study_orders.services import study_order as study_order_service

VALID_ITEM = {"study_name": "Biometría hemática"}


class StudyOrderAuditTests(ClinicalEncounterFixture, TestCase):
    def test_issue_is_audited_with_real_actor(self):
        order = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM],
        )
        event = AuditEvent.objects.get(action=AuditEvent.Action.ISSUE_STUDY_ORDER)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.doctor_user)
        self.assertEqual(event.resource_id, order.pk)

    def test_generated_document_is_audited(self):
        study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM],
        )
        event = AuditEvent.objects.get(
            action=AuditEvent.Action.GENERATE_CLINICAL_DOCUMENT,
            resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT,
        )
        self.assertEqual(event.actor, self.doctor_user)

    def test_denied_issue_is_audited(self):
        with self.assertRaises(DocumentPermissionDenied):
            study_order_service.issue(
                actor=self.other_doctor_user, clinical_encounter=self.encounter,
                study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM],
            )
        event = AuditEvent.objects.get(action=AuditEvent.Action.ISSUE_STUDY_ORDER)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)

    def test_void_is_audited(self):
        order = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM],
        )
        study_order_service.void(actor=self.doctor_user, study_order_id=order.pk, reason="Ya no procede")
        event = AuditEvent.objects.get(action=AuditEvent.Action.VOID_STUDY_ORDER)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)

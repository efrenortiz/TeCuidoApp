from django.test import TestCase

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
from study_orders.models import StudyOrder
from study_orders.services import study_order as study_order_service

VALID_ITEM = {"study_name": "Biometría hemática"}


class IssueStudyOrderTests(ClinicalEncounterFixture, TestCase):
    def test_assigned_doctor_can_issue(self):
        order = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM],
        )
        self.assertEqual(order.status, StudyOrder.Status.ISSUED)
        self.assertEqual(order.items.count(), 1)

    def test_issue_generates_pdf_document(self):
        order = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.IMAGING, items=[VALID_ITEM],
        )
        document = ClinicalDocument.objects.get(study_order=order)
        self.assertEqual(document.document_type, ClinicalDocument.DocumentType.STUDY_ORDER)
        self.assertIsNone(document.status)

    def test_invalid_study_type_rejected(self):
        with self.assertRaises(DocumentValidationError):
            study_order_service.issue(
                actor=self.doctor_user, clinical_encounter=self.encounter, study_type="BOGUS", items=[VALID_ITEM],
            )

    def test_unassigned_doctor_cannot_issue(self):
        with self.assertRaises(DocumentPermissionDenied):
            study_order_service.issue(
                actor=self.other_doctor_user, clinical_encounter=self.encounter,
                study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM],
            )

    def test_issue_without_items_rejected(self):
        with self.assertRaises(DocumentValidationError):
            study_order_service.issue(
                actor=self.doctor_user, clinical_encounter=self.encounter,
                study_type=StudyOrder.StudyType.LABORATORY, items=[],
            )

    def test_double_issue_with_same_idempotency_key_returns_same_order(self):
        first = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM], idempotency_key="so-k1",
        )
        second = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM], idempotency_key="so-k1",
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(StudyOrder.objects.count(), 1)

    def test_reused_idempotency_key_for_different_encounter_conflicts(self):
        study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM], idempotency_key="so-k2",
        )
        appointment2 = self._book(hour=11)
        from medical_records.services import encounter as encounter_service
        encounter2 = encounter_service.start_encounter(actor=self.doctor_user, appointment=appointment2)
        with self.assertRaises(DocumentConflict):
            study_order_service.issue(
                actor=self.doctor_user, clinical_encounter=encounter2,
                study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM], idempotency_key="so-k2",
            )


class ReadStudyOrderTests(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.order = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.HISTOPATHOLOGY, items=[VALID_ITEM],
        )

    def test_assigned_doctor_can_read(self):
        fetched = study_order_service.get(actor=self.doctor_user, study_order_id=self.order.pk)
        self.assertEqual(fetched.pk, self.order.pk)

    def test_patient_can_read_own_order(self):
        fetched = study_order_service.get(actor=self.patient_user, study_order_id=self.order.pk)
        self.assertEqual(fetched.pk, self.order.pk)

    def test_unrelated_doctor_cannot_read(self):
        with self.assertRaises(DocumentNotFound):
            study_order_service.get(actor=self.other_doctor_user, study_order_id=self.order.pk)


class VersionAndVoidStudyOrderTests(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.order = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM],
        )

    def test_create_version_supersedes_previous(self):
        new_version = study_order_service.create_version(
            actor=self.doctor_user, study_order_id=self.order.pk,
            items=[{"study_name": "Química sanguínea"}], reason="Estudio adicional",
        )
        self.assertEqual(new_version.version_number, 2)
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_current_version)
        self.assertEqual(ClinicalDocument.objects.filter(study_order=new_version).count(), 1)

    def test_cannot_version_a_superseded_version(self):
        study_order_service.create_version(
            actor=self.doctor_user, study_order_id=self.order.pk, items=[VALID_ITEM], reason="v2",
        )
        with self.assertRaises(DocumentImmutableResource):
            study_order_service.create_version(
                actor=self.doctor_user, study_order_id=self.order.pk, items=[VALID_ITEM], reason="v3-invalida",
            )

    def test_void_requires_reason_trace(self):
        voided = study_order_service.void(actor=self.doctor_user, study_order_id=self.order.pk, reason="Ya no se requiere")
        self.assertEqual(voided.status, StudyOrder.Status.VOIDED)
        self.assertIsNotNone(voided.voided_at)

    def test_repeated_void_with_different_reason_is_rejected(self):
        study_order_service.void(actor=self.doctor_user, study_order_id=self.order.pk, reason="Motivo A")
        with self.assertRaises(DocumentInvalidState):
            study_order_service.void(actor=self.doctor_user, study_order_id=self.order.pk, reason="Motivo B")

    def test_unauthorized_actor_cannot_void(self):
        with self.assertRaises(DocumentPermissionDenied):
            study_order_service.void(actor=self.other_doctor_user, study_order_id=self.order.pk, reason="x")

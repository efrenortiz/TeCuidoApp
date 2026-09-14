from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone as dj_timezone

from medical_records.testing import ClinicalEncounterFixture
from study_orders.models import StudyOrder, StudyOrderItem


class StudyOrderModelTests(ClinicalEncounterFixture, TestCase):
    def _make(self, **overrides):
        defaults = dict(
            patient=self.patient,
            doctor=self.doctor,
            clinical_encounter=self.encounter,
            status=StudyOrder.Status.ISSUED,
            study_type=StudyOrder.StudyType.LABORATORY,
            issued_at=dj_timezone.now(),
        )
        defaults.update(overrides)
        return StudyOrder.objects.create(**defaults)

    def test_create_valid_study_order_with_items(self):
        order = self._make()
        StudyOrderItem.objects.create(study_order=order, position=1, study_name="Biometría hemática")
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.version_number, 1)
        self.assertTrue(order.is_current_version)

    def test_status_choices_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudyOrder.objects.create(
                    patient=self.patient, doctor=self.doctor, clinical_encounter=self.encounter,
                    status="BOGUS", study_type=StudyOrder.StudyType.LABORATORY, issued_at=dj_timezone.now(),
                )

    def test_study_type_choices_constraint_is_enforced_at_django_level(self):
        order = self._make()
        order.study_type = "BOGUS"
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_voided_requires_trace_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudyOrder.objects.create(
                    patient=self.patient, doctor=self.doctor, clinical_encounter=self.encounter,
                    status=StudyOrder.Status.VOIDED, study_type=StudyOrder.StudyType.LABORATORY,
                    issued_at=dj_timezone.now(),
                )

    def test_voided_with_trace_succeeds(self):
        order = self._make(
            status=StudyOrder.Status.VOIDED, voided_at=dj_timezone.now(), voided_by=self.doctor,
            void_reason="Solicitud duplicada",
        )
        self.assertEqual(order.status, StudyOrder.Status.VOIDED)

    def test_idempotency_key_unique_per_doctor(self):
        self._make(idempotency_key="so-key-1")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make(idempotency_key="so-key-1")

    def test_previous_version_self_reference_rejected(self):
        order = self._make()
        order.previous_version_id = order.pk
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_version_chain(self):
        v1 = self._make()
        v1.is_current_version = False
        v1.save()
        v2 = self._make(version_number=2, previous_version=v1)
        self.assertEqual(v2.previous_version, v1)
        self.assertFalse(StudyOrder.objects.get(pk=v1.pk).is_current_version)


class StudyOrderItemModelTests(ClinicalEncounterFixture, TestCase):
    def _order(self):
        return StudyOrder.objects.create(
            patient=self.patient, doctor=self.doctor, clinical_encounter=self.encounter,
            status=StudyOrder.Status.ISSUED, study_type=StudyOrder.StudyType.IMAGING,
            issued_at=dj_timezone.now(),
        )

    def test_position_must_be_positive(self):
        order = self._order()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudyOrderItem.objects.create(study_order=order, position=0, study_name="Radiografía")

    def test_position_unique_per_order(self):
        order = self._order()
        StudyOrderItem.objects.create(study_order=order, position=1, study_name="Radiografía")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudyOrderItem.objects.create(study_order=order, position=1, study_name="Tomografía")

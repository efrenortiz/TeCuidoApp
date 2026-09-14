from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone as dj_timezone

from medical_records.testing import ClinicalEncounterFixture
from prescriptions.models import Prescription, PrescriptionItem


class PrescriptionModelTests(ClinicalEncounterFixture, TestCase):
    def _make(self, **overrides):
        defaults = dict(
            patient=self.patient,
            doctor=self.doctor,
            clinical_encounter=self.encounter,
            status=Prescription.Status.ISSUED,
            issued_at=dj_timezone.now(),
        )
        defaults.update(overrides)
        return Prescription.objects.create(**defaults)

    def test_create_valid_prescription_with_items(self):
        prescription = self._make()
        PrescriptionItem.objects.create(
            prescription=prescription, position=1, medication_name="Paracetamol",
            dose="500", dose_unit="mg", route="Oral", frequency="c/8h", instructions="Con alimentos",
        )
        self.assertEqual(prescription.items.count(), 1)
        self.assertEqual(prescription.version_number, 1)
        self.assertTrue(prescription.is_current_version)

    def test_status_choices_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Prescription.objects.create(
                    patient=self.patient, doctor=self.doctor, clinical_encounter=self.encounter,
                    status="BOGUS", issued_at=dj_timezone.now(),
                )

    def test_voided_requires_trace_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Prescription.objects.create(
                    patient=self.patient, doctor=self.doctor, clinical_encounter=self.encounter,
                    status=Prescription.Status.VOIDED, issued_at=dj_timezone.now(),
                )

    def test_voided_with_trace_succeeds(self):
        prescription = self._make(
            status=Prescription.Status.VOIDED, voided_at=dj_timezone.now(), voided_by=self.doctor,
            void_reason="Error de captura",
        )
        self.assertEqual(prescription.status, Prescription.Status.VOIDED)

    def test_idempotency_key_unique_per_doctor(self):
        self._make(idempotency_key="abc-123")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make(idempotency_key="abc-123")

    def test_idempotency_key_allows_blank_repeats(self):
        self._make()
        self._make()  # no error: blank keys are excluded from the constraint

    def test_different_doctor_can_reuse_idempotency_key(self):
        self._make(idempotency_key="shared-key")
        Prescription.objects.create(
            patient=self.patient, doctor=self.other_doctor, clinical_encounter=self.encounter,
            status=Prescription.Status.ISSUED, issued_at=dj_timezone.now(), idempotency_key="shared-key",
        )

    def test_previous_version_self_reference_rejected(self):
        prescription = self._make()
        prescription.previous_version_id = prescription.pk
        with self.assertRaises(ValidationError):
            prescription.full_clean()

    def test_version_chain(self):
        v1 = self._make()
        v1.is_current_version = False
        v1.save()
        v2 = self._make(version_number=2, previous_version=v1)
        self.assertEqual(v2.previous_version, v1)
        self.assertTrue(v2.is_current_version)
        self.assertFalse(Prescription.objects.get(pk=v1.pk).is_current_version)


class PrescriptionItemModelTests(ClinicalEncounterFixture, TestCase):
    def _prescription(self):
        return Prescription.objects.create(
            patient=self.patient, doctor=self.doctor, clinical_encounter=self.encounter,
            status=Prescription.Status.ISSUED, issued_at=dj_timezone.now(),
        )

    def test_position_must_be_positive(self):
        prescription = self._prescription()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PrescriptionItem.objects.create(
                    prescription=prescription, position=0, medication_name="X",
                    dose="1", route="Oral", frequency="c/8h",
                )

    def test_position_unique_per_prescription(self):
        prescription = self._prescription()
        PrescriptionItem.objects.create(
            prescription=prescription, position=1, medication_name="A", dose="1", route="Oral", frequency="c/8h",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PrescriptionItem.objects.create(
                    prescription=prescription, position=1, medication_name="B", dose="1", route="Oral", frequency="c/8h",
                )

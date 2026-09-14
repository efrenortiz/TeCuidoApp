from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone as dj_timezone

from clinical_documents.models import ClinicalDocument
from medical_records.testing import ClinicalEncounterFixture
from prescriptions.models import Prescription
from study_orders.models import StudyOrder


class ClinicalDocumentModelTests(ClinicalEncounterFixture, TestCase):
    def _prescription(self):
        return Prescription.objects.create(
            patient=self.patient, doctor=self.doctor, clinical_encounter=self.encounter,
            status=Prescription.Status.ISSUED, issued_at=dj_timezone.now(),
        )

    def _upload_kwargs(self, **overrides):
        defaults = dict(
            patient=self.patient,
            document_type=ClinicalDocument.DocumentType.PHOTOGRAPH,
            origin=ClinicalDocument.Origin.UPLOADED,
            status=ClinicalDocument.Status.ACTIVE,
            original_filename="foto.jpg",
            storage_key="clinical-documents/2026/09/11/abc123.jpg",
            mime_type="image/jpeg",
            size_bytes=1024,
            created_by=self.doctor_user,
        )
        defaults.update(overrides)
        return defaults

    def test_standalone_uploaded_document_requires_status(self):
        doc = ClinicalDocument.objects.create(**self._upload_kwargs())
        self.assertEqual(doc.status, ClinicalDocument.Status.ACTIVE)

    def test_standalone_document_without_status_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalDocument.objects.create(**self._upload_kwargs(status=None))

    def test_document_backed_by_prescription_forbids_own_status(self):
        prescription = self._prescription()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalDocument.objects.create(**self._upload_kwargs(
                    prescription=prescription, document_type=ClinicalDocument.DocumentType.PRESCRIPTION,
                    origin=ClinicalDocument.Origin.GENERATED, status=ClinicalDocument.Status.ACTIVE,
                    storage_key="clinical-documents/2026/09/11/rx1.pdf", mime_type="application/pdf",
                ))

    def test_document_backed_by_prescription_with_null_status_succeeds(self):
        prescription = self._prescription()
        doc = ClinicalDocument.objects.create(**self._upload_kwargs(
            prescription=prescription, document_type=ClinicalDocument.DocumentType.PRESCRIPTION,
            origin=ClinicalDocument.Origin.GENERATED, status=None,
            storage_key="clinical-documents/2026/09/11/rx1.pdf", mime_type="application/pdf",
        ))
        self.assertIsNone(doc.status)

    def test_only_one_generated_document_per_prescription(self):
        prescription = self._prescription()
        ClinicalDocument.objects.create(**self._upload_kwargs(
            prescription=prescription, document_type=ClinicalDocument.DocumentType.PRESCRIPTION,
            origin=ClinicalDocument.Origin.GENERATED, status=None,
            storage_key="clinical-documents/2026/09/11/rx1.pdf", mime_type="application/pdf",
        ))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalDocument.objects.create(**self._upload_kwargs(
                    prescription=prescription, document_type=ClinicalDocument.DocumentType.PRESCRIPTION,
                    origin=ClinicalDocument.Origin.GENERATED, status=None,
                    storage_key="clinical-documents/2026/09/11/rx2.pdf", mime_type="application/pdf",
                ))

    def test_size_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalDocument.objects.create(**self._upload_kwargs(size_bytes=0))

    def test_storage_key_unique(self):
        ClinicalDocument.objects.create(**self._upload_kwargs(storage_key="dup-key"))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalDocument.objects.create(**self._upload_kwargs(storage_key="dup-key"))

    def test_voided_requires_trace(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalDocument.objects.create(**self._upload_kwargs(status=ClinicalDocument.Status.VOIDED))

    def test_voided_with_trace_succeeds(self):
        doc = ClinicalDocument.objects.create(**self._upload_kwargs(
            status=ClinicalDocument.Status.VOIDED, voided_at=dj_timezone.now(), void_reason="Archivo equivocado",
        ))
        self.assertEqual(doc.status, ClinicalDocument.Status.VOIDED)

    def test_previous_version_self_reference_rejected(self):
        doc = ClinicalDocument.objects.create(**self._upload_kwargs(version_number=1, is_current_version=True))
        doc.previous_version_id = doc.pk
        with self.assertRaises(ValidationError):
            doc.full_clean()

    def test_version_chain_for_standalone_upload(self):
        v1 = ClinicalDocument.objects.create(**self._upload_kwargs(
            version_number=1, is_current_version=True, storage_key="v1.jpg",
        ))
        v1.is_current_version = False
        v1.save()
        v2 = ClinicalDocument.objects.create(**self._upload_kwargs(
            version_number=2, is_current_version=True, previous_version=v1, storage_key="v2.jpg",
        ))
        self.assertEqual(v2.previous_version, v1)
        self.assertFalse(ClinicalDocument.objects.get(pk=v1.pk).is_current_version)

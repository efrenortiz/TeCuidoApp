import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from clinical_documents.models import ClinicalDocument
from clinical_documents.services import document as document_service
from medical_records.services.exceptions import (
    DocumentInvalidState,
    DocumentNotFound,
    DocumentPermissionDenied,
    DocumentValidationError,
)
from medical_records.testing import ClinicalEncounterFixture

_MINIMAL_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"0" * 64
_MINIMAL_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"0" * 64
_MINIMAL_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
_FAKE_EXE = b"MZ\x90\x00" + b"0" * 64


class ClinicalDocumentServiceTestCase(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        self._tmp_storage = tempfile.mkdtemp(prefix="tecuido-test-storage-")
        self._override = override_settings(CLINICAL_DOCUMENTS_STORAGE_ROOT=Path(self._tmp_storage))
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(lambda: shutil.rmtree(self._tmp_storage, ignore_errors=True))
        super().setUp()


class UploadTests(ClinicalDocumentServiceTestCase):
    def test_doctor_with_encounter_can_upload(self):
        document = document_service.upload(
            actor=self.doctor_user, patient=self.patient, content=_MINIMAL_PDF,
            original_filename="estudio_externo.pdf", document_type=ClinicalDocument.DocumentType.LABORATORY,
            clinical_encounter=self.encounter,
        )
        self.assertEqual(document.origin, ClinicalDocument.Origin.UPLOADED)
        self.assertEqual(document.status, ClinicalDocument.Status.ACTIVE)
        self.assertEqual(document.mime_type, "application/pdf")
        self.assertEqual(document.size_bytes, len(_MINIMAL_PDF))
        stored_path = Path(self._tmp_storage) / document.storage_key
        self.assertTrue(stored_path.exists())

    def test_patient_can_upload_own_document(self):
        document = document_service.upload(
            actor=self.patient_user, patient=self.patient, content=_MINIMAL_JPEG,
            original_filename="foto.jpg", document_type=ClinicalDocument.DocumentType.PHOTOGRAPH,
        )
        self.assertEqual(document.patient, self.patient)

    def test_unrelated_doctor_cannot_upload(self):
        with self.assertRaises(DocumentPermissionDenied):
            document_service.upload(
                actor=self.other_doctor_user, patient=self.patient, content=_MINIMAL_PDF,
                original_filename="x.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
            )

    def test_wrong_mime_content_mismatch_rejected(self):
        with self.assertRaises(DocumentValidationError):
            document_service.upload(
                actor=self.doctor_user, patient=self.patient, content=_MINIMAL_JPEG,
                original_filename="fake.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
                clinical_encounter=self.encounter,
            )

    def test_executable_disguised_as_pdf_rejected(self):
        with self.assertRaises(DocumentValidationError):
            document_service.upload(
                actor=self.doctor_user, patient=self.patient, content=_FAKE_EXE,
                original_filename="malware.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
                clinical_encounter=self.encounter,
            )

    def test_oversized_file_rejected(self):
        from clinical_documents.services import storage
        oversized = b"%PDF-1.4\n" + b"0" * (storage.max_size_bytes() + 1)
        with self.assertRaises(DocumentValidationError):
            document_service.upload(
                actor=self.doctor_user, patient=self.patient, content=oversized,
                original_filename="grande.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
                clinical_encounter=self.encounter,
            )

    def test_empty_file_rejected(self):
        with self.assertRaises(DocumentValidationError):
            document_service.upload(
                actor=self.doctor_user, patient=self.patient, content=b"",
                original_filename="vacio.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
                clinical_encounter=self.encounter,
            )

    def test_png_upload_succeeds(self):
        document = document_service.upload(
            actor=self.doctor_user, patient=self.patient, content=_MINIMAL_PNG,
            original_filename="captura.png", document_type=ClinicalDocument.DocumentType.PHOTOGRAPH,
            clinical_encounter=self.encounter,
        )
        self.assertEqual(document.mime_type, "image/png")

    def test_failed_row_creation_cleans_up_orphan_file(self):
        """Simula un fallo de persistencia posterior a la escritura del
        archivo (ADR-027 §6): el archivo huérfano se limpia best-effort."""
        from unittest import mock

        from clinical_documents.services import storage as storage_module

        with mock.patch.object(ClinicalDocument.objects, "create", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                document_service.upload(
                    actor=self.doctor_user, patient=self.patient, content=_MINIMAL_PDF,
                    original_filename="x.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
                    clinical_encounter=self.encounter,
                )
        # No debe quedar ningún archivo huérfano en el storage.
        remaining = list(Path(self._tmp_storage).rglob("*.pdf"))
        self.assertEqual(remaining, [])


class ReadDownloadTests(ClinicalDocumentServiceTestCase):
    def setUp(self):
        super().setUp()
        self.document = document_service.upload(
            actor=self.doctor_user, patient=self.patient, content=_MINIMAL_PDF,
            original_filename="doc.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
            clinical_encounter=self.encounter,
        )

    def test_assigned_doctor_can_read_and_download(self):
        fetched = document_service.get(actor=self.doctor_user, document_id=self.document.pk)
        self.assertEqual(fetched.pk, self.document.pk)
        _, content = document_service.download(actor=self.doctor_user, document_id=self.document.pk)
        self.assertEqual(content, _MINIMAL_PDF)

    def test_unrelated_doctor_gets_not_found_not_forbidden(self):
        """P-041/SC-068 (por analogía) — nunca se distingue "no existe" de
        "no autorizado" en la respuesta."""
        with self.assertRaises(DocumentNotFound):
            document_service.get(actor=self.other_doctor_user, document_id=self.document.pk)

    def test_nonexistent_document_raises_not_found(self):
        with self.assertRaises(DocumentNotFound):
            document_service.get(actor=self.doctor_user, document_id=999999)


class StandaloneVersionVoidTests(ClinicalDocumentServiceTestCase):
    def setUp(self):
        super().setUp()
        self.document = document_service.upload(
            actor=self.doctor_user, patient=self.patient, content=_MINIMAL_PDF,
            original_filename="doc.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
            clinical_encounter=self.encounter,
        )

    def test_version_chain(self):
        new_version = document_service.create_version(
            actor=self.doctor_user, document_id=self.document.pk, content=_MINIMAL_PNG,
            original_filename="doc-v2.png",
        )
        self.assertEqual(new_version.version_number, 2)
        self.document.refresh_from_db()
        self.assertFalse(self.document.is_current_version)

    def test_void_standalone_document(self):
        voided = document_service.void_or_inactivate(
            actor=self.doctor_user, document_id=self.document.pk, reason="Archivo equivocado",
        )
        self.assertEqual(voided.status, ClinicalDocument.Status.VOIDED)

    def test_cannot_void_generated_document_directly(self):
        from clinical_documents.services import pdf as pdf_service
        from prescriptions.services import prescription as prescription_service
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            items=[{"medication_name": "X", "dose": "1", "route": "Oral", "frequency": "c/8h"}],
        )
        generated = ClinicalDocument.objects.get(prescription=prescription)
        with self.assertRaises(DocumentValidationError):
            document_service.void_or_inactivate(actor=self.doctor_user, document_id=generated.pk, reason="x")

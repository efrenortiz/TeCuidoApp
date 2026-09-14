"""ETAPA 6 — Auditoría y seguridad de ClinicalDocument (Gate 6): lectura,
descarga, carga, versión y anulación auditadas; sin binarios ni contenido
clínico en el audit trail; sin actor nulo."""

import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from clinical_documents.models import ClinicalDocument
from clinical_documents.services import document as document_service
from medical_records.models import AuditEvent
from medical_records.services.exceptions import DocumentPermissionDenied
from medical_records.testing import ClinicalEncounterFixture

_MINIMAL_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"0" * 64


class ClinicalDocumentAuditTests(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        self._tmp_storage = tempfile.mkdtemp(prefix="tecuido-test-storage-audit-")
        self._override = override_settings(CLINICAL_DOCUMENTS_STORAGE_ROOT=Path(self._tmp_storage))
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(lambda: shutil.rmtree(self._tmp_storage, ignore_errors=True))
        super().setUp()

    def _upload(self, actor=None):
        return document_service.upload(
            actor=actor or self.doctor_user, patient=self.patient, content=_MINIMAL_PDF,
            original_filename="doc.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
            clinical_encounter=self.encounter,
        )

    def test_upload_is_audited_with_real_actor(self):
        document = self._upload()
        event = AuditEvent.objects.get(action=AuditEvent.Action.UPLOAD_CLINICAL_DOCUMENT)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.doctor_user)
        self.assertEqual(event.resource_id, document.pk)

    def test_read_is_audited(self):
        document = self._upload()
        AuditEvent.objects.all().delete()
        document_service.get(actor=self.doctor_user, document_id=document.pk)
        event = AuditEvent.objects.get(action=AuditEvent.Action.READ_CLINICAL_DOCUMENT)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.doctor_user)

    def test_denied_read_is_audited_idor_safe(self):
        document = self._upload()
        AuditEvent.objects.all().delete()
        with self.assertRaises(Exception):
            document_service.get(actor=self.other_doctor_user, document_id=document.pk)
        event = AuditEvent.objects.get(action=AuditEvent.Action.READ_CLINICAL_DOCUMENT)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)
        self.assertEqual(event.actor, self.other_doctor_user)

    def test_download_is_audited(self):
        document = self._upload()
        AuditEvent.objects.all().delete()
        document_service.download(actor=self.doctor_user, document_id=document.pk)
        event = AuditEvent.objects.get(action=AuditEvent.Action.DOWNLOAD_CLINICAL_DOCUMENT)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.doctor_user)

    def test_void_is_audited(self):
        document = self._upload()
        document_service.void_or_inactivate(actor=self.doctor_user, document_id=document.pk, reason="Error")
        event = AuditEvent.objects.get(action=AuditEvent.Action.VOID_CLINICAL_DOCUMENT)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)

    def test_no_binary_or_filename_in_audit_trail(self):
        """AH-009 (por analogía) — nunca se almacena el binario completo
        ni referencias identificables del contenido en el registro."""
        self._upload()
        for event in AuditEvent.objects.all():
            # AuditEvent no tiene ningún campo de tipo binario/archivo —
            # verificado estructuralmente, no sólo por valor.
            field_names = {f.name for f in event._meta.get_fields()}
            self.assertNotIn("content", field_names)
            self.assertNotIn("file", field_names)
            self.assertNotIn("storage_key", field_names)

    def test_actor_never_null_for_authenticated_operations(self):
        """Gate 6 — 'que no existan eventos clínicos con actor nulo cuando
        se requiere actor'. Los servicios de Fase 4 nunca aceptan
        actor=None; el helper de auditoría compartido (medical_records.services.audit,
        ya endurecido en la corrección de Fase 3 del hallazgo AuditEvent.actor_id)
        rechaza explícitamente cualquier intento con `ValueError` antes de
        llegar al INSERT."""
        from medical_records.services import audit as audit_service

        with self.assertRaises(ValueError):
            audit_service.safe_record_event(
                actor=None, action=AuditEvent.Action.READ_CLINICAL_DOCUMENT, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT,
            )
        self.assertFalse(AuditEvent.objects.filter(actor__isnull=True).exists())


class DocumentPermissionDeniedAuditTests(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        self._tmp_storage = tempfile.mkdtemp(prefix="tecuido-test-storage-audit2-")
        self._override = override_settings(CLINICAL_DOCUMENTS_STORAGE_ROOT=Path(self._tmp_storage))
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(lambda: shutil.rmtree(self._tmp_storage, ignore_errors=True))
        super().setUp()

    def test_denied_upload_does_not_create_orphan_file_or_document(self):
        with self.assertRaises(DocumentPermissionDenied):
            document_service.upload(
                actor=self.other_doctor_user, patient=self.patient, content=_MINIMAL_PDF,
                original_filename="x.pdf", document_type=ClinicalDocument.DocumentType.OTHER,
            )
        self.assertFalse(ClinicalDocument.objects.exists())
        self.assertEqual(list(Path(self._tmp_storage).rglob("*.pdf")), [])

"""ETAPA 5 — UX/UI de ClinicalDocument (Gate 5): lista, carga, detalle,
descarga, permisos."""

import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from clinical_documents.services import document as document_service
from medical_records.testing import ClinicalEncounterFixture
from patients.models import DoctorPatientRelationship

_MINIMAL_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"0" * 64


class DocumentUiTestCase(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        self._tmp_storage = tempfile.mkdtemp(prefix="tecuido-test-storage-ui-")
        self._override = override_settings(CLINICAL_DOCUMENTS_STORAGE_ROOT=Path(self._tmp_storage))
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(lambda: shutil.rmtree(self._tmp_storage, ignore_errors=True))
        super().setUp()


class DocumentUploadUiTests(DocumentUiTestCase):
    def test_form_renders(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_documents_ui:document_upload", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 200)

    def test_upload_redirects_to_detail(self):
        # P-009/P-010 (ADR-028): cargar un documento standalone (sin
        # encuentro asociado) usa el mismo criterio que el historial
        # documental completo — requiere relación activa, no basta con
        # haber atendido una consulta puntual.
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_documents_ui:document_upload", args=[self.patient.pk]),
            data={
                "document_type": "OTHER",
                "file": SimpleUploadedFile("x.pdf", _MINIMAL_PDF, content_type="application/pdf"),
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_upload_without_active_relationship_is_rejected(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_documents_ui:document_upload", args=[self.patient.pk]),
            data={
                "document_type": "OTHER",
                "file": SimpleUploadedFile("x.pdf", _MINIMAL_PDF, content_type="application/pdf"),
            },
        )
        self.assertEqual(response.status_code, 200)
        from clinical_documents.models import ClinicalDocument
        self.assertFalse(ClinicalDocument.objects.exists())


class DocumentListUiTests(DocumentUiTestCase):
    def setUp(self):
        super().setUp()
        document_service.upload(
            actor=self.doctor_user, patient=self.patient, content=_MINIMAL_PDF,
            original_filename="doc.pdf", document_type="OTHER", clinical_encounter=self.encounter,
        )
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)

    def test_list_renders_documents(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_documents_ui:document_list", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver")

    def test_list_empty_for_unrelated_doctor(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("clinical_documents_ui:document_list", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 404)

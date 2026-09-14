"""ETAPA 4 — API de ClinicalDocument (Gate 4): upload multipart, lectura,
descarga, filtros, permisos, IDOR."""

import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from medical_records.testing import ClinicalEncounterFixture

_MINIMAL_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"0" * 64


class ClinicalDocumentApiTestCase(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        self._tmp_storage = tempfile.mkdtemp(prefix="tecuido-test-storage-api-")
        self._override = override_settings(CLINICAL_DOCUMENTS_STORAGE_ROOT=Path(self._tmp_storage))
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(lambda: shutil.rmtree(self._tmp_storage, ignore_errors=True))
        super().setUp()

    def _upload(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_documents_api:document_list_create"),
            data={
                "patient_id": self.patient.pk,
                "document_type": "LABORATORY",
                "clinical_encounter_id": self.encounter.pk,
                "file": SimpleUploadedFile("estudio.pdf", _MINIMAL_PDF, content_type="application/pdf"),
            },
        )
        self.client.logout()
        return response


class UploadApiTests(ClinicalDocumentApiTestCase):
    def test_requires_authentication(self):
        response = self.client.post(reverse("clinical_documents_api:document_list_create"), data={})
        self.assertEqual(response.status_code, 401)

    def test_happy_path_returns_201(self):
        response = self._upload()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["document_type"], "LABORATORY")
        self.assertEqual(body["origin"], "UPLOADED")
        self.assertNotIn("storage_key", body)

    def test_missing_file_returns_400(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_documents_api:document_list_create"),
            data={"patient_id": self.patient.pk, "document_type": "LABORATORY"},
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthorized_doctor_gets_403(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.post(
            reverse("clinical_documents_api:document_list_create"),
            data={
                "patient_id": self.patient.pk, "document_type": "LABORATORY",
                "file": SimpleUploadedFile("x.pdf", _MINIMAL_PDF, content_type="application/pdf"),
            },
        )
        self.assertEqual(response.status_code, 403)


class ReadDownloadListApiTests(ClinicalDocumentApiTestCase):
    def setUp(self):
        super().setUp()
        self.document_id = self._upload().json()["id"]
        # P-009/P-010 (ADR-028): listar el historial documental COMPLETO
        # del paciente exige relación activa, no sólo estar asignado al
        # encuentro que originó un documento concreto (eso ya lo cubre
        # `test_get_happy_path`, sin relación activa).
        from patients.models import DoctorPatientRelationship
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)

    def test_get_idor_safe(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("clinical_documents_api:document_detail", args=[self.document_id]))
        self.assertEqual(response.status_code, 404)

    def test_get_happy_path(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_documents_api:document_detail", args=[self.document_id]))
        self.assertEqual(response.status_code, 200)

    def test_download_happy_path(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_documents_api:document_download", args=[self.document_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), _MINIMAL_PDF)
        self.assertIn("attachment", response["Content-Disposition"])

    def test_download_unauthorized_returns_404_not_leaking_existence(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("clinical_documents_api:document_download", args=[self.document_id]))
        self.assertEqual(response.status_code, 404)

    def test_list_requires_patient_param(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_documents_api:document_list_create"))
        self.assertEqual(response.status_code, 400)

    def test_list_filters_by_type(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(
            reverse("clinical_documents_api:document_list_create"),
            {"patient": self.patient.pk, "type": "LABORATORY"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        response_other_type = self.client.get(
            reverse("clinical_documents_api:document_list_create"),
            {"patient": self.patient.pk, "type": "PHOTOGRAPH"},
        )
        self.assertEqual(response_other_type.json()["count"], 0)

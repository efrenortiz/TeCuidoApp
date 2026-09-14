"""ETAPA 4 — API de Prescription (Gate 4): happy path, validación, permisos,
IDOR, idempotencia, shape de errores."""

import json

from django.test import TestCase
from django.urls import reverse

from medical_records.testing import ClinicalEncounterFixture
from prescriptions.models import Prescription

VALID_ITEM = {
    "medication_name": "Paracetamol", "dose": "500", "dose_unit": "mg",
    "route": "Oral", "frequency": "c/8h", "instructions": "Con alimentos",
}


class PrescriptionApiTestCase(ClinicalEncounterFixture, TestCase):
    def _post(self, url, data):
        return self.client.post(url, data=json.dumps(data), content_type="application/json")


class CreatePrescriptionApiTests(PrescriptionApiTestCase):
    def test_requires_authentication(self):
        response = self._post(
            reverse("prescriptions_api:prescription_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 401)

    def test_happy_path_returns_201(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("prescriptions_api:prescription_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], Prescription.Status.ISSUED)
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_unauthorized_doctor_gets_403(self):
        self.client.force_login(self.other_doctor_user)
        response = self._post(
            reverse("prescriptions_api:prescription_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "CLINICAL_ACCESS_DENIED")

    def test_missing_items_returns_400(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("prescriptions_api:prescription_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "items": []},
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_encounter_returns_404(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("prescriptions_api:prescription_list_create"),
            {"clinical_encounter_id": 999999, "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 404)

    def test_idempotent_double_submit_returns_200_second_time(self):
        self.client.force_login(self.doctor_user)
        url = reverse("prescriptions_api:prescription_list_create")
        payload = {"clinical_encounter_id": self.encounter.pk, "items": [VALID_ITEM], "idempotency_key": "api-k1"}
        first = self._post(url, payload)
        second = self._post(url, payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["id"], second.json()["id"])


class ReadVersionVoidApiTests(PrescriptionApiTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("prescriptions_api:prescription_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "items": [VALID_ITEM]},
        )
        self.prescription_id = response.json()["id"]
        self.client.logout()

    def test_get_requires_authorization_idor_safe(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("prescriptions_api:prescription_detail", args=[self.prescription_id]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "CLINICAL_RESOURCE_NOT_FOUND")

    def test_get_happy_path(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("prescriptions_api:prescription_detail", args=[self.prescription_id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.prescription_id)

    def test_create_version_happy_path(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("prescriptions_api:prescription_versions", args=[self.prescription_id]),
            {"items": [{**VALID_ITEM, "dose": "1000"}], "reason": "Ajuste"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["version_number"], 2)

    def test_void_requires_reason(self):
        self.client.force_login(self.doctor_user)
        response = self._post(reverse("prescriptions_api:prescription_void", args=[self.prescription_id]), {})
        self.assertEqual(response.status_code, 400)

    def test_void_happy_path(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("prescriptions_api:prescription_void", args=[self.prescription_id]), {"reason": "Error"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], Prescription.Status.VOIDED)

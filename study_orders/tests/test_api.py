"""ETAPA 4 — API de StudyOrder (Gate 4): mismo esquema que
`prescriptions/tests/test_api.py`."""

import json

from django.test import TestCase
from django.urls import reverse

from medical_records.testing import ClinicalEncounterFixture
from study_orders.models import StudyOrder

VALID_ITEM = {"study_name": "Biometría hemática"}


class StudyOrderApiTestCase(ClinicalEncounterFixture, TestCase):
    def _post(self, url, data):
        return self.client.post(url, data=json.dumps(data), content_type="application/json")


class CreateStudyOrderApiTests(StudyOrderApiTestCase):
    def test_requires_authentication(self):
        response = self._post(
            reverse("study_orders_api:study_order_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "study_type": "LABORATORY", "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 401)

    def test_happy_path_returns_201(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("study_orders_api:study_order_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "study_type": "LABORATORY", "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], StudyOrder.Status.ISSUED)
        self.assertEqual(body["study_type"], "LABORATORY")

    def test_unauthorized_doctor_gets_403(self):
        self.client.force_login(self.other_doctor_user)
        response = self._post(
            reverse("study_orders_api:study_order_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "study_type": "LABORATORY", "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_study_type_returns_400(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("study_orders_api:study_order_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "study_type": "BOGUS", "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_encounter_returns_404(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("study_orders_api:study_order_list_create"),
            {"clinical_encounter_id": 999999, "study_type": "LABORATORY", "items": [VALID_ITEM]},
        )
        self.assertEqual(response.status_code, 404)

    def test_idempotent_double_submit_returns_200_second_time(self):
        self.client.force_login(self.doctor_user)
        url = reverse("study_orders_api:study_order_list_create")
        payload = {
            "clinical_encounter_id": self.encounter.pk, "study_type": "LABORATORY", "items": [VALID_ITEM],
            "idempotency_key": "api-so-k1",
        }
        first = self._post(url, payload)
        second = self._post(url, payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["id"], second.json()["id"])


class ReadVersionVoidApiTests(StudyOrderApiTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("study_orders_api:study_order_list_create"),
            {"clinical_encounter_id": self.encounter.pk, "study_type": "IMAGING", "items": [VALID_ITEM]},
        )
        self.order_id = response.json()["id"]
        self.client.logout()

    def test_get_requires_authorization_idor_safe(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("study_orders_api:study_order_detail", args=[self.order_id]))
        self.assertEqual(response.status_code, 404)

    def test_create_version_happy_path(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("study_orders_api:study_order_versions", args=[self.order_id]),
            {"items": [{"study_name": "Radiografía de tórax"}], "reason": "Estudio adicional"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["version_number"], 2)

    def test_void_happy_path(self):
        self.client.force_login(self.doctor_user)
        response = self._post(
            reverse("study_orders_api:study_order_void", args=[self.order_id]), {"reason": "Ya no se requiere"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], StudyOrder.Status.VOIDED)

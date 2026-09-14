"""ETAPA 5 — UX/UI de StudyOrder (Gate 5) — mismo esquema que
`prescriptions/tests/test_ui.py`."""

from django.test import TestCase
from django.urls import reverse

from medical_records.testing import ClinicalEncounterFixture
from study_orders.models import StudyOrder
from study_orders.services import study_order as study_order_service

VALID_ITEM_FORM = {
    "study_type": "LABORATORY", "indications": "", "observations": "",
    "item-1-study_name": "Biometría hemática", "item-1-specific_instructions": "",
}


class StudyOrderCreateUiTests(ClinicalEncounterFixture, TestCase):
    def test_form_renders_for_assigned_doctor(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("study_orders_ui:study_order_create", args=[self.encounter.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitar estudios")

    def test_submit_creates_order_and_redirects_to_detail(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("study_orders_ui:study_order_create", args=[self.encounter.pk]), data=VALID_ITEM_FORM,
        )
        order = StudyOrder.objects.get()
        self.assertRedirects(response, reverse("study_orders_ui:study_order_detail", args=[order.pk]))

    def test_unauthorized_doctor_sees_error_not_created(self):
        self.client.force_login(self.other_doctor_user)
        self.client.post(
            reverse("study_orders_ui:study_order_create", args=[self.encounter.pk]), data=VALID_ITEM_FORM,
        )
        self.assertFalse(StudyOrder.objects.exists())


class StudyOrderDetailUiTests(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.order = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[{"study_name": "X"}],
        )

    def test_unrelated_doctor_gets_404(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("study_orders_ui:study_order_detail", args=[self.order.pk]))
        self.assertEqual(response.status_code, 404)

    def test_void_flow(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("study_orders_ui:study_order_void", args=[self.order.pk]), data={"reason": "Ya no procede"},
        )
        self.assertRedirects(response, reverse("study_orders_ui:study_order_detail", args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, StudyOrder.Status.VOIDED)

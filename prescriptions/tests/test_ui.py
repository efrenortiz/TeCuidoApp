"""ETAPA 5 — UX/UI de Prescription (Gate 5): navegación, creación, emisión,
versionado, anulación, permisos visibles y efectivos — vía test client
(equivalente automatizado de la validación manual)."""

from django.test import TestCase
from django.urls import reverse

from medical_records.testing import ClinicalEncounterFixture
from prescriptions.models import Prescription
from prescriptions.services import prescription as prescription_service

VALID_ITEM_FORM = {
    "item-1-medication_name": "Paracetamol", "item-1-dose": "500", "item-1-dose_unit": "mg",
    "item-1-route": "Oral", "item-1-frequency": "c/8h", "item-1-instructions": "",
    "item-1-presentation": "", "item-1-duration": "",
}


class PrescriptionCreateUiTests(ClinicalEncounterFixture, TestCase):
    def test_form_renders_for_assigned_doctor(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("prescriptions_ui:prescription_create", args=[self.encounter.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nueva receta")

    def test_submit_creates_prescription_and_redirects_to_detail(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("prescriptions_ui:prescription_create", args=[self.encounter.pk]), data=VALID_ITEM_FORM,
        )
        prescription = Prescription.objects.get()
        self.assertRedirects(response, reverse("prescriptions_ui:prescription_detail", args=[prescription.pk]))

    def test_unauthorized_doctor_sees_error_not_created(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.post(
            reverse("prescriptions_ui:prescription_create", args=[self.encounter.pk]), data=VALID_ITEM_FORM,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Prescription.objects.exists())
        messages = list(response.context["messages"])
        self.assertTrue(any("permiso" in str(m).lower() for m in messages))

    def test_requires_login(self):
        response = self.client.get(reverse("prescriptions_ui:prescription_create", args=[self.encounter.pk]))
        self.assertEqual(response.status_code, 302)


class PrescriptionDetailUiTests(ClinicalEncounterFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            items=[{"medication_name": "X", "dose": "1", "route": "Oral", "frequency": "c/8h"}],
        )

    def test_assigned_doctor_sees_actions(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("prescriptions_ui:prescription_detail", args=[self.prescription.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nueva versión")
        self.assertContains(response, "Descargar PDF")

    def test_unrelated_doctor_gets_404_not_leaking_existence(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("prescriptions_ui:prescription_detail", args=[self.prescription.pk]))
        self.assertEqual(response.status_code, 404)

    def test_void_flow(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("prescriptions_ui:prescription_void", args=[self.prescription.pk]), data={"reason": "Error"},
        )
        self.assertRedirects(response, reverse("prescriptions_ui:prescription_detail", args=[self.prescription.pk]))
        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.status, Prescription.Status.VOIDED)

    def test_voided_prescription_detail_hides_mutating_actions(self):
        prescription_service.void(actor=self.doctor_user, prescription_id=self.prescription.pk, reason="x")
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("prescriptions_ui:prescription_detail", args=[self.prescription.pk]))
        self.assertNotContains(response, "Nueva versión")

    def test_version_flow(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("prescriptions_ui:prescription_version", args=[self.prescription.pk]),
            data={"reason": "Ajuste", **VALID_ITEM_FORM},
        )
        new_version = Prescription.objects.get(previous_version=self.prescription)
        self.assertRedirects(response, reverse("prescriptions_ui:prescription_detail", args=[new_version.pk]))

"""UI de creación de CareRequest — vista GET-only (`views.CareRequestCreateView`);
la creación real ocurre vía `POST /api/v1/care-requests/` desde JS, no desde esta vista."""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import Patient, Responsible, ResponsiblePatientRelationship


def _make_person(email, first_name="Test"):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1)
    )


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_patient(email):
    return Patient.objects.create(
        person=_make_person(email, "Pat"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT
    )


def _make_responsible(email):
    return Responsible.objects.create(person=_make_person(email, "Resp"))


class CareRequestCreateUiTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("cr-ui-doc@example.com")
        self.clinic = Clinic.objects.create(name="Consultorio UI", timezone="America/Mexico_City")
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=30)
        self.url = reverse("care_requests_ui:care_request_create")

    def test_patient_sees_self_mode(self):
        patient = _make_patient("cr-ui-patient@example.com")
        self.client.force_login(patient.person.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitar cita")
        self.assertEqual(response.context["patient_mode"], "self")
        self.assertEqual(response.context["fixed_patient"], patient)
        self.assertEqual(response.context["care_request_config"]["patientMode"], "self")
        self.assertEqual(response.context["care_request_config"]["fixedPatientId"], patient.pk)

    def test_responsible_sees_active_dependents_only(self):
        responsible = _make_responsible("cr-ui-resp@example.com")
        active_patient = _make_patient("cr-ui-dep-active@example.com")
        inactive_patient = _make_patient("cr-ui-dep-inactive@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible, patient=active_patient,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible, patient=inactive_patient,
            status=ResponsiblePatientRelationship.Status.INACTIVE,
            deactivated_at=dj_timezone.now(), deactivation_reason="Prueba de UI",
        )
        self.client.force_login(responsible.person.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["patient_mode"], "responsible")
        self.assertEqual(list(response.context["responsible_patients"]), [active_patient])
        self.assertEqual(response.context["care_request_config"]["patientMode"], "responsible")
        self.assertIsNone(response.context["care_request_config"]["fixedPatientId"])

    def test_doctor_gets_404(self):
        self.client.force_login(self.doctor.person.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_administrator_gets_404(self):
        admin_user = User.objects.create_user(email="cr-ui-admin@example.com", password="s3cure-pass!")
        Person.objects.create(
            user=admin_user, first_name="Admin", last_name_paterno="Test", birth_date=date(1990, 1, 1)
        )
        admin_user.is_superuser = True
        admin_user.save(update_fields=["is_superuser"])
        self.client.force_login(admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_config_exposes_slots_and_create_urls(self):
        patient = _make_patient("cr-ui-urls@example.com")
        self.client.force_login(patient.person.user)
        response = self.client.get(self.url)
        config = response.context["care_request_config"]
        self.assertEqual(config["slotsApiUrl"], reverse("appointments_api:availability_slots"))
        self.assertEqual(config["createApiUrl"], reverse("care_requests_api:care_request_create"))

    def test_config_exposes_attachment_limits_from_real_source_constants(self):
        """Prompt 02 (2026-09-18) — hallazgo B: los límites de adjuntos que
        el cliente usa para validar deben venir de las mismas constantes
        que ya usa el servidor (`care_requests.api.MAX_ATTACHMENTS`,
        `clinical_documents.services.storage`), no de números repetidos
        aparte en la vista/JS."""
        from care_requests.api import MAX_ATTACHMENTS
        from clinical_documents.services.storage import ALLOWED_MIME_TO_EXTENSIONS, max_size_bytes

        patient = _make_patient("cr-ui-limits@example.com")
        self.client.force_login(patient.person.user)
        response = self.client.get(self.url)
        config = response.context["care_request_config"]
        self.assertEqual(config["maxAttachments"], MAX_ATTACHMENTS)
        self.assertEqual(config["maxAttachmentSizeBytes"], max_size_bytes())
        expected_extensions = sorted(
            {ext for extensions in ALLOWED_MIME_TO_EXTENSIONS.values() for ext in extensions}
        )
        self.assertEqual(config["allowedAttachmentExtensions"], expected_extensions)

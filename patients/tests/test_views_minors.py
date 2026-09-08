from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Person, User
from doctors.models import Doctor
from patients.models import (
    DoctorPatientRelationship,
    Patient,
    Responsible,
    ResponsiblePatientRelationship,
)


def _make_responsible(email, first_name="Resp", **person_kwargs):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user,
        first_name=first_name,
        last_name_paterno="Test",
        birth_date=date(1985, 1, 1),
        **person_kwargs,
    )
    return Responsible.objects.create(person=person)


def _make_patient(
    first_name,
    curp="",
    birth_date=date(2015, 6, 1),
    last_name_paterno="Minor",
    last_name_materno="",
    regime=Patient.Regime.MINOR,
):
    person = Person.objects.create(
        first_name=first_name,
        last_name_paterno=last_name_paterno,
        last_name_materno=last_name_materno,
        birth_date=birth_date,
    )
    return Patient.objects.create(person=person, sex=Patient.Sex.MALE, curp=curp, regime=regime)


MINOR_STEP1_PAYLOAD = {
    "first_name": "Juan",
    "last_name_paterno": "Perez",
    "last_name_materno": "Lopez",
    "birth_date": "2015-06-01",
    "sex": "M",
    "curp": "",
    "nationality": "Mexicana",
}


class RegisterMinorWizardAccessTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("patients:register_minor_step1"))
        self.assertEqual(response.status_code, 302)

    def test_non_responsible_is_forbidden(self):
        User.objects.create_user(email="plain@example.com", password="s3cure-pass!")
        self.client.login(username="plain@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("patients:register_minor_step1"))
        self.assertEqual(response.status_code, 403)

    def test_step2_get_without_session_data_redirects_to_step1(self):
        _make_responsible("resp@example.com")
        self.client.login(username="resp@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("patients:register_minor_step2"))
        self.assertRedirects(response, reverse("patients:register_minor_step1"))

    def test_step3_get_without_result_redirects_to_step1(self):
        _make_responsible("resp2@example.com")
        self.client.login(username="resp2@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("patients:register_minor_step3"))
        self.assertRedirects(response, reverse("patients:register_minor_step1"))


class RegisterMinorWizardHappyPathTests(TestCase):
    def setUp(self):
        self.responsible = _make_responsible("resp3@example.com")
        self.client.login(username="resp3@example.com", password="s3cure-pass!")

    def test_full_wizard_creates_patient_and_active_relationship(self):
        response = self.client.post(
            reverse("patients:register_minor_step1"), MINOR_STEP1_PAYLOAD
        )
        self.assertRedirects(response, reverse("patients:register_minor_step2"))

        response = self.client.post(
            reverse("patients:register_minor_step2"), {"relationship_type": "PADRE"}
        )
        # fetch_redirect_response=False: step3's GET pops a one-time session
        # value, so we must not let assertRedirects' own verification GET
        # consume it before our explicit GET below inspects the content.
        self.assertRedirects(
            response,
            reverse("patients:register_minor_step3"),
            fetch_redirect_response=False,
        )

        response = self.client.get(reverse("patients:register_minor_step3"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "registrado correctamente")

        patient = Patient.objects.get(person__first_name="Juan")
        relationship = ResponsiblePatientRelationship.objects.get(
            responsible=self.responsible, patient=patient
        )
        self.assertEqual(relationship.status, ResponsiblePatientRelationship.Status.ACTIVE)

    def test_step1_rejects_invalid_data(self):
        payload = dict(MINOR_STEP1_PAYLOAD)
        payload["birth_date"] = ""
        response = self.client.post(reverse("patients:register_minor_step1"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Patient.objects.exists())

    def test_step1_blocks_low_confidence_match_with_generic_message(self):
        # Same name+birthdate as MINOR_STEP1_PAYLOAD, no CURP on either side.
        _make_patient("Juan", last_name_paterno="Perez", last_name_materno="Lopez")
        response = self.client.post(
            reverse("patients:register_minor_step1"), MINOR_STEP1_PAYLOAD
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe un registro relacionado")
        self.assertNotIn(reverse("patients:register_minor_step2"), response.content.decode())

    def test_self_registration_is_rejected_at_step2(self):
        self.responsible.person.first_name = "Juan"
        self.responsible.person.last_name_paterno = "Perez"
        self.responsible.person.last_name_materno = "Lopez"
        self.responsible.person.birth_date = date(2015, 6, 1)
        self.responsible.person.save()

        self.client.post(reverse("patients:register_minor_step1"), MINOR_STEP1_PAYLOAD)
        response = self.client.post(
            reverse("patients:register_minor_step2"), {"relationship_type": "PADRE"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No puedes registrarte a ti mismo")
        self.assertFalse(Patient.objects.exists())


class RegisterMinorWizardCurpMatchTests(TestCase):
    def setUp(self):
        self.responsible = _make_responsible("resp4@example.com")
        self.existing_patient = _make_patient("Juan", curp="PELJ150601HDFRPN01")
        self.client.login(username="resp4@example.com", password="s3cure-pass!")

    def test_curp_match_creates_pending_request(self):
        payload = dict(MINOR_STEP1_PAYLOAD, curp="PELJ150601HDFRPN01")
        self.client.post(reverse("patients:register_minor_step1"), payload)
        response = self.client.post(
            reverse("patients:register_minor_step2"), {"relationship_type": "TUTOR_LEGAL"}
        )
        self.assertRedirects(
            response,
            reverse("patients:register_minor_step3"),
            fetch_redirect_response=False,
        )

        response = self.client.get(reverse("patients:register_minor_step3"))
        self.assertContains(response, "solicitud de acceso")

        relationship = ResponsiblePatientRelationship.objects.get(
            responsible=self.responsible, patient=self.existing_patient
        )
        self.assertEqual(relationship.status, ResponsiblePatientRelationship.Status.PENDING)
        self.assertEqual(Patient.objects.count(), 1)


class ApproveRejectViewTests(TestCase):
    def setUp(self):
        self.approver = _make_responsible("approver@example.com", "Approver")
        self.requester = _make_responsible("requester@example.com", "Requester")
        self.patient = _make_patient("Menor")
        ResponsiblePatientRelationship.objects.create(
            responsible=self.approver,
            patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        self.pending = ResponsiblePatientRelationship.objects.create(
            responsible=self.requester,
            patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
            status=ResponsiblePatientRelationship.Status.PENDING,
        )

    def test_authorized_responsible_can_approve(self):
        self.client.login(username="approver@example.com", password="s3cure-pass!")
        response = self.client.post(
            reverse("patients:approve_relationship_request", args=[self.pending.pk])
        )
        self.assertRedirects(response, reverse("patients:my_dependents"))
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, ResponsiblePatientRelationship.Status.ACTIVE)

    def test_authorized_responsible_can_reject(self):
        self.client.login(username="approver@example.com", password="s3cure-pass!")
        response = self.client.post(
            reverse("patients:reject_relationship_request", args=[self.pending.pk])
        )
        self.assertRedirects(response, reverse("patients:my_dependents"))
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, ResponsiblePatientRelationship.Status.INACTIVE)

    def test_unrelated_responsible_cannot_approve(self):
        _make_responsible("stranger@example.com", "Stranger")
        self.client.login(username="stranger@example.com", password="s3cure-pass!")
        response = self.client.post(
            reverse("patients:approve_relationship_request", args=[self.pending.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, ResponsiblePatientRelationship.Status.PENDING)

    def test_my_dependents_shows_pending_request_for_approver(self):
        self.client.login(username="approver@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("patients:my_dependents"))
        self.assertContains(response, "Requester Test")
        self.assertContains(response, "Solicitud pendiente")

    def test_reject_records_deactivation_reason(self):
        self.client.login(username="approver@example.com", password="s3cure-pass!")
        self.client.post(reverse("patients:reject_relationship_request", args=[self.pending.pk]))
        self.pending.refresh_from_db()
        self.assertIsNotNone(self.pending.deactivated_at)
        self.assertEqual(
            self.pending.deactivation_reason,
            ResponsiblePatientRelationship.DeactivationReason.REQUEST_REJECTED,
        )


def _make_doctor(email, first_name="Doc"):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Tor", birth_date=date(1980, 1, 1)
    )
    return Doctor.objects.create(person=person)


class TransitionToAdultViewTests(TestCase):
    """docs/design/screens.md §6.5, ADR-007 §3.8 addendum."""

    def setUp(self):
        self.doctor = _make_doctor("transition-doc@example.com")
        # Chronologically adult (born 1990) but still in MINOR regime — the
        # only state from which the action should be reachable.
        self.patient = _make_patient(
            "Adulto", birth_date=date(1990, 1, 1), regime=Patient.Regime.MINOR
        )
        self.responsible = _make_responsible("transition-resp@example.com")
        self.relationship = ResponsiblePatientRelationship.objects.create(
            responsible=self.responsible,
            patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )

    def _login_doctor(self):
        self.client.login(username="transition-doc@example.com", password="s3cure-pass!")

    def test_doctor_with_active_relationship_transitions_patient(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient)
        self._login_doctor()

        response = self.client.post(
            reverse("patients:transition_to_adult", args=[self.patient.pk])
        )

        self.assertRedirects(response, reverse("patients:patient_detail", args=[self.patient.pk]))
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.regime, Patient.Regime.ADULT)
        self.assertIsNotNone(self.patient.regime_changed_at)
        self.assertEqual(self.patient.regime_changed_by, self.doctor)

        self.relationship.refresh_from_db()
        self.assertEqual(self.relationship.status, ResponsiblePatientRelationship.Status.INACTIVE)
        self.assertEqual(
            self.relationship.deactivation_reason,
            ResponsiblePatientRelationship.DeactivationReason.ADULT_TRANSITION,
        )

    def test_doctor_without_relationship_gets_404(self):
        self._login_doctor()
        response = self.client.post(
            reverse("patients:transition_to_adult", args=[self.patient.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.regime, Patient.Regime.MINOR)

    def test_non_doctor_role_is_forbidden(self):
        self.client.login(username="transition-resp@example.com", password="s3cure-pass!")
        response = self.client.post(
            reverse("patients:transition_to_adult", args=[self.patient.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.post(
            reverse("patients:transition_to_adult", args=[self.patient.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_still_minor_chronologically_is_rejected(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient)
        self.patient.person.birth_date = date(2015, 6, 1)
        self.patient.person.save(update_fields=["birth_date"])
        self._login_doctor()

        response = self.client.post(
            reverse("patients:transition_to_adult", args=[self.patient.pk])
        )

        self.assertRedirects(response, reverse("patients:patient_detail", args=[self.patient.pk]))
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.regime, Patient.Regime.MINOR)

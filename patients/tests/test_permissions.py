from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from accounts.models import Person, User
from doctors.models import Doctor
from patients.models import (
    DoctorPatientRelationship,
    Patient,
    Responsible,
    ResponsiblePatientRelationship,
)
from patients.services.permissions import can_edit_patient, can_view_patient


def _make_person(email, first_name):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1)
    )


def _make_patient(email, first_name="Pat"):
    return Patient.objects.create(person=_make_person(email, first_name), sex=Patient.Sex.FEMALE)


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_responsible(email):
    return Responsible.objects.create(person=_make_person(email, "Resp"))


class PatientSelfAccessTests(TestCase):
    def test_patient_can_view_own_profile(self):
        patient = _make_patient("self@example.com")
        self.assertTrue(can_view_patient(patient.person.user, patient))

    def test_patient_a_cannot_view_patient_b(self):
        patient_a = _make_patient("a@example.com", "A")
        patient_b = _make_patient("b@example.com", "B")
        self.assertFalse(can_view_patient(patient_a.person.user, patient_b))


class DoctorAccessTests(TestCase):
    def test_doctor_with_active_relationship_can_view_patient(self):
        doctor = _make_doctor("doc@example.com")
        patient = _make_patient("dp@example.com")
        DoctorPatientRelationship.objects.create(doctor=doctor, patient=patient)
        self.assertTrue(can_view_patient(doctor.person.user, patient))

    def test_unrelated_doctor_cannot_view_patient(self):
        doctor = _make_doctor("doc2@example.com")
        patient = _make_patient("dp2@example.com")
        self.assertFalse(can_view_patient(doctor.person.user, patient))

    def test_doctor_with_inactive_relationship_cannot_view_patient(self):
        doctor = _make_doctor("doc3@example.com")
        patient = _make_patient("dp3@example.com")
        DoctorPatientRelationship.objects.create(doctor=doctor, patient=patient, is_active=False)
        self.assertFalse(can_view_patient(doctor.person.user, patient))

    def test_deactivated_doctor_loses_access_despite_active_relationship(self):
        doctor = _make_doctor("doc4@example.com")
        patient = _make_patient("dp4@example.com")
        DoctorPatientRelationship.objects.create(doctor=doctor, patient=patient, is_active=True)
        doctor.is_active = False
        doctor.save(update_fields=["is_active"])
        self.assertFalse(can_view_patient(doctor.person.user, patient))


class ResponsibleAccessTests(TestCase):
    def test_responsible_with_active_relationship_can_view_patient(self):
        responsible = _make_responsible("resp@example.com")
        patient = _make_patient("rp@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
        )
        self.assertTrue(can_view_patient(responsible.person.user, patient))

    def test_responsible_cannot_view_unauthorized_patient(self):
        responsible = _make_responsible("resp2@example.com")
        other_patient = _make_patient("rp2@example.com")
        self.assertFalse(can_view_patient(responsible.person.user, other_patient))

    def test_responsible_with_inactive_relationship_cannot_view_patient(self):
        responsible = _make_responsible("resp3@example.com")
        patient = _make_patient("rp3@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.INACTIVE,
        )
        self.assertFalse(can_view_patient(responsible.person.user, patient))

    def test_responsible_with_pending_relationship_cannot_view_patient(self):
        # ADR-007 §3.7: a match by CURP never grants access by itself — the
        # relationship starts PENDING and must be approved first.
        responsible = _make_responsible("resp5@example.com")
        patient = _make_patient("rp5@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.PENDING,
        )
        self.assertFalse(can_view_patient(responsible.person.user, patient))

    def test_deactivated_responsible_loses_access_despite_active_relationship(self):
        responsible = _make_responsible("resp4@example.com")
        patient = _make_patient("rp4@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        responsible.is_active = False
        responsible.save(update_fields=["is_active"])
        self.assertFalse(can_view_patient(responsible.person.user, patient))


class AdminAndAnonymousAccessTests(TestCase):
    def test_superuser_can_view_any_patient(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="s3cure-pass!")
        patient = _make_patient("anyp@example.com")
        self.assertTrue(can_view_patient(admin, patient))

    def test_anonymous_user_cannot_view_patient(self):
        patient = _make_patient("anon@example.com")
        self.assertFalse(can_view_patient(AnonymousUser(), patient))

    def test_authenticated_user_without_any_profile_cannot_view_patient(self):
        bystander = User.objects.create_user(email="bystander@example.com", password="s3cure-pass!")
        patient = _make_patient("bp@example.com")
        self.assertFalse(can_view_patient(bystander, patient))


class EditPermissionTests(TestCase):
    def test_can_edit_patient_mirrors_can_view_patient(self):
        patient = _make_patient("edit@example.com")
        self.assertTrue(can_edit_patient(patient.person.user, patient))

        other_patient = _make_patient("edit2@example.com", "Other")
        self.assertFalse(can_edit_patient(other_patient.person.user, patient))

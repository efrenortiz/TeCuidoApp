from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Person, User
from doctors.models import Doctor
from patients.models import (
    DoctorPatientRelationship,
    Patient,
    Responsible,
    ResponsiblePatientRelationship,
)


def _make_person(email, first_name):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1)
    )


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_patient(email, first_name="Pat"):
    return Patient.objects.create(person=_make_person(email, first_name), sex=Patient.Sex.FEMALE)


def _make_responsible(email, first_name="Resp"):
    return Responsible.objects.create(person=_make_person(email, first_name))


class PatientModelTests(TestCase):
    def test_patient_creation_defaults(self):
        patient = _make_patient("p1@example.com")
        self.assertTrue(patient.is_active)

    def test_patient_fields_can_be_updated(self):
        patient = _make_patient("p2@example.com")
        patient.allergies = "Penicilina"
        patient.save(update_fields=["allergies"])
        patient.refresh_from_db()
        self.assertEqual(patient.allergies, "Penicilina")

    def test_patient_can_relate_to_a_doctor(self):
        patient = _make_patient("p3@example.com")
        doctor = _make_doctor("doc1@example.com")
        relation = DoctorPatientRelationship.objects.create(doctor=doctor, patient=patient)
        self.assertTrue(relation.is_active)
        self.assertEqual(
            DoctorPatientRelationship.RelationType.TRATANTE, relation.relationship_type
        )


class ResponsibleModelTests(TestCase):
    def test_responsible_can_manage_multiple_patients(self):
        responsible = _make_responsible("resp1@example.com")
        patient_a = _make_patient("pa@example.com", "A")
        patient_b = _make_patient("pb@example.com", "B")

        ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=patient_a,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
        )
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=patient_b,
            relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
        )

        self.assertEqual(responsible.patient_relationships.count(), 2)

    def test_relationship_can_be_deactivated_without_deleting_it(self):
        responsible = _make_responsible("resp2@example.com")
        patient = _make_patient("pc@example.com", "C")
        relation = ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
        )

        relation.status = ResponsiblePatientRelationship.Status.INACTIVE
        relation.save(update_fields=["status"])

        self.assertTrue(
            ResponsiblePatientRelationship.objects.filter(
                pk=relation.pk, status=ResponsiblePatientRelationship.Status.INACTIVE
            ).exists()
        )


class RelationshipUniquenessTests(TestCase):
    def test_doctor_patient_pair_is_unique(self):
        doctor = _make_doctor("doc-unique@example.com")
        patient = _make_patient("p-unique@example.com")
        DoctorPatientRelationship.objects.create(doctor=doctor, patient=patient)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DoctorPatientRelationship.objects.create(doctor=doctor, patient=patient)

    def test_responsible_patient_pair_is_unique(self):
        responsible = _make_responsible("resp-unique@example.com")
        patient = _make_patient("p-unique2@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ResponsiblePatientRelationship.objects.create(
                    responsible=responsible,
                    patient=patient,
                    relationship_type=ResponsiblePatientRelationship.RelationType.OTRO,
                )

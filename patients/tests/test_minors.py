from datetime import date

from django.test import TestCase

from accounts.models import Person, User
from patients.models import DoctorPatientRelationship, Patient, Responsible, ResponsiblePatientRelationship
from patients.services import minors


def _make_person(email, first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1), **extra):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user,
        first_name=first_name,
        last_name_paterno=last_name_paterno,
        birth_date=birth_date,
        **extra,
    )


def _make_responsible(email, first_name="Resp"):
    return Responsible.objects.create(person=_make_person(email, first_name))


MINOR_PERSON_DATA = dict(
    first_name="Juan",
    last_name_paterno="Perez",
    last_name_materno="Lopez",
    birth_date=date(2015, 6, 1),
)
MINOR_PATIENT_DATA = dict(sex=Patient.Sex.MALE)


class RegisterNewMinorTests(TestCase):
    def test_creates_patient_and_active_relationship(self):
        responsible = _make_responsible("resp1@example.com")

        patient, relationship, outcome = minors.register_minor_patient(
            responsible=responsible,
            person_data=dict(MINOR_PERSON_DATA),
            patient_data=dict(MINOR_PATIENT_DATA),
            relationship_type=ResponsiblePatientRelationship.RelationType.PADRE,
        )

        self.assertEqual(outcome, "created")
        self.assertEqual(patient.person.first_name, "Juan")
        self.assertIsNone(patient.person.user)
        self.assertEqual(relationship.status, ResponsiblePatientRelationship.Status.ACTIVE)
        self.assertEqual(relationship.responsible, responsible)

    def test_does_not_create_doctor_patient_relationship(self):
        responsible = _make_responsible("resp2@example.com")

        patient, _relationship, _outcome = minors.register_minor_patient(
            responsible=responsible,
            person_data=dict(MINOR_PERSON_DATA, first_name="Ana"),
            patient_data=dict(MINOR_PATIENT_DATA, sex=Patient.Sex.FEMALE),
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
        )

        self.assertFalse(DoctorPatientRelationship.objects.filter(patient=patient).exists())


class SelfRegistrationTests(TestCase):
    def test_responsible_cannot_register_themselves_as_the_minor(self):
        responsible = _make_responsible("resp3@example.com", "Juan")
        responsible.person.last_name_paterno = "Perez"
        responsible.person.last_name_materno = "Lopez"
        responsible.person.birth_date = date(2015, 6, 1)
        responsible.person.save()

        with self.assertRaises(minors.ResponsibleSelfRegistrationNotAllowed):
            minors.register_minor_patient(
                responsible=responsible,
                person_data=dict(MINOR_PERSON_DATA),
                patient_data=dict(MINOR_PATIENT_DATA),
                relationship_type=ResponsiblePatientRelationship.RelationType.PADRE,
            )
        self.assertFalse(Patient.objects.exists())


class ExistingPatientMatchTests(TestCase):
    def setUp(self):
        self.responsible = _make_responsible("resp4@example.com")
        # The existing minor has no User of their own — a Person can exist
        # without one (ADR-002), which is exactly the normal case here.
        self.existing_person = Person.objects.create(
            first_name="Juan",
            last_name_paterno="Perez",
            last_name_materno="Lopez",
            birth_date=date(2015, 6, 1),
        )
        self.existing_patient = Patient.objects.create(
            person=self.existing_person, sex=Patient.Sex.MALE, curp="PELJ150601HDFRPN01"
        )

    def test_curp_match_creates_pending_relationship_not_a_duplicate_patient(self):
        patient, relationship, outcome = minors.register_minor_patient(
            responsible=self.responsible,
            person_data=dict(MINOR_PERSON_DATA, first_name="Otro Nombre"),
            patient_data=dict(MINOR_PATIENT_DATA, curp="PELJ150601HDFRPN01"),
            relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
        )

        self.assertEqual(outcome, "pending")
        self.assertEqual(patient.pk, self.existing_patient.pk)
        self.assertEqual(relationship.status, ResponsiblePatientRelationship.Status.PENDING)
        self.assertEqual(Patient.objects.count(), 1)

    def test_name_and_birthdate_match_without_curp_escalates_generically(self):
        with self.assertRaises(minors.ExistingPatientRequiresManualReview):
            minors.register_minor_patient(
                responsible=self.responsible,
                person_data=dict(MINOR_PERSON_DATA),
                patient_data=dict(MINOR_PATIENT_DATA),
                relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
            )
        self.assertEqual(Patient.objects.count(), 1)
        self.assertFalse(ResponsiblePatientRelationship.objects.exists())

    def test_curp_match_against_patient_with_own_account_escalates_generically(self):
        self.existing_person.user = User.objects.create_user(
            email="grown-up@example.com", password="s3cure-pass!"
        )
        self.existing_person.save()

        with self.assertRaises(minors.ExistingPatientRequiresManualReview):
            minors.register_minor_patient(
                responsible=self.responsible,
                person_data=dict(MINOR_PERSON_DATA),
                patient_data=dict(MINOR_PATIENT_DATA, curp="PELJ150601HDFRPN01"),
                relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
            )
        self.assertFalse(ResponsiblePatientRelationship.objects.exists())

    def test_responsible_already_linked_does_not_duplicate(self):
        ResponsiblePatientRelationship.objects.create(
            responsible=self.responsible,
            patient=self.existing_patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )

        with self.assertRaises(minors.AlreadyLinked):
            minors.register_minor_patient(
                responsible=self.responsible,
                person_data=dict(MINOR_PERSON_DATA),
                patient_data=dict(MINOR_PATIENT_DATA, curp="PELJ150601HDFRPN01"),
                relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
            )
        self.assertEqual(
            ResponsiblePatientRelationship.objects.filter(
                responsible=self.responsible, patient=self.existing_patient
            ).count(),
            1,
        )

    def test_already_linked_takes_precedence_over_own_account_gate(self):
        # If this responsible already has a relationship, that fact should
        # surface even if the patient later got their own account — it's
        # informational, not a new grant, so the stricter gate shouldn't
        # suppress it.
        ResponsiblePatientRelationship.objects.create(
            responsible=self.responsible,
            patient=self.existing_patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        self.existing_person.user = User.objects.create_user(
            email="grown-up2@example.com", password="s3cure-pass!"
        )
        self.existing_person.save()

        with self.assertRaises(minors.AlreadyLinked):
            minors.register_minor_patient(
                responsible=self.responsible,
                person_data=dict(MINOR_PERSON_DATA),
                patient_data=dict(MINOR_PATIENT_DATA, curp="PELJ150601HDFRPN01"),
                relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
            )

    def test_match_never_reveals_existing_registrant_details(self):
        # The exception itself must carry nothing about the existing patient —
        # callers can only build a generic message from it (requirements.md §7.2.7).
        try:
            minors.register_minor_patient(
                responsible=self.responsible,
                person_data=dict(MINOR_PERSON_DATA),
                patient_data=dict(MINOR_PATIENT_DATA),
                relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
            )
        except minors.ExistingPatientRequiresManualReview as exc:
            self.assertNotIn("Juan", str(exc))
            self.assertNotIn("Perez", str(exc))


class ApproveRejectTests(TestCase):
    def setUp(self):
        self.approver = _make_responsible("approver@example.com", "Approver")
        self.requester = _make_responsible("requester@example.com", "Requester")
        self.patient = Patient.objects.create(
            person=_make_person("minor@example.com", "Menor", birth_date=date(2015, 6, 1)),
            sex=Patient.Sex.FEMALE,
        )
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

    def test_active_responsible_can_approve(self):
        minors.approve_relationship_request(
            relationship=self.pending, approving_responsible=self.approver
        )
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, ResponsiblePatientRelationship.Status.ACTIVE)

    def test_active_responsible_can_reject(self):
        minors.reject_relationship_request(
            relationship=self.pending, approving_responsible=self.approver
        )
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, ResponsiblePatientRelationship.Status.INACTIVE)

    def test_unrelated_responsible_cannot_approve(self):
        stranger = _make_responsible("stranger@example.com", "Stranger")
        with self.assertRaises(minors.NotAuthorizedToDecide):
            minors.approve_relationship_request(
                relationship=self.pending, approving_responsible=stranger
            )
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, ResponsiblePatientRelationship.Status.PENDING)

    def test_cannot_approve_already_resolved_request(self):
        self.pending.status = ResponsiblePatientRelationship.Status.ACTIVE
        self.pending.save(update_fields=["status"])
        with self.assertRaises(minors.MinorRegistrationError):
            minors.approve_relationship_request(
                relationship=self.pending, approving_responsible=self.approver
            )

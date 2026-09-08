from datetime import date

from django.test import TestCase

from accounts.models import Person, User
from doctors.models import Doctor
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
        self.assertEqual(patient.regime, Patient.Regime.MINOR)
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
            person=self.existing_person,
            sex=Patient.Sex.MALE,
            curp="PELJ150601HDFRPN01",
            regime=Patient.Regime.MINOR,
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
            regime=Patient.Regime.MINOR,
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
        self.assertIsNotNone(self.pending.deactivated_at)
        self.assertEqual(
            self.pending.deactivation_reason,
            ResponsiblePatientRelationship.DeactivationReason.REQUEST_REJECTED,
        )

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


def _make_doctor(email, first_name="Doc"):
    return Doctor.objects.create(person=_make_person(email, first_name))


class AdultTransitionTests(TestCase):
    """ADR-007 §3.8 addendum, requirements.md §7.2.8."""

    def setUp(self):
        self.doctor = _make_doctor("transition-doc@example.com")
        # Chronologically adult (1990) but still in MINOR regime, and with
        # no User of their own — exactly the realistic scenario this
        # transition exists for (registered as a minor, never logged in).
        self.patient = Patient.objects.create(
            person=Person.objects.create(
                first_name="Grown", last_name_paterno="Test", birth_date=date(1990, 1, 1)
            ),
            sex=Patient.Sex.FEMALE,
            regime=Patient.Regime.MINOR,
        )
        self.responsible = _make_responsible("transition-resp@example.com")
        self.relationship = ResponsiblePatientRelationship.objects.create(
            responsible=self.responsible,
            patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )

    def test_successful_transition_effects(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient)

        result = minors.transition_patient_to_adult(
            patient=self.patient, performed_by_doctor=self.doctor
        )

        self.assertEqual(result.regime, Patient.Regime.ADULT)
        self.assertIsNotNone(result.regime_changed_at)
        self.assertEqual(result.regime_changed_by, self.doctor)

        self.relationship.refresh_from_db()
        self.assertEqual(self.relationship.status, ResponsiblePatientRelationship.Status.INACTIVE)
        self.assertIsNotNone(self.relationship.deactivated_at)
        self.assertEqual(
            self.relationship.deactivation_reason,
            ResponsiblePatientRelationship.DeactivationReason.ADULT_TRANSITION,
        )

    def test_deactivates_every_active_relationship_in_one_operation(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient)
        second_responsible = _make_responsible("transition-resp2@example.com")
        second_relationship = ResponsiblePatientRelationship.objects.create(
            responsible=second_responsible,
            patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.PADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        # A PENDING request (not yet approved) must not be touched — only
        # ACTIVE relationships are in scope for this transition.
        third_responsible = _make_responsible("transition-resp3@example.com")
        pending_request = ResponsiblePatientRelationship.objects.create(
            responsible=third_responsible,
            patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.TUTOR_LEGAL,
            status=ResponsiblePatientRelationship.Status.PENDING,
        )

        minors.transition_patient_to_adult(patient=self.patient, performed_by_doctor=self.doctor)

        self.relationship.refresh_from_db()
        second_relationship.refresh_from_db()
        pending_request.refresh_from_db()
        self.assertEqual(self.relationship.status, ResponsiblePatientRelationship.Status.INACTIVE)
        self.assertEqual(second_relationship.status, ResponsiblePatientRelationship.Status.INACTIVE)
        self.assertEqual(pending_request.status, ResponsiblePatientRelationship.Status.PENDING)

    def test_does_not_touch_doctor_patient_relationship(self):
        relation = DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient)
        minors.transition_patient_to_adult(patient=self.patient, performed_by_doctor=self.doctor)
        relation.refresh_from_db()
        self.assertTrue(relation.is_active)
        self.assertEqual(
            relation.relationship_type, DoctorPatientRelationship.RelationType.TRATANTE
        )

    def test_never_creates_or_requires_a_user(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient)
        user_count_before = User.objects.count()
        minors.transition_patient_to_adult(patient=self.patient, performed_by_doctor=self.doctor)
        self.assertEqual(User.objects.count(), user_count_before)
        self.assertIsNone(self.patient.person.user)

    def test_is_irreversible(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient)
        minors.transition_patient_to_adult(patient=self.patient, performed_by_doctor=self.doctor)

        with self.assertRaises(minors.PatientAlreadyAdult):
            minors.transition_patient_to_adult(patient=self.patient, performed_by_doctor=self.doctor)

    def test_legal_lock_rejects_chronologically_minor_patient(self):
        self.patient.person.birth_date = date(2015, 6, 1)
        self.patient.person.save(update_fields=["birth_date"])
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient)

        with self.assertRaises(minors.PatientStillMinor):
            minors.transition_patient_to_adult(patient=self.patient, performed_by_doctor=self.doctor)

        self.patient.refresh_from_db()
        self.assertEqual(self.patient.regime, Patient.Regime.MINOR)
        self.relationship.refresh_from_db()
        self.assertEqual(self.relationship.status, ResponsiblePatientRelationship.Status.ACTIVE)

    def test_doctor_without_active_relationship_cannot_transition(self):
        with self.assertRaises(minors.DoctorNotAuthorizedForTransition):
            minors.transition_patient_to_adult(patient=self.patient, performed_by_doctor=self.doctor)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.regime, Patient.Regime.MINOR)

    def test_any_relationship_type_qualifies_not_only_tratante(self):
        DoctorPatientRelationship.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            relationship_type=DoctorPatientRelationship.RelationType.SUSTITUTO,
        )
        result = minors.transition_patient_to_adult(
            patient=self.patient, performed_by_doctor=self.doctor
        )
        self.assertEqual(result.regime, Patient.Regime.ADULT)

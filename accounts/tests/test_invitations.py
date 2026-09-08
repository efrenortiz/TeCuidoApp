import threading
from datetime import date, timedelta

from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from accounts.models import Invitation, Person, User
from accounts.services import invitations
from doctors.models import Doctor
from patients.models import DoctorPatientRelationship, Patient


def _make_doctor(email):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user, first_name="Doc", last_name_paterno="Tor", birth_date=date(1980, 1, 1)
    )
    return Doctor.objects.create(person=person)


class CreateInvitationTests(TestCase):
    def test_create_invitation_is_pending_with_hashed_token(self):
        doctor = _make_doctor("doc1@example.com")
        invitation, raw_token = invitations.create_invitation(
            doctor=doctor, email="Prospect@Example.com"
        )
        self.assertEqual(invitation.status, Invitation.Status.PENDING)
        self.assertEqual(invitation.email, "prospect@example.com")
        self.assertNotEqual(invitation.token_hash, raw_token)
        self.assertGreater(invitation.expires_at, timezone.now())


class AcceptInvitationTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("doc2@example.com")
        self.invitation, self.raw_token = invitations.create_invitation(
            doctor=self.doctor, email="prospect2@example.com"
        )
        self.person_data = dict(
            first_name="Prospect", last_name_paterno="Two", birth_date=date(1995, 1, 1)
        )
        self.patient_data = dict(sex=Patient.Sex.FEMALE)

    def test_accept_creates_full_chain_and_marks_used(self):
        patient = invitations.accept_invitation(
            self.raw_token,
            password="s3cure-pass!",
            person_data=self.person_data,
            patient_data=self.patient_data,
        )
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, Invitation.Status.USED)
        self.assertIsNotNone(self.invitation.used_at)
        self.assertTrue(
            DoctorPatientRelationship.objects.filter(doctor=self.doctor, patient=patient).exists()
        )
        self.assertEqual(patient.person.user.email, "prospect2@example.com")
        self.assertEqual(patient.regime, Patient.Regime.ADULT)

    def test_accept_with_unknown_token_raises_not_found(self):
        with self.assertRaises(invitations.InvitationNotFound):
            invitations.accept_invitation(
                "bogus-token", password="s3cure-pass!", person_data=self.person_data
            )

    def test_accept_twice_fails_second_time(self):
        invitations.accept_invitation(
            self.raw_token,
            password="s3cure-pass!",
            person_data=self.person_data,
            patient_data=self.patient_data,
        )
        with self.assertRaises(invitations.InvitationNotUsable) as ctx:
            invitations.accept_invitation(
                self.raw_token,
                password="another-pass!",
                person_data=self.person_data,
                patient_data=self.patient_data,
            )
        self.assertEqual(ctx.exception.status, Invitation.Status.USED)

    def test_accept_expired_invitation_marks_expired_and_fails(self):
        self.invitation.expires_at = timezone.now() - timedelta(hours=1)
        self.invitation.save(update_fields=["expires_at"])

        with self.assertRaises(invitations.InvitationNotUsable) as ctx:
            invitations.accept_invitation(
                self.raw_token,
                password="s3cure-pass!",
                person_data=self.person_data,
                patient_data=self.patient_data,
            )
        self.assertEqual(ctx.exception.status, Invitation.Status.EXPIRED)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, Invitation.Status.EXPIRED)

    def test_accept_failure_leaves_no_partial_state(self):
        # Person.birth_date is NOT NULL with no default — omitting it forces
        # a real DB-level failure after the User has already been created,
        # proving the whole chain (including the User) rolls back together.
        broken_person_data = {"first_name": "Prospect", "last_name_paterno": "Two"}
        with self.assertRaises(Exception):
            invitations.accept_invitation(
                self.raw_token,
                password="s3cure-pass!",
                person_data=broken_person_data,
                patient_data=self.patient_data,
            )
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, Invitation.Status.PENDING)
        self.assertFalse(User.objects.filter(email="prospect2@example.com").exists())

    def test_accept_with_email_already_registered_raises_and_leaves_no_partial_state(self):
        User.objects.create_user(email="prospect2@example.com", password="already-here!")

        with self.assertRaises(invitations.EmailAlreadyRegistered):
            invitations.accept_invitation(
                self.raw_token,
                password="s3cure-pass!",
                person_data=self.person_data,
                patient_data=self.patient_data,
            )

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, Invitation.Status.PENDING)
        self.assertEqual(User.objects.filter(email="prospect2@example.com").count(), 1)

    def test_doctor_association_cannot_be_supplied_by_caller(self):
        # accept_invitation() has no `doctor` parameter at all — the doctor on
        # the resulting relationship can only ever be invitation.doctor.
        other_doctor = _make_doctor("other-doc@example.com")
        patient = invitations.accept_invitation(
            self.raw_token,
            password="s3cure-pass!",
            person_data=self.person_data,
            patient_data=self.patient_data,
        )
        relationship = DoctorPatientRelationship.objects.get(patient=patient)
        self.assertEqual(relationship.doctor, self.doctor)
        self.assertNotEqual(relationship.doctor, other_doctor)


class InvitationConcurrencyTests(TransactionTestCase):
    """ADR-003 §19 / ADR-006 §11: two simultaneous requests must not both
    consume the same invitation. Uses real threads + TransactionTestCase so
    the `select_for_update()` lock is exercised against real DB connections."""

    def test_concurrent_accept_only_succeeds_once(self):
        doctor = _make_doctor("doc-conc@example.com")
        _invitation, raw_token = invitations.create_invitation(
            doctor=doctor, email="conc@example.com"
        )

        results = []
        errors = []

        def attempt(password):
            try:
                patient = invitations.accept_invitation(
                    raw_token,
                    password=password,
                    person_data=dict(
                        first_name="Conc", last_name_paterno="Urrent", birth_date=date(1990, 1, 1)
                    ),
                    patient_data=dict(sex=Patient.Sex.FEMALE),
                )
                results.append(patient)
            except Exception as exc:  # noqa: BLE001 - captured for assertion below
                errors.append(exc)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("pass-one-123!",))
        t2 = threading.Thread(target=attempt, args=("pass-two-123!",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], invitations.InvitationNotUsable)
        self.assertEqual(DoctorPatientRelationship.objects.filter(doctor=doctor).count(), 1)

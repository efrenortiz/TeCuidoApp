import threading
from datetime import date, time, timedelta
from unittest import mock

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Hold
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from appointments.services.exceptions import (
    AvailabilityNotFound,
    BookingWindowExpired,
    HoldAlreadyExists,
    HoldConflict,
    HoldNotActive,
    HoldNotFound,
    HoldNotOwned,
    InvalidSlot,
    NotAuthorized,
    SlotUnavailable,
)
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import Patient


def _make_person(email, first_name="Test", birth_date=date(1990, 1, 1)):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=birth_date
    )


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_patient(email):
    return Patient.objects.create(
        person=_make_person(email, "Pat"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT
    )


def _make_clinic(name="Consultorio Centro"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class HoldServiceTestCase(TransactionTestCase):
    """TransactionTestCase (not TestCase) — the concurrency test below
    needs real, separately-committing DB connections, which TestCase's
    wrap-every-test-in-a-transaction strategy would hide."""

    reset_sequences = False

    def setUp(self):
        self.doctor = _make_doctor("hold-svc-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(
            doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60
        )
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        self.availability = availability_service.create_availability(
            actor=self.doctor_user,
            doctor=self.doctor,
            clinic=self.clinic,
            date=self.day,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        self.patient = _make_patient("hold-svc-patient@example.com")
        self.patient_user = self.patient.person.user

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(hours=1)


class CreateHoldTests(HoldServiceTestCase):
    def test_patient_can_create_hold(self):
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        self.assertEqual(hold.status, Hold.Status.ACTIVE)
        self.assertEqual(hold.availability_id, self.availability.pk)

    def test_doctor_can_create_hold_for_own_clinic(self):
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        self.assertEqual(hold.status, Hold.Status.ACTIVE)

    def test_administrator_can_create_hold_with_valid_doctorclinic(self):
        admin = User.objects.create_superuser(email="hold-admin@example.com", password="s3cure-pass!")
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=admin, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at,
        )
        self.assertEqual(hold.status, Hold.Status.ACTIVE)

    def test_bystander_without_any_profile_is_rejected(self):
        bystander = User.objects.create_user(email="hold-bystander@example.com", password="s3cure-pass!")
        start_at, end_at = self._slot()
        with self.assertRaises(NotAuthorized):
            hold_service.create_hold(
                actor=bystander, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at,
            )

    def test_slot_outside_any_availability_is_rejected(self):
        start_at = availability_service.combine_local(self.day, time(20, 0), self.clinic)
        with self.assertRaises(AvailabilityNotFound):
            hold_service.create_hold(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=start_at + timedelta(hours=1),
            )

    def test_misaligned_slot_is_rejected(self):
        start_at = availability_service.combine_local(self.day, time(9, 15), self.clinic)
        with self.assertRaises(InvalidSlot):
            hold_service.create_hold(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=start_at + timedelta(hours=1),
            )

    def test_slot_more_than_30_minutes_late_is_rejected(self):
        start_at, end_at = self._slot()
        simulated_now = start_at + timedelta(minutes=31)
        with mock.patch(
            "appointments.services.hold.dj_timezone.now", return_value=simulated_now
        ):
            with self.assertRaises(BookingWindowExpired):
                hold_service.create_hold(
                    actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                    start_at=start_at, end_at=end_at,
                )

    def test_slot_within_30_minute_grace_is_allowed(self):
        start_at, end_at = self._slot()
        simulated_now = start_at + timedelta(minutes=29)
        with mock.patch(
            "appointments.services.hold.dj_timezone.now", return_value=simulated_now
        ):
            hold = hold_service.create_hold(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at,
            )
        self.assertEqual(hold.status, Hold.Status.ACTIVE)

    def test_one_active_hold_per_user(self):
        start_at, end_at = self._slot(9)
        hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        start_at2, end_at2 = self._slot(10)
        with self.assertRaises(HoldAlreadyExists):
            hold_service.create_hold(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at2, end_at=end_at2,
            )

    def test_two_users_cannot_hold_the_same_slot(self):
        start_at, end_at = self._slot()
        hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        other_patient = _make_patient("hold-svc-patient2@example.com")
        with self.assertRaises(HoldConflict):
            hold_service.create_hold(
                actor=other_patient.person.user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at,
            )

    def test_conflicting_appointment_blocks_hold(self):
        from appointments.models import Appointment

        start_at, end_at = self._slot()
        creator = User.objects.create_user(email="hold-svc-creator@example.com", password="s3cure-pass!")
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, clinic=self.clinic,
            availability=self.availability, start_at=start_at, end_at=end_at,
            duration_minutes=60, status=Appointment.Status.SCHEDULED, created_by=creator,
        )
        other_patient = _make_patient("hold-svc-patient3@example.com")
        with self.assertRaises(SlotUnavailable):
            hold_service.create_hold(
                actor=other_patient.person.user, doctor=self.doctor, clinic=self.clinic,
                start_at=start_at, end_at=end_at,
            )

    def test_expired_hold_does_not_block_new_hold(self):
        start_at, end_at = self._slot()
        first = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        # Force it into the past without going through release_hold().
        Hold.objects.filter(pk=first.pk).update(
            expires_at=dj_timezone.now() - timedelta(minutes=1)
        )
        other_patient = _make_patient("hold-svc-patient4@example.com")
        second = hold_service.create_hold(
            actor=other_patient.person.user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        self.assertEqual(second.status, Hold.Status.ACTIVE)
        first.refresh_from_db()
        self.assertEqual(first.status, Hold.Status.EXPIRED)

    def test_expired_hold_does_not_block_same_user_new_hold(self):
        start_at, end_at = self._slot(9)
        first = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        Hold.objects.filter(pk=first.pk).update(
            expires_at=dj_timezone.now() - timedelta(minutes=1)
        )
        start_at2, end_at2 = self._slot(10)
        second = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at2, end_at=end_at2,
        )
        self.assertEqual(second.status, Hold.Status.ACTIVE)


class ReleaseHoldTests(HoldServiceTestCase):
    def test_owner_can_release(self):
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        released = hold_service.release_hold(actor=self.patient_user, hold=hold)
        self.assertEqual(released.status, Hold.Status.RELEASED)
        self.assertIsNotNone(released.released_at)

    def test_released_hold_frees_the_slot_immediately(self):
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        hold_service.release_hold(actor=self.patient_user, hold=hold)
        other_patient = _make_patient("hold-svc-patient5@example.com")
        new_hold = hold_service.create_hold(
            actor=other_patient.person.user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        self.assertEqual(new_hold.status, Hold.Status.ACTIVE)

    def test_other_user_cannot_release(self):
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        other_patient = _make_patient("hold-svc-patient6@example.com")
        with self.assertRaises(HoldNotOwned):
            hold_service.release_hold(actor=other_patient.person.user, hold=hold)

    def test_cannot_release_already_released_hold(self):
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        hold_service.release_hold(actor=self.patient_user, hold=hold)
        with self.assertRaises(HoldNotActive):
            hold_service.release_hold(actor=self.patient_user, hold=hold)

    def test_release_nonexistent_hold(self):
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        hold_id = hold.pk
        hold.delete()
        phantom = Hold(pk=hold_id)
        with self.assertRaises(HoldNotFound):
            hold_service.release_hold(actor=self.patient_user, hold=phantom)


class MarkConsumedTests(HoldServiceTestCase):
    def test_marks_hold_consumed(self):
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        consumed = hold_service.mark_consumed(hold)
        self.assertEqual(consumed.status, Hold.Status.CONSUMED)
        self.assertIsNotNone(consumed.consumed_at)


class HoldConcurrencyTests(HoldServiceTestCase):
    """docs/phases/phase-2-agenda.md §27 — real concurrency, not just
    sequential calls: two threads with independent DB connections racing
    for the same slot."""

    def test_two_concurrent_holds_for_same_slot_only_one_succeeds(self):
        start_at, end_at = self._slot()
        other_patient = _make_patient("hold-svc-concurrent@example.com")

        results = {}
        barrier = threading.Barrier(2)

        def attempt(key, actor):
            try:
                barrier.wait(timeout=5)
                hold_service.create_hold(
                    actor=actor, doctor=self.doctor, clinic=self.clinic,
                    start_at=start_at, end_at=end_at,
                )
                results[key] = "success"
            except HoldConflict:
                results[key] = "conflict"
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = f"error: {exc!r}"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a", self.patient_user))
        t2 = threading.Thread(target=attempt, args=("b", other_patient.person.user))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = list(results.values())
        self.assertEqual(outcomes.count("success"), 1, results)
        self.assertEqual(outcomes.count("conflict"), 1, results)
        self.assertEqual(Hold.objects.filter(status=Hold.Status.ACTIVE).count(), 1)

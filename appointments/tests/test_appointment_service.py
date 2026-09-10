import threading
from datetime import date, time, timedelta

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment, Hold
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from appointments.services.exceptions import (
    HoldExpired,
    HoldNotFound,
    HoldNotOwned,
    IdempotencyKeyConflict,
    InvalidDoctorClinic,
    InvalidPatient,
    NotAuthorized,
    SlotUnavailable,
)
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import (
    DoctorPatientRelationship,
    Patient,
    Responsible,
    ResponsiblePatientRelationship,
)


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


def _make_responsible(email):
    return Responsible.objects.create(person=_make_person(email, "Resp"))


def _make_clinic(name="Consultorio Centro"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class AppointmentServiceTestCase(TransactionTestCase):
    """TransactionTestCase — the concurrency test needs independently
    committing DB connections."""

    reset_sequences = False

    def setUp(self):
        self.doctor = _make_doctor("appt-svc-doc@example.com")
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
        self.patient = _make_patient("appt-svc-patient@example.com")
        self.patient_user = self.patient.person.user

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(hours=1)

    def _hold(self, actor, hour=9):
        start_at, end_at = self._slot(hour)
        return hold_service.create_hold(
            actor=actor, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at
        )


class CreateAppointmentFromHoldTests(AppointmentServiceTestCase):
    def test_patient_can_book_for_self(self):
        hold = self._hold(self.patient_user)
        appointment = appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient,
            doctor=self.doctor, clinic=self.clinic,
        )
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)
        self.assertEqual(appointment.patient_id, self.patient.pk)
        self.assertEqual(appointment.created_by_id, self.patient_user.id)
        hold.refresh_from_db()
        self.assertEqual(hold.status, Hold.Status.CONSUMED)
        self.assertIsNotNone(hold.consumed_at)

    def test_doctor_can_book_first_appointment_without_prior_relationship(self):
        """Mandatory test (2026-09-09 closing decision): a doctor may
        create a patient's first Appointment with a valid DoctorClinic and
        NO prior DoctorPatientRelationship — and doing so must NOT create
        one either."""
        self.assertFalse(
            DoctorPatientRelationship.objects.filter(
                doctor=self.doctor, patient=self.patient
            ).exists()
        )
        hold = self._hold(self.doctor_user)
        appointment = appointment_service.create_appointment_from_hold(
            actor=self.doctor_user, hold=hold, patient=self.patient,
            doctor=self.doctor, clinic=self.clinic,
        )
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)
        self.assertFalse(
            DoctorPatientRelationship.objects.filter(
                doctor=self.doctor, patient=self.patient
            ).exists()
        )

    def test_administrator_can_book_with_valid_doctorclinic(self):
        admin = User.objects.create_superuser(email="appt-svc-admin@example.com", password="s3cure-pass!")
        hold = self._hold(admin)
        appointment = appointment_service.create_appointment_from_hold(
            actor=admin, hold=hold, patient=self.patient, doctor=self.doctor, clinic=self.clinic,
        )
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)

    def test_responsible_with_active_relationship_can_book(self):
        responsible = _make_responsible("appt-svc-resp@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        responsible_user = responsible.person.user
        hold = self._hold(responsible_user)
        appointment = appointment_service.create_appointment_from_hold(
            actor=responsible_user, hold=hold, patient=self.patient,
            doctor=self.doctor, clinic=self.clinic,
        )
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)

    def test_responsible_without_active_relationship_is_rejected(self):
        responsible = _make_responsible("appt-svc-resp2@example.com")
        responsible_user = responsible.person.user
        hold = self._hold(responsible_user)
        with self.assertRaises(InvalidPatient):
            appointment_service.create_appointment_from_hold(
                actor=responsible_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )

    def test_patient_cannot_book_for_another_patient(self):
        other_patient = _make_patient("appt-svc-patient2@example.com")
        hold = self._hold(self.patient_user)
        with self.assertRaises(InvalidPatient):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=other_patient,
                doctor=self.doctor, clinic=self.clinic,
            )

    def test_bystander_is_rejected(self):
        bystander = User.objects.create_user(email="appt-svc-bystander@example.com", password="s3cure-pass!")
        hold = self._hold(self.patient_user)
        with self.assertRaises(NotAuthorized):
            appointment_service.create_appointment_from_hold(
                actor=bystander, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )

    def test_hold_owned_by_someone_else_is_rejected(self):
        hold = self._hold(self.patient_user)
        other_patient = _make_patient("appt-svc-patient3@example.com")
        with self.assertRaises(HoldNotOwned):
            appointment_service.create_appointment_from_hold(
                actor=other_patient.person.user, hold=hold, patient=other_patient,
                doctor=self.doctor, clinic=self.clinic,
            )

    def test_nonexistent_hold_is_rejected(self):
        hold = self._hold(self.patient_user)
        hold_id = hold.pk
        hold.delete()
        with self.assertRaises(HoldNotFound):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=Hold(pk=hold_id), patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )

    def test_expired_hold_is_rejected(self):
        # The expiry-marking write happens inside the same atomic() block
        # as the HoldExpired raise, so it rolls back with everything else
        # — by design, correctness here rests on the `expires_at` check
        # itself (re-applied on every call), not on a persisted status
        # column, same as HoldService's own lazy-expire pattern.
        hold = self._hold(self.patient_user)
        Hold.objects.filter(pk=hold.pk).update(expires_at=dj_timezone.now() - timedelta(minutes=1))
        with self.assertRaises(HoldExpired):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )
        self.assertEqual(Appointment.objects.count(), 0)

    def test_released_hold_is_rejected(self):
        hold = self._hold(self.patient_user)
        hold_service.release_hold(actor=self.patient_user, hold=hold)
        with self.assertRaises(HoldExpired):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )

    def test_already_consumed_hold_without_idempotency_key_is_rejected(self):
        hold = self._hold(self.patient_user)
        appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient,
            doctor=self.doctor, clinic=self.clinic,
        )
        with self.assertRaises(HoldExpired):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )

    def test_doctor_clinic_mismatch_with_hold_is_rejected(self):
        hold = self._hold(self.patient_user)
        other_clinic = _make_clinic("Otro consultorio")
        DoctorClinic.objects.create(doctor=self.doctor, clinic=other_clinic)
        with self.assertRaises(InvalidDoctorClinic):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=other_clinic,
            )

    def test_deactivated_availability_blocks_booking(self):
        hold = self._hold(self.patient_user)
        availability_service.deactivate_availability(actor=self.doctor_user, availability=self.availability)
        with self.assertRaises(SlotUnavailable):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )

    def test_conflicting_appointment_blocks_booking(self):
        start_at, end_at = self._slot()
        other_patient = _make_patient("appt-svc-patient4@example.com")
        creator = User.objects.create_user(email="appt-svc-creator@example.com", password="s3cure-pass!")
        Appointment.objects.create(
            patient=other_patient, doctor=self.doctor, clinic=self.clinic,
            availability=self.availability, start_at=start_at, end_at=end_at,
            duration_minutes=60, status=Appointment.Status.SCHEDULED, created_by=creator,
        )
        # HoldService itself would already block a new hold on this exact
        # interval — simulate a hold that predates the conflicting
        # Appointment to exercise AppointmentService's own re-check.
        hold = Hold.objects.create(
            user=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            availability=self.availability, start_at=start_at, end_at=end_at,
            status=Hold.Status.ACTIVE, expires_at=dj_timezone.now() + timedelta(minutes=15),
        )
        with self.assertRaises(SlotUnavailable):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )


class IdempotencyTests(AppointmentServiceTestCase):
    def test_replay_with_same_payload_returns_original_appointment(self):
        hold = self._hold(self.patient_user)
        first = appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient,
            doctor=self.doctor, clinic=self.clinic, idempotency_key="retry-key-1",
        )
        second = appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient,
            doctor=self.doctor, clinic=self.clinic, idempotency_key="retry-key-1",
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_same_key_different_payload_conflicts(self):
        hold = self._hold(self.patient_user)
        appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient,
            doctor=self.doctor, clinic=self.clinic, idempotency_key="retry-key-2",
        )
        other_patient = _make_patient("appt-svc-patient5@example.com")
        other_hold = self._hold(other_patient.person.user, hour=10)
        with self.assertRaises(IdempotencyKeyConflict):
            appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=other_hold, patient=other_patient,
                doctor=self.doctor, clinic=self.clinic, idempotency_key="retry-key-2",
            )


class AppointmentConcurrencyTests(AppointmentServiceTestCase):
    """docs/phases/phase-2-agenda.md §27 — real concurrency: two threads
    racing to convert the *same* hold into an Appointment (a duplicated
    retry), with independent DB connections."""

    def test_two_concurrent_calls_same_hold_same_idempotency_key_create_one_appointment(self):
        hold = self._hold(self.patient_user)
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                appt = appointment_service.create_appointment_from_hold(
                    actor=self.patient_user, hold=hold, patient=self.patient,
                    doctor=self.doctor, clinic=self.clinic, idempotency_key="concurrent-retry",
                )
                results[key] = appt.pk
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = f"error: {exc!r}"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a",))
        t2 = threading.Thread(target=attempt, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(Appointment.objects.count(), 1, results)
        pks = [v for v in results.values() if isinstance(v, int)]
        self.assertEqual(len(pks), 2, results)
        self.assertEqual(pks[0], pks[1])

    def test_two_concurrent_calls_same_hold_without_idempotency_key_only_one_succeeds(self):
        hold = self._hold(self.patient_user)
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                appt = appointment_service.create_appointment_from_hold(
                    actor=self.patient_user, hold=hold, patient=self.patient,
                    doctor=self.doctor, clinic=self.clinic,
                )
                results[key] = ("success", appt.pk)
            except HoldExpired:
                results[key] = ("hold_expired", None)
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = (f"error: {exc!r}", None)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a",))
        t2 = threading.Thread(target=attempt, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = [outcome for outcome, _ in results.values()]
        self.assertEqual(outcomes.count("success"), 1, results)
        self.assertEqual(outcomes.count("hold_expired"), 1, results)
        self.assertEqual(Appointment.objects.count(), 1)

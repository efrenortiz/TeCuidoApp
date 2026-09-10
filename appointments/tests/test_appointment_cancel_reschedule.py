import threading
from datetime import date, time, timedelta

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment, AppointmentRescheduleHistory, RequestReason
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from appointments.services.exceptions import (
    AppointmentAlreadyCancelled,
    AppointmentNotCancellable,
    AppointmentNotFound,
    AppointmentNotReschedulable,
    DurationIncompatible,
    IdempotencyKeyConflict,
    InvalidDoctorClinic,
    NotAuthorized,
    SlotUnavailable,
)
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import Patient, Responsible, ResponsiblePatientRelationship


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


def _make_clinic(name="Consultorio Centro", duration=60):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class AppointmentMutationTestCase(TransactionTestCase):
    reset_sequences = False

    def setUp(self):
        self.doctor = _make_doctor("cxl-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        self.availability = availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("cxl-patient@example.com")
        self.patient_user = self.patient.person.user

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(hours=1)

    def _book(self, actor, patient, hour=9):
        start_at, end_at = self._slot(hour)
        hold = hold_service.create_hold(
            actor=actor, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at
        )
        return appointment_service.create_appointment_from_hold(
            actor=actor, hold=hold, patient=patient, doctor=self.doctor, clinic=self.clinic,
        )


class CancelAppointmentTests(AppointmentMutationTestCase):
    def test_patient_can_cancel_own_appointment(self):
        appointment = self._book(self.patient_user, self.patient)
        cancelled = appointment_service.cancel_appointment(
            actor=self.patient_user, appointment=appointment, reason=RequestReason.PATIENT_REQUEST,
        )
        self.assertEqual(cancelled.status, Appointment.Status.CANCELLED)
        self.assertEqual(cancelled.cancelled_by_id, self.patient_user.id)
        self.assertEqual(cancelled.cancellation_reason, RequestReason.PATIENT_REQUEST)
        self.assertIsNotNone(cancelled.cancelled_at)

    def test_cancelling_frees_the_slot_immediately(self):
        appointment = self._book(self.patient_user, self.patient)
        appointment_service.cancel_appointment(
            actor=self.patient_user, appointment=appointment, reason=RequestReason.PATIENT_REQUEST,
        )
        other_patient = _make_patient("cxl-patient2@example.com")
        new_appointment = self._book(other_patient.person.user, other_patient)
        self.assertEqual(new_appointment.status, Appointment.Status.SCHEDULED)

    def test_doctor_can_cancel_assigned_appointment(self):
        appointment = self._book(self.patient_user, self.patient)
        cancelled = appointment_service.cancel_appointment(
            actor=self.doctor_user, appointment=appointment, reason=RequestReason.DOCTOR_REQUEST,
        )
        self.assertEqual(cancelled.status, Appointment.Status.CANCELLED)

    def test_administrator_can_cancel_with_valid_doctorclinic(self):
        admin = User.objects.create_superuser(email="cxl-admin@example.com", password="s3cure-pass!")
        appointment = self._book(self.patient_user, self.patient)
        cancelled = appointment_service.cancel_appointment(
            actor=admin, appointment=appointment, reason=RequestReason.CLINIC_REQUEST,
        )
        self.assertEqual(cancelled.status, Appointment.Status.CANCELLED)

    def test_responsible_with_active_relationship_can_cancel(self):
        responsible = _make_responsible("cxl-resp@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible, patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        appointment = self._book(self.patient_user, self.patient)
        cancelled = appointment_service.cancel_appointment(
            actor=responsible.person.user, appointment=appointment, reason=RequestReason.RESPONSIBLE_REQUEST,
        )
        self.assertEqual(cancelled.status, Appointment.Status.CANCELLED)

    def test_unrelated_doctor_cannot_cancel(self):
        other_doctor = _make_doctor("cxl-doc2@example.com")
        appointment = self._book(self.patient_user, self.patient)
        with self.assertRaises(NotAuthorized):
            appointment_service.cancel_appointment(
                actor=other_doctor.person.user, appointment=appointment, reason=RequestReason.DOCTOR_REQUEST,
            )

    def test_bystander_cannot_cancel(self):
        bystander = User.objects.create_user(email="cxl-bystander@example.com", password="s3cure-pass!")
        appointment = self._book(self.patient_user, self.patient)
        with self.assertRaises(NotAuthorized):
            appointment_service.cancel_appointment(
                actor=bystander, appointment=appointment, reason=RequestReason.OTHER,
            )

    def test_cannot_cancel_already_cancelled(self):
        appointment = self._book(self.patient_user, self.patient)
        appointment_service.cancel_appointment(
            actor=self.patient_user, appointment=appointment, reason=RequestReason.PATIENT_REQUEST,
        )
        with self.assertRaises(AppointmentAlreadyCancelled):
            appointment_service.cancel_appointment(
                actor=self.patient_user, appointment=appointment, reason=RequestReason.PATIENT_REQUEST,
            )

    def test_cannot_cancel_started_appointment(self):
        appointment = self._book(self.patient_user, self.patient)
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(minutes=1)
        )
        appointment.refresh_from_db()
        with self.assertRaises(AppointmentNotCancellable):
            appointment_service.cancel_appointment(
                actor=self.patient_user, appointment=appointment, reason=RequestReason.PATIENT_REQUEST,
            )

    def test_invalid_reason_rejected(self):
        appointment = self._book(self.patient_user, self.patient)
        with self.assertRaises(ValueError):
            appointment_service.cancel_appointment(
                actor=self.patient_user, appointment=appointment, reason="NOT_A_REAL_REASON",
            )

    def test_nonexistent_appointment_raises_not_found(self):
        appointment = self._book(self.patient_user, self.patient, hour=10)
        appointment_id = appointment.pk
        appointment.delete()
        with self.assertRaises(AppointmentNotFound):
            appointment_service.cancel_appointment(
                actor=self.patient_user, appointment=Appointment(pk=appointment_id),
                reason=RequestReason.PATIENT_REQUEST,
            )


class RescheduleTestCase(AppointmentMutationTestCase):
    def setUp(self):
        super().setUp()
        self.other_clinic = _make_clinic("Consultorio Norte")
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.other_clinic, appointment_duration_minutes=60)
        # A doctor cannot have simultaneous availability in two different
        # clinics (CLAUDE.md Fase 2 closing decision) — this window must
        # not overlap self.clinic's 09:00-13:00 for the same doctor.
        self.other_availability = availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.other_clinic,
            date=self.day, start_time=time(14, 0), end_time=time(18, 0),
        )


class RescheduleAppointmentTests(RescheduleTestCase):
    def test_patient_can_reschedule_same_clinic_different_time(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at, new_end_at = self._slot(hour=10)
        rescheduled = appointment_service.reschedule_appointment(
            actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
            new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
        )
        self.assertEqual(rescheduled.pk, appointment.pk)
        self.assertEqual(rescheduled.status, Appointment.Status.SCHEDULED)
        self.assertEqual(rescheduled.start_at, new_start_at)
        self.assertEqual(rescheduled.end_at, new_end_at)

    def test_reschedule_to_different_clinic(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at = availability_service.combine_local(self.day, time(15, 0), self.other_clinic)
        rescheduled = appointment_service.reschedule_appointment(
            actor=self.patient_user, appointment=appointment, new_clinic=self.other_clinic,
            new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
        )
        self.assertEqual(rescheduled.clinic_id, self.other_clinic.pk)
        self.assertEqual(rescheduled.doctor_id, self.doctor.pk)

    def test_reschedule_records_history(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        old_start_at = appointment.start_at
        new_start_at, _ = self._slot(hour=11)
        appointment_service.reschedule_appointment(
            actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
            new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
        )
        history = AppointmentRescheduleHistory.objects.get(appointment=appointment)
        self.assertEqual(history.old_start_at, old_start_at)
        self.assertEqual(history.new_start_at, new_start_at)
        self.assertEqual(history.reason, RequestReason.PATIENT_REQUEST)

    def test_reschedule_frees_original_slot(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at, _ = self._slot(hour=11)
        appointment_service.reschedule_appointment(
            actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
            new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
        )
        other_patient = _make_patient("resched-patient2@example.com")
        new_appointment = self._book(other_patient.person.user, other_patient, hour=9)
        self.assertEqual(new_appointment.status, Appointment.Status.SCHEDULED)

    def test_cannot_change_doctor(self):
        """The service signature has no doctor parameter at all — the
        doctor is always read from the existing Appointment, matching
        docs/design/agenda-permissions.md §14 ('no permite cambiar el
        médico'). This test documents that structurally rather than
        exercising a runtime rejection path."""
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at, _ = self._slot(hour=11)
        rescheduled = appointment_service.reschedule_appointment(
            actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
            new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
        )
        self.assertEqual(rescheduled.doctor_id, self.doctor.pk)

    def test_conflicting_target_slot_is_rejected(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        other_patient = _make_patient("resched-patient3@example.com")
        self._book(other_patient.person.user, other_patient, hour=11)
        new_start_at, _ = self._slot(hour=11)
        with self.assertRaises(SlotUnavailable):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )
        appointment.refresh_from_db()
        self.assertEqual(appointment.start_at, self._slot(hour=9)[0])

    def test_target_outside_any_availability_is_rejected(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at = availability_service.combine_local(self.day, time(20, 0), self.clinic)
        with self.assertRaises(SlotUnavailable):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )

    def test_incompatible_duration_is_rejected(self):
        narrow_clinic = _make_clinic("Consultorio Express")
        DoctorClinic.objects.create(doctor=self.doctor, clinic=narrow_clinic, appointment_duration_minutes=30)
        # Must not overlap self.clinic (09:00-13:00) or self.other_clinic
        # (14:00-18:00) for the same doctor.
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=narrow_clinic,
            date=self.day, start_time=time(19, 0), end_time=time(21, 0),
        )
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at = availability_service.combine_local(self.day, time(19, 0), narrow_clinic)
        with self.assertRaises(DurationIncompatible):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=narrow_clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )

    def test_no_doctorclinic_for_new_clinic_is_rejected(self):
        stranger_clinic = _make_clinic("Consultorio Ajeno")
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at = availability_service.combine_local(self.day, time(9, 0), stranger_clinic)
        with self.assertRaises(InvalidDoctorClinic):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=stranger_clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )

    def test_cannot_reschedule_cancelled_appointment(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        appointment_service.cancel_appointment(
            actor=self.patient_user, appointment=appointment, reason=RequestReason.PATIENT_REQUEST,
        )
        new_start_at, _ = self._slot(hour=11)
        with self.assertRaises(AppointmentNotReschedulable):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )

    def test_bystander_cannot_reschedule(self):
        bystander = User.objects.create_user(email="resched-bystander@example.com", password="s3cure-pass!")
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at, _ = self._slot(hour=11)
        with self.assertRaises(NotAuthorized):
            appointment_service.reschedule_appointment(
                actor=bystander, appointment=appointment, new_clinic=self.clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )


class RescheduleIdempotencyTests(RescheduleTestCase):
    def test_replay_with_same_payload_returns_same_appointment(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at, _ = self._slot(hour=11)
        first = appointment_service.reschedule_appointment(
            actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
            new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST, idempotency_key="resched-key-1",
        )
        second = appointment_service.reschedule_appointment(
            actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
            new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST, idempotency_key="resched-key-1",
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(AppointmentRescheduleHistory.objects.filter(appointment=appointment).count(), 1)

    def test_same_key_different_payload_conflicts(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        slot_11, _ = self._slot(hour=11)
        slot_12, _ = self._slot(hour=12)
        appointment_service.reschedule_appointment(
            actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
            new_start_at=slot_11, reason=RequestReason.PATIENT_REQUEST, idempotency_key="resched-key-2",
        )
        with self.assertRaises(IdempotencyKeyConflict):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                new_start_at=slot_12, reason=RequestReason.PATIENT_REQUEST, idempotency_key="resched-key-2",
            )


class RescheduleConcurrencyTests(AppointmentMutationTestCase):
    """docs/phases/phase-2-agenda.md §27 — real concurrency: two threads
    racing to reschedule the same appointment to the same target."""

    def test_two_concurrent_identical_reschedules_produce_one_history_row(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        new_start_at, _ = self._slot(hour=11)
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                appt = appointment_service.reschedule_appointment(
                    actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                    new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
                    idempotency_key="concurrent-resched",
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

        self.assertEqual(
            AppointmentRescheduleHistory.objects.filter(appointment=appointment).count(), 1, results
        )
        pks = [v for v in results.values() if isinstance(v, int)]
        self.assertEqual(len(pks), 2, results)
        self.assertEqual(pks[0], pks[1])

    def test_two_concurrent_reschedules_to_overlapping_slots_only_one_succeeds(self):
        appointment = self._book(self.patient_user, self.patient, hour=9)
        other_patient = _make_patient("resched-concurrent-patient@example.com")
        other_appointment = self._book(other_patient.person.user, other_patient, hour=10)
        target_start_at, _ = self._slot(hour=11)

        results = {}
        barrier = threading.Barrier(2)

        def attempt(key, actor, appt):
            try:
                barrier.wait(timeout=5)
                appointment_service.reschedule_appointment(
                    actor=actor, appointment=appt, new_clinic=self.clinic,
                    new_start_at=target_start_at, reason=RequestReason.PATIENT_REQUEST,
                )
                results[key] = "success"
            except SlotUnavailable:
                results[key] = "slot_unavailable"
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = f"error: {exc!r}"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a", self.patient_user, appointment))
        t2 = threading.Thread(target=attempt, args=("b", other_patient.person.user, other_appointment))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = list(results.values())
        self.assertEqual(outcomes.count("success"), 1, results)
        self.assertEqual(outcomes.count("slot_unavailable"), 1, results)

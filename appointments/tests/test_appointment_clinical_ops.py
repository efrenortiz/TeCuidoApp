import threading
from datetime import date, time, timedelta

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from appointments.services.exceptions import (
    AppointmentNotCompletable,
    AppointmentNotFound,
    AppointmentNotStartable,
    NoShowNotAllowed,
    NotAuthorized,
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


class ClinicalOpsTestCase(TransactionTestCase):
    """TransactionTestCase — the concurrency test needs independently
    committing DB connections."""

    reset_sequences = False

    def setUp(self):
        self.doctor = _make_doctor("clinops-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        self.availability = availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("clinops-patient@example.com")
        self.patient_user = self.patient.person.user

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(hours=1)

    def _book(self, hour=9):
        start_at, end_at = self._slot(hour)
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at
        )
        return appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient, doctor=self.doctor, clinic=self.clinic,
        )

    def _book_started(self, hour=9):
        appointment = self._book(hour)
        return appointment_service.start_appointment(actor=self.doctor_user, appointment=appointment)


class StartAppointmentTests(ClinicalOpsTestCase):
    def test_assigned_doctor_can_start(self):
        appointment = self._book()
        started = appointment_service.start_appointment(actor=self.doctor_user, appointment=appointment)
        self.assertEqual(started.status, Appointment.Status.IN_CONSULTATION)
        self.assertEqual(started.started_by_id, self.doctor.pk)
        self.assertIsNotNone(started.started_at)

    def test_patient_cannot_start(self):
        appointment = self._book()
        with self.assertRaises(NotAuthorized):
            appointment_service.start_appointment(actor=self.patient_user, appointment=appointment)

    def test_administrator_cannot_start(self):
        admin = User.objects.create_superuser(email="clinops-admin@example.com", password="s3cure-pass!")
        appointment = self._book()
        with self.assertRaises(NotAuthorized):
            appointment_service.start_appointment(actor=admin, appointment=appointment)

    def test_other_doctor_cannot_start(self):
        other_doctor = _make_doctor("clinops-doc2@example.com")
        appointment = self._book()
        with self.assertRaises(NotAuthorized):
            appointment_service.start_appointment(actor=other_doctor.person.user, appointment=appointment)

    def test_cannot_start_already_started(self):
        appointment = self._book_started()
        with self.assertRaises(AppointmentNotStartable):
            appointment_service.start_appointment(actor=self.doctor_user, appointment=appointment)

    def test_cannot_start_cancelled_appointment(self):
        from appointments.models import RequestReason

        appointment = self._book()
        appointment_service.cancel_appointment(
            actor=self.patient_user, appointment=appointment, reason=RequestReason.PATIENT_REQUEST,
        )
        with self.assertRaises(AppointmentNotStartable):
            appointment_service.start_appointment(actor=self.doctor_user, appointment=appointment)

    def test_nonexistent_appointment_raises_not_found(self):
        appointment = self._book()
        appointment_id = appointment.pk
        appointment.delete()
        with self.assertRaises(AppointmentNotFound):
            appointment_service.start_appointment(
                actor=self.doctor_user, appointment=Appointment(pk=appointment_id)
            )


class CompleteAppointmentTests(ClinicalOpsTestCase):
    def test_assigned_doctor_can_complete(self):
        appointment = self._book_started()
        completed = appointment_service.complete_appointment(actor=self.doctor_user, appointment=appointment)
        self.assertEqual(completed.status, Appointment.Status.COMPLETED)
        self.assertEqual(completed.completed_by_id, self.doctor.pk)
        self.assertIsNotNone(completed.completed_at)

    def test_cannot_complete_without_starting(self):
        appointment = self._book()
        with self.assertRaises(AppointmentNotCompletable):
            appointment_service.complete_appointment(actor=self.doctor_user, appointment=appointment)

    def test_patient_cannot_complete(self):
        appointment = self._book_started()
        with self.assertRaises(NotAuthorized):
            appointment_service.complete_appointment(actor=self.patient_user, appointment=appointment)

    def test_administrator_cannot_complete(self):
        admin = User.objects.create_superuser(email="clinops-admin2@example.com", password="s3cure-pass!")
        appointment = self._book_started()
        with self.assertRaises(NotAuthorized):
            appointment_service.complete_appointment(actor=admin, appointment=appointment)

    def test_completed_appointment_still_occupies_slot(self):
        appointment = self._book_started()
        appointment_service.complete_appointment(actor=self.doctor_user, appointment=appointment)
        other_patient = _make_patient("clinops-patient2@example.com")

        from appointments.services.exceptions import SlotUnavailable

        with self.assertRaises(SlotUnavailable):
            hold_service.create_hold(
                actor=other_patient.person.user, doctor=self.doctor, clinic=self.clinic,
                start_at=appointment.start_at, end_at=appointment.end_at,
            )


class MarkNoShowTests(ClinicalOpsTestCase):
    def test_assigned_doctor_can_mark_no_show_after_grace_period(self):
        appointment = self._book()
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(minutes=2)
        )
        appointment.refresh_from_db()
        result = appointment_service.mark_no_show(actor=self.doctor_user, appointment=appointment)
        self.assertEqual(result.status, Appointment.Status.NO_SHOW)
        self.assertEqual(result.no_show_by_id, self.doctor.pk)
        self.assertIsNotNone(result.no_show_at)

    def test_no_show_requires_scheduled_start_to_have_passed(self):
        appointment = self._book()  # start_at is days in the future
        with self.assertRaises(NoShowNotAllowed):
            appointment_service.mark_no_show(actor=self.doctor_user, appointment=appointment)

    def test_no_show_requires_at_least_one_minute_grace(self):
        appointment = self._book()
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(seconds=30)
        )
        appointment.refresh_from_db()
        with self.assertRaises(NoShowNotAllowed):
            appointment_service.mark_no_show(actor=self.doctor_user, appointment=appointment)

    def test_no_show_frees_the_slot(self):
        appointment = self._book()
        original_start_at = appointment.start_at
        original_end_at = appointment.end_at
        # Shift only start_at into the past to satisfy the "≥1 minute since
        # scheduled start" precondition — end_at (and therefore the slot's
        # duration/alignment with the Availability grid) must stay intact,
        # so capture the original bounds above to re-book against below.
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(minutes=2)
        )
        appointment.refresh_from_db()
        appointment_service.mark_no_show(actor=self.doctor_user, appointment=appointment)
        other_patient = _make_patient("clinops-patient3@example.com")
        other_hold = hold_service.create_hold(
            actor=other_patient.person.user, doctor=self.doctor, clinic=self.clinic,
            start_at=original_start_at, end_at=original_end_at,
        )
        new_appointment = appointment_service.create_appointment_from_hold(
            actor=other_patient.person.user, hold=other_hold, patient=other_patient,
            doctor=self.doctor, clinic=self.clinic,
        )
        self.assertEqual(new_appointment.status, Appointment.Status.SCHEDULED)

    def test_no_show_not_automatic_requires_explicit_call(self):
        appointment = self._book()
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(hours=1)
        )
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)

    def test_patient_cannot_mark_no_show(self):
        appointment = self._book()
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(minutes=2)
        )
        appointment.refresh_from_db()
        with self.assertRaises(NotAuthorized):
            appointment_service.mark_no_show(actor=self.patient_user, appointment=appointment)

    def test_administrator_cannot_mark_no_show(self):
        admin = User.objects.create_superuser(email="clinops-admin3@example.com", password="s3cure-pass!")
        appointment = self._book()
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(minutes=2)
        )
        appointment.refresh_from_db()
        with self.assertRaises(NotAuthorized):
            appointment_service.mark_no_show(actor=admin, appointment=appointment)

    def test_cannot_mark_no_show_on_started_appointment(self):
        appointment = self._book()
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(minutes=2)
        )
        appointment.refresh_from_db()
        appointment_service.start_appointment(actor=self.doctor_user, appointment=appointment)
        with self.assertRaises(NoShowNotAllowed):
            appointment_service.mark_no_show(actor=self.doctor_user, appointment=appointment)


class ClinicalOpsConcurrencyTests(ClinicalOpsTestCase):
    """docs/phases/phase-2-agenda.md §27 — real concurrency: a doctor
    double-clicking "Iniciar consulta" from two tabs/devices at once."""

    def test_two_concurrent_start_calls_only_one_succeeds(self):
        appointment = self._book()
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                started = appointment_service.start_appointment(
                    actor=self.doctor_user, appointment=appointment
                )
                results[key] = ("success", started.pk)
            except AppointmentNotStartable:
                results[key] = ("not_startable", None)
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
        self.assertEqual(outcomes.count("not_startable"), 1, results)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.IN_CONSULTATION)

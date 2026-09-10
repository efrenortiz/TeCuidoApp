from datetime import date, datetime, time, timedelta, timezone as dt_timezone

from django.db import DataError, IntegrityError, transaction
from django.test import TestCase

from accounts.models import Person, User
from appointments.models import (
    Appointment,
    AppointmentRescheduleHistory,
    Availability,
    Hold,
    RequestReason,
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


def _make_clinic(name="Consultorio Centro", timezone="America/Mexico_City"):
    return Clinic.objects.create(name=name, timezone=timezone)


def _make_doctor_clinic(doctor, clinic, duration=60):
    return DoctorClinic.objects.create(
        doctor=doctor, clinic=clinic, appointment_duration_minutes=duration
    )


def _make_availability(doctor, clinic, day=date(2026, 9, 15), start=time(9, 0), end=time(13, 0), duration=60):
    return Availability.objects.create(
        doctor=doctor,
        clinic=clinic,
        date=day,
        start_time=start,
        end_time=end,
        duration_minutes=duration,
    )


class AvailabilityModelTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("avail-doc@example.com")
        self.clinic = _make_clinic()
        _make_doctor_clinic(self.doctor, self.clinic)

    def test_creates_and_computes_period(self):
        availability = _make_availability(self.doctor, self.clinic)
        # America/Mexico_City is UTC-6 year-round (no DST since 2022).
        self.assertEqual(
            availability.start_at.astimezone(dt_timezone.utc).isoformat(),
            "2026-09-15T15:00:00+00:00",
        )
        self.assertEqual(
            availability.end_at.astimezone(dt_timezone.utc).isoformat(),
            "2026-09-15T19:00:00+00:00",
        )
        self.assertTrue(availability.is_active)

    def test_start_time_must_be_before_end_time(self):
        # An inverted interval fails at PostgreSQL range-construction time
        # (DataError: "range lower bound must be less than or equal to
        # upper bound") before the CheckConstraint is even evaluated — the
        # CheckConstraint stays as a defense-in-depth backstop for any path
        # that doesn't go through save()/period. Either way, creation must
        # fail loudly.
        with self.assertRaises((IntegrityError, DataError)):
            with transaction.atomic():
                Availability.objects.create(
                    doctor=self.doctor,
                    clinic=self.clinic,
                    date=date(2026, 9, 15),
                    start_time=time(13, 0),
                    end_time=time(9, 0),
                    duration_minutes=60,
                )

    def test_duration_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Availability.objects.create(
                    doctor=self.doctor,
                    clinic=self.clinic,
                    date=date(2026, 9, 15),
                    start_time=time(9, 0),
                    end_time=time(10, 0),
                    duration_minutes=0,
                )

    def test_rejects_overlap_same_doctor_and_clinic(self):
        _make_availability(self.doctor, self.clinic, start=time(9, 0), end=time(13, 0))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                _make_availability(self.doctor, self.clinic, start=time(12, 0), end=time(15, 0))

    def test_rejects_overlap_same_doctor_different_clinic(self):
        # Decisión de cierre 2026-09-09: un médico no puede tener
        # disponibilidad simultánea en dos consultorios distintos.
        other_clinic = _make_clinic("Consultorio Norte")
        _make_doctor_clinic(self.doctor, other_clinic)
        _make_availability(self.doctor, self.clinic, start=time(9, 0), end=time(14, 0))

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                _make_availability(self.doctor, other_clinic, start=time(11, 0), end=time(14, 0))

    def test_allows_non_overlapping_different_clinics(self):
        other_clinic = _make_clinic("Consultorio Norte")
        _make_doctor_clinic(self.doctor, other_clinic)
        _make_availability(self.doctor, self.clinic, start=time(9, 0), end=time(14, 0))
        # Consecutive/disjoint — must not raise.
        _make_availability(self.doctor, other_clinic, start=time(16, 0), end=time(19, 0))

    def test_allows_consecutive_availabilities(self):
        _make_availability(self.doctor, self.clinic, start=time(9, 0), end=time(13, 0))
        # 13:00 start immediately after 13:00 end — semi-open interval, not
        # an overlap.
        _make_availability(self.doctor, self.clinic, start=time(13, 0), end=time(15, 0))

    def test_inactive_availability_does_not_block_overlap(self):
        existing = _make_availability(self.doctor, self.clinic, start=time(9, 0), end=time(13, 0))
        existing.is_active = False
        existing.save(update_fields=["is_active"])
        # Must not raise — inactive rows are excluded from the constraint.
        _make_availability(self.doctor, self.clinic, start=time(10, 0), end=time(12, 0))


class HoldModelTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("hold-doc@example.com")
        self.clinic = _make_clinic()
        _make_doctor_clinic(self.doctor, self.clinic)
        self.availability = _make_availability(self.doctor, self.clinic)
        self.user = User.objects.create_user(email="hold-user@example.com", password="s3cure-pass!")

    def _hold_kwargs(self, **overrides):
        start_at = datetime(2026, 9, 15, 15, 0, tzinfo=dt_timezone.utc)
        end_at = start_at + timedelta(hours=1)
        now = datetime.now(dt_timezone.utc)
        kwargs = dict(
            user=self.user,
            doctor=self.doctor,
            clinic=self.clinic,
            availability=self.availability,
            start_at=start_at,
            end_at=end_at,
            status=Hold.Status.ACTIVE,
            expires_at=now + timedelta(minutes=15),
        )
        kwargs.update(overrides)
        return kwargs

    def test_status_has_no_default_and_must_be_supplied_explicitly(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                kwargs = self._hold_kwargs()
                del kwargs["status"]
                Hold.objects.create(**kwargs)

    def test_creates_active_hold(self):
        hold = Hold.objects.create(**self._hold_kwargs())
        self.assertEqual(hold.status, Hold.Status.ACTIVE)
        self.assertIsNotNone(hold.period)

    def test_one_active_hold_per_user(self):
        Hold.objects.create(**self._hold_kwargs())
        other_availability = _make_availability(
            self.doctor, self.clinic, day=date(2026, 9, 16)
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Hold.objects.create(
                    **self._hold_kwargs(
                        availability=other_availability,
                        start_at=datetime(2026, 9, 16, 15, 0, tzinfo=dt_timezone.utc),
                        end_at=datetime(2026, 9, 16, 16, 0, tzinfo=dt_timezone.utc),
                    )
                )

    def test_two_users_cannot_hold_the_same_doctor_clinic_slot(self):
        Hold.objects.create(**self._hold_kwargs())
        other_user = User.objects.create_user(
            email="hold-user2@example.com", password="s3cure-pass!"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Hold.objects.create(**self._hold_kwargs(user=other_user))

    def test_non_active_holds_do_not_block_overlap(self):
        first = Hold.objects.create(**self._hold_kwargs())
        first.status = Hold.Status.RELEASED
        first.released_at = datetime.now(dt_timezone.utc)
        first.save(update_fields=["status", "released_at"])

        other_user = User.objects.create_user(
            email="hold-user3@example.com", password="s3cure-pass!"
        )
        # Must not raise — the first hold is no longer ACTIVE.
        Hold.objects.create(**self._hold_kwargs(user=other_user))


class AppointmentModelTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("appt-doc@example.com")
        self.clinic = _make_clinic()
        _make_doctor_clinic(self.doctor, self.clinic)
        self.availability = _make_availability(self.doctor, self.clinic)
        self.patient = _make_patient("appt-patient@example.com")
        self.creator = User.objects.create_user(
            email="appt-creator@example.com", password="s3cure-pass!"
        )

    def _appointment_kwargs(self, **overrides):
        start_at = datetime(2026, 9, 15, 15, 0, tzinfo=dt_timezone.utc)
        end_at = start_at + timedelta(hours=1)
        kwargs = dict(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            availability=self.availability,
            start_at=start_at,
            end_at=end_at,
            duration_minutes=60,
            status=Appointment.Status.SCHEDULED,
            created_by=self.creator,
        )
        kwargs.update(overrides)
        return kwargs

    def test_status_has_no_default_and_must_be_supplied_explicitly(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                kwargs = self._appointment_kwargs()
                del kwargs["status"]
                Appointment.objects.create(**kwargs)

    def test_creates_scheduled_appointment(self):
        appointment = Appointment.objects.create(**self._appointment_kwargs())
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)

    def test_cancelled_requires_full_trace(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    **self._appointment_kwargs(status=Appointment.Status.CANCELLED)
                )

    def test_cancelled_with_full_trace_is_valid(self):
        appointment = Appointment.objects.create(
            **self._appointment_kwargs(
                status=Appointment.Status.CANCELLED,
                cancelled_at=datetime.now(dt_timezone.utc),
                cancelled_by=self.creator,
                cancellation_reason=RequestReason.PATIENT_REQUEST,
            )
        )
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)

    def test_no_show_requires_trace(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    **self._appointment_kwargs(status=Appointment.Status.NO_SHOW)
                )

    def test_no_show_with_trace_is_valid(self):
        appointment = Appointment.objects.create(
            **self._appointment_kwargs(
                status=Appointment.Status.NO_SHOW,
                no_show_at=datetime.now(dt_timezone.utc),
                no_show_by=self.doctor,
            )
        )
        self.assertEqual(appointment.status, Appointment.Status.NO_SHOW)

    def test_rejects_doctor_double_booking(self):
        Appointment.objects.create(**self._appointment_kwargs())
        other_clinic = _make_clinic("Consultorio Norte")
        _make_doctor_clinic(self.doctor, other_clinic)
        other_availability = _make_availability(
            self.doctor, other_clinic, day=date(2026, 9, 15), start=time(15, 0), end=time(18, 0)
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    **self._appointment_kwargs(
                        clinic=other_clinic, availability=other_availability
                    )
                )

    def test_rejects_clinic_double_booking_with_different_doctor(self):
        Appointment.objects.create(**self._appointment_kwargs())
        other_doctor = _make_doctor("appt-doc2@example.com")
        _make_doctor_clinic(other_doctor, self.clinic)
        other_availability = _make_availability(
            other_doctor, self.clinic, day=date(2026, 9, 15), start=time(9, 0), end=time(18, 0)
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    **self._appointment_kwargs(
                        doctor=other_doctor, availability=other_availability
                    )
                )

    def test_cancelled_appointment_does_not_block_new_booking(self):
        first = Appointment.objects.create(
            **self._appointment_kwargs(
                status=Appointment.Status.CANCELLED,
                cancelled_at=datetime.now(dt_timezone.utc),
                cancelled_by=self.creator,
                cancellation_reason=RequestReason.PATIENT_REQUEST,
            )
        )
        # Same doctor/clinic/interval — must not raise, CANCELLED frees it.
        second = Appointment.objects.create(**self._appointment_kwargs())
        self.assertNotEqual(first.pk, second.pk)

    def test_idempotency_key_unique_per_creator(self):
        Appointment.objects.create(**self._appointment_kwargs(idempotency_key="abc-123"))
        other_availability = _make_availability(
            self.doctor, self.clinic, day=date(2026, 9, 16)
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    **self._appointment_kwargs(
                        availability=other_availability,
                        start_at=datetime(2026, 9, 16, 15, 0, tzinfo=dt_timezone.utc),
                        end_at=datetime(2026, 9, 16, 16, 0, tzinfo=dt_timezone.utc),
                        idempotency_key="abc-123",
                    )
                )

    def test_same_idempotency_key_allowed_for_different_creators(self):
        Appointment.objects.create(**self._appointment_kwargs(idempotency_key="shared-key"))
        other_creator = User.objects.create_user(
            email="appt-creator2@example.com", password="s3cure-pass!"
        )
        other_availability = _make_availability(
            self.doctor, self.clinic, day=date(2026, 9, 16)
        )
        # Must not raise — uniqueness is scoped per created_by.
        Appointment.objects.create(
            **self._appointment_kwargs(
                created_by=other_creator,
                availability=other_availability,
                start_at=datetime(2026, 9, 16, 15, 0, tzinfo=dt_timezone.utc),
                end_at=datetime(2026, 9, 16, 16, 0, tzinfo=dt_timezone.utc),
                idempotency_key="shared-key",
            )
        )


class AppointmentRescheduleHistoryModelTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("hist-doc@example.com")
        self.clinic = _make_clinic()
        _make_doctor_clinic(self.doctor, self.clinic)
        self.availability = _make_availability(self.doctor, self.clinic)
        self.patient = _make_patient("hist-patient@example.com")
        self.creator = User.objects.create_user(
            email="hist-creator@example.com", password="s3cure-pass!"
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            clinic=self.clinic,
            availability=self.availability,
            start_at=datetime(2026, 9, 15, 15, 0, tzinfo=dt_timezone.utc),
            end_at=datetime(2026, 9, 15, 16, 0, tzinfo=dt_timezone.utc),
            duration_minutes=60,
            status=Appointment.Status.SCHEDULED,
            created_by=self.creator,
        )

    def test_records_reschedule_history(self):
        entry = AppointmentRescheduleHistory.objects.create(
            appointment=self.appointment,
            old_clinic=self.clinic,
            old_date=date(2026, 9, 15),
            old_start_at=datetime(2026, 9, 15, 15, 0, tzinfo=dt_timezone.utc),
            old_end_at=datetime(2026, 9, 15, 16, 0, tzinfo=dt_timezone.utc),
            new_clinic=self.clinic,
            new_date=date(2026, 9, 18),
            new_start_at=datetime(2026, 9, 18, 12, 0, tzinfo=dt_timezone.utc),
            new_end_at=datetime(2026, 9, 18, 13, 0, tzinfo=dt_timezone.utc),
            rescheduled_by=self.creator,
            reason=RequestReason.PATIENT_REQUEST,
        )
        self.assertEqual(self.appointment.reschedule_history.count(), 1)
        self.assertEqual(entry.reason, RequestReason.PATIENT_REQUEST)

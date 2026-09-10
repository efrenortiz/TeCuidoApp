from datetime import date, datetime, time, timedelta, timezone as dt_timezone

from django.test import TestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment, Availability
from appointments.services import availability as availability_service
from appointments.services.exceptions import (
    AvailabilityBeyondBookingHorizon,
    AvailabilityConflict,
    AvailabilityHasAppointments,
    AvailabilityHasIncompatibleAppointments,
    AvailabilityNotFound,
    AvailabilityStartInPast,
    DoctorClinicRequired,
    InvalidAvailabilityInterval,
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


def _make_doctor_clinic(doctor, clinic, duration=60):
    return DoctorClinic.objects.create(
        doctor=doctor, clinic=clinic, appointment_duration_minutes=duration
    )


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class CreateAvailabilityTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("create-avail-doc@example.com")
        self.clinic = _make_clinic()
        _make_doctor_clinic(self.doctor, self.clinic)
        self.doctor_user = self.doctor.person.user

    def test_doctor_can_create_own_availability(self):
        availability = availability_service.create_availability(
            actor=self.doctor_user,
            doctor=self.doctor,
            clinic=self.clinic,
            date=_future_date(),
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        self.assertTrue(availability.is_active)
        self.assertEqual(availability.duration_minutes, 60)

    def test_administrator_can_create_availability_with_valid_doctorclinic(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="s3cure-pass!")
        availability = availability_service.create_availability(
            actor=admin,
            doctor=self.doctor,
            clinic=self.clinic,
            date=_future_date(),
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        self.assertTrue(availability.is_active)

    def test_administrator_without_doctorclinic_is_rejected(self):
        admin = User.objects.create_superuser(email="admin2@example.com", password="s3cure-pass!")
        other_clinic = _make_clinic("Consultorio Sin Relacion")
        with self.assertRaises(DoctorClinicRequired):
            availability_service.create_availability(
                actor=admin,
                doctor=self.doctor,
                clinic=other_clinic,
                date=_future_date(),
                start_time=time(9, 0),
                end_time=time(13, 0),
            )

    def test_other_doctor_cannot_create_for_this_doctor(self):
        other_doctor = _make_doctor("other-doc@example.com")
        with self.assertRaises(NotAuthorized):
            availability_service.create_availability(
                actor=other_doctor.person.user,
                doctor=self.doctor,
                clinic=self.clinic,
                date=_future_date(),
                start_time=time(9, 0),
                end_time=time(13, 0),
            )

    def test_patient_cannot_create_availability(self):
        patient = _make_patient("patient-noavail@example.com")
        with self.assertRaises(NotAuthorized):
            availability_service.create_availability(
                actor=patient.person.user,
                doctor=self.doctor,
                clinic=self.clinic,
                date=_future_date(),
                start_time=time(9, 0),
                end_time=time(13, 0),
            )

    def test_inactive_doctorclinic_is_rejected(self):
        dc = DoctorClinic.objects.get(doctor=self.doctor, clinic=self.clinic)
        dc.is_active = False
        dc.save(update_fields=["is_active"])
        with self.assertRaises(DoctorClinicRequired):
            availability_service.create_availability(
                actor=self.doctor_user,
                doctor=self.doctor,
                clinic=self.clinic,
                date=_future_date(),
                start_time=time(9, 0),
                end_time=time(13, 0),
            )

    def test_invalid_interval_is_rejected(self):
        with self.assertRaises(InvalidAvailabilityInterval):
            availability_service.create_availability(
                actor=self.doctor_user,
                doctor=self.doctor,
                clinic=self.clinic,
                date=_future_date(),
                start_time=time(13, 0),
                end_time=time(9, 0),
            )

    def test_start_in_the_past_is_rejected(self):
        with self.assertRaises(AvailabilityStartInPast):
            availability_service.create_availability(
                actor=self.doctor_user,
                doctor=self.doctor,
                clinic=self.clinic,
                date=(dj_timezone.now() - timedelta(days=1)).date(),
                start_time=time(9, 0),
                end_time=time(13, 0),
            )

    def test_beyond_six_calendar_months_is_rejected(self):
        today_local = dj_timezone.now().astimezone(self.clinic.zoneinfo).date()
        too_far = date(today_local.year, today_local.month, today_local.day) + timedelta(days=200)
        with self.assertRaises(AvailabilityBeyondBookingHorizon):
            availability_service.create_availability(
                actor=self.doctor_user,
                doctor=self.doctor,
                clinic=self.clinic,
                date=too_far,
                start_time=time(9, 0),
                end_time=time(13, 0),
            )

    def test_within_six_calendar_months_is_accepted(self):
        today_local = dj_timezone.now().astimezone(self.clinic.zoneinfo).date()
        # ~5 months out: safely inside the 6 calendar-month horizon, unlike
        # a naive 180-day check this must not reject it.
        five_months = date(
            today_local.year + (1 if today_local.month + 5 > 12 else 0),
            (today_local.month + 5 - 1) % 12 + 1,
            min(today_local.day, 28),
        )
        availability = availability_service.create_availability(
            actor=self.doctor_user,
            doctor=self.doctor,
            clinic=self.clinic,
            date=five_months,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        self.assertTrue(availability.is_active)

    def test_overlap_raises_availability_conflict(self):
        day = _future_date()
        availability_service.create_availability(
            actor=self.doctor_user,
            doctor=self.doctor,
            clinic=self.clinic,
            date=day,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        with self.assertRaises(AvailabilityConflict):
            availability_service.create_availability(
                actor=self.doctor_user,
                doctor=self.doctor,
                clinic=self.clinic,
                date=day,
                start_time=time(12, 0),
                end_time=time(15, 0),
            )


class UpdateAvailabilityTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("update-avail-doc@example.com")
        self.clinic = _make_clinic()
        _make_doctor_clinic(self.doctor, self.clinic)
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

    def _make_appointment(self, start_time, end_time, patient=None):
        patient = patient or _make_patient(f"update-avail-patient-{Patient.objects.count()}@example.com")
        creator = User.objects.create_user(
            email=f"update-avail-creator-{Appointment.objects.count()}@example.com",
            password="s3cure-pass!",
        )
        start_at = availability_service.combine_local(self.day, start_time, self.clinic)
        end_at = availability_service.combine_local(self.day, end_time, self.clinic)
        return Appointment.objects.create(
            patient=patient,
            doctor=self.doctor,
            clinic=self.clinic,
            availability=self.availability,
            start_at=start_at,
            end_at=end_at,
            duration_minutes=60,
            status=Appointment.Status.SCHEDULED,
            created_by=creator,
        )

    def test_compatible_modification_is_allowed_with_appointments(self):
        # Existing appointment 10:00-11:00; shrinking to 09:00-12:00 still
        # contains it — must succeed (availability-rules.md §19 example).
        self._make_appointment(time(10, 0), time(11, 0))
        updated = availability_service.update_availability(
            actor=self.doctor_user,
            availability=self.availability,
            date=self.day,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        self.assertEqual(updated.end_time, time(12, 0))

    def test_incompatible_modification_is_rejected(self):
        # Appointment at 12:00-13:00; shrinking to 09:00-12:00 would leave
        # it outside the new window — must be rejected.
        self._make_appointment(time(12, 0), time(13, 0))
        with self.assertRaises(AvailabilityHasIncompatibleAppointments):
            availability_service.update_availability(
                actor=self.doctor_user,
                availability=self.availability,
                date=self.day,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.end_time, time(13, 0))

    def test_modification_without_appointments_is_unrestricted(self):
        updated = availability_service.update_availability(
            actor=self.doctor_user,
            availability=self.availability,
            date=self.day,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        self.assertEqual(updated.start_time, time(10, 0))

    def test_other_doctor_cannot_modify(self):
        other_doctor = _make_doctor("update-avail-other@example.com")
        with self.assertRaises(NotAuthorized):
            availability_service.update_availability(
                actor=other_doctor.person.user,
                availability=self.availability,
                date=self.day,
                start_time=time(10, 0),
                end_time=time(11, 0),
            )


class DeactivateAvailabilityTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("deact-avail-doc@example.com")
        self.clinic = _make_clinic()
        _make_doctor_clinic(self.doctor, self.clinic)
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

    def test_deactivates_availability_without_appointments(self):
        deactivated = availability_service.deactivate_availability(
            actor=self.doctor_user, availability=self.availability
        )
        self.assertFalse(deactivated.is_active)

    def test_rejects_deactivation_with_any_appointment(self):
        patient = _make_patient("deact-avail-patient@example.com")
        creator = User.objects.create_user(
            email="deact-avail-creator@example.com", password="s3cure-pass!"
        )
        start_at = availability_service.combine_local(self.day, time(10, 0), self.clinic)
        Appointment.objects.create(
            patient=patient,
            doctor=self.doctor,
            clinic=self.clinic,
            availability=self.availability,
            start_at=start_at,
            end_at=start_at + timedelta(hours=1),
            duration_minutes=60,
            status=Appointment.Status.SCHEDULED,
            created_by=creator,
        )
        with self.assertRaises(AvailabilityHasAppointments):
            availability_service.deactivate_availability(
                actor=self.doctor_user, availability=self.availability
            )
        self.availability.refresh_from_db()
        self.assertTrue(self.availability.is_active)


class GetAvailableSlotsTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("slots-doc@example.com")
        self.clinic = _make_clinic()
        _make_doctor_clinic(self.doctor, self.clinic)
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        self.availability = availability_service.create_availability(
            actor=self.doctor_user,
            doctor=self.doctor,
            clinic=self.clinic,
            date=self.day,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )

    def test_generates_hourly_aligned_slots(self):
        slots = availability_service.get_available_slots(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic, date=self.day
        )
        self.assertEqual(len(slots), 3)
        for slot in slots:
            self.assertEqual(slot["status"], "AVAILABLE")
        self.assertEqual(
            (slots[1]["start"] - slots[0]["start"]).total_seconds(), 3600
        )

    def test_booked_slot_is_marked(self):
        patient = _make_patient("slots-patient@example.com")
        creator = User.objects.create_user(
            email="slots-creator@example.com", password="s3cure-pass!"
        )
        start_at = availability_service.combine_local(self.day, time(10, 0), self.clinic)
        Appointment.objects.create(
            patient=patient,
            doctor=self.doctor,
            clinic=self.clinic,
            availability=self.availability,
            start_at=start_at,
            end_at=start_at + timedelta(hours=1),
            duration_minutes=60,
            status=Appointment.Status.SCHEDULED,
            created_by=creator,
        )
        slots = availability_service.get_available_slots(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic, date=self.day
        )
        statuses = {slot["start"].astimezone(self.clinic.zoneinfo).time(): slot["status"] for slot in slots}
        self.assertEqual(statuses[time(10, 0)], "BOOKED")
        self.assertEqual(statuses[time(9, 0)], "AVAILABLE")

    def test_anonymous_actor_is_rejected(self):
        from django.contrib.auth.models import AnonymousUser

        with self.assertRaises(NotAuthorized):
            availability_service.get_available_slots(
                actor=AnonymousUser(), doctor=self.doctor, clinic=self.clinic, date=self.day
            )

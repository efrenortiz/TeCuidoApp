"""AvailabilityService (docs/design/agenda-service-contracts.md §5):
create/update/deactivate Availability and derive its slots. Slots are
never persisted (docs/design/booking-and-concurrency.md §2.2).
"""

import datetime as dt

from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone

from appointments.models import Appointment, Availability, Hold
from appointments.services.dates import add_months, combine_local
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
from appointments.services.permissions import can_manage_availability
from clinics.models import DoctorClinic

BOOKING_HORIZON_MONTHS = 6
LATE_BOOKING_GRACE_MINUTES = 30


def _validate_interval_and_horizon(*, date, start_time, end_time, clinic):
    if start_time >= end_time:
        raise InvalidAvailabilityInterval()

    start_at = combine_local(date, start_time, clinic)
    now = dj_timezone.now()
    if start_at <= now:
        raise AvailabilityStartInPast()

    today_local = now.astimezone(clinic.zoneinfo).date()
    horizon_date = add_months(today_local, BOOKING_HORIZON_MONTHS)
    if date > horizon_date:
        raise AvailabilityBeyondBookingHorizon()


def create_availability(*, actor, doctor, clinic, date, start_time, end_time):
    """docs/design/agenda-service-contracts.md §5.1."""
    if not can_manage_availability(actor, doctor=doctor):
        raise NotAuthorized()

    doctor_clinic = DoctorClinic.objects.filter(
        doctor=doctor, clinic=clinic, is_active=True
    ).first()
    if doctor_clinic is None:
        raise DoctorClinicRequired()

    _validate_interval_and_horizon(
        date=date, start_time=start_time, end_time=end_time, clinic=clinic
    )

    try:
        with transaction.atomic():
            return Availability.objects.create(
                doctor=doctor,
                clinic=clinic,
                date=date,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=doctor_clinic.appointment_duration_minutes,
                is_active=True,
            )
    except IntegrityError as exc:
        raise AvailabilityConflict() from exc


def update_availability(*, actor, availability, date, start_time, end_time):
    """docs/design/agenda-service-contracts.md §5.2 (corrected 2026-09-10):
    a compatible modification — one that still fully contains every
    existing occupying appointment — is allowed even when the
    availability already has appointments. Only an incompatible one is
    rejected."""
    if not can_manage_availability(actor, doctor=availability.doctor):
        raise NotAuthorized()
    if not availability.is_active:
        raise AvailabilityNotFound()

    _validate_interval_and_horizon(
        date=date, start_time=start_time, end_time=end_time, clinic=availability.clinic
    )

    new_start_at = combine_local(date, start_time, availability.clinic)
    new_end_at = combine_local(date, end_time, availability.clinic)

    with transaction.atomic():
        locked = Availability.objects.select_for_update().get(pk=availability.pk)

        occupying = locked.appointments.filter(status__in=Appointment.OCCUPYING_STATUSES)
        for appointment in occupying:
            if appointment.start_at < new_start_at or appointment.end_at > new_end_at:
                raise AvailabilityHasIncompatibleAppointments()

        locked.date = date
        locked.start_time = start_time
        locked.end_time = end_time
        try:
            locked.save(update_fields=["date", "start_time", "end_time", "start_at", "end_at", "period"])
        except IntegrityError as exc:
            raise AvailabilityConflict() from exc
        return locked


def deactivate_availability(*, actor, availability):
    """docs/design/agenda-service-contracts.md §5.3 — blanket rule: any
    occupying appointment at all blocks deactivation (unlike update, this
    is not about compatibility, it's binary)."""
    if not can_manage_availability(actor, doctor=availability.doctor):
        raise NotAuthorized()

    with transaction.atomic():
        locked = Availability.objects.select_for_update().get(pk=availability.pk)
        if locked.appointments.filter(status__in=Appointment.OCCUPYING_STATUSES).exists():
            raise AvailabilityHasAppointments()
        locked.is_active = False
        locked.save(update_fields=["is_active"])
        return locked


def get_available_slots(*, actor, doctor, clinic, date):
    """docs/design/agenda-service-contracts.md §5.4. Deliberately has no
    authorization gate beyond "actor autenticado" — the contract itself
    lists no `NotAuthorized` precondition for this read, unlike
    create/update/deactivate; slot visibility is how patients/responsables
    discover whom to book with."""
    if not getattr(actor, "is_authenticated", False):
        raise NotAuthorized()

    now = dj_timezone.now()
    slots = []

    availabilities = Availability.objects.filter(
        doctor=doctor, clinic=clinic, date=date, is_active=True
    ).order_by("start_time")

    occupying_appointments = list(
        Appointment.objects.filter(
            doctor=doctor,
            clinic=clinic,
            status__in=Appointment.OCCUPYING_STATUSES,
            start_at__date=date,
        )
    )
    active_holds = list(
        Hold.objects.filter(
            doctor=doctor, clinic=clinic, status=Hold.Status.ACTIVE, start_at__date=date
        ).filter(expires_at__gt=now)
    )

    for availability in availabilities:
        cursor = availability.start_at
        step = dt.timedelta(minutes=availability.duration_minutes)
        while cursor + step <= availability.end_at:
            slot_end = cursor + step
            status = _slot_status(cursor, slot_end, occupying_appointments, active_holds, now)
            slots.append({"start": cursor, "end": slot_end, "status": status})
            cursor = slot_end

    return slots


def _slot_status(start, end, appointments, holds, now):
    for appointment in appointments:
        if appointment.start_at < end and start < appointment.end_at:
            return "BOOKED"
    for hold in holds:
        if hold.start_at < end and start < hold.end_at:
            return "HELD"
    if now - start > dt.timedelta(minutes=LATE_BOOKING_GRACE_MINUTES):
        return "UNAVAILABLE"
    return "AVAILABLE"

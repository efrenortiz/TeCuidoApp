"""HoldService (docs/design/agenda-service-contracts.md §6,
docs/design/booking-and-concurrency.md): create/release a temporary slot
lock. Never a stage of appointment approval — purely a concurrency-
protection mechanism (docs/phases/phase-2-agenda.md §7.1).
"""

import datetime as dt

from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone

from appointments.models import Appointment, Availability, Hold
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
from appointments.services.permissions import can_initiate_booking

HOLD_DURATION_MINUTES = 15
LATE_BOOKING_GRACE_MINUTES = 30


def _find_containing_availability(*, doctor, clinic, start_at, end_at):
    """The active Availability whose window fully contains
    [start_at, end_at), or None."""
    return (
        Availability.objects.filter(
            doctor=doctor, clinic=clinic, is_active=True, start_at__lte=start_at, end_at__gte=end_at
        )
        .order_by("start_at")
        .first()
    )


def _slot_is_aligned(availability, start_at, end_at):
    step = dt.timedelta(minutes=availability.duration_minutes)
    if end_at - start_at != step:
        return False
    offset = start_at - availability.start_at
    return offset >= dt.timedelta(0) and offset % step == dt.timedelta(0)


def _expire_stale(queryset, *, now):
    """Lazily transition any ACTIVE-but-expired rows in `queryset` to
    EXPIRED. Called with a `select_for_update()`-locked queryset so the
    check-then-act is safe under concurrency (docs/design/
    booking-and-concurrency.md §12)."""
    for hold in queryset:
        if hold.status == Hold.Status.ACTIVE and hold.expires_at <= now:
            hold.status = Hold.Status.EXPIRED
            hold.save(update_fields=["status"])


@transaction.atomic
def create_hold(*, actor, doctor, clinic, start_at, end_at):
    """docs/design/agenda-service-contracts.md §6.1."""
    if not can_initiate_booking(actor, doctor=doctor, clinic=clinic):
        raise NotAuthorized()

    availability = _find_containing_availability(
        doctor=doctor, clinic=clinic, start_at=start_at, end_at=end_at
    )
    if availability is None:
        raise AvailabilityNotFound()
    if not _slot_is_aligned(availability, start_at, end_at):
        raise InvalidSlot()

    now = dj_timezone.now()
    if now - start_at > dt.timedelta(minutes=LATE_BOOKING_GRACE_MINUTES):
        raise BookingWindowExpired()

    # Lock + lazily expire this actor's own stale hold, and any stale
    # holds on the requested doctor+clinic, before re-checking conflicts —
    # `expires_at` can't live in the ExclusionConstraint (not IMMUTABLE),
    # so this is where expiry actually gets enforced transactionally.
    own_locked = list(
        Hold.objects.select_for_update()
        .filter(user=actor, status=Hold.Status.ACTIVE)
    )
    _expire_stale(own_locked, now=now)
    if Hold.objects.filter(user=actor, status=Hold.Status.ACTIVE).exists():
        raise HoldAlreadyExists()

    slot_locked = list(
        Hold.objects.select_for_update().filter(
            doctor=doctor, clinic=clinic, status=Hold.Status.ACTIVE, start_at__lt=end_at, end_at__gt=start_at
        )
    )
    _expire_stale(slot_locked, now=now)
    if Hold.objects.filter(
        doctor=doctor, clinic=clinic, status=Hold.Status.ACTIVE, start_at__lt=end_at, end_at__gt=start_at
    ).exists():
        raise HoldConflict()

    if Appointment.objects.filter(
        doctor=doctor,
        clinic=clinic,
        status__in=Appointment.OCCUPYING_STATUSES,
        start_at__lt=end_at,
        end_at__gt=start_at,
    ).exists():
        raise SlotUnavailable()

    try:
        return Hold.objects.create(
            user=actor,
            doctor=doctor,
            clinic=clinic,
            availability=availability,
            start_at=start_at,
            end_at=end_at,
            status=Hold.Status.ACTIVE,
            expires_at=now + dt.timedelta(minutes=HOLD_DURATION_MINUTES),
        )
    except IntegrityError as exc:
        # Lost a race against a concurrent create_hold() for the exact
        # same interval that committed between our check and our insert.
        raise HoldConflict() from exc


@transaction.atomic
def release_hold(*, actor, hold):
    """docs/design/agenda-service-contracts.md §6.2."""
    locked = Hold.objects.select_for_update().filter(pk=hold.pk).first()
    if locked is None:
        raise HoldNotFound()
    if locked.user_id != actor.id:
        raise HoldNotOwned()
    if locked.status != Hold.Status.ACTIVE:
        raise HoldNotActive()

    locked.status = Hold.Status.RELEASED
    locked.released_at = dj_timezone.now()
    locked.save(update_fields=["status", "released_at"])
    return locked


def mark_consumed(hold, *, now=None):
    """Transitions a hold to CONSUMED as part of creating its Appointment
    (Etapa 4 / `AppointmentService.create_appointment_from_hold`). Must be
    called from within the same `transaction.atomic()` block that creates
    the Appointment — this function does not open its own transaction."""
    hold.status = Hold.Status.CONSUMED
    hold.consumed_at = now or dj_timezone.now()
    hold.save(update_fields=["status", "consumed_at"])
    return hold

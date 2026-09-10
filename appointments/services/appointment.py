"""AppointmentService (docs/design/agenda-service-contracts.md §7):
create/cancel/reschedule/start/complete/NO_SHOW (Etapas 4-6 — all of
AppointmentService is now implemented).
"""

import datetime as dt

from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone

from appointments.models import (
    Appointment,
    AppointmentRescheduleHistory,
    Availability,
    Hold,
    RequestReason,
)
from appointments.services.exceptions import (
    AppointmentAlreadyCancelled,
    AppointmentConflict,
    AppointmentNotCancellable,
    AppointmentNotCompletable,
    AppointmentNotFound,
    AppointmentNotReschedulable,
    AppointmentNotStartable,
    DurationIncompatible,
    HoldExpired,
    HoldNotFound,
    HoldNotOwned,
    IdempotencyKeyConflict,
    InvalidDoctorClinic,
    InvalidPatient,
    NoShowNotAllowed,
    NotAuthorized,
    SlotUnavailable,
)
from appointments.services.hold import mark_consumed
from appointments.services.permissions import (
    can_book_for_patient,
    can_initiate_booking,
    can_manage_appointment,
    can_view_appointment,
    doctor_profile,
    is_administrator,
    is_assigned_doctor,
    patient_profile,
    responsible_profile,
)
from clinics.models import DoctorClinic
from patients.models import ResponsiblePatientRelationship

NO_SHOW_MIN_MINUTES_AFTER_START = 1


def _idempotent_replay_matches(existing, *, hold, patient, doctor, clinic):
    return (
        existing.patient_id == patient.pk
        and existing.doctor_id == doctor.pk
        and existing.clinic_id == clinic.pk
        and existing.start_at == hold.start_at
        and existing.end_at == hold.end_at
    )


@transaction.atomic
def create_appointment_from_hold(*, actor, hold, patient, doctor, clinic, idempotency_key=""):
    """docs/design/agenda-service-contracts.md §7.1."""
    if idempotency_key:
        existing = Appointment.objects.filter(
            created_by=actor, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            if not _idempotent_replay_matches(
                existing, hold=hold, patient=patient, doctor=doctor, clinic=clinic
            ):
                raise IdempotencyKeyConflict()
            return existing

    if not can_initiate_booking(actor, doctor=doctor, clinic=clinic):
        raise NotAuthorized()

    locked_hold = Hold.objects.select_for_update().filter(pk=hold.pk).first()
    if locked_hold is None:
        raise HoldNotFound()
    if locked_hold.user_id != actor.id:
        raise HoldNotOwned()
    if locked_hold.doctor_id != doctor.pk or locked_hold.clinic_id != clinic.pk:
        # docs/design/agenda-api-contracts.md §18 — never trust a
        # client-supplied doctor/clinic that contradicts the hold itself.
        raise InvalidDoctorClinic()

    now = dj_timezone.now()
    if locked_hold.status != Hold.Status.ACTIVE or locked_hold.expires_at <= now:
        if locked_hold.status == Hold.Status.ACTIVE:
            locked_hold.status = Hold.Status.EXPIRED
            locked_hold.save(update_fields=["status"])
        elif idempotency_key:
            # A concurrent request with the exact same idempotency_key may
            # have already consumed this hold and created the Appointment
            # between our earlier (unlocked) idempotency check and
            # acquiring the hold lock here — replay it instead of failing.
            existing = Appointment.objects.filter(
                created_by=actor, idempotency_key=idempotency_key
            ).first()
            if existing is not None and _idempotent_replay_matches(
                existing, hold=locked_hold, patient=patient, doctor=doctor, clinic=clinic
            ):
                return existing
        raise HoldExpired()

    if not can_book_for_patient(actor, patient=patient):
        raise InvalidPatient()

    # Re-validate disponibilidad (step 2 of the transactional operation,
    # §7.1): the hold's Availability may have been deactivated, or
    # modified to a narrower window, since the hold was created.
    availability = Availability.objects.select_for_update().filter(
        pk=locked_hold.availability_id
    ).first()
    if (
        availability is None
        or not availability.is_active
        or availability.start_at > locked_hold.start_at
        or availability.end_at < locked_hold.end_at
    ):
        raise SlotUnavailable()

    # Re-validate conflicts (step 3) — defense in depth; the
    # ExclusionConstraint below is the final authority.
    conflict_exists = Appointment.objects.filter(
        doctor=doctor,
        clinic=clinic,
        status__in=Appointment.OCCUPYING_STATUSES,
        start_at__lt=locked_hold.end_at,
        end_at__gt=locked_hold.start_at,
    ).exists()
    if conflict_exists:
        raise SlotUnavailable()

    try:
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            clinic=clinic,
            availability=availability,
            start_at=locked_hold.start_at,
            end_at=locked_hold.end_at,
            duration_minutes=availability.duration_minutes,
            status=Appointment.Status.SCHEDULED,
            created_by=actor,
            idempotency_key=idempotency_key,
        )
    except IntegrityError as exc:
        raise AppointmentConflict() from exc

    mark_consumed(locked_hold, now=now)
    return appointment


def _require_valid_reason(reason):
    if reason not in RequestReason.values:
        raise ValueError(f"reason must be one of {RequestReason.values!r}, got {reason!r}")


@transaction.atomic
def cancel_appointment(*, actor, appointment, reason):
    """docs/design/agenda-service-contracts.md §7.2."""
    _require_valid_reason(reason)

    locked = Appointment.objects.select_for_update().filter(pk=appointment.pk).first()
    if locked is None:
        raise AppointmentNotFound()

    if not can_manage_appointment(actor, appointment=locked):
        raise NotAuthorized()

    if locked.status == Appointment.Status.CANCELLED:
        raise AppointmentAlreadyCancelled()

    now = dj_timezone.now()
    if locked.status != Appointment.Status.SCHEDULED or locked.start_at <= now:
        raise AppointmentNotCancellable()

    locked.status = Appointment.Status.CANCELLED
    locked.cancelled_at = now
    locked.cancelled_by = actor
    locked.cancellation_reason = reason
    locked.save()
    return locked


def _find_containing_availability_for_reschedule(*, doctor, clinic, start_at, end_at):
    return (
        Availability.objects.select_for_update()
        .filter(doctor=doctor, clinic=clinic, is_active=True, start_at__lte=start_at, end_at__gte=end_at)
        .order_by("start_at")
        .first()
    )


def _slot_is_aligned(availability, start_at, end_at):
    step = dt.timedelta(minutes=availability.duration_minutes)
    if end_at - start_at != step:
        return False
    offset = start_at - availability.start_at
    return offset >= dt.timedelta(0) and offset % step == dt.timedelta(0)


@transaction.atomic
def reschedule_appointment(*, actor, appointment, new_clinic, new_start_at, reason, idempotency_key=""):
    """docs/design/agenda-service-contracts.md §7.3."""
    _require_valid_reason(reason)

    if idempotency_key:
        existing_history = AppointmentRescheduleHistory.objects.filter(
            rescheduled_by=actor, idempotency_key=idempotency_key
        ).first()
        if existing_history is not None:
            if (
                existing_history.appointment_id != appointment.pk
                or existing_history.new_clinic_id != new_clinic.pk
                or existing_history.new_start_at != new_start_at
            ):
                raise IdempotencyKeyConflict()
            return Appointment.objects.get(pk=existing_history.appointment_id)

    locked = Appointment.objects.select_for_update().filter(pk=appointment.pk).first()
    if locked is None:
        raise AppointmentNotFound()

    if not can_manage_appointment(actor, appointment=locked):
        raise NotAuthorized()

    now = dj_timezone.now()
    if locked.status != Appointment.Status.SCHEDULED or locked.start_at <= now:
        raise AppointmentNotReschedulable()

    new_end_at = new_start_at + dt.timedelta(minutes=locked.duration_minutes)

    if not DoctorClinic.objects.filter(doctor=locked.doctor, clinic=new_clinic, is_active=True).exists():
        raise InvalidDoctorClinic()

    availability = _find_containing_availability_for_reschedule(
        doctor=locked.doctor, clinic=new_clinic, start_at=new_start_at, end_at=new_end_at
    )
    if availability is None:
        raise SlotUnavailable()

    if availability.duration_minutes != locked.duration_minutes:
        raise DurationIncompatible()

    if not _slot_is_aligned(availability, new_start_at, new_end_at):
        raise SlotUnavailable()

    conflict_exists = (
        Appointment.objects.filter(
            doctor=locked.doctor,
            clinic=new_clinic,
            status__in=Appointment.OCCUPYING_STATUSES,
            start_at__lt=new_end_at,
            end_at__gt=new_start_at,
        )
        .exclude(pk=locked.pk)
        .exists()
    )
    if conflict_exists:
        raise SlotUnavailable()

    old_clinic = locked.clinic
    old_date = locked.start_at.astimezone(old_clinic.zoneinfo).date()
    old_start_at = locked.start_at
    old_end_at = locked.end_at

    locked.clinic = new_clinic
    locked.availability = availability
    locked.start_at = new_start_at
    locked.end_at = new_end_at
    try:
        # Nested atomic() = SAVEPOINT: an IntegrityError here must not
        # poison the outer transaction, since the except branch below
        # needs to keep querying on the same connection.
        with transaction.atomic():
            locked.save()
    except IntegrityError as exc:
        raise SlotUnavailable() from exc

    try:
        with transaction.atomic():
            AppointmentRescheduleHistory.objects.create(
                appointment=locked,
                old_clinic=old_clinic,
                old_date=old_date,
                old_start_at=old_start_at,
                old_end_at=old_end_at,
                new_clinic=new_clinic,
                new_date=new_start_at.astimezone(new_clinic.zoneinfo).date(),
                new_start_at=new_start_at,
                new_end_at=new_end_at,
                rescheduled_by=actor,
                reason=reason,
                idempotency_key=idempotency_key,
            )
    except IntegrityError as exc:
        # Lost a race against a concurrent identical retry that already
        # recorded this exact idempotency_key — replay its result instead
        # of surfacing a raw uniqueness violation.
        if idempotency_key:
            existing_history = AppointmentRescheduleHistory.objects.filter(
                rescheduled_by=actor, idempotency_key=idempotency_key
            ).first()
            if (
                existing_history is not None
                and existing_history.appointment_id == locked.pk
                and existing_history.new_clinic_id == new_clinic.pk
                and existing_history.new_start_at == new_start_at
            ):
                return locked
        raise IdempotencyKeyConflict() from exc

    return locked


@transaction.atomic
def start_appointment(*, actor, appointment):
    """docs/design/agenda-service-contracts.md §7.4."""
    locked = Appointment.objects.select_for_update().filter(pk=appointment.pk).first()
    if locked is None:
        raise AppointmentNotFound()

    if not is_assigned_doctor(actor, appointment=locked):
        raise NotAuthorized()

    if locked.status != Appointment.Status.SCHEDULED:
        raise AppointmentNotStartable()

    locked.status = Appointment.Status.IN_CONSULTATION
    locked.started_at = dj_timezone.now()
    locked.started_by = locked.doctor
    locked.save()
    return locked


@transaction.atomic
def complete_appointment(*, actor, appointment):
    """docs/design/agenda-service-contracts.md §7.5."""
    locked = Appointment.objects.select_for_update().filter(pk=appointment.pk).first()
    if locked is None:
        raise AppointmentNotFound()

    if not is_assigned_doctor(actor, appointment=locked):
        raise NotAuthorized()

    if locked.status != Appointment.Status.IN_CONSULTATION:
        raise AppointmentNotCompletable()

    locked.status = Appointment.Status.COMPLETED
    locked.completed_at = dj_timezone.now()
    locked.completed_by = locked.doctor
    locked.save()
    return locked


@transaction.atomic
def mark_no_show(*, actor, appointment):
    """docs/design/agenda-service-contracts.md §7.6."""
    locked = Appointment.objects.select_for_update().filter(pk=appointment.pk).first()
    if locked is None:
        raise AppointmentNotFound()

    if not is_assigned_doctor(actor, appointment=locked):
        raise NotAuthorized()

    if locked.status != Appointment.Status.SCHEDULED:
        raise NoShowNotAllowed()

    now = dj_timezone.now()
    if now - locked.start_at < dt.timedelta(minutes=NO_SHOW_MIN_MINUTES_AFTER_START):
        raise NoShowNotAllowed()

    locked.status = Appointment.Status.NO_SHOW
    locked.no_show_at = now
    locked.no_show_by = locked.doctor
    locked.save()
    return locked


def _scoped_appointments_queryset(actor):
    """The authorized ámbito of Appointments for `actor` (docs/design/
    agenda-permissions.md §10) — filters passed by a caller only ever
    narrow this, never replace it (docs/design/agenda-api-contracts.md
    §7.2: knowing a patient_id/doctor_id/clinic_id never grants access on
    its own)."""
    patient_actor = patient_profile(actor)
    if patient_actor is not None:
        return Appointment.objects.filter(patient=patient_actor)

    responsible = responsible_profile(actor)
    if responsible is not None:
        patient_ids = ResponsiblePatientRelationship.objects.filter(
            responsible=responsible, status=ResponsiblePatientRelationship.Status.ACTIVE
        ).values_list("patient_id", flat=True)
        return Appointment.objects.filter(patient_id__in=patient_ids)

    doctor_actor = doctor_profile(actor)
    if doctor_actor is not None:
        return Appointment.objects.filter(doctor=doctor_actor)

    if is_administrator(actor):
        return Appointment.objects.all()

    return Appointment.objects.none()


def list_appointments_for_actor(
    actor, *, status=None, date_from=None, date_to=None, patient_id=None, doctor_id=None, clinic_id=None
):
    """docs/design/agenda-service-contracts.md §12 read counterpart /
    agenda-api-contracts.md §7.2 — not a mutation, so no `transaction.atomic()`."""
    qs = _scoped_appointments_queryset(actor)

    if status:
        qs = qs.filter(status=status)
    if date_from is not None:
        qs = qs.filter(start_at__date__gte=date_from)
    if date_to is not None:
        qs = qs.filter(start_at__date__lte=date_to)
    if patient_id is not None:
        qs = qs.filter(patient_id=patient_id)
    if doctor_id is not None:
        qs = qs.filter(doctor_id=doctor_id)
    if clinic_id is not None:
        qs = qs.filter(clinic_id=clinic_id)

    return qs.order_by("-start_at")


def get_appointment_detail(actor, *, appointment_id):
    """docs/design/agenda-api-contracts.md §7.3. Raises `AppointmentNotFound`
    both when the row doesn't exist and when `actor` isn't authorized to
    view it — deliberately indistinguishable, per §13's 404 definition
    ('el recurso no existe o no debe revelarse al actor')."""
    appointment = Appointment.objects.filter(pk=appointment_id).first()
    if appointment is None or not can_view_appointment(actor, appointment=appointment):
        raise AppointmentNotFound()
    return appointment

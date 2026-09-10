"""Agenda domain models (Fase 2). Contract: docs/phases/phase-2-agenda.md,
docs/design/appointment-domain.md, docs/design/availability-rules.md,
docs/design/booking-and-concurrency.md.

Design notes that explain choices that aren't obvious from the fields
alone:

- `Availability`/`Hold`/`Appointment` each store both the business-facing
  fields (`date`/`start_time`/`end_time`, or plain `start_at`/`end_at`) AND
  a `period` `DateTimeRangeField`. `period` exists purely so PostgreSQL can
  enforce non-overlap via `ExclusionConstraint` — it is always kept in
  sync with `start_at`/`end_at` in `save()`, never edited directly.
- `Availability.period` is keyed only by `doctor` (not `doctor+clinic`):
  "no two Availability rows for the same doctor may overlap, regardless of
  clinic" is strictly stronger than "no overlap within the same
  doctor+clinic", so one constraint covers both rules from
  availability-rules.md §10/§11.
- No status field here has a `default=` — every creation path must state
  it explicitly (deny-by-default, same reasoning applied throughout this
  project to `ResponsiblePatientRelationship.status` and `Patient.regime`).
- Slots are never persisted (`docs/design/booking-and-concurrency.md` §2.2)
  — there is deliberately no `Slot` model here.
"""

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.backends.postgresql.psycopg_any import DateTimeTZRange

from appointments.services.dates import combine_local


class RequestReason(models.TextChoices):
    """Shared by Appointment.cancellation_reason and
    AppointmentRescheduleHistory.reason (phase-2-agenda.md §11.3/§12.4 use
    the identical set for both)."""

    PATIENT_REQUEST = "PATIENT_REQUEST", "Solicitud del paciente"
    RESPONSIBLE_REQUEST = "RESPONSIBLE_REQUEST", "Solicitud del responsable"
    DOCTOR_REQUEST = "DOCTOR_REQUEST", "Solicitud del médico"
    CLINIC_REQUEST = "CLINIC_REQUEST", "Solicitud del consultorio"
    OTHER = "OTHER", "Otro"


class Availability(models.Model):
    """A concrete date/time window in which a doctor offers care at a
    clinic (docs/design/availability-rules.md). Never recurring."""

    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.PROTECT, related_name="availabilities"
    )
    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.PROTECT, related_name="availabilities"
    )

    date = models.DateField("fecha")
    start_time = models.TimeField("hora de inicio")
    end_time = models.TimeField("hora de fin")

    # UTC-aware equivalents of date+start_time/end_time in clinic.timezone —
    # computed in save(), never set directly by callers. Exist only so
    # PostgreSQL can enforce non-overlap (see `period` below).
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    period = DateTimeRangeField()

    # Frozen at creation from DoctorClinic.appointment_duration_minutes —
    # docs/design/availability-rules.md §4 "Duración congelada".
    duration_minutes = models.PositiveIntegerField("duración (minutos)")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "disponibilidad"
        verbose_name_plural = "disponibilidades"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_time__lt=models.F("end_time")),
                name="availability_start_before_end",
            ),
            models.CheckConstraint(
                condition=models.Q(duration_minutes__gt=0),
                name="availability_duration_positive",
            ),
            # Covers both "no solapamiento dentro de Doctor+Clinic" and "no
            # solapamiento del médico entre consultorios distintos"
            # (availability-rules.md §10/§11) — doctor-only is the
            # stronger rule and subsumes the same-clinic case.
            ExclusionConstraint(
                name="availability_doctor_no_overlap",
                expressions=[
                    ("period", RangeOperators.OVERLAPS),
                    ("doctor", RangeOperators.EQUAL),
                ],
                condition=models.Q(is_active=True),
            ),
        ]

    def save(self, *args, **kwargs):
        self.start_at = combine_local(self.date, self.start_time, self.clinic)
        self.end_at = combine_local(self.date, self.end_time, self.clinic)
        self.period = DateTimeTZRange(self.start_at, self.end_at, bounds="[)")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.doctor} @ {self.clinic} {self.date} {self.start_time}-{self.end_time}"


class Hold(models.Model):
    """Temporary lock on a slot while an authorized user completes a
    reservation (docs/design/booking-and-concurrency.md). Never a stage
    of appointment approval."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        EXPIRED = "EXPIRED", "Expirado"
        RELEASED = "RELEASED", "Liberado"
        CONSUMED = "CONSUMED", "Consumido"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agenda_holds"
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.PROTECT, related_name="holds"
    )
    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.PROTECT, related_name="holds"
    )
    availability = models.ForeignKey(
        Availability, on_delete=models.PROTECT, related_name="holds"
    )

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    period = DateTimeRangeField()

    # No default — every hold is created ACTIVE by the service that
    # creates it, stated explicitly, same convention as elsewhere.
    status = models.CharField(max_length=10, choices=Status.choices)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    released_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "bloqueo temporal"
        verbose_name_plural = "bloqueos temporales"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["ACTIVE", "EXPIRED", "RELEASED", "CONSUMED"]),
                name="hold_status_valid",
            ),
            # One ACTIVE hold per user (booking-and-concurrency.md §9).
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="ACTIVE"),
                name="hold_one_active_per_user",
            ),
            # Hard DB guarantee against two ACTIVE holds on the same
            # doctor+clinic+interval. Deliberately does not reference
            # `expires_at` (PostgreSQL exclusion constraints require
            # immutable predicates; `now()` isn't one) — expiry is instead
            # re-validated transactionally by the service on every read
            # (booking-and-concurrency.md §12).
            ExclusionConstraint(
                name="hold_active_no_doctor_clinic_overlap",
                expressions=[
                    ("period", RangeOperators.OVERLAPS),
                    ("doctor", RangeOperators.EQUAL),
                    ("clinic", RangeOperators.EQUAL),
                ],
                condition=models.Q(status="ACTIVE"),
            ),
        ]

    def save(self, *args, **kwargs):
        self.period = DateTimeTZRange(self.start_at, self.end_at, bounds="[)")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Hold({self.user}, {self.doctor}, {self.start_at}, {self.status})"


class Appointment(models.Model):
    """A scheduled encounter (docs/design/appointment-domain.md). Never
    represents the clinical encounter itself — that's Fase 3."""

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Programada"
        IN_CONSULTATION = "IN_CONSULTATION", "En consulta"
        COMPLETED = "COMPLETED", "Atendida"
        CANCELLED = "CANCELLED", "Cancelada"
        NO_SHOW = "NO_SHOW", "No se presentó"

    # Statuses that still occupy the doctor/clinic for exclusion purposes —
    # CANCELLED/NO_SHOW free the slot immediately (phase-2-agenda.md §11.4).
    OCCUPYING_STATUSES = [Status.SCHEDULED, Status.IN_CONSULTATION, Status.COMPLETED]

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="appointments"
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.PROTECT, related_name="appointments"
    )
    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.PROTECT, related_name="appointments"
    )
    availability = models.ForeignKey(
        Availability, on_delete=models.PROTECT, related_name="appointments"
    )

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    period = DateTimeRangeField()
    duration_minutes = models.PositiveIntegerField("duración (minutos)")

    # No default — deny-by-default, same convention as `status` elsewhere.
    status = models.CharField(max_length=20, choices=Status.choices)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="appointments_created"
    )
    # Idempotency (docs/design/booking-and-concurrency.md §18,
    # agenda-api-contracts.md §15) — scoped per creator so two different
    # users can't collide on the same key.
    idempotency_key = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="appointments_cancelled",
    )
    cancellation_reason = models.CharField(
        max_length=20, choices=RequestReason.choices, blank=True
    )

    no_show_at = models.DateTimeField(null=True, blank=True)
    no_show_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="appointments_marked_no_show",
    )

    started_at = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="appointments_started",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="appointments_completed",
    )

    class Meta:
        verbose_name = "cita"
        verbose_name_plural = "citas"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "SCHEDULED",
                        "IN_CONSULTATION",
                        "COMPLETED",
                        "CANCELLED",
                        "NO_SHOW",
                    ]
                ),
                name="appointment_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(duration_minutes__gt=0),
                name="appointment_duration_positive",
            ),
            # CANCELLED requires its trace, mirroring
            # ResponsiblePatientRelationship's deactivation-info pattern.
            models.CheckConstraint(
                condition=~models.Q(status="CANCELLED")
                | (
                    models.Q(cancelled_at__isnull=False)
                    & models.Q(cancelled_by__isnull=False)
                    & ~models.Q(cancellation_reason="")
                ),
                name="appointment_cancelled_requires_trace",
            ),
            models.CheckConstraint(
                condition=~models.Q(status="NO_SHOW")
                | (models.Q(no_show_at__isnull=False) & models.Q(no_show_by__isnull=False)),
                name="appointment_no_show_requires_trace",
            ),
            models.UniqueConstraint(
                fields=["created_by", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="appointment_idempotency_key_unique",
            ),
            # Hard DB guarantees against double-booking — doctor and
            # clinic are each protected independently
            # (booking-and-concurrency.md §23). Nested/sibling class
            # attributes aren't visible by name inside Meta.constraints
            # (class bodies aren't a closure — same reason `OCCUPYING_STATUSES`
            # can't be referenced here directly); these three literal
            # strings must keep matching OCCUPYING_STATUSES above.
            ExclusionConstraint(
                name="appointment_doctor_no_overlap",
                expressions=[
                    ("period", RangeOperators.OVERLAPS),
                    ("doctor", RangeOperators.EQUAL),
                ],
                condition=models.Q(status__in=["SCHEDULED", "IN_CONSULTATION", "COMPLETED"]),
            ),
            ExclusionConstraint(
                name="appointment_clinic_no_overlap",
                expressions=[
                    ("period", RangeOperators.OVERLAPS),
                    ("clinic", RangeOperators.EQUAL),
                ],
                condition=models.Q(status__in=["SCHEDULED", "IN_CONSULTATION", "COMPLETED"]),
            ),
        ]

    def save(self, *args, **kwargs):
        self.period = DateTimeTZRange(self.start_at, self.end_at, bounds="[)")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} @ {self.doctor} {self.start_at} ({self.status})"


class AppointmentRescheduleHistory(models.Model):
    """One row per reprogramación (docs/design/appointment-domain.md §11.1)
    — `RESCHEDULED` is never a state of `Appointment`, only history."""

    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="reschedule_history"
    )

    old_clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.PROTECT, related_name="+"
    )
    old_date = models.DateField()
    old_start_at = models.DateTimeField()
    old_end_at = models.DateTimeField()

    new_clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.PROTECT, related_name="+"
    )
    new_date = models.DateField()
    new_start_at = models.DateTimeField()
    new_end_at = models.DateTimeField()

    rescheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    rescheduled_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=20, choices=RequestReason.choices)
    idempotency_key = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "historial de reprogramación"
        verbose_name_plural = "historial de reprogramaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["rescheduled_by", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="reschedule_idempotency_key_unique",
            ),
        ]
        ordering = ["-rescheduled_at"]

    def __str__(self):
        return f"Reschedule({self.appointment_id}, {self.old_start_at} -> {self.new_start_at})"

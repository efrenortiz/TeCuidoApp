import zoneinfo

from django.core.exceptions import ValidationError
from django.db import models


def validate_timezone(value):
    try:
        zoneinfo.ZoneInfo(value)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ValidationError("%(value)s no es una zona horaria IANA válida.", params={"value": value})


class Clinic(models.Model):
    """A physical clinic/consultorio (Fase 1: administrative info only)."""

    name = models.CharField("nombre", max_length=150)
    description = models.TextField("descripción", blank=True)
    address = models.CharField("dirección", max_length=255, blank=True)
    phone = models.CharField("teléfono", max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    # Agenda (Fase 2) business timezone — docs/phases/phase-2-agenda.md §5.9:
    # availability/appointment dates and times are always interpreted in the
    # Clinic's own timezone, never the server's or the requester's.
    timezone = models.CharField(
        "zona horaria",
        max_length=64,
        default="America/Mexico_City",
        validators=[validate_timezone],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "consultorio"
        verbose_name_plural = "consultorios"

    def __str__(self):
        return self.name

    @property
    def zoneinfo(self):
        return zoneinfo.ZoneInfo(self.timezone)


class DoctorClinic(models.Model):
    """Explicit Doctor <-> Clinic relationship (a doctor may work at several
    clinics; a clinic may host several doctors)."""

    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.CASCADE, related_name="clinic_relationships"
    )
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name="doctor_relationships"
    )
    is_active = models.BooleanField(default=True)

    # Agenda (Fase 2) — docs/design/appointment-domain.md §4: the default
    # appointment duration for this doctor+clinic combination. A new
    # Availability freezes this value at creation time; changing it later
    # never reinterprets existing Availability/Appointment rows.
    appointment_duration_minutes = models.PositiveIntegerField(
        "duración de citas (minutos)", default=60
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "relación médico-consultorio"
        verbose_name_plural = "relaciones médico-consultorio"
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "clinic"], name="unique_doctor_clinic"
            )
        ]

    def __str__(self):
        return f"{self.doctor} @ {self.clinic}"

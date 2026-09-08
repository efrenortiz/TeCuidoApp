from django.db import models


class Clinic(models.Model):
    """A physical clinic/consultorio (Fase 1: administrative info only)."""

    name = models.CharField("nombre", max_length=150)
    description = models.TextField("descripción", blank=True)
    address = models.CharField("dirección", max_length=255, blank=True)
    phone = models.CharField("teléfono", max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "consultorio"
        verbose_name_plural = "consultorios"

    def __str__(self):
        return self.name


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

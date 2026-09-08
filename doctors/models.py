from django.db import models


class Doctor(models.Model):
    """Doctor functional profile (Fase 1: identity only).

    Availability, agenda, and clinical-encounter relations are Phase 2/3
    concerns and are intentionally not modeled here yet.
    """

    person = models.OneToOneField(
        "accounts.Person",
        on_delete=models.PROTECT,
        related_name="doctor_profile",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "médico"
        verbose_name_plural = "médicos"

    def __str__(self):
        return str(self.person)

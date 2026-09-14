"""Fase 4 — dominio de solicitudes de estudio (`study_orders`).

Mismo criterio que `prescriptions` (ADR-021/022/023) — ver los docstrings de
ese módulo para el razonamiento completo de `patient` derivado, versionado
por fila nueva e idempotencia reutilizada de Fase 2.
"""

from django.db import models


class StudyOrder(models.Model):
    """Solicitud de uno o más estudios emitida por un `Doctor` en el
    contexto de un `ClinicalEncounter` (ADR-022). No captura resultados
    (ADR-030 — fuera de alcance de Fase 4)."""

    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Emitida"
        VOIDED = "VOIDED", "Anulada"

    class StudyType(models.TextChoices):
        LABORATORY = "LABORATORY", "Laboratorio"
        IMAGING = "IMAGING", "Gabinete"
        HISTOPATHOLOGY = "HISTOPATHOLOGY", "Histopatología"
        OTHER = "OTHER", "Otro"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="study_orders"
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.PROTECT, related_name="study_orders"
    )
    clinical_encounter = models.ForeignKey(
        "medical_records.ClinicalEncounter", on_delete=models.PROTECT, related_name="study_orders"
    )

    status = models.CharField(max_length=20, choices=Status.choices)
    study_type = models.CharField(max_length=20, choices=StudyType.choices)
    indications = models.TextField(blank=True, default="")
    observations = models.TextField(blank=True, default="")
    issued_at = models.DateTimeField()

    version_number = models.PositiveIntegerField(default=1)
    previous_version = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="next_version"
    )
    is_current_version = models.BooleanField(default=True)

    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="study_orders_voided",
    )
    void_reason = models.TextField(blank=True, default="")

    idempotency_key = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "solicitud de estudio"
        verbose_name_plural = "solicitudes de estudio"
        indexes = [
            models.Index(fields=["patient", "issued_at"]),
            models.Index(fields=["doctor", "issued_at"]),
            models.Index(fields=["clinical_encounter"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["ISSUED", "VOIDED"]),
                name="study_order_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="VOIDED", voided_at__isnull=False, voided_by__isnull=False)
                    | models.Q(status="ISSUED", voided_at__isnull=True, voided_by__isnull=True)
                ),
                name="study_order_voided_requires_trace",
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__gte=1),
                name="study_order_version_number_positive",
            ),
            models.UniqueConstraint(
                fields=["doctor", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="study_order_idempotency_key_unique",
            ),
        ]

    def __str__(self):
        return f"Solicitud {self.pk} — {self.patient_id} ({self.status})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.previous_version_id is not None and self.previous_version_id == self.pk:
            raise ValidationError("previous_version no puede autorreferenciarse.")


class StudyOrderItem(models.Model):
    """Estudio explícito solicitado dentro de una `StudyOrder` (SO-004: sin
    catálogo obligatorio — nombre explícito)."""

    study_order = models.ForeignKey(
        StudyOrder, on_delete=models.CASCADE, related_name="items"
    )
    position = models.PositiveIntegerField()
    study_name = models.CharField(max_length=255)
    specific_instructions = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "estudio solicitado"
        verbose_name_plural = "estudios solicitados"
        ordering = ["study_order", "position"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(position__gt=0), name="study_order_item_position_positive"
            ),
            models.UniqueConstraint(
                fields=["study_order", "position"], name="study_order_item_position_unique"
            ),
        ]

    def __str__(self):
        return f"{self.study_name} (solicitud {self.study_order_id})"

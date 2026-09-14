"""Fase 4 — dominio de recetas (`prescriptions`).

Frontera de dominio (ADR-021): esta app posee `Prescription`/`PrescriptionItem`.
No duplica `Patient`, `Doctor` ni `ClinicalEncounter` — los referencia.

`patient` se deriva siempre de `clinical_encounter.appointment.patient` en el
servicio de emisión (ADR-022, D-003 de `clinical-documents-data-model.md`);
nunca se acepta como parámetro independiente del cliente. Se conserva aquí
como columna propia por razones de consulta/índice — mismo patrón ya usado
por `medical_records.AuditEvent`, que también mantiene `patient` como FK
independiente pese a ser derivable vía `appointment`/`clinical_encounter`.

Versionado (ADR-023): una corrección crea una *nueva fila* con
`version_number` incrementado; `is_current_version` identifica la vigente.
No existe una columna de "cadena/raíz" — la corrección siempre parte de la
versión actual conocida por su propio id, protegida con `select_for_update`
en el servicio.

Convención de campos sin `default` en `status`: mismo patrón deny-by-default
ya usado en `appointments.models`/`medical_records.models`.
"""

from django.db import models


class Prescription(models.Model):
    """Receta médica emitida por un `Doctor` en el contexto de un
    `ClinicalEncounter` (ADR-022). SC-065/AH-065 (Fase 3): un `ClinicalEncounter`
    puede originar múltiples recetas — no hay cardinalidad 1:1."""

    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Emitida"
        VOIDED = "VOIDED", "Anulada"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="prescriptions"
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.PROTECT, related_name="prescriptions"
    )
    clinical_encounter = models.ForeignKey(
        "medical_records.ClinicalEncounter", on_delete=models.PROTECT, related_name="prescriptions"
    )

    status = models.CharField(max_length=20, choices=Status.choices)
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
        related_name="prescriptions_voided",
    )
    void_reason = models.TextField(blank=True, default="")

    # Idempotencia (ADR-029, mismo mecanismo que `appointments.Appointment`).
    idempotency_key = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "receta"
        verbose_name_plural = "recetas"
        indexes = [
            models.Index(fields=["patient", "issued_at"]),
            models.Index(fields=["doctor", "issued_at"]),
            models.Index(fields=["clinical_encounter"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["ISSUED", "VOIDED"]),
                name="prescription_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="VOIDED", voided_at__isnull=False, voided_by__isnull=False)
                    | models.Q(status="ISSUED", voided_at__isnull=True, voided_by__isnull=True)
                ),
                name="prescription_voided_requires_trace",
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__gte=1),
                name="prescription_version_number_positive",
            ),
            models.UniqueConstraint(
                fields=["doctor", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="prescription_idempotency_key_unique",
            ),
        ]

    def __str__(self):
        return f"Receta {self.pk} — {self.patient_id} ({self.status})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.previous_version_id is not None and self.previous_version_id == self.pk:
            raise ValidationError("previous_version no puede autorreferenciarse.")


class PrescriptionItem(models.Model):
    """Medicamento explícito de una receta (D-PR-003: sin catálogo
    farmacológico obligatorio — texto explícito)."""

    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="items"
    )
    position = models.PositiveIntegerField()

    medication_name = models.CharField(max_length=255)
    presentation = models.CharField(max_length=255, blank=True, default="")
    dose = models.CharField(max_length=100)
    dose_unit = models.CharField(max_length=50, blank=True, default="")
    route = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100, blank=True, default="")
    instructions = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "medicamento de receta"
        verbose_name_plural = "medicamentos de receta"
        ordering = ["prescription", "position"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(position__gt=0), name="prescription_item_position_positive"
            ),
            models.UniqueConstraint(
                fields=["prescription", "position"], name="prescription_item_position_unique"
            ),
        ]

    def __str__(self):
        return f"{self.medication_name} (receta {self.prescription_id})"

"""Fase 4 — dominio de documentos clínicos (`clinical_documents`).

`ClinicalDocument` pertenece obligatoriamente a un `Patient` (CD-001); sus
demás relaciones son opcionales (ADR-025). No se agrega FK a `MedicalRecord`
— `Patient` ya lo determina (CD-002, ADR-025).

Estado (D-002, `clinical-documents-data-model.md` §3): un documento
respaldado por `Prescription`/`StudyOrder` NO tiene `status` propio (sigue
la vigencia de la entidad que lo respalda, CD-006/CD-007) — su `status` es
`NULL`. Un documento sin ese respaldo (subido directamente) sí lo tiene
(`ACTIVE`/`VOIDED`).

`document_type = STUDY_ORDER` es siempre el usado para el PDF `GENERATED`
de una `StudyOrder` (CD-008) — `LABORATORY`/`IMAGING`/`HISTOPATHOLOGY`
quedan reservados a documentos `UPLOADED`.
"""

from django.db import models


class ClinicalDocument(models.Model):
    class DocumentType(models.TextChoices):
        LABORATORY = "LABORATORY", "Laboratorio"
        IMAGING = "IMAGING", "Gabinete"
        HISTOPATHOLOGY = "HISTOPATHOLOGY", "Histopatología"
        PHOTOGRAPH = "PHOTOGRAPH", "Fotografía"
        PRESCRIPTION = "PRESCRIPTION", "Receta"
        INSTRUCTIONS = "INSTRUCTIONS", "Indicaciones"
        STUDY_ORDER = "STUDY_ORDER", "Solicitud de estudio"
        OTHER = "OTHER", "Otro"

    class Origin(models.TextChoices):
        UPLOADED = "UPLOADED", "Subido"
        GENERATED = "GENERATED", "Generado"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        VOIDED = "VOIDED", "Anulado"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="clinical_documents"
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="clinical_documents",
    )
    clinical_encounter = models.ForeignKey(
        "medical_records.ClinicalEncounter",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="clinical_documents",
    )
    prescription = models.ForeignKey(
        "prescriptions.Prescription",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="clinical_documents",
    )
    study_order = models.ForeignKey(
        "study_orders.StudyOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="clinical_documents",
    )

    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    origin = models.CharField(max_length=20, choices=Origin.choices)

    # D-002: sólo aplica cuando el documento no está respaldado por
    # Prescription/StudyOrder (ver constraint clinicaldocument_status_matches_backing).
    status = models.CharField(max_length=20, choices=Status.choices, null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True, default="")

    original_filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500, unique=True)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="clinical_documents_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Versionado (D-001/ADR-023) — sólo tiene sentido para documentos
    # `UPLOADED` sin respaldo de Prescription/StudyOrder (esos ya versionan
    # a través de su propia entidad, CD-006).
    version_number = models.PositiveIntegerField(null=True, blank=True)
    previous_version = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="next_version"
    )
    is_current_version = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = "documento clínico"
        verbose_name_plural = "documentos clínicos"
        indexes = [
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["patient", "document_type", "created_at"]),
            models.Index(fields=["appointment"]),
            models.Index(fields=["clinical_encounter"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(prescription__isnull=False) | models.Q(study_order__isnull=False))
                    & models.Q(status__isnull=True)
                )
                | (
                    models.Q(prescription__isnull=True)
                    & models.Q(study_order__isnull=True)
                    & models.Q(status__isnull=False)
                    & models.Q(status__in=["ACTIVE", "VOIDED"])
                ),
                name="clinicaldocument_status_matches_backing",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="VOIDED", voided_at__isnull=False)
                    | ~models.Q(status="VOIDED")
                ),
                name="clinicaldocument_voided_requires_trace",
            ),
            models.CheckConstraint(
                condition=models.Q(size_bytes__gt=0), name="clinicaldocument_size_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(version_number__isnull=True) | models.Q(version_number__gte=1),
                name="clinicaldocument_version_number_positive",
            ),
            # Un único ClinicalDocument GENERATED por Prescription/StudyOrder
            # (cada versión de Prescription/StudyOrder genera el suyo propio).
            models.UniqueConstraint(
                fields=["prescription"],
                condition=models.Q(origin="GENERATED"),
                name="clinicaldocument_one_generated_per_prescription",
            ),
            models.UniqueConstraint(
                fields=["study_order"],
                condition=models.Q(origin="GENERATED"),
                name="clinicaldocument_one_generated_per_study_order",
            ),
        ]

    def __str__(self):
        return f"Documento {self.pk} — {self.document_type} ({self.patient_id})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.previous_version_id is not None and self.previous_version_id == self.pk:
            raise ValidationError("previous_version no puede autorreferenciarse.")

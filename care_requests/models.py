"""Fase 5 — dominio de solicitudes de atención (`care_requests`).

`docs/design/care-request-data-model.md`. `CareRequest` orquesta la creación
directa de una cita a partir de un slot ya generado por Agenda (Fase 2);
`Appointment` no conoce esta app — la FK vive del lado de `CareRequest`
(`appointment`), nunca al revés, para que `appointments` no dependa de
`care_requests` ni a nivel de código ni de modelo (ADR-005 §12/§44).
"""

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class CareRequest(models.Model):
    """Solicitud de atención iniciada por un paciente o por un responsable
    en su nombre (`requirements.md` §12). Workflow único: `NUEVA` →
    `CONVERTIDA` — sin estados de revisión/atención/cierre manual."""

    class Status(models.TextChoices):
        NUEVA = "NUEVA", "Nueva"
        CONVERTIDA = "CONVERTIDA", "Convertida"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="care_requests"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="care_requests_created"
    )
    responsible = models.ForeignKey(
        "patients.Responsible",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="care_requests",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.PROTECT, related_name="care_requests"
    )
    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.PROTECT, related_name="care_requests"
    )
    # Propietaria de la relación (docs/design/care-request-data-model.md §3):
    # `Appointment` no gana ningún campo — `NULL` mientras `status=NUEVA`,
    # se asigna antes de pasar a `CONVERTIDA`, dentro de la misma transacción.
    # `related_name="+"` (corrección 2026-09-18, care-request-data-model.md
    # §3): un `related_name` explícito o por defecto habría expuesto
    # `Appointment.care_request` como accessor inverso de Django — sin
    # agregar columna ni migración en `appointments`, pero sí navegabilidad
    # ORM en el sentido prohibido (`appointments ↛ care_requests`, ADR-005
    # §12/§44). `related_name="+"` es el mecanismo estándar de Django para
    # no generar ese accessor, sin tocar `appointments/models.py`.
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    # Tal cual el slot de Agenda (`get_available_slots`) — nunca calculado
    # aquí (`docs/design/care-request-service-contracts.md` §3).
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    motivo = models.TextField()
    padecimiento = models.TextField(blank=True, default="")
    descripcion = models.TextField(blank=True, default="")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NUEVA)

    idempotency_key = models.CharField(max_length=255, blank=True, default="")

    # Identidad estable de los adjuntos de ESTA conversión (corrección
    # 2026-09-18, care-request-data-model.md §3.1): fijada una sola vez, en
    # el momento en que `status` pasa a `CONVERTIDA`, con los `pk` de los
    # `ClinicalDocument` creados durante ESTA ejecución — nunca recalculada
    # consultando `ClinicalDocument.objects.filter(appointment_id=...)`,
    # que se contaminaría con documentos que otro flujo agregue después a
    # la misma `Appointment`. No es una FK/M2M hacia `ClinicalDocument`
    # (evita exponer un accessor inverso allí, igual razón que
    # `appointment` arriba, y evita una tabla intermedia nueva): es una
    # referencia lógica por `pk`, mismo criterio ya usado en el proyecto
    # por `AuditEvent.resource_id`. `ArrayField` reutiliza
    # `django.contrib.postgres` (ya instalado y usado por `appointments`
    # para `ExclusionConstraint`/`DateTimeRangeField`) — no introduce una
    # dependencia nueva.
    clinical_document_ids = ArrayField(
        models.PositiveBigIntegerField(), blank=True, default=list,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "solicitud de atención"
        verbose_name_plural = "solicitudes de atención"
        indexes = [
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["doctor", "created_at"]),
            models.Index(fields=["created_by", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["NUEVA", "CONVERTIDA"]),
                name="care_request_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(start_at__lt=models.F("end_at")),
                name="care_request_start_before_end",
            ),
            models.UniqueConstraint(
                fields=["created_by", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="care_request_idempotency_key_unique",
            ),
        ]

    def __str__(self):
        return f"CareRequest {self.pk} — {self.patient_id} ({self.status})"

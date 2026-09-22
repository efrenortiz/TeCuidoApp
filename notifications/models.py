"""Fase 6 — dominio de notificaciones (`notifications`).

Contrato: docs/phases/phase-6-design-freeze.md,
docs/design/phase-6-notification-domain.md,
docs/design/phase-6-notification-data-model.md.

`notifications` no es dueño de ninguna regla de Agenda/identidad — solo referencia
lógicamente `Appointment`/`User` mediante `resource_type`/`resource_id` y
`recipient_user` (docs/design/phase-6-notification-data-model.md §4).
"""

from django.conf import settings
from django.db import models


class ReminderWindow(models.Model):
    """Ventana de recordatorio configurable sin cambiar código
    (docs/design/phase-6-notification-data-model.md §2.2, cierra H-01 de la
    auditoría documental — requirements.md §27.1). Las cuatro ventanas
    iniciales (15/10/5/1 días) se cargan como datos semilla en una
    migración de datos, nunca como constante Python."""

    offset_days = models.PositiveSmallIntegerField("días de anticipación")
    is_active = models.BooleanField("activa", default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ventana de recordatorio"
        verbose_name_plural = "ventanas de recordatorio"
        constraints = [
            models.UniqueConstraint(fields=["offset_days"], name="reminderwindow_offset_days_unique"),
            models.CheckConstraint(
                condition=models.Q(offset_days__gt=0), name="reminderwindow_offset_days_positive"
            ),
        ]
        ordering = ["-offset_days"]

    def __str__(self):
        return f"{self.offset_days} día(s) antes"


class Notification(models.Model):
    """Una intención concreta de comunicación por Email
    (docs/design/phase-6-notification-data-model.md §2.1).

    No se recomienda ni se permite guardar contenido clínico en esta fila —
    solo referencias lógicas (`resource_type`/`resource_id`)."""

    class EventType(models.TextChoices):
        REGISTRATION_INVITATION = "REGISTRATION_INVITATION", "Invitación de registro"
        EMAIL_VERIFICATION = "EMAIL_VERIFICATION", "Verificación de correo"
        PASSWORD_RECOVERY = "PASSWORD_RECOVERY", "Recuperación de contraseña"
        APPOINTMENT_CREATED = "APPOINTMENT_CREATED", "Cita creada"
        APPOINTMENT_MODIFIED = "APPOINTMENT_MODIFIED", "Cita modificada"
        APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED", "Cita cancelada"
        APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER", "Recordatorio de cita"

    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        SENDING = "SENDING", "Enviando"
        SENT = "SENT", "Enviada"
        FAILED = "FAILED", "Fallida"
        CANCELLED = "CANCELLED", "Cancelada"

    class ResourceType(models.TextChoices):
        USER = "User", "Usuario"
        APPOINTMENT = "Appointment", "Cita"

    # Sin default — igual que `Appointment.status`/`ClinicalEncounter.status`:
    # toda fila declara su estado inicial explícitamente en el punto de
    # creación (deny-by-default, convención ya establecida en el proyecto).
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.EMAIL)

    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="notifications_received",
    )
    # Congelada en el momento del intento — nunca se relee de `recipient_user`
    # después, para que la trazabilidad del intento no cambie si el usuario
    # cambia su correo más tarde (docs/design/phase-6-notification-data-model.md §2.1).
    recipient_address = models.EmailField("dirección de envío")

    resource_type = models.CharField(max_length=20, choices=ResourceType.choices, blank=True)
    resource_id = models.PositiveBigIntegerField(null=True, blank=True)

    scheduled_for = models.DateTimeField("momento previsto de procesamiento")
    status = models.CharField(max_length=10, choices=Status.choices)

    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    provider_reference = models.CharField(max_length=255, blank=True, default="")
    reason_code = models.CharField(max_length=60, blank=True, default="")

    # Identidad operacional para deduplicación
    # (docs/design/phase-6-notification-domain.md §11): mismo evento de
    # negocio + destinatario + canal + ventana funcional = misma fila.
    dedupe_key = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        indexes = [
            models.Index(fields=["scheduled_for", "status"]),
            models.Index(fields=["recipient_user", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]
        constraints = [
            # docs/design/phase-6-notification-data-model.md §3 — unicidad
            # de dedupe_key cuando la semántica de evento la exige; una
            # cadena vacía (evento sin necesidad de dedupe, p. ej. una
            # invitación) nunca colisiona consigo misma.
            models.UniqueConstraint(
                fields=["dedupe_key"],
                condition=~models.Q(dedupe_key=""),
                name="notification_dedupe_key_unique",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} · {self.recipient_address} · {self.status}"

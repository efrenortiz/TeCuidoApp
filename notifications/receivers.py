"""Conecta las señales de `appointments` (Fase 2) con los servicios de
`notifications` (Fase 6) — ver `appointments/signals.py` y
`notifications/apps.py::ready()` para la justificación de por qué esto es un
signal y no una llamada directa (ITD-002)."""

import logging

from django.dispatch import receiver

from appointments.signals import appointment_cancelled, appointment_created, appointment_modified
from notifications import services

logger = logging.getLogger("notifications")


@receiver(appointment_created)
def _on_appointment_created(sender, appointment, **kwargs):
    try:
        services.notify_appointment_created(appointment)
    except Exception:  # noqa: BLE001 — nunca debe propagar hacia el llamador de Agenda
        logger.exception("Fallo al procesar notify_appointment_created para Appointment %s", appointment.pk)


@receiver(appointment_modified)
def _on_appointment_modified(sender, appointment, event_context=None, **kwargs):
    try:
        services.notify_appointment_modified(appointment, event_context=event_context)
    except Exception:  # noqa: BLE001
        logger.exception("Fallo al procesar notify_appointment_modified para Appointment %s", appointment.pk)


@receiver(appointment_cancelled)
def _on_appointment_cancelled(sender, appointment, event_context=None, **kwargs):
    try:
        services.notify_appointment_cancelled(appointment, event_context=event_context)
    except Exception:  # noqa: BLE001
        logger.exception("Fallo al procesar notify_appointment_cancelled para Appointment %s", appointment.pk)

"""NotificationService (docs/design/phase-6-notification-service-contracts.md).

Capas (docs/phases/phase-6-design-freeze.md §9):

    Business Operation -> Notification Intent -> Notification Service ->
    Transport abstraction -> Email transport

Este módulo es la única frontera de servicio de `notifications`. No contiene
reglas de Agenda/identidad — solo resuelve destinatarios ya autorizados por
las relaciones de dominio existentes y gestiona el ciclo de vida de
`Notification`.
"""

import datetime as dt
import logging
import smtplib

from django.core.exceptions import ValidationError
from django.core.mail import BadHeaderError, send_mail
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone

from notifications.models import Notification, ReminderWindow
from patients.models import ResponsiblePatientRelationship

logger = logging.getLogger("notifications")

# ITD-005 (docs/phases/phase-6-implementation-summary.md): la recuperación
# de contraseña sigue usando el mecanismo ya existente de Django
# (PasswordResetView/PasswordResetForm) y no pasa por este transporte — ver
# el resumen de implementación para la justificación completa.

# PD-007 / ITD-011 (docs/phases/phase-6-implementation-summary.md): política
# de reintentos. Valores puramente técnicos, elegidos por escala actual
# (volumen bajo, sin infraestructura de colas) — no representan una
# decisión de producto y pueden ajustarse sin tocar la política funcional.
MAX_DELIVERY_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 60  # 1er reintento ~1 min después del primer fallo
BACKOFF_MAX_SECONDS = 6 * 60 * 60  # tope de 6 horas entre reintentos
# ITD-012: una fila que quede en SENDING más tiempo que esto sin resolverse
# (proceso interrumpido a media ejecución, hallazgo 12.3) se considera
# huérfana y vuelve a quedar disponible para reclamo.
SENDING_LEASE_TIMEOUT = dt.timedelta(minutes=10)


def _backoff_seconds(attempt_count):
    seconds = BACKOFF_BASE_SECONDS * (2 ** max(attempt_count - 1, 0))
    return min(seconds, BACKOFF_MAX_SECONDS)


class TransportResult:
    """Resultado de un intento de transporte (docs/design/phase-6-notification-service-contracts.md §8).

    Prompt 1 de la ronda de corrección post-implementación (§3, "diferenciar
    fallos transitorios y permanentes"): `is_permanent` distingue, cuando es
    técnicamente determinable, un fallo que ningún reintento puede resolver
    (dirección con formato inválido, encabezado malformado, destinatario
    rechazado por el servidor) de uno transitorio (timeout de red,
    servidor no disponible) — sin inventar categorías de negocio nuevas, solo
    a partir del tipo de excepción/validación técnica."""

    def __init__(self, *, ok, provider_reference="", reason_code="", is_permanent=False):
        self.ok = ok
        self.provider_reference = provider_reference
        self.reason_code = reason_code
        self.is_permanent = is_permanent


class EmailTransport:
    """Abstracción de transporte (docs/design/phase-6-notification-service-contracts.md §8).

    El dominio nunca conoce SMTP host/API key/SDK concreto: delega en
    `django.core.mail`, que ya resuelve `EMAIL_BACKEND`/`DEFAULT_FROM_EMAIL`
    desde configuración (`TeCuidoApp/settings.py`), nunca desde código."""

    def send(self, *, subject, message, recipient_address):
        """Hallazgo 12.7 (docs/phases/phase-6-implementation-summary.md):
        no basta con "sin excepción" — `send_mail` devuelve el número de
        mensajes efectivamente entregados por el backend; un backend que
        "no falla" pero reporta 0 entregas no debe marcarse `SENT`.

        Fallo permanente vs. transitorio (Prompt 1, §3): un formato de
        dirección inválido se detecta *antes* de intentar el transporte —
        ningún reintento lo arreglaría. `SMTPRecipientsRefused`/
        `BadHeaderError` (el servidor rechazó explícitamente al
        destinatario, o el encabezado es inválido) también son permanentes.
        Cualquier otra excepción (timeout, conexión rechazada, servidor no
        disponible) se trata como transitoria — sujeta a reintento."""
        try:
            validate_email(recipient_address)
        except ValidationError:
            logger.warning("Dirección de destino con formato inválido: %s", recipient_address)
            return TransportResult(ok=False, reason_code="INVALID_RECIPIENT_FORMAT", is_permanent=True)

        try:
            delivered = send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[recipient_address],
                fail_silently=False,
            )
        except (smtplib.SMTPRecipientsRefused, BadHeaderError) as exc:
            logger.warning("Fallo permanente de transporte hacia %s: %s", recipient_address, exc)
            return TransportResult(ok=False, reason_code="RECIPIENT_REJECTED", is_permanent=True)
        except Exception as exc:  # noqa: BLE001 — un fallo de proveedor nunca debe propagarse
            logger.warning("Fallo transitorio de transporte hacia %s: %s", recipient_address, exc)
            return TransportResult(ok=False, reason_code="TRANSPORT_ERROR")
        if not delivered:
            logger.warning("Transporte de Email hacia %s reportó 0 entregas.", recipient_address)
            return TransportResult(ok=False, reason_code="TRANSPORT_ZERO_DELIVERED")
        return TransportResult(ok=True)


_TRANSPORT = EmailTransport()


# ---------------------------------------------------------------------------
# Resolución de destinatarios (F6-D01/F6-D02)
# ---------------------------------------------------------------------------


def _user_for_person_owner(owner):
    """`owner` es un Patient/Responsible/Doctor — todos comparten el mismo
    patrón `owner.person.user` (nullable — ADR-002, Person.user es opcional
    para pacientes MINOR sin cuenta propia)."""
    person = getattr(owner, "person", None)
    user = getattr(person, "user", None) if person is not None else None
    if user is None or not user.is_active or not user.email:
        return None
    return user


def _appointment_recipients(appointment, *, include_doctor):
    """F6-D01/F6-D02 (docs/design/phase-6-notification-domain.md §4): resuelve
    los destinatarios elegibles a partir de las relaciones vigentes en el
    momento en que se genera la intención — nunca desde un flag propio de
    `notifications`. Un destinatario sin correo resoluble (paciente MINOR
    sin `User`, responsable/doctor con cuenta desactivada) se omite en
    silencio: no es un error, es la ausencia legítima de esa vía de
    contacto."""
    recipients = []

    patient_user = _user_for_person_owner(appointment.patient)
    if patient_user is not None:
        recipients.append(("PATIENT", patient_user))

    for rel in ResponsiblePatientRelationship.objects.filter(
        patient=appointment.patient, status=ResponsiblePatientRelationship.Status.ACTIVE
    ).select_related("responsible__person__user"):
        resp_user = _user_for_person_owner(rel.responsible)
        if resp_user is not None:
            recipients.append(("RESPONSIBLE", resp_user))

    if include_doctor:
        doctor_user = _user_for_person_owner(appointment.doctor)
        if doctor_user is not None:
            recipients.append(("DOCTOR", doctor_user))

    return recipients


# ---------------------------------------------------------------------------
# Creación + envío inmediato (bloque interno común)
# ---------------------------------------------------------------------------


def _get_or_create_notification(
    *, event_type, recipient_user, recipient_address, resource_type="", resource_id=None,
    scheduled_for=None, dedupe_key="",
):
    """Idempotente por `dedupe_key` (docs/design/phase-6-notification-domain.md
    §11): dos intentos de crear la misma intención lógica devuelven la misma
    fila, nunca una segunda."""
    scheduled_for = scheduled_for or dj_timezone.now()
    if dedupe_key:
        existing = Notification.objects.filter(dedupe_key=dedupe_key).first()
        if existing is not None:
            return existing, False
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                event_type=event_type,
                recipient_user=recipient_user,
                recipient_address=recipient_address,
                resource_type=resource_type,
                resource_id=resource_id,
                scheduled_for=scheduled_for,
                status=Notification.Status.PENDING,
                dedupe_key=dedupe_key,
            )
    except IntegrityError:
        # Carrera perdida contra una creación concurrente con el mismo
        # dedupe_key — igual que el patrón ya usado en
        # appointments.services.appointment (IntegrityError -> replay).
        existing = Notification.objects.filter(dedupe_key=dedupe_key).first() if dedupe_key else None
        if existing is None:
            raise
        return existing, False
    return notification, True


def _attempt_send(notification, *, message_override=None):
    """Intenta el transporte y persiste el resultado. Nunca propaga una
    excepción del proveedor (docs/phases/phase-6-design-freeze.md §21).

    `message_override` cubre los casos (invitación, verificación de correo)
    cuyo contenido depende de un token/URL de un solo uso ya generado por el
    llamador — ese valor nunca se persiste en `Notification` (no hay columna
    para ello, docs/design/phase-6-notification-data-model.md §2.1): solo
    vive en memoria durante este intento de envío, igual que ya ocurría con
    el `send_mail(...)` directo que sustituye en `accounts/views.py`.

    Un `Notification` ya `SENT` nunca se reenvía (idempotencia real, no solo
    de fila — docs/design/phase-6-notification-domain.md §11: "un mismo
    evento lógico no debe producir accidentalmente múltiples efectos"). Esto
    cubre tanto una repetición manual como una futura llamada duplicada al
    mismo `notify_appointment_*` para la misma cita.

    PD-007 (reintentos limitados + backoff): un fallo reprograma
    `scheduled_for` hacia adelante en vez de reintentar de inmediato; al
    agotar `MAX_DELIVERY_ATTEMPTS` la fila queda en `FAILED` como estado
    terminal (no se introduce un estado nuevo — se distingue por
    `attempt_count`/`reason_code`, ver docs/phases/phase-6-implementation-summary.md)."""
    if notification.status == Notification.Status.SENT:
        return notification
    notification.status = Notification.Status.SENDING
    notification.attempt_count += 1
    notification.last_attempt_at = dj_timezone.now()
    notification.save(update_fields=["status", "attempt_count", "last_attempt_at", "updated_at"])

    subject, message = message_override or _render(notification)
    result = _TRANSPORT.send(
        subject=subject, message=message, recipient_address=notification.recipient_address
    )
    if result.ok:
        notification.status = Notification.Status.SENT
        notification.sent_at = dj_timezone.now()
        notification.reason_code = ""
    elif result.is_permanent:
        # Fallo permanente (Prompt 1, §3): terminal de inmediato, sin
        # esperar a agotar MAX_DELIVERY_ATTEMPTS — ningún reintento
        # cambiaría un formato de dirección inválido o un rechazo
        # explícito del servidor.
        notification.status = Notification.Status.FAILED
        notification.reason_code = f"PERMANENT:{result.reason_code}"
    elif notification.attempt_count >= MAX_DELIVERY_ATTEMPTS:
        notification.status = Notification.Status.FAILED
        notification.reason_code = f"MAX_ATTEMPTS_EXCEEDED:{result.reason_code}"
    else:
        notification.status = Notification.Status.FAILED
        notification.reason_code = result.reason_code
        notification.scheduled_for = dj_timezone.now() + dt.timedelta(
            seconds=_backoff_seconds(notification.attempt_count)
        )
    notification.provider_reference = result.provider_reference
    notification.save(
        update_fields=[
            "status", "sent_at", "reason_code", "provider_reference", "scheduled_for", "updated_at",
        ]
    )
    return notification


# ---------------------------------------------------------------------------
# Plantillas mínimas (docs/design/phase-6-notification-security-and-privacy.md
# §2/§3 — mínima información necesaria, nunca contenido clínico)
# ---------------------------------------------------------------------------


def _appointment_url(appointment):
    """PD-005: el correo enlaza a TeCuidoApp para el detalle completo — el
    correo mismo nunca lo sustituye."""
    from django.conf import settings
    from django.urls import reverse

    return f"{settings.SITE_BASE_URL}{reverse('appointments:appointment_detail', args=[appointment.pk])}"


def _appointment_essentials(appointment):
    """PD-005 (docs/phases/phase-6-implementation-summary.md): información
    esencial de la cita — fecha/hora, médico, consultorio — nunca
    contenido clínico (motivo, diagnóstico, notas, documentos)."""
    local_start = appointment.start_at.astimezone(appointment.clinic.zoneinfo)
    return {
        "when": local_start.strftime("%d/%m/%Y %H:%M"),
        "doctor": str(appointment.doctor),
        "clinic": appointment.clinic.name,
        "url": _appointment_url(appointment),
    }


# PD-005: por evento de cita — (título, saludo, etiqueta de la fecha/hora).
# El cuerpo completo se arma en `_render` interpolando `_appointment_essentials`.
_APPOINTMENT_EVENT_COPY = {
    Notification.EventType.APPOINTMENT_CREATED: (
        "Cita reservada — TeCuidoApp", "Tu cita fue reservada correctamente.", "Fecha y hora",
    ),
    Notification.EventType.APPOINTMENT_MODIFIED: (
        "Cita modificada — TeCuidoApp", "Tu cita fue modificada.", "Nueva fecha y hora",
    ),
    Notification.EventType.APPOINTMENT_CANCELLED: (
        "Cita cancelada — TeCuidoApp", "Tu cita fue cancelada.", "Fecha y hora que fue cancelada",
    ),
    Notification.EventType.APPOINTMENT_REMINDER: (
        "Recordatorio de cita — TeCuidoApp", "Tienes una cita próxima.", "Fecha y hora",
    ),
}


def _render(notification):
    """Hallazgo PD-005: cada plantilla de cita incluye información esencial
    real (fecha/hora, médico, consultorio) + enlace a TeCuidoApp — nunca
    solo un mensaje genérico. "Cita confirmada" se corrige a "Cita
    reservada": Fase 2 no tiene una etapa de confirmación separada
    (docs/design/phase-6-notification-domain.md §8), así que "confirmada"
    sugeriría un estado que no existe."""
    if notification.event_type in _APPOINTMENT_EVENT_COPY:
        from appointments.models import Appointment

        appointment = Appointment.objects.select_related("doctor__person", "clinic").get(
            pk=notification.resource_id
        )
        info = _appointment_essentials(appointment)
        subject, greeting, when_label = _APPOINTMENT_EVENT_COPY[notification.event_type]
        message = (
            f"{greeting}\n\n"
            f"{when_label}: {info['when']}\n"
            f"Médico: {info['doctor']}\n"
            f"Consultorio: {info['clinic']}\n\n"
            f"Ver detalle en TeCuidoApp: {info['url']}"
        )
        return subject, message

    templates = {
        Notification.EventType.REGISTRATION_INVITATION: (
            "Invitación a TeCuidoApp",
            "Has recibido una invitación de registro.",
        ),
        Notification.EventType.EMAIL_VERIFICATION: (
            "Verifica tu correo — TeCuidoApp",
            "Verifica tu correo para completar tu registro.",
        ),
        Notification.EventType.PASSWORD_RECOVERY: (
            "Recuperación de contraseña — TeCuidoApp",
            "Se solicitó restablecer tu contraseña.",
        ),
    }
    return templates[notification.event_type]


# ---------------------------------------------------------------------------
# Identidad (F6 §5.1 / notification-domain.md §3 "Identidad")
# ---------------------------------------------------------------------------


def create_registration_invitation_notification(*, recipient_address, accept_url):
    notification, _created = _get_or_create_notification(
        event_type=Notification.EventType.REGISTRATION_INVITATION,
        recipient_user=None,
        recipient_address=recipient_address,
    )
    message = (
        "Invitación a TeCuidoApp",
        f"Completa tu registro aquí: {accept_url}",
    )
    return _attempt_send(notification, message_override=message)


def create_email_verification_notification(*, user, verify_url):
    notification, _created = _get_or_create_notification(
        event_type=Notification.EventType.EMAIL_VERIFICATION,
        recipient_user=user,
        recipient_address=user.email,
        resource_type=Notification.ResourceType.USER,
        resource_id=user.pk,
    )
    message = (
        "Verifica tu correo — TeCuidoApp",
        f"Verifica tu correo aquí: {verify_url}",
    )
    return _attempt_send(notification, message_override=message)


def create_password_recovery_notification(*, user):
    """Definida por contrato (docs/design/phase-6-notification-service-contracts.md
    §2) pero no invocada en esta fase — ITD-005: la recuperación de
    contraseña sigue el flujo ya existente de Django
    (`PasswordResetView`/`PasswordResetForm`), que ya envía su propio correo
    de forma segura. Queda disponible para una integración futura si se
    decide reemplazar ese flujo."""
    notification, _created = _get_or_create_notification(
        event_type=Notification.EventType.PASSWORD_RECOVERY,
        recipient_user=user,
        recipient_address=user.email,
        resource_type=Notification.ResourceType.USER,
        resource_id=user.pk,
    )
    return _attempt_send(notification)


# ---------------------------------------------------------------------------
# Agenda (F6-D01/F6-D02)
# ---------------------------------------------------------------------------


def notify_appointment_created(appointment):
    for _role, user in _appointment_recipients(appointment, include_doctor=True):
        dedupe_key = f"APPOINTMENT_CREATED:{appointment.pk}:{user.pk}"
        notification, _created = _get_or_create_notification(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            recipient_user=user,
            recipient_address=user.email,
            resource_type=Notification.ResourceType.APPOINTMENT,
            resource_id=appointment.pk,
            dedupe_key=dedupe_key,
        )
        _attempt_send(notification)
    schedule_appointment_reminders(appointment)


def notify_appointment_modified(appointment, event_context=None):
    # La marca de modificación distingue cada reprogramación efectiva
    # (docs/design/phase-6-notification-domain.md §11) sin depender de una
    # copia paralela del estado de Agenda: se usa `updated_at`, ya escrito
    # por `appointments.services.appointment.reschedule_appointment` antes
    # de despachar la señal.
    change_marker = appointment.updated_at.isoformat()
    for _role, user in _appointment_recipients(appointment, include_doctor=True):
        dedupe_key = f"APPOINTMENT_MODIFIED:{appointment.pk}:{user.pk}:{change_marker}"
        notification, _created = _get_or_create_notification(
            event_type=Notification.EventType.APPOINTMENT_MODIFIED,
            recipient_user=user,
            recipient_address=user.email,
            resource_type=Notification.ResourceType.APPOINTMENT,
            resource_id=appointment.pk,
            dedupe_key=dedupe_key,
        )
        _attempt_send(notification)
    reschedule_appointment_reminders(appointment)


def notify_appointment_cancelled(appointment, event_context=None):
    for _role, user in _appointment_recipients(appointment, include_doctor=True):
        dedupe_key = f"APPOINTMENT_CANCELLED:{appointment.pk}:{user.pk}"
        notification, _created = _get_or_create_notification(
            event_type=Notification.EventType.APPOINTMENT_CANCELLED,
            recipient_user=user,
            recipient_address=user.email,
            resource_type=Notification.ResourceType.APPOINTMENT,
            resource_id=appointment.pk,
            dedupe_key=dedupe_key,
        )
        _attempt_send(notification)
    cancel_appointment_reminders(appointment)


# ---------------------------------------------------------------------------
# Recordatorios (F6-D02, docs/design/phase-6-notification-data-model.md §5/§6)
# ---------------------------------------------------------------------------


def schedule_appointment_reminders(appointment):
    """Materializa una fila PENDING por (ventana activa x destinatario
    elegible) — ITD-007: se calculan en el momento de creación de la cita,
    no bajo demanda, para mantener la deduplicación trivial por
    `dedupe_key` estable.

    También la reutiliza `reschedule_appointment_reminders` (C-019) para
    materializar ventanas activas nuevas tras un cambio de configuración
    de `ReminderWindow` — es la misma función, no una segunda fuente de
    verdad; `dedupe_key` evita duplicar lo que ya exista."""
    windows = ReminderWindow.objects.filter(is_active=True)
    for window in windows:
        scheduled_for = appointment.start_at - dt.timedelta(days=window.offset_days)
        if scheduled_for <= dj_timezone.now():
            # La ventana ya pasó respecto de la fecha de la cita (p. ej.
            # una cita reservada a 3 días de anticipación no puede generar
            # un recordatorio de 15/10/5 días) — no se crea una fila para
            # un recordatorio que nunca podría dispararse.
            continue
        for _role, user in _appointment_recipients(appointment, include_doctor=False):
            dedupe_key = f"APPOINTMENT_REMINDER:{appointment.pk}:{user.pk}:{window.offset_days}"
            _get_or_create_notification(
                event_type=Notification.EventType.APPOINTMENT_REMINDER,
                recipient_user=user,
                recipient_address=user.email,
                resource_type=Notification.ResourceType.APPOINTMENT,
                resource_id=appointment.pk,
                scheduled_for=scheduled_for,
                dedupe_key=dedupe_key,
            )


def reschedule_appointment_reminders(appointment):
    """docs/design/phase-6-notification-data-model.md §6: las tareas
    futuras se recalculan respecto de la fecha vigente, sin recrear filas
    (el `dedupe_key` no incluye la fecha, así que sigue siendo la misma
    fila lógica).

    Hallazgo 12.5 (docs/phases/phase-6-implementation-summary.md): incluye
    también `FAILED` (no solo `PENDING`) — un recordatorio que falló una
    vez y todavía es elegible para reintento (`attempt_count <
    MAX_DELIVERY_ATTEMPTS`) sigue siendo una tarea futura pendiente de esta
    cita; dejarlo fuera de este recálculo habría permitido que se
    reintentara más tarde con la fecha de la cita ya obsoleta.

    `SENDING` deliberadamente no se toca aquí (Prompt 1, corrección
    post-implementación, §4): es un estado transitorio de milisegundos, y
    `_render(...)` siempre relee la `Appointment` desde la base de datos en
    el momento del envío — un recordatorio ya en `SENDING` durante una
    reprogramación termina reflejando igualmente la fecha nueva, sin
    necesidad de tocar su fila. Solo queda una ventana de carrera
    extremadamente estrecha (milisegundos) entre la verificación de
    elegibilidad de `process_due_notifications` y el envío real, aceptada
    y documentada en vez de resuelta con locking adicional no justificado
    por el volumen actual del proyecto.

    C-019 (PD-004, corrección post-implementación — prompt 1/4 de la ronda
    de correcciones funcionales): la configuración vigente al momento de
    la reprogramación es la que manda — "nueva configuración de
    ReminderWindow aplica a nuevas citas y a citas reprogramadas
    posteriormente", nunca la configuración congelada que tenía la fila ya
    existente. Antes, esta función releía el `offset_days` desde el propio
    `dedupe_key` de cada notificación existente en vez de volver a
    consultar `ReminderWindow.objects.filter(is_active=True)` — así que un
    cambio de configuración nunca se reflejaba en una cita reprogramada.
    Ahora: (1) todo offset que ya no esté activo se cancela explícitamente
    (no se recalcula con una ventana obsoleta); (2) todo offset que sigue
    activo se recalcula contra la fecha vigente, igual que antes; (3) se
    reutiliza `schedule_appointment_reminders` (misma función que la
    creación original, no una segunda fuente de verdad) para materializar
    cualquier ventana activa nueva que la cita todavía no tenga — respeta
    elegibilidad (no crea para offsets ya vencidos) e idempotencia
    (`dedupe_key` evita duplicar lo que ya existe)."""
    now = dj_timezone.now()
    active_offsets = set(
        ReminderWindow.objects.filter(is_active=True).values_list("offset_days", flat=True)
    )
    affected = Notification.objects.filter(
        event_type=Notification.EventType.APPOINTMENT_REMINDER,
        resource_type=Notification.ResourceType.APPOINTMENT,
        resource_id=appointment.pk,
        status__in=[Notification.Status.PENDING, Notification.Status.FAILED],
        attempt_count__lt=MAX_DELIVERY_ATTEMPTS,
    )
    for notification in affected:
        offset_days = int(notification.dedupe_key.rsplit(":", 1)[-1])
        if offset_days not in active_offsets:
            # La ventana que originó esta fila ya no forma parte de la
            # configuración vigente (PD-004) — se cancela en vez de
            # recalcularse con un offset obsoleto.
            notification.status = Notification.Status.CANCELLED
            notification.reason_code = "REMINDER_WINDOW_NO_LONGER_ACTIVE"
            notification.save(update_fields=["status", "reason_code", "updated_at"])
            continue
        new_scheduled_for = appointment.start_at - dt.timedelta(days=offset_days)
        if new_scheduled_for <= now:
            notification.status = Notification.Status.CANCELLED
            notification.reason_code = "WINDOW_ELAPSED_AFTER_RESCHEDULE"
            notification.save(update_fields=["status", "reason_code", "updated_at"])
        else:
            notification.scheduled_for = new_scheduled_for
            notification.save(update_fields=["scheduled_for", "updated_at"])
    # Ventanas activas que esta cita todavía no tiene materializadas (p.
    # ej. la configuración creció, o cambió a offsets que esta cita nunca
    # tuvo) — se crean ahora con la misma función de creación original;
    # `dedupe_key` evita duplicar lo que el bucle de arriba ya recalculó.
    schedule_appointment_reminders(appointment)
    # Recordatorios para un destinatario que apareció después de la
    # reprogramación (p. ej. una relación de responsable activada
    # mientras tanto) no se retro-generan automáticamente: la próxima
    # `notify_appointment_modified` solo ajusta lo ya existente, igual que
    # documenta phase-6-notification-data-model.md §6 ("se recalculan
    # respecto de la fecha vigente", no "se regeneran desde cero").


def cancel_appointment_reminders(appointment):
    """Hallazgo 12.5: también cubre `FAILED` con reintentos restantes — no
    solo `PENDING` — por la misma razón que `reschedule_appointment_reminders`."""
    Notification.objects.filter(
        event_type=Notification.EventType.APPOINTMENT_REMINDER,
        resource_type=Notification.ResourceType.APPOINTMENT,
        resource_id=appointment.pk,
        status__in=[Notification.Status.PENDING, Notification.Status.FAILED],
        attempt_count__lt=MAX_DELIVERY_ATTEMPTS,
    ).update(status=Notification.Status.CANCELLED, reason_code="APPOINTMENT_CANCELLED")


# ---------------------------------------------------------------------------
# Procesamiento diferido (recordatorios + reintentos) — ITD-006
# ---------------------------------------------------------------------------



# REGISTRATION_INVITATION/EMAIL_VERIFICATION nunca se reintentan
# automáticamente: su contenido depende de un token/URL de un solo uso que
# solo existe en memoria en el momento del primer intento
# (`message_override`, ver `_attempt_send`) — no hay nada seguro que
# re-renderizar más tarde. Si fallan, permanecen FAILED y el flujo ya
# existente (reenviar invitación, reenviar verificación) es responsabilidad
# de `accounts`, no de este reintento genérico.
_RETRYABLE_EVENT_TYPES = [
    Notification.EventType.APPOINTMENT_CREATED,
    Notification.EventType.APPOINTMENT_MODIFIED,
    Notification.EventType.APPOINTMENT_CANCELLED,
    Notification.EventType.APPOINTMENT_REMINDER,
]


def process_due_notifications(now=None):
    """Punto de entrada del management command `process_due_notifications`
    (ITD-006: sin Celery/Redis — un comando Django pensado para ejecutarse
    vía cron del sistema operativo, consistente con
    docs/phases/phase-6-design-freeze.md §19/§24).

    Un recordatorio solo se envía si, al procesarlo, la cita sigue siendo
    elegible (docs/design/phase-6-notification-service-contracts.md §7).

    Concurrencia (docs/design/phase-6-notification-service-contracts.md §6):
    el reclamo de filas (`select_for_update(skip_locked=True)` + marca a
    `SENDING`) ocurre en una transacción corta y separada del envío real —
    el transporte (I/O de red) nunca se ejecuta con locks de fila
    retenidos, ni comparte el límite ACID con la reclamación (§5/§9/§21).

    PD-007 / hallazgo 12.3 y 12.4: una fila `PENDING`/`FAILED` solo se
    reclama si `attempt_count < MAX_DELIVERY_ATTEMPTS` (respeta el tope de
    reintentos) y su `scheduled_for` ya llegó (respeta el backoff aplicado
    por `_attempt_send`). Una fila `SENDING` cuyo `last_attempt_at` excede
    `SENDING_LEASE_TIMEOUT` se considera huérfana (proceso interrumpido a
    media ejecución) y se reclama igual — salvo que su tipo no sea
    reintentable, en cuyo caso se cierra como `FAILED` sin reenviar."""
    from django.db.models import Q

    from appointments.models import Appointment

    now = now or dj_timezone.now()
    stale_sending_cutoff = now - SENDING_LEASE_TIMEOUT

    with transaction.atomic():
        claimable = (
            Notification.objects.select_for_update(skip_locked=True)
            .filter(
                Q(
                    status__in=[Notification.Status.PENDING, Notification.Status.FAILED],
                    scheduled_for__lte=now,
                    attempt_count__lt=MAX_DELIVERY_ATTEMPTS,
                )
                | Q(status=Notification.Status.SENDING, last_attempt_at__lte=stale_sending_cutoff)
            )
            # Un fallo marcado PERMANENT (§3) es terminal de inmediato,
            # incluso si attempt_count todavía no llega al máximo — nunca
            # debe volver a reclamarse para un nuevo intento.
            .exclude(reason_code__startswith="PERMANENT:")
        )
        # Corrección (Prompt 1 de la ronda de corrección post-implementación,
        # docs/phases/phase-6-implementation-summary.md): la rama SENDING de
        # arriba, a diferencia de la de PENDING/FAILED, no filtraba por
        # `attempt_count` — una fila huérfana que ya había alcanzado
        # `MAX_DELIVERY_ATTEMPTS` en su último intento (proceso interrumpido
        # justo después de incrementar `attempt_count` pero antes de
        # persistir el resultado) podía reclamarse igual y recibir un sexto
        # intento real de envío. `.exclude(...)` cierra ese hueco: una
        # SENDING huérfana que ya agotó el máximo nunca entra a `due_ids`.
        due_ids = list(
            claimable.filter(event_type__in=_RETRYABLE_EVENT_TYPES)
            .exclude(status=Notification.Status.SENDING, attempt_count__gte=MAX_DELIVERY_ATTEMPTS)
            .values_list("pk", flat=True)
        )
        # Todo lo demás que sea SENDING huérfano (tipo no reintentable, o
        # tipo reintentable que ya agotó el máximo de intentos) se cierra
        # sin generar ningún intento adicional.
        closed_without_resend = list(
            claimable.filter(status=Notification.Status.SENDING)
            .exclude(pk__in=due_ids)
            .values_list("pk", "attempt_count")
        )
        closed_without_resend_ids = [pk for pk, _attempts in closed_without_resend]
        exhausted_ids = [pk for pk, attempts in closed_without_resend if attempts >= MAX_DELIVERY_ATTEMPTS]
        non_retryable_ids = [pk for pk in closed_without_resend_ids if pk not in exhausted_ids]
        # Reclamo inmediato: un worker concurrente que corra
        # `skip_locked=True` sobre las mismas filas ya no las verá
        # disponibles una vez que este bloque haga commit.
        Notification.objects.filter(pk__in=due_ids).update(status=Notification.Status.SENDING)
        Notification.objects.filter(pk__in=exhausted_ids).update(
            status=Notification.Status.FAILED, reason_code="MAX_ATTEMPTS_EXCEEDED:ORPHANED_SENDING",
        )
        Notification.objects.filter(pk__in=non_retryable_ids).update(
            status=Notification.Status.FAILED, reason_code="ORPHANED_NON_RETRYABLE_SENDING",
        )

    sent, skipped = 0, len(closed_without_resend_ids)
    for pk in due_ids:
        notification = Notification.objects.get(pk=pk)
        if notification.event_type == Notification.EventType.APPOINTMENT_REMINDER:
            appointment = Appointment.objects.filter(pk=notification.resource_id).first()
            eligible = appointment is not None and appointment.status == Appointment.Status.SCHEDULED
            if eligible and notification.recipient_user is not None:
                eligible = any(
                    user.pk == notification.recipient_user_id
                    for _role, user in _appointment_recipients(appointment, include_doctor=False)
                )
            if not eligible:
                notification.status = Notification.Status.CANCELLED
                notification.reason_code = "APPOINTMENT_OR_RECIPIENT_NO_LONGER_ELIGIBLE"
                notification.save(update_fields=["status", "reason_code", "updated_at"])
                skipped += 1
                continue
        _attempt_send(notification)
        sent += 1
    return {"sent": sent, "skipped": skipped}

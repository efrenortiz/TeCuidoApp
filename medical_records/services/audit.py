"""AH-153 — servicio central de auditoría clínica
(docs/design/clinical-audit-and-history.md). Toda emisión de
`AuditEvent` pasa por aquí: nunca disperso en vistas (AH-155) ni delegado
a signals de Django (AH-156) — el significado clínico de la acción lo
decide el servicio de dominio que llama a esta función, en el punto
exacto donde ya conoce el resultado real de la operación.

Dos puntos de entrada, por el requisito explícito de AH-088/089:

- `record_event` — para mutaciones. Se llama DENTRO del mismo
  `@transaction.atomic()` que la mutación que audita (AH-088: "se
  propone que la auditoría de éxito sea parte del mismo límite
  transaccional"). Si el registro de auditoría falla, la excepción se
  propaga y aborta la mutación completa — mejor perder la operación que
  dejar un cambio clínico sin rastro.
- `safe_record_event` — para lecturas. AH-089 prioriza no bloquear una
  lectura clínica legítima por una falla de un mecanismo auxiliar; un
  fallo aquí se registra en el logger de la aplicación y nunca se
  propaga.
"""

import logging

from django.db import transaction

from appointments.services.permissions import doctor_profile, patient_profile, responsible_profile
from medical_records.models import AuditEvent
from medical_records.services.exceptions import ClinicalNotAuthorized

logger = logging.getLogger("medical_records.audit")


def _actor_role(actor):
    """AH-098 — rol operativo observado al momento del evento."""
    if getattr(actor, "is_superuser", False):
        return "ADMINISTRATOR"
    if doctor_profile(actor) is not None:
        return "DOCTOR"
    if patient_profile(actor) is not None:
        return "PATIENT"
    if responsible_profile(actor) is not None:
        return "RESPONSIBLE"
    return "UNKNOWN"


def record_event(
    *, actor, action, result, resource_type, resource_id=None,
    patient=None, appointment=None, clinical_encounter=None, reason_code="",
):
    if actor is None:
        # AH-086 — el actor se deriva siempre de la sesión autenticada;
        # una operación clínica auditable nunca tiene actor ausente. Que
        # esto ocurra es un bug de propagación de identidad del llamador
        # (p. ej. un servicio que perdió el actor real en el camino), no
        # una condición de negocio válida — debe fallar aquí, de forma
        # clara, en vez de convertirse en un `IntegrityError` opaco de
        # PostgreSQL contra el NOT NULL de `actor_id`.
        raise ValueError(
            f"record_event requiere un actor real para {action!r}; "
            "actor=None nunca es válido (AH-086)."
        )
    return AuditEvent.objects.create(
        actor=actor,
        actor_role=_actor_role(actor),
        action=action,
        result=result,
        resource_type=resource_type,
        resource_id=resource_id,
        patient=patient,
        appointment=appointment,
        clinical_encounter=clinical_encounter,
        reason_code=reason_code,
    )


def safe_record_event(**kwargs):
    """`transaction.atomic()` aquí crea un SAVEPOINT (no una transacción
    nueva) cuando ya hay una transacción ambiente (p. ej. la del propio
    request, o la de un `TestCase`): si el `INSERT` falla, Postgres solo
    revierte hasta ese savepoint — sin este `atomic()`, un `IntegrityError`
    sin capturar mediante savepoint deja la conexión completa en estado
    "current transaction is aborted" hasta el próximo rollback externo,
    lo que rompería exactamente la lectura clínica que este helper existe
    para proteger (AH-089).

    AH-088 — la tolerancia de AH-089 cubre fallos reales del mecanismo
    auxiliar (p. ej. una indisponibilidad puntual de persistencia), no
    errores de programación del propio llamador. Un `actor=None` es lo
    segundo: se valida y se deja propagar *antes* de entrar al bloque
    tolerante, para que un bug de este tipo nunca quede maquillado como
    una auditoría exitosa silenciosa."""
    if kwargs.get("actor") is None:
        raise ValueError(
            "safe_record_event requiere un actor real para "
            f"{kwargs.get('action')!r}; actor=None nunca es válido (AH-086)."
        )
    try:
        with transaction.atomic():
            return record_event(**kwargs)
    except Exception:
        logger.exception("No se pudo registrar el evento de auditoría clínica: %s", kwargs.get("action"))
        return None


def list_audit_events(*, actor, patient=None, action=None, result=None, date_from=None, date_to=None):
    """AH-107/108/109/182 (cerrado) — sin endpoint público general;
    lectura restringida al Administrador, con los filtros mínimos que
    AH-111 pide (por paciente y/o por acción) y orden estable/paginable
    (AH-112/162: fecha descendente, id como desempate).

    Fase 6 (docs/design/phase-6-audit-service-contracts.md §7) amplía los
    filtros con `result`/`date_from`/`date_to` — misma frontera de
    servicio, sin crear una segunda función ni una segunda fuente de
    verdad de consulta."""
    from medical_records.services.permissions import can_view_audit_log

    if not can_view_audit_log(actor):
        raise ClinicalNotAuthorized()

    queryset = AuditEvent.objects.all()
    if patient is not None:
        queryset = queryset.filter(patient=patient)
    if action is not None:
        queryset = queryset.filter(action=action)
    if result is not None:
        queryset = queryset.filter(result=result)
    if date_from is not None:
        queryset = queryset.filter(occurred_at__gte=date_from)
    if date_to is not None:
        queryset = queryset.filter(occurred_at__lte=date_to)
    return queryset.order_by("-occurred_at", "-pk")

"""`ClinicalEncounterService` (docs/design/clinical-service-contracts.md §5-9).

Reuses `appointments.services.appointment.start_appointment()` /
`complete_appointment()` directly from inside this module's own
`@transaction.atomic()` blocks (Django nests atomic blocks as savepoints
on the same connection/transaction) instead of reimplementing Agenda's
own locking/authorization/state-transition logic — this is the ADR-008
integration strategy: the two `Appointment` transitions
(SCHEDULED→IN_CONSULTATION on start, IN_CONSULTATION→COMPLETED on
complete) and their paired `ClinicalEncounter` transitions commit or roll
back together as one real database transaction.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone as dj_timezone

from appointments.models import Appointment
from appointments.services import appointment as appointment_service
from appointments.services.permissions import doctor_profile, is_assigned_doctor
from medical_records.models import AuditEvent, ClinicalEncounter, MedicalRecord
from medical_records.services import audit
from medical_records.services import record as record_service
from medical_records.services.exceptions import (
    ClinicalContentPlaceholder,
    ClinicalNotAuthorized,
    ClinicalNotFound,
    EncounterAlreadyCompleted,
    EncounterNotStartable,
    IncompleteClinicalContent,
    InvalidClinicalData,
)
from medical_records.services.permissions import can_access_patient_record, can_read_encounter

# API-084 — ordenamiento clínico permitido, lista blanca explícita (nunca
# nombres de columna arbitrarios).
ALLOWED_ORDERINGS = ("started_at", "-started_at")

# R-053 — comparación insensible a mayúsculas/minúsculas y a espacios
# externos (R-051/R-054), ya normalizados antes de esta comparación.
_PLACEHOLDER_VALUES = {
    "n/a", "na", "no aplica", "sin datos", "ninguno", "-", "--", ".", "...",
    "no disponible", "desconocido",
}

# ADR-012 — los cinco campos obligatorios, nombres canónicos definitivos.
CORE_FIELDS = ("reason_for_visit", "present_illness", "physical_exam", "assessment", "plan")
# Campos opcionales de texto libre (clinical-encounter-domain.md §48) — sin
# reglas de contenido real (R-050-057 solo aplica a los cinco obligatorios,
# clinical-encounter-domain.md §17.1: "Al completar, los cinco campos
# obligatorios deben contener contenido clínico real").
OPTIONAL_TEXT_FIELDS = ("vital_signs", "relevant_history", "studies", "observations")
DECIMAL_FIELDS = ("weight_kg", "height_cm")
_ALLOWED_FIELDS = set(CORE_FIELDS) | set(OPTIONAL_TEXT_FIELDS) | set(DECIMAL_FIELDS)


def _is_placeholder(value):
    return value.strip().lower() in _PLACEHOLDER_VALUES


def _clean_payload(data):
    """SC-038/039 normalización, SC-040 placeholders (solo en los cinco
    campos obligatorios), SC-043 solo campos permitidos."""
    unknown = set(data) - _ALLOWED_FIELDS
    if unknown:
        raise InvalidClinicalData(f"Campos no permitidos: {sorted(unknown)}")

    cleaned = {}
    placeholder_fields = []
    for field in CORE_FIELDS + OPTIONAL_TEXT_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if not isinstance(value, str):
            raise InvalidClinicalData(f"El campo '{field}' debe ser texto.")
        value = value.strip()
        if field in CORE_FIELDS and value and _is_placeholder(value):
            placeholder_fields.append(field)
            continue
        cleaned[field] = value
    if placeholder_fields:
        # API-103 — se reportan todos los campos con placeholder de una
        # vez, no solo el primero encontrado.
        raise ClinicalContentPlaceholder(placeholder_fields)

    for field in DECIMAL_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if value is None:
            cleaned[field] = None
            continue
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise InvalidClinicalData(f"El campo '{field}' debe ser numérico.")
        if decimal_value <= 0:
            raise InvalidClinicalData(f"El campo '{field}' debe ser positivo.")
        cleaned[field] = decimal_value

    return cleaned


def start_encounter(*, actor, appointment):
    """SC-014 a SC-030. Auditoría AH-059/060/061/069: `record_event` se
    llama dentro de la misma transacción (AH-088) — si el evento
    `DENIED` se lanzara ahí, el `raise` inmediatamente después lo
    revertiría junto con todo lo demás, así que ese caso se audita
    FUERA del `with` (en el `except`), una vez que la transacción ya
    hizo rollback y una escritura nueva puede confirmarse de forma
    independiente."""
    now = dj_timezone.now()
    try:
        with transaction.atomic():
            locked_appointment = Appointment.objects.select_for_update().filter(pk=appointment.pk).first()
            if locked_appointment is None:
                raise ClinicalNotFound()

            if not is_assigned_doctor(actor, appointment=locked_appointment):
                raise ClinicalNotAuthorized()

            existing = ClinicalEncounter.objects.filter(appointment=locked_appointment).first()
            if existing is not None:
                # SC-022/SC-029 — segundo `start` sobre una cita ya
                # iniciada por esta misma operación es idempotente;
                # cualquier otra combinación (p. ej. encuentro ya
                # COMPLETED) no admite reiniciar (ADR-016, no reopen).
                # AH-061: la repetición idempotente no audita un nuevo
                # START_ENCOUNTER/SUCCESS (no es una nueva atención).
                if (
                    locked_appointment.status == Appointment.Status.IN_CONSULTATION
                    and existing.status == ClinicalEncounter.Status.IN_PROGRESS
                ):
                    return existing
                raise EncounterNotStartable()

            if locked_appointment.status != Appointment.Status.SCHEDULED:
                raise EncounterNotStartable()

            encounter = ClinicalEncounter.objects.create(
                appointment=locked_appointment,
                doctor=locked_appointment.doctor,
                status=ClinicalEncounter.Status.IN_PROGRESS,
                created_at=now,
                started_at=now,
            )
            # CR-002/003 — creación lazy del expediente en la primera
            # operación clínica real. `actor=None`: esta llamada es un
            # efecto interno de una operación ya autorizada arriba
            # (P-027, sin exigir `DoctorPatientRelationship` — P-031); no
            # es un punto de entrada protegido independiente (ver
            # docstring de `permissions.can_access_patient_record`).
            record_existed = MedicalRecord.objects.filter(patient=locked_appointment.patient).exists()
            record_service.get_or_create_for_patient(patient=locked_appointment.patient, actor=None)
            if not record_existed:
                # AH-069 — creación correlacionada con esta operación;
                # se audita aquí (con el actor real) en vez de dentro de
                # `get_or_create_for_patient(actor=None)`, que no conoce
                # a quién atribuir el evento cuando se le pide omitir la
                # autorización.
                audit.record_event(
                    actor=actor, action=AuditEvent.Action.CREATE_MEDICAL_RECORD, result=AuditEvent.Result.SUCCESS,
                    resource_type=AuditEvent.ResourceType.MEDICAL_RECORD, patient=locked_appointment.patient,
                )

            appointment_service.start_appointment(actor=actor, appointment=locked_appointment)

            audit.record_event(
                actor=actor, action=AuditEvent.Action.START_ENCOUNTER, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER, resource_id=encounter.pk,
                patient=locked_appointment.patient, appointment=locked_appointment, clinical_encounter=encounter,
            )
            return encounter
    except ClinicalNotAuthorized:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.START_ENCOUNTER, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.APPOINTMENT, resource_id=appointment.pk, appointment=appointment,
        )
        raise


def save_encounter(*, actor, encounter, data):
    """SC-031 a SC-047. Auditoría AH-062/063 — ver nota de
    `start_encounter` sobre por qué el evento `DENIED` se registra fuera
    del `with transaction.atomic()`."""
    try:
        with transaction.atomic():
            try:
                locked = ClinicalEncounter.objects.select_for_update().select_related(
                    "appointment"
                ).get(pk=encounter.pk)
            except ClinicalEncounter.DoesNotExist:
                # TS-155 — un id inexistente nunca debe convertirse en un
                # 500 ni revelar internals; se traduce al mismo
                # `ClinicalNotFound` ya usado en el resto del servicio
                # (start_encounter/get_encounter) para el caso "no existe".
                raise ClinicalNotFound() from None

            if not is_assigned_doctor(actor, appointment=locked.appointment):
                raise ClinicalNotAuthorized()

            if locked.status != ClinicalEncounter.Status.IN_PROGRESS:
                # Solo dos estados existen (ADR-010); "no IN_PROGRESS" en
                # este dominio siempre significa COMPLETED (SC-046).
                raise EncounterAlreadyCompleted()

            cleaned = _clean_payload(data)
            for field, value in cleaned.items():
                setattr(locked, field, value)
            locked.save()

            audit.record_event(
                actor=actor, action=AuditEvent.Action.SAVE_ENCOUNTER, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER, resource_id=locked.pk,
                patient=locked.patient, appointment=locked.appointment, clinical_encounter=locked,
            )
            return locked
    except ClinicalNotAuthorized:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.SAVE_ENCOUNTER, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER, resource_id=encounter.pk, clinical_encounter=encounter,
        )
        raise


def complete_encounter(*, actor, encounter, data):
    """SC-048 a SC-065. Auditoría AH-064/065 — `COMPLETE_ENCOUNTER/SUCCESS`
    solo se emite después de que `appointment_service.complete_appointment`
    ya confirmó `Appointment → COMPLETED` dentro de la misma transacción;
    si cualquier paso previo falla, no hay evento de éxito (AH-184)."""
    now = dj_timezone.now()
    try:
        with transaction.atomic():
            try:
                locked = ClinicalEncounter.objects.select_for_update().select_related(
                    "appointment", "appointment__doctor"
                ).get(pk=encounter.pk)
            except ClinicalEncounter.DoesNotExist:
                # TS-155 — ver la nota equivalente en save_encounter.
                raise ClinicalNotFound() from None

            if not is_assigned_doctor(actor, appointment=locked.appointment):
                raise ClinicalNotAuthorized()

            cleaned = _clean_payload(data)

            if locked.status == ClinicalEncounter.Status.COMPLETED:
                # SC-065/D-001 — repetición exacta es éxito idempotente;
                # contenido distinto sobre un encuentro ya cerrado se
                # rechaza como `EncounterAlreadyCompleted` (SC-136 —
                # nombre resuelto: la prosa de SC-065 menciona
                # "EncounterImmutable", que no existe en la taxonomía
                # cerrada de §19; SC-136 describe exactamente este caso
                # — "ya se cerró y no admite nuevas mutaciones" — así
                # que se usa ese nombre, ya definitivo). AH-061 aplica
                # por analogía: la repetición idempotente no genera un
                # segundo COMPLETE_ENCOUNTER/SUCCESS.
                if all(getattr(locked, field) == value for field, value in cleaned.items()):
                    return locked
                raise EncounterAlreadyCompleted()

            for field, value in cleaned.items():
                setattr(locked, field, value)

            missing_fields = [field for field in CORE_FIELDS if not getattr(locked, field)]
            if missing_fields:
                raise IncompleteClinicalContent(missing_fields)

            locked.status = ClinicalEncounter.Status.COMPLETED
            locked.completed_at = now
            locked.save()

            appointment_service.complete_appointment(actor=actor, appointment=locked.appointment)

            audit.record_event(
                actor=actor, action=AuditEvent.Action.COMPLETE_ENCOUNTER, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER, resource_id=locked.pk,
                patient=locked.patient, appointment=locked.appointment, clinical_encounter=locked,
            )
            return locked
    except ClinicalNotAuthorized:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.COMPLETE_ENCOUNTER, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER, resource_id=encounter.pk, clinical_encounter=encounter,
        )
        raise


def get_encounter(*, actor, encounter_id):
    """SC-066 a SC-071. AH-067 — lectura auditable; AH-089 — una lectura
    nunca se bloquea por un fallo del mecanismo de auditoría
    (`safe_record_event`, nunca `record_event`, aquí)."""
    encounter = ClinicalEncounter.objects.select_related(
        "appointment", "appointment__doctor", "doctor"
    ).filter(pk=encounter_id).first()
    if encounter is None:
        raise ClinicalNotFound()
    if not can_read_encounter(actor, encounter):
        # SC-068/AH-078/079 — nunca se distingue "no existe" de "no
        # autorizado" en la respuesta; el evento de auditoría SÍ puede
        # conservar internamente cuál fue el caso (P-041: solo lo lee el
        # Administrador).
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.READ_CLINICAL_ENCOUNTER, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER, resource_id=encounter.pk,
            patient=encounter.patient, clinical_encounter=encounter,
        )
        raise ClinicalNotFound()

    audit.safe_record_event(
        actor=actor, action=AuditEvent.Action.READ_CLINICAL_ENCOUNTER, result=AuditEvent.Result.SUCCESS,
        resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER, resource_id=encounter.pk,
        patient=encounter.patient, clinical_encounter=encounter,
    )
    return encounter


def list_encounters_for_patient(*, actor, patient, ordering="-started_at"):
    """`ClinicalHistoryService` (SC-093 a SC-098) — historial paginable en
    orden determinista (SC-086/API-079/API-084). Misma autorización
    "longitudinal" que `record.get_medical_record` (SC-084/API-082): un
    médico necesita relación activa (P-013); paciente/responsable solo ven
    encuentros `COMPLETED` (P-017/018) — nunca uno `IN_PROGRESS` ajeno o
    propio en curso. AH-026/072 — lectura longitudinal auditable; AH-089
    — nunca bloqueada por un fallo de auditoría."""
    if not can_access_patient_record(actor, patient):
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.READ_CLINICAL_HISTORY, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.CLINICAL_HISTORY, patient=patient,
        )
        raise ClinicalNotAuthorized()

    if ordering not in ALLOWED_ORDERINGS:
        raise InvalidClinicalData(f"ordering no soportado: {ordering!r}")

    queryset = ClinicalEncounter.objects.filter(appointment__patient=patient).select_related(
        "appointment", "appointment__doctor", "doctor"
    )
    if doctor_profile(actor) is None:
        queryset = queryset.filter(status=ClinicalEncounter.Status.COMPLETED)

    tie_break = "-pk" if ordering.startswith("-") else "pk"

    audit.safe_record_event(
        actor=actor, action=AuditEvent.Action.READ_CLINICAL_HISTORY, result=AuditEvent.Result.SUCCESS,
        resource_type=AuditEvent.ResourceType.CLINICAL_HISTORY, patient=patient,
    )
    return queryset.order_by(ordering, tie_break)

"""`MedicalRecordService` (docs/design/clinical-service-contracts.md §10-12)."""

from django.db import transaction

from medical_records.models import AuditEvent, MedicalRecord
from medical_records.services import audit
from medical_records.services.exceptions import (
    ClinicalNotAuthorized,
    ClinicalRecordNotFound,
    InvalidClinicalData,
)
from medical_records.services.permissions import can_access_patient_record, can_edit_patient_record

# clinical-record-domain.md §5.1 / DM-015 — los seis campos longitudinales,
# todos opcionales.
RECORD_FIELDS = (
    "family_history",
    "personal_pathological_history",
    "personal_non_pathological_history",
    "housing_history",
    "gynecologic_obstetric_history",
    "other_relevant_history",
)


def get_or_create_for_patient(*, patient, actor=None):
    """SC-074/075/076/077 — creación lazy e idempotente. `get_or_create`
    ya tolera la carrera de creación concurrente (reintenta el `get` tras
    un `IntegrityError` de la unicidad de `patient`), sin necesidad de
    bloqueo manual (SC-075).

    AH-069 — la creación se audita aquí solo cuando esta función actúa
    como su propio punto de entrada protegido (`actor` no es `None`). La
    llamada interna de `start_encounter` (`actor=None`) audita la
    creación ella misma, con el actor real — ver esa función."""
    if actor is not None and not can_access_patient_record(actor, patient):
        raise ClinicalNotAuthorized()
    record, created = MedicalRecord.objects.get_or_create(patient=patient)
    if created and actor is not None:
        audit.record_event(
            actor=actor, action=AuditEvent.Action.CREATE_MEDICAL_RECORD, result=AuditEvent.Result.SUCCESS,
            resource_type=AuditEvent.ResourceType.MEDICAL_RECORD, resource_id=record.pk, patient=patient,
        )
    return record


def get_medical_record(*, actor, patient):
    """SC-083/083a/084 — lectura pura; nunca dispara creación lazy (D-005).
    Ausencia se representa como `None`, no como excepción (la traducción a
    404 es responsabilidad de la capa de API, no de este servicio).
    AH-025/073/074/075 — lectura auditable; AH-089 nunca bloqueada por un
    fallo de auditoría."""
    if not can_access_patient_record(actor, patient):
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.READ_MEDICAL_RECORD, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.MEDICAL_RECORD, patient=patient,
        )
        raise ClinicalNotAuthorized()
    record = MedicalRecord.objects.filter(patient=patient).first()
    audit.safe_record_event(
        actor=actor, action=AuditEvent.Action.READ_MEDICAL_RECORD, result=AuditEvent.Result.SUCCESS,
        resource_type=AuditEvent.ResourceType.MEDICAL_RECORD, resource_id=record.pk if record else None,
        patient=patient,
    )
    return record


def update_medical_record(*, actor, patient, data):
    """SC-088 a SC-092 / API-095 — a diferencia de
    `get_or_create_for_patient`, esta operación NUNCA crea el expediente:
    `clinical-api-contracts.md` API-095 cierra explícitamente que el PATCH
    de expediente longitudinal "no crea silenciosamente un expediente...
    si se requiere creación, debe existir una operación interna de
    servicio explícita" — esa operación explícita es
    `get_or_create_for_patient` (disparada solo por `start_encounter`),
    no esta. Si el expediente aún no existe, se rechaza con
    `ClinicalRecordNotFound`. AH-027/070/071 — toda actualización
    persistida genera `UPDATE_MEDICAL_RECORD`, sin duplicar los valores
    completos del expediente en el evento."""
    if not can_edit_patient_record(actor, patient):
        # Autorización resuelta antes de abrir la transacción — sin
        # riesgo de que un rollback posterior descarte este evento (a
        # diferencia de los casos en encounter.py).
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.UPDATE_MEDICAL_RECORD, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.MEDICAL_RECORD, patient=patient,
        )
        raise ClinicalNotAuthorized()

    unknown = set(data) - set(RECORD_FIELDS)
    if unknown:
        raise InvalidClinicalData(f"Campos no permitidos: {sorted(unknown)}")

    cleaned = {}
    for field in RECORD_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if not isinstance(value, str):
            raise InvalidClinicalData(f"El campo '{field}' debe ser texto.")
        cleaned[field] = value.strip()

    with transaction.atomic():
        record = MedicalRecord.objects.select_for_update().filter(patient=patient).first()
        if record is None:
            raise ClinicalRecordNotFound()
        for field, value in cleaned.items():
            setattr(record, field, value)
        record.save()
        audit.record_event(
            actor=actor, action=AuditEvent.Action.UPDATE_MEDICAL_RECORD, result=AuditEvent.Result.SUCCESS,
            resource_type=AuditEvent.ResourceType.MEDICAL_RECORD, resource_id=record.pk, patient=patient,
        )
        return record

"""`PrescriptionService` (docs/design/phase-4-service-contracts.md §2/3,
ADR-022/023/028/029).

Frontera: `UI/API → Service → Authorization → Transaction → ORM/PostgreSQL`
(mismo patrón que `medical_records.services.encounter`). `patient` nunca se
acepta como parámetro independiente del cliente (D-003) — siempre se deriva
de `clinical_encounter.appointment.patient`.

Generación de PDF/`ClinicalDocument` diferida a Stage 3 (`clinical_documents`)
por diseño — `issue`/`create_version` invocan
`clinical_documents.services.document.create_generated_document` dentro de
la misma transacción una vez que ese servicio exista.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone

from clinical_documents.models import ClinicalDocument
from clinical_documents.services import document as document_service
from clinical_documents.services import pdf as pdf_service
from medical_records.models import AuditEvent
from medical_records.services import audit
from medical_records.services.exceptions import (
    DocumentConflict,
    DocumentImmutableResource,
    DocumentInvalidState,
    DocumentNotFound,
    DocumentPermissionDenied,
    DocumentValidationError,
)
from medical_records.services.permissions import (
    can_correct_or_void_document,
    can_issue_document_for_encounter,
    can_read_document_resource,
    doctor_profile,
)
from prescriptions.models import Prescription, PrescriptionItem

ITEM_FIELDS = ("medication_name", "presentation", "dose", "dose_unit", "route", "frequency", "duration", "instructions")
REQUIRED_ITEM_FIELDS = ("medication_name", "dose", "route", "frequency")


def _clean_items(items):
    """PR-002/PR-003 — al menos un item; campos explícitos, sin catálogo."""
    if not items:
        raise DocumentValidationError("Una receta requiere al menos un PrescriptionItem.")
    cleaned = []
    for index, raw in enumerate(items, start=1):
        unknown = set(raw) - set(ITEM_FIELDS)
        if unknown:
            raise DocumentValidationError(f"Campos no permitidos en item: {sorted(unknown)}")
        missing = [f for f in REQUIRED_ITEM_FIELDS if not raw.get(f)]
        if missing:
            raise DocumentValidationError(f"Campos obligatorios ausentes en item {index}: {missing}")
        cleaned.append({field: raw.get(field, "") for field in ITEM_FIELDS})
    return cleaned


def _idempotent_replay_matches(existing, *, clinical_encounter):
    return existing.clinical_encounter_id == clinical_encounter.pk


def issue(*, actor, clinical_encounter, items, idempotency_key=""):
    """SC-003 (por analogía a Fase 3) — emisión atómica: Prescription +
    items + auditoría. Autorización: médico asignado al encuentro
    (ADR-028/ADR-022)."""
    if idempotency_key:
        existing = Prescription.objects.filter(
            doctor=clinical_encounter.doctor, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            if not _idempotent_replay_matches(existing, clinical_encounter=clinical_encounter):
                raise DocumentConflict("idempotency_key reutilizado para una intención distinta.")
            return existing

    if not can_issue_document_for_encounter(actor, clinical_encounter):
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.ISSUE_PRESCRIPTION, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.PRESCRIPTION,
            patient=clinical_encounter.patient, clinical_encounter=clinical_encounter,
        )
        raise DocumentPermissionDenied()

    cleaned_items = _clean_items(items)

    try:
        with transaction.atomic():
            prescription = Prescription.objects.create(
                patient=clinical_encounter.patient,
                doctor=clinical_encounter.doctor,
                clinical_encounter=clinical_encounter,
                status=Prescription.Status.ISSUED,
                issued_at=dj_timezone.now(),
                idempotency_key=idempotency_key,
            )
            for position, item in enumerate(cleaned_items, start=1):
                PrescriptionItem.objects.create(prescription=prescription, position=position, **item)

            audit.record_event(
                actor=actor, action=AuditEvent.Action.ISSUE_PRESCRIPTION, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.PRESCRIPTION, resource_id=prescription.pk,
                patient=prescription.patient, appointment=clinical_encounter.appointment,
                clinical_encounter=clinical_encounter,
            )

            # ADR-027 — el PDF se genera y el ClinicalDocument se crea DENTRO
            # de esta misma transacción: si algo falla después, la receta
            # nunca queda "emitida" sin su representación documental.
            pdf_bytes = pdf_service.render_prescription_pdf(prescription)
            document_service.create_generated_document(
                actor=actor, patient=prescription.patient, document_type=ClinicalDocument.DocumentType.PRESCRIPTION,
                content=pdf_bytes, mime_type="application/pdf", original_filename=f"receta-{prescription.pk}.pdf",
                appointment=clinical_encounter.appointment, clinical_encounter=clinical_encounter,
                prescription=prescription,
            )
            return prescription
    except IntegrityError:
        # Carrera real (Gate 7): dos peticiones con el mismo
        # Idempotency-Key pasaron ambas la comprobación inicial (sin
        # lock) antes de que cualquiera confirmara. La que pierde la
        # carrera del UNIQUE constraint replica el resultado de la
        # ganadora en vez de propagar un IntegrityError crudo — mismo
        # criterio que `appointments.services.appointment.create_appointment_from_hold`.
        if not idempotency_key:
            raise
        existing = Prescription.objects.filter(
            doctor=clinical_encounter.doctor, idempotency_key=idempotency_key
        ).first()
        if existing is None or not _idempotent_replay_matches(existing, clinical_encounter=clinical_encounter):
            raise
        return existing


def get(*, actor, prescription_id):
    """SC-lectura (ADR-028): médico asignado al encuentro de origen, médico
    con relación activa, paciente propio o responsable activo."""
    prescription = Prescription.objects.select_related(
        "clinical_encounter", "clinical_encounter__appointment"
    ).filter(pk=prescription_id).first()
    if prescription is None:
        raise DocumentNotFound()
    if not can_read_document_resource(actor, prescription.patient, prescription.clinical_encounter):
        raise DocumentNotFound()
    return prescription


def list_for_patient(*, actor, patient):
    """Historial de recetas del paciente — misma regla de autorización que
    `get`, evaluada sobre el paciente (sin encuentro concreto: sólo el
    camino de relación activa/paciente propio/responsable aplica)."""
    if not can_read_document_resource(actor, patient):
        raise DocumentPermissionDenied()
    return Prescription.objects.filter(patient=patient).order_by("-issued_at", "-pk")


def create_version(*, actor, prescription_id, items, reason):
    """ADR-023 — nueva fila, `select_for_update` sobre la versión actual;
    rechaza con `ImmutableResource` si ya no es la vigente.

    El evento `DENIED` se registra FUERA del `with transaction.atomic()`
    (en el `except`), igual que `medical_records.services.encounter`: si se
    auditara dentro, el `raise` inmediatamente posterior revertiría también
    ese registro junto con todo lo demás."""
    cleaned_items = _clean_items(items)
    try:
        with transaction.atomic():
            current = Prescription.objects.select_for_update().filter(pk=prescription_id).first()
            if current is None:
                raise DocumentNotFound()
            if not can_correct_or_void_document(actor, current.clinical_encounter):
                raise DocumentPermissionDenied()
            if current.status == Prescription.Status.VOIDED:
                raise DocumentInvalidState("No se puede versionar una receta anulada.")
            if not current.is_current_version:
                raise DocumentImmutableResource("La versión indicada ya no es la vigente.")

            current.is_current_version = False
            current.save(update_fields=["is_current_version"])

            new_version = Prescription.objects.create(
                patient=current.patient,
                doctor=current.doctor,
                clinical_encounter=current.clinical_encounter,
                status=Prescription.Status.ISSUED,
                issued_at=dj_timezone.now(),
                version_number=current.version_number + 1,
                previous_version=current,
                is_current_version=True,
            )
            for position, item in enumerate(cleaned_items, start=1):
                PrescriptionItem.objects.create(prescription=new_version, position=position, **item)

            audit.record_event(
                actor=actor, action=AuditEvent.Action.CREATE_DOCUMENT_VERSION, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.PRESCRIPTION, resource_id=new_version.pk,
                patient=new_version.patient, clinical_encounter=new_version.clinical_encounter,
                reason_code=reason[:60] if reason else "",
            )

            pdf_bytes = pdf_service.render_prescription_pdf(new_version)
            document_service.create_generated_document(
                actor=actor, patient=new_version.patient, document_type=ClinicalDocument.DocumentType.PRESCRIPTION,
                content=pdf_bytes, mime_type="application/pdf",
                original_filename=f"receta-{new_version.pk}-v{new_version.version_number}.pdf",
                appointment=new_version.clinical_encounter.appointment,
                clinical_encounter=new_version.clinical_encounter, prescription=new_version,
            )
            return new_version
    except DocumentPermissionDenied:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.CREATE_DOCUMENT_VERSION, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.PRESCRIPTION, resource_id=prescription_id,
        )
        raise


def void(*, actor, prescription_id, reason):
    """PR-007/SC-065 (por analogía) — idempotente ante repetición exacta;
    `InvalidState` ante una repetición con motivo distinto sobre un
    recurso ya `VOIDED`. Mismo criterio que `create_version` sobre dónde
    se audita el `DENIED`."""
    try:
        with transaction.atomic():
            prescription = Prescription.objects.select_for_update().filter(pk=prescription_id).first()
            if prescription is None:
                raise DocumentNotFound()
            if not can_correct_or_void_document(actor, prescription.clinical_encounter):
                raise DocumentPermissionDenied()

            if prescription.status == Prescription.Status.VOIDED:
                if prescription.void_reason == reason:
                    return prescription
                raise DocumentInvalidState("La receta ya está anulada con un motivo distinto.")

            doctor = doctor_profile(actor)
            prescription.status = Prescription.Status.VOIDED
            prescription.voided_at = dj_timezone.now()
            prescription.voided_by = doctor
            prescription.void_reason = reason
            prescription.save(update_fields=["status", "voided_at", "voided_by", "void_reason"])

            audit.record_event(
                actor=actor, action=AuditEvent.Action.VOID_PRESCRIPTION, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.PRESCRIPTION, resource_id=prescription.pk,
                patient=prescription.patient, reason_code=reason[:60] if reason else "",
            )
            return prescription
    except DocumentPermissionDenied:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.VOID_PRESCRIPTION, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.PRESCRIPTION, resource_id=prescription_id,
        )
        raise

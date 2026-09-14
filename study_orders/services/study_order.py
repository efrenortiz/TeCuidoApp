"""`StudyOrderService` — mismo patrón que `prescriptions.services.prescription`
(ver ese módulo para el razonamiento completo de autorización, idempotencia,
versionado y dónde se audita el `DENIED`)."""

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
from study_orders.models import StudyOrder, StudyOrderItem

ITEM_FIELDS = ("study_name", "specific_instructions")
VALID_STUDY_TYPES = {choice for choice, _ in StudyOrder.StudyType.choices}


def _clean_items(items):
    """SO-002/SO-003 — al menos un item; sin catálogo obligatorio."""
    if not items:
        raise DocumentValidationError("Una solicitud requiere al menos un StudyOrderItem.")
    cleaned = []
    for index, raw in enumerate(items, start=1):
        unknown = set(raw) - set(ITEM_FIELDS)
        if unknown:
            raise DocumentValidationError(f"Campos no permitidos en item: {sorted(unknown)}")
        if not raw.get("study_name"):
            raise DocumentValidationError(f"'study_name' es obligatorio en item {index}.")
        cleaned.append({field: raw.get(field, "") for field in ITEM_FIELDS})
    return cleaned


def _idempotent_replay_matches(existing, *, clinical_encounter):
    return existing.clinical_encounter_id == clinical_encounter.pk


def issue(*, actor, clinical_encounter, study_type, items, indications="", observations="", idempotency_key=""):
    if study_type not in VALID_STUDY_TYPES:
        raise DocumentValidationError(f"study_type inválido: {study_type!r}")

    if idempotency_key:
        existing = StudyOrder.objects.filter(
            doctor=clinical_encounter.doctor, idempotency_key=idempotency_key
        ).first()
        if existing is not None:
            if not _idempotent_replay_matches(existing, clinical_encounter=clinical_encounter):
                raise DocumentConflict("idempotency_key reutilizado para una intención distinta.")
            return existing

    if not can_issue_document_for_encounter(actor, clinical_encounter):
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.ISSUE_STUDY_ORDER, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.STUDY_ORDER,
            patient=clinical_encounter.patient, clinical_encounter=clinical_encounter,
        )
        raise DocumentPermissionDenied()

    cleaned_items = _clean_items(items)

    try:
        with transaction.atomic():
            order = StudyOrder.objects.create(
                patient=clinical_encounter.patient,
                doctor=clinical_encounter.doctor,
                clinical_encounter=clinical_encounter,
                status=StudyOrder.Status.ISSUED,
                study_type=study_type,
                indications=indications,
                observations=observations,
                issued_at=dj_timezone.now(),
                idempotency_key=idempotency_key,
            )
            for position, item in enumerate(cleaned_items, start=1):
                StudyOrderItem.objects.create(study_order=order, position=position, **item)

            audit.record_event(
                actor=actor, action=AuditEvent.Action.ISSUE_STUDY_ORDER, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.STUDY_ORDER, resource_id=order.pk,
                patient=order.patient, appointment=clinical_encounter.appointment,
                clinical_encounter=clinical_encounter,
            )

            pdf_bytes = pdf_service.render_study_order_pdf(order)
            document_service.create_generated_document(
                actor=actor, patient=order.patient, document_type=ClinicalDocument.DocumentType.STUDY_ORDER,
                content=pdf_bytes, mime_type="application/pdf", original_filename=f"solicitud-{order.pk}.pdf",
                appointment=clinical_encounter.appointment, clinical_encounter=clinical_encounter,
                study_order=order,
            )
            return order
    except IntegrityError:
        # Carrera real (Gate 7) — ver la nota equivalente en
        # prescriptions.services.prescription.issue.
        if not idempotency_key:
            raise
        existing = StudyOrder.objects.filter(
            doctor=clinical_encounter.doctor, idempotency_key=idempotency_key
        ).first()
        if existing is None or not _idempotent_replay_matches(existing, clinical_encounter=clinical_encounter):
            raise
        return existing


def get(*, actor, study_order_id):
    order = StudyOrder.objects.select_related(
        "clinical_encounter", "clinical_encounter__appointment"
    ).filter(pk=study_order_id).first()
    if order is None:
        raise DocumentNotFound()
    if not can_read_document_resource(actor, order.patient, order.clinical_encounter):
        raise DocumentNotFound()
    return order


def list_for_patient(*, actor, patient):
    if not can_read_document_resource(actor, patient):
        raise DocumentPermissionDenied()
    return StudyOrder.objects.filter(patient=patient).order_by("-issued_at", "-pk")


def create_version(*, actor, study_order_id, items, reason, indications=None, observations=None):
    cleaned_items = _clean_items(items)
    try:
        with transaction.atomic():
            current = StudyOrder.objects.select_for_update().filter(pk=study_order_id).first()
            if current is None:
                raise DocumentNotFound()
            if not can_correct_or_void_document(actor, current.clinical_encounter):
                raise DocumentPermissionDenied()
            if current.status == StudyOrder.Status.VOIDED:
                raise DocumentInvalidState("No se puede versionar una solicitud anulada.")
            if not current.is_current_version:
                raise DocumentImmutableResource("La versión indicada ya no es la vigente.")

            current.is_current_version = False
            current.save(update_fields=["is_current_version"])

            new_version = StudyOrder.objects.create(
                patient=current.patient,
                doctor=current.doctor,
                clinical_encounter=current.clinical_encounter,
                status=StudyOrder.Status.ISSUED,
                study_type=current.study_type,
                indications=current.indications if indications is None else indications,
                observations=current.observations if observations is None else observations,
                issued_at=dj_timezone.now(),
                version_number=current.version_number + 1,
                previous_version=current,
                is_current_version=True,
            )
            for position, item in enumerate(cleaned_items, start=1):
                StudyOrderItem.objects.create(study_order=new_version, position=position, **item)

            audit.record_event(
                actor=actor, action=AuditEvent.Action.CREATE_DOCUMENT_VERSION, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.STUDY_ORDER, resource_id=new_version.pk,
                patient=new_version.patient, clinical_encounter=new_version.clinical_encounter,
                reason_code=reason[:60] if reason else "",
            )

            pdf_bytes = pdf_service.render_study_order_pdf(new_version)
            document_service.create_generated_document(
                actor=actor, patient=new_version.patient, document_type=ClinicalDocument.DocumentType.STUDY_ORDER,
                content=pdf_bytes, mime_type="application/pdf",
                original_filename=f"solicitud-{new_version.pk}-v{new_version.version_number}.pdf",
                appointment=new_version.clinical_encounter.appointment,
                clinical_encounter=new_version.clinical_encounter, study_order=new_version,
            )
            return new_version
    except DocumentPermissionDenied:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.CREATE_DOCUMENT_VERSION, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.STUDY_ORDER, resource_id=study_order_id,
        )
        raise


def void(*, actor, study_order_id, reason):
    try:
        with transaction.atomic():
            order = StudyOrder.objects.select_for_update().filter(pk=study_order_id).first()
            if order is None:
                raise DocumentNotFound()
            if not can_correct_or_void_document(actor, order.clinical_encounter):
                raise DocumentPermissionDenied()

            if order.status == StudyOrder.Status.VOIDED:
                if order.void_reason == reason:
                    return order
                raise DocumentInvalidState("La solicitud ya está anulada con un motivo distinto.")

            doctor = doctor_profile(actor)
            order.status = StudyOrder.Status.VOIDED
            order.voided_at = dj_timezone.now()
            order.voided_by = doctor
            order.void_reason = reason
            order.save(update_fields=["status", "voided_at", "voided_by", "void_reason"])

            audit.record_event(
                actor=actor, action=AuditEvent.Action.VOID_STUDY_ORDER, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.STUDY_ORDER, resource_id=order.pk,
                patient=order.patient, reason_code=reason[:60] if reason else "",
            )
            return order
    except DocumentPermissionDenied:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.VOID_STUDY_ORDER, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.STUDY_ORDER, resource_id=study_order_id,
        )
        raise

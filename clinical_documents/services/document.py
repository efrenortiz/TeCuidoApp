"""`ClinicalDocumentService` (docs/design/phase-4-service-contracts.md §2,
ADR-025/026/027).

`create_generated_document` es deliberadamente genérico (no importa
`prescriptions`/`study_orders`): recibe instancias ya resueltas por el
llamador. Se invoca DESDE el `with transaction.atomic()` de
`PrescriptionService.issue`/`create_version` (y su análogo de
`StudyOrderService`) — Django anida `atomic()` como SAVEPOINT, así que el
documento generado y la receta/solicitud que lo origina comparten la misma
transacción real: si algo falla después, ambos se revierten juntos (más
fuerte que la compensación best-effort que sí necesita `upload`, que no
tiene una transacción padre preexistente)."""

from django.db import transaction
from django.utils import timezone as dj_timezone

from clinical_documents.models import ClinicalDocument
from clinical_documents.services import storage
from medical_records.models import AuditEvent
from medical_records.services import audit
from medical_records.services.exceptions import (
    DocumentImmutableResource,
    DocumentInvalidState,
    DocumentNotFound,
    DocumentPermissionDenied,
    DocumentValidationError,
)
from medical_records.services.permissions import (
    can_correct_or_void_document,
    can_read_document_resource,
)


def create_generated_document(
    *, actor, patient, document_type, content, mime_type, original_filename,
    appointment=None, clinical_encounter=None, prescription=None, study_order=None,
):
    """Debe llamarse dentro de la transacción del servicio que emite el
    recurso de origen (Prescription/StudyOrder) — ver docstring del
    módulo. No valida MIME por contenido (el PDF lo genera la propia
    aplicación, no un usuario) — `storage.save` sí puede fallar por I/O,
    y ese fallo revierte también al recurso de origen."""
    storage_key = storage.build_storage_key(mime_type=mime_type)
    storage.save(storage_key=storage_key, content=content)

    document = ClinicalDocument.objects.create(
        patient=patient, appointment=appointment, clinical_encounter=clinical_encounter,
        prescription=prescription, study_order=study_order,
        document_type=document_type, origin=ClinicalDocument.Origin.GENERATED, status=None,
        original_filename=original_filename, storage_key=storage_key, mime_type=mime_type,
        size_bytes=len(content), created_by=actor,
    )
    audit.record_event(
        actor=actor, action=AuditEvent.Action.GENERATE_CLINICAL_DOCUMENT, result=AuditEvent.Result.SUCCESS,
        resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=document.pk,
        patient=patient, appointment=appointment, clinical_encounter=clinical_encounter,
    )
    return document


def upload(
    *, actor, patient, content, original_filename, document_type,
    appointment=None, clinical_encounter=None,
):
    """CD-007 — documento standalone (`UPLOADED`, `status=ACTIVE`). El
    archivo se valida y se escribe ANTES de abrir la transacción (no hay
    una transacción padre que lo proteja, a diferencia de
    `create_generated_document`); si la fila falla después, se compensa
    con un borrado best-effort (ADR-027 §6)."""
    if not can_read_document_resource(actor, patient, clinical_encounter):
        raise DocumentPermissionDenied()

    mime_type = storage.validate_and_detect_mime(content=content, declared_filename=original_filename)
    storage_key = storage.build_storage_key(mime_type=mime_type)
    storage.save(storage_key=storage_key, content=content)

    try:
        with transaction.atomic():
            document = ClinicalDocument.objects.create(
                patient=patient, appointment=appointment, clinical_encounter=clinical_encounter,
                document_type=document_type, origin=ClinicalDocument.Origin.UPLOADED,
                status=ClinicalDocument.Status.ACTIVE,
                original_filename=original_filename, storage_key=storage_key, mime_type=mime_type,
                size_bytes=len(content), created_by=actor,
                version_number=1, is_current_version=True,
            )
            audit.record_event(
                actor=actor, action=AuditEvent.Action.UPLOAD_CLINICAL_DOCUMENT, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=document.pk,
                patient=patient, appointment=appointment, clinical_encounter=clinical_encounter,
            )
            return document
    except Exception:
        storage.delete_best_effort(storage_key=storage_key)
        raise


def get(*, actor, document_id):
    """AH-089-style: la lectura siempre se intenta auditar (safe_record_event
    tolera un fallo del mecanismo auxiliar, nunca la ausencia del intento —
    ver corrección M-02 de la revisión documental)."""
    document = ClinicalDocument.objects.select_related("clinical_encounter", "clinical_encounter__appointment").filter(
        pk=document_id
    ).first()
    if document is None:
        raise DocumentNotFound()
    if not can_read_document_resource(actor, document.patient, document.clinical_encounter):
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.READ_CLINICAL_DOCUMENT, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=document.pk,
            patient=document.patient,
        )
        raise DocumentNotFound()

    audit.safe_record_event(
        actor=actor, action=AuditEvent.Action.READ_CLINICAL_DOCUMENT, result=AuditEvent.Result.SUCCESS,
        resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=document.pk,
        patient=document.patient,
    )
    return document


def list_for_patient(*, actor, patient, document_type=None):
    if not can_read_document_resource(actor, patient):
        raise DocumentPermissionDenied()
    queryset = ClinicalDocument.objects.filter(patient=patient)
    if document_type is not None:
        queryset = queryset.filter(document_type=document_type)
    return queryset.order_by("-created_at", "-pk")


def download(*, actor, document_id):
    """Vuelve a autorizar siempre (P-005 `phase-4-permissions.md`), nunca
    confía en una lectura previa. Devuelve `(document, bytes)`."""
    document = get(actor=actor, document_id=document_id)
    content = storage.read(storage_key=document.storage_key)
    audit.record_event(
        actor=actor, action=AuditEvent.Action.DOWNLOAD_CLINICAL_DOCUMENT, result=AuditEvent.Result.SUCCESS,
        resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=document.pk,
        patient=document.patient,
    )
    return document, content


def create_version(*, actor, document_id, content, original_filename):
    """Sólo para documentos standalone (`prescription`/`study_order`
    ambos NULL, CD-007) — un documento respaldado por una entidad con
    ciclo propio nunca se versiona por sí mismo (CD-006)."""
    try:
        with transaction.atomic():
            current = ClinicalDocument.objects.select_for_update().filter(pk=document_id).first()
            if current is None:
                raise DocumentNotFound()
            if current.prescription_id is not None or current.study_order_id is not None:
                raise DocumentValidationError(
                    "Un documento generado no se versiona directamente; corrija la entidad de origen."
                )
            if not can_correct_or_void_document(actor, current.clinical_encounter) and not can_read_document_resource(
                actor, current.patient, current.clinical_encounter
            ):
                raise DocumentPermissionDenied()
            if current.status == ClinicalDocument.Status.VOIDED:
                raise DocumentInvalidState("No se puede versionar un documento anulado.")
            if not current.is_current_version:
                raise DocumentImmutableResource("La versión indicada ya no es la vigente.")

            mime_type = storage.validate_and_detect_mime(content=content, declared_filename=original_filename)
            current.is_current_version = False
            current.save(update_fields=["is_current_version"])

            storage_key = storage.build_storage_key(mime_type=mime_type)
            storage.save(storage_key=storage_key, content=content)

            new_version = ClinicalDocument.objects.create(
                patient=current.patient, appointment=current.appointment,
                clinical_encounter=current.clinical_encounter,
                document_type=current.document_type, origin=ClinicalDocument.Origin.UPLOADED,
                status=ClinicalDocument.Status.ACTIVE,
                original_filename=original_filename, storage_key=storage_key, mime_type=mime_type,
                size_bytes=len(content), created_by=actor,
                version_number=(current.version_number or 1) + 1, previous_version=current,
                is_current_version=True,
            )
            audit.record_event(
                actor=actor, action=AuditEvent.Action.CREATE_DOCUMENT_VERSION, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=new_version.pk,
                patient=new_version.patient,
            )
            return new_version
    except DocumentPermissionDenied:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.CREATE_DOCUMENT_VERSION, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=document_id,
        )
        raise


def void_or_inactivate(*, actor, document_id, reason):
    """CD-007 — sólo aplica a documentos standalone; un documento
    respaldado por Prescription/StudyOrder se anula anulando esa entidad
    (`status` es `NULL` aquí por construcción, ver constraint del modelo)."""
    try:
        with transaction.atomic():
            document = ClinicalDocument.objects.select_for_update().filter(pk=document_id).first()
            if document is None:
                raise DocumentNotFound()
            if document.prescription_id is not None or document.study_order_id is not None:
                raise DocumentValidationError(
                    "Un documento generado se anula anulando su Prescription/StudyOrder de origen."
                )
            if not can_correct_or_void_document(actor, document.clinical_encounter) and not can_read_document_resource(
                actor, document.patient, document.clinical_encounter
            ):
                raise DocumentPermissionDenied()

            if document.status == ClinicalDocument.Status.VOIDED:
                if document.void_reason == reason:
                    return document
                raise DocumentInvalidState("El documento ya está anulado con un motivo distinto.")

            document.status = ClinicalDocument.Status.VOIDED
            document.voided_at = dj_timezone.now()
            document.void_reason = reason
            document.save(update_fields=["status", "voided_at", "void_reason"])

            audit.record_event(
                actor=actor, action=AuditEvent.Action.VOID_CLINICAL_DOCUMENT, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=document.pk,
                patient=document.patient, reason_code=reason[:60] if reason else "",
            )
            return document
    except DocumentPermissionDenied:
        audit.safe_record_event(
            actor=actor, action=AuditEvent.Action.VOID_CLINICAL_DOCUMENT, result=AuditEvent.Result.DENIED,
            resource_type=AuditEvent.ResourceType.CLINICAL_DOCUMENT, resource_id=document_id,
        )
        raise

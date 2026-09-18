"""`CareRequestService` (docs/design/care-request-service-contracts.md).

Frontera: `UI/API → CareRequestService → Agenda (F2) / ClinicalDocument (F4) →
ORM/PostgreSQL`. Principio: **CareRequest orquesta; Agenda reserva;
Appointment representa la cita; ClinicalDocument gestiona los archivos.**
`CareRequestService` no implementa ninguna regla de disponibilidad,
conflicto, concurrencia, `DoctorClinic`, timezone o duración — todo eso
sigue siendo responsabilidad exclusiva de `appointments`.
"""

import dataclasses
import datetime as dt

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone

from appointments.services import appointment as appointment_service
from appointments.services import hold as hold_service
from appointments.services.permissions import patient_profile, responsible_profile
from care_requests.models import CareRequest
from care_requests.services.exceptions import (
    CareRequestConflict,
    CareRequestPermissionDenied,
    CareRequestRateLimitExceeded,
    CareRequestValidationError,
)
from clinical_documents.models import ClinicalDocument
from clinical_documents.services import document as document_service
from clinical_documents.services import storage as storage_service
from patients.models import Patient
from patients.services.permissions import responsible_has_active_relationship

MAX_ATTACHMENTS = 5
RATE_LIMIT_MAX_PER_HOUR = 3


@dataclasses.dataclass(frozen=True)
class CareRequestResult:
    """DTO de salida (docs/design/care-request-service-contracts.md §16) —
    única excepción al patrón de "devolver la instancia ORM" del resto de
    los servicios del proyecto: esta operación abarca varias entidades."""

    care_request_id: int
    status: str
    appointment_id: int
    clinical_document_ids: list


def _resolve_patient(actor, *, patient_id):
    """`CareRequest` es un mecanismo de autoservicio (`requirements.md`
    §12): solo un paciente para sí mismo, o un responsable para un
    paciente relacionado, pueden iniciarla — nunca un médico o
    administrador (eso ya lo cubre la reserva directa de Fase 2)."""
    patient = patient_profile(actor)
    if patient is not None:
        if patient_id is not None and patient_id != patient.pk:
            raise CareRequestPermissionDenied()
        return patient

    responsible = responsible_profile(actor)
    if responsible is not None:
        if patient_id is None:
            raise CareRequestValidationError("patient_id es obligatorio cuando el actor es un responsable.")
        target = Patient.objects.filter(pk=patient_id).first()
        if target is None:
            raise CareRequestValidationError("patient_id no corresponde a un paciente válido.")
        # `docs/design/care-request-permissions.md` §4: la relación debe
        # validarse en la capa de autorización de CareRequest, no dejarse
        # caer por accidente en el rechazo posterior de Agenda
        # (`can_book_for_patient` dentro de `create_appointment_from_hold`)
        # — ese rechazo es sobre disponibilidad/reserva, no sobre quién
        # puede actuar como creador de la solicitud.
        if not responsible_has_active_relationship(responsible, target):
            raise CareRequestPermissionDenied()
        return target

    raise CareRequestPermissionDenied()


def _validate_interval(start_at, end_at):
    """`docs/design/care-request-data-model.md`: `start_at < end_at` es
    constraint de base de datos (`care_request_start_before_end`), pero
    debe rechazarse antes como error de entrada controlado — nunca como
    `IntegrityError` crudo propagado al consumidor (`docs/design/
    care-request-api-contracts.md` §6.1). El `CheckConstraint` permanece
    como defensa en profundidad, sin cambios."""
    if start_at >= end_at:
        raise CareRequestValidationError("'start_at' debe ser anterior a 'end_at'.")


def _clean_motivo(motivo):
    """`docs/design/care-request-domain.md` invariante 1: `motivo` nunca
    puede estar vacío en una creación válida. La regla es de dominio, así
    que se aplica aquí — nunca delegada a `form`/JavaScript — y de forma
    independiente del frontend (`requirements.md` §12.1)."""
    if not motivo or not motivo.strip():
        raise CareRequestValidationError("El motivo de la consulta es obligatorio.")
    return motivo.strip()


def _attachments_are_identical(existing_care_request, attachments):
    """Identidad de adjuntos (`docs/design/care-request-service-contracts.md`
    §7.1, corrección 2026-09-18): nombre + tamaño ya NO bastan — dos
    archivos distintos pueden compartir ambos por casualidad (o de forma
    adversarial). La identidad correcta para esta fase es nombre + tamaño
    + contenido byte a byte.

    El contenido solo se lee cuando nombre y tamaño YA coinciden en esa
    posición — evita leer/comparar contenido binario cuando la
    incompatibilidad ya es evidente por metadatos, y evita cualquier
    lectura para el lado entrante (`attachments` ya trae los bytes en
    memoria, sin I/O adicional). Se reutiliza `storage_service.read()`
    (Fase 4, sin cambios) — la única fuente estable ya existente para
    recuperar el contenido original — en vez de introducir una tabla de
    hashes, un campo nuevo en `ClinicalDocument` o cualquier
    infraestructura de almacenamiento adicional.

    El conjunto de documentos ORIGINALES se resuelve por
    `existing_care_request.clinical_document_ids` (corrección 2026-09-18,
    hallazgo B) — nunca consultando `ClinicalDocument.objects.filter(
    appointment_id=...)`, que incluiría cualquier documento que otro flujo
    agregue después a la misma `Appointment` y contaminaría la identidad
    de esta CareRequest con datos ajenos a su propia conversión."""
    if not existing_care_request.appointment_id:
        return not attachments

    existing_documents = list(
        ClinicalDocument.objects.filter(pk__in=existing_care_request.clinical_document_ids).order_by("pk")
    )
    if len(existing_documents) != len(attachments):
        return False

    for document, (content, original_filename) in zip(existing_documents, attachments):
        if document.original_filename != original_filename or document.size_bytes != len(content):
            return False
        if storage_service.read(storage_key=document.storage_key) != content:
            return False
    return True


def _idempotent_replay_matches(
    existing, *, patient, doctor, clinic, start_at, end_at, motivo, padecimiento, descripcion, attachments,
):
    """Identidad lógica de la operación (`docs/design/care-request-
    service-contracts.md` §7/§13): dos solicitudes con el mismo
    `(created_by, idempotency_key)` son la MISMA intención solo si además
    coinciden en paciente, médico, consultorio, intervalo, los tres campos
    de texto libre (`motivo`/`padecimiento`/`descripcion` — son
    clínicamente relevantes, no metadatos incidentales) y el contenido
    exacto de los adjuntos (§7.1). Cualquier otra combinación es un
    conflicto, nunca un replay. Los campos "baratos" se comparan primero
    para evitar leer archivos cuando ya hay incompatibilidad evidente."""
    return (
        existing.patient_id == patient.pk
        and existing.doctor_id == doctor.pk
        and existing.clinic_id == clinic.pk
        and existing.start_at == start_at
        and existing.end_at == end_at
        and existing.motivo == motivo
        and existing.padecimiento == padecimiento
        and existing.descripcion == descripcion
        and _attachments_are_identical(existing, attachments)
    )


def _to_result(care_request):
    """`clinical_document_ids` viene directo del campo persistido
    (corrección 2026-09-18, hallazgo B) — nunca de una consulta fresca a
    `ClinicalDocument` por `appointment_id`, para que un replay siga
    reportando exactamente los documentos de la conversión original,
    aunque otro flujo haya agregado más documentos a la misma
    `Appointment` después."""
    return CareRequestResult(
        care_request_id=care_request.pk,
        status=care_request.status,
        appointment_id=care_request.appointment_id,
        clinical_document_ids=list(care_request.clinical_document_ids),
    )


def create(
    *, actor, doctor, clinic, start_at, end_at, motivo, padecimiento="", descripcion="",
    patient_id=None, attachments=(), idempotency_key="",
):
    """docs/design/care-request-service-contracts.md §4/§7/§9/§11/§12.

    `attachments` es una secuencia de `(content: bytes, original_filename: str)`.
    `start_at`/`end_at` deben venir tal cual de un slot ya generado por
    Agenda (`appointments.services.availability.get_available_slots`) — este
    servicio no los recalcula ni valida su duración (Agenda lo hace en
    `create_hold`)."""
    if len(attachments) > MAX_ATTACHMENTS:
        raise CareRequestValidationError(f"Máximo {MAX_ATTACHMENTS} archivos por solicitud.")
    _validate_interval(start_at, end_at)
    motivo = _clean_motivo(motivo)

    patient = _resolve_patient(actor, patient_id=patient_id)

    User = get_user_model()
    created_storage_keys = []
    created_document_ids = []

    try:
        with transaction.atomic():
            # Un solo lock: sirve tanto para el re-check de idempotencia
            # como para el conteo de rate limit — ambos bajo la misma
            # fila bloqueada, sin adquirir un segundo lock (docs/design/
            # care-request-service-contracts.md §7/§11).
            User.objects.select_for_update().get(pk=actor.pk)

            if idempotency_key:
                existing = CareRequest.objects.filter(
                    created_by=actor, idempotency_key=idempotency_key
                ).first()
                if existing is not None:
                    if not _idempotent_replay_matches(
                        existing, patient=patient, doctor=doctor, clinic=clinic,
                        start_at=start_at, end_at=end_at, motivo=motivo,
                        padecimiento=padecimiento, descripcion=descripcion, attachments=attachments,
                    ):
                        raise CareRequestConflict()
                    return _to_result(existing)

            one_hour_ago = dj_timezone.now() - dt.timedelta(hours=1)
            recent_count = CareRequest.objects.filter(
                created_by=actor, created_at__gte=one_hour_ago
            ).count()
            if recent_count >= RATE_LIMIT_MAX_PER_HOUR:
                raise CareRequestRateLimitExceeded()

            try:
                with transaction.atomic():  # SAVEPOINT — defensa en profundidad, ver §7
                    care_request = CareRequest.objects.create(
                        patient=patient,
                        created_by=actor,
                        responsible=responsible_profile(actor),
                        doctor=doctor,
                        clinic=clinic,
                        start_at=start_at,
                        end_at=end_at,
                        motivo=motivo,
                        padecimiento=padecimiento,
                        descripcion=descripcion,
                        status=CareRequest.Status.NUEVA,
                        idempotency_key=idempotency_key,
                    )
            except IntegrityError as exc:
                if not idempotency_key:
                    raise
                existing = CareRequest.objects.filter(
                    created_by=actor, idempotency_key=idempotency_key
                ).first()
                if existing is None or not _idempotent_replay_matches(
                    existing, patient=patient, doctor=doctor, clinic=clinic,
                    start_at=start_at, end_at=end_at, motivo=motivo,
                    padecimiento=padecimiento, descripcion=descripcion, attachments=attachments,
                ):
                    raise CareRequestConflict() from exc
                return _to_result(existing)

            hold = hold_service.create_hold(
                actor=actor, doctor=doctor, clinic=clinic, start_at=start_at, end_at=end_at,
            )
            appointment = appointment_service.create_appointment_from_hold(
                actor=actor, hold=hold, patient=patient, doctor=doctor, clinic=clinic,
                idempotency_key="",  # namespace de idempotencia propio de CareRequest — no se propaga (§13)
            )

            care_request.appointment = appointment
            care_request.save(update_fields=["appointment"])

            for content, original_filename in attachments:
                # `upload()` valida MIME/tamaño real, escribe el archivo y
                # crea el ClinicalDocument (origin=UPLOADED) — es contenido
                # provisto por el usuario, nunca `create_generated_document`
                # (esa función no valida contenido, pensada para PDFs que la
                # propia aplicación genera).
                document = document_service.upload(
                    actor=actor, patient=patient, content=content,
                    original_filename=original_filename,
                    document_type=ClinicalDocument.DocumentType.OTHER,
                    appointment=appointment,
                )
                created_storage_keys.append(document.storage_key)
                created_document_ids.append(document.pk)

            # `clinical_document_ids` se fija aquí, una sola vez, junto con
            # la transición a CONVERTIDA — es la identidad estable de esta
            # conversión (hallazgo B, corrección 2026-09-18), no una
            # consulta recalculable después.
            care_request.status = CareRequest.Status.CONVERTIDA
            care_request.clinical_document_ids = created_document_ids
            care_request.save(update_fields=["status", "clinical_document_ids"])

            return _to_result(care_request)
    except Exception:
        # Compensación síncrona: `upload()` ya limpia su propio archivo si
        # su propia fila falla, pero si un adjunto POSTERIOR o cualquier
        # otro paso falla, los archivos de adjuntos YA aceptados en esta
        # ejecución deben limpiarse también (docs/design/
        # care-request-service-contracts.md §12).
        for storage_key in created_storage_keys:
            storage_service.delete_best_effort(storage_key=storage_key)
        raise

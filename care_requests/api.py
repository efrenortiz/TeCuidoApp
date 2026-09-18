"""JSON HTTP API para `CareRequest` (docs/design/care-request-service-contracts.md §17,
docs/design/care-request-api-contracts.md).

`multipart/form-data` siempre (attachments opcionales) — mismo mecanismo que
`clinical_documents.api.ClinicalDocumentListCreateView`, reutilizado tal
cual en vez de introducir un segundo formato de entrada solo para el caso
sin adjuntos. Vistas planas + `JsonResponse`, sin DRF — mismo patrón que
`appointments/api.py`/`clinical_documents/api_common.py`.
"""

from django.conf import settings
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views import View

from appointments.services.exceptions import (
    AgendaError,
    AppointmentConflict,
    AvailabilityNotFound,
    BookingWindowExpired,
    HoldAlreadyExists,
    HoldConflict,
    HoldExpired,
    IdempotencyKeyConflict,
    InvalidDoctorClinic,
    InvalidPatient,
    InvalidSlot,
    NotAuthorized,
    SlotUnavailable,
)
from care_requests.services import care_request as care_request_service
from care_requests.services.exceptions import (
    CareRequestConflict,
    CareRequestError,
    CareRequestPermissionDenied,
    CareRequestRateLimitExceeded,
    CareRequestValidationError,
)
from clinics.models import Clinic
from doctors.models import Doctor
from medical_records.services.exceptions import DocumentError, DocumentStorageError, DocumentValidationError

MAX_ATTACHMENTS = 5

_ERROR_MAP = {
    # CareRequest — propios de esta app.
    CareRequestPermissionDenied: (403, "NOT_AUTHORIZED", "No tienes autorización para esta operación."),
    CareRequestConflict: (
        409, "IDEMPOTENCY_CONFLICT", "Esta clave de idempotencia ya se usó para una operación distinta.",
    ),
    CareRequestRateLimitExceeded: (
        429, "RATE_LIMITED", "Alcanzaste el máximo de solicitudes permitidas en la última hora.",
    ),
    CareRequestValidationError: (400, "VALIDATION_ERROR", "Los datos enviados no son válidos."),
    # Agenda (Fase 2) — mismos códigos que `appointments/api.py`, reutilizados
    # tal cual (no se inventa una segunda taxonomía para lo que Agenda ya
    # clasifica).
    NotAuthorized: (403, "NOT_AUTHORIZED", "No tienes autorización para esta operación."),
    AvailabilityNotFound: (404, "AVAILABILITY_NOT_FOUND", "La disponibilidad no existe."),
    InvalidSlot: (422, "INVALID_SLOT", "El horario solicitado no corresponde a un slot válido."),
    SlotUnavailable: (409, "SLOT_UNAVAILABLE", "El horario seleccionado ya no está disponible."),
    BookingWindowExpired: (422, "BOOKING_WINDOW_EXPIRED", "El plazo para reservar este horario ya venció."),
    HoldAlreadyExists: (409, "HOLD_ALREADY_EXISTS", "Ya tienes otro horario en espera."),
    HoldConflict: (409, "HOLD_CONFLICT", "Otro usuario ya tiene este horario en espera."),
    HoldExpired: (409, "HOLD_EXPIRED", "El hold expiró."),
    AppointmentConflict: (409, "APPOINTMENT_CONFLICT", "El horario ya fue ocupado por otra cita."),
    InvalidPatient: (422, "INVALID_PATIENT", "No puedes reservar una cita para este paciente."),
    InvalidDoctorClinic: (422, "INVALID_DOCTOR_CLINIC", "La combinación médico-consultorio no es válida."),
    IdempotencyKeyConflict: (
        409, "IDEMPOTENCY_CONFLICT", "Esta clave de idempotencia ya se usó para una operación distinta.",
    ),
    # ClinicalDocument (Fase 4) — mismos códigos que `clinical_documents/api_common.py`.
    DocumentValidationError: (400, "VALIDATION_ERROR", "Los datos enviados no son válidos."),
    DocumentStorageError: (503, "DOCUMENT_STORAGE_ERROR", "No se pudo completar la operación de almacenamiento."),
}


class ApiError(Exception):
    """Error de capa de vista (payload estructuralmente inválido) — nunca
    una regla de negocio."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _error_response(status, code, message):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


class CareRequestJsonApiView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            response = _error_response(401, "NOT_AUTHENTICATED", "Se requiere autenticación.")
            response["Cache-Control"] = "no-store"
            return response
        try:
            response = super().dispatch(request, *args, **kwargs)
        except ApiError as exc:
            response = _error_response(400, "BAD_REQUEST", exc.message)
        except ValueError as exc:
            response = _error_response(400, "BAD_REQUEST", str(exc) or "Datos inválidos.")
        except (CareRequestError, AgendaError, DocumentError) as exc:
            status, code, message = _ERROR_MAP.get(
                type(exc), (400, "DOMAIN_ERROR", "No se pudo completar la operación."),
            )
            response = _error_response(status, code, message)
        except Exception:
            # Divergencia deliberada y acotada respecto de `appointments.
            # api.JsonApiView`/`clinical_documents.api_common.
            # DocumentJsonApiView` (ninguna de las dos captura excepciones
            # no anticipadas): la política clínica de no-cache exige que
            # TODA respuesta de este endpoint, incluida una excepción
            # inesperada, lleve `Cache-Control: no-store` — algo que el
            # `500` por defecto de Django nunca añade por sí solo. Con
            # `DEBUG=True` se re-lanza tal cual para no perder la página de
            # depuración de Django en desarrollo (idéntico a como se
            # comporta hoy cualquier otra vista del proyecto); solo con
            # `DEBUG=False` (el único caso que un cliente real ve) se
            # produce aquí un `500` genérico y cacheado como no-store, sin
            # exponer ningún detalle interno — mismo mensaje fijo ya
            # verificado en `test_unexpected_exception_returns_generic_500_
            # without_internals`.
            if settings.DEBUG:
                raise
            response = _error_response(500, "INTERNAL_ERROR", "Ocurrió un error inesperado.")
        response["Cache-Control"] = "no-store"
        return response


def _require_field(data, field):
    value = data.get(field)
    if not value:
        raise ApiError(f"'{field}' es obligatorio.")
    return value


def _parse_int(value, field):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(f"'{field}' debe ser un entero.") from exc


def _parse_iso_datetime(value, field):
    parsed = parse_datetime(value) if value else None
    if parsed is None:
        raise ApiError(f"'{field}' debe ser una fecha/hora ISO 8601 válida.")
    return parsed


def _get_doctor_or_400(pk):
    doctor = Doctor.objects.filter(pk=pk).first()
    if doctor is None:
        raise ApiError("'doctor_id' no corresponde a un médico válido.")
    return doctor


def _get_clinic_or_400(pk):
    clinic = Clinic.objects.filter(pk=pk).first()
    if clinic is None:
        raise ApiError("'clinic_id' no corresponde a un consultorio válido.")
    return clinic


def _serialize_result(result):
    return {
        "care_request_id": result.care_request_id,
        "status": result.status,
        "appointment_id": result.appointment_id,
        "clinical_document_ids": result.clinical_document_ids,
    }


class CareRequestCreateView(CareRequestJsonApiView):
    def post(self, request):
        # `multipart/form-data` es obligatorio, no una de varias
        # codificaciones toleradas (docs/design/care-request-api-
        # contracts.md §5): es el único formato que el cliente real
        # (`static/js/care-request.js::submitCareRequest`, vía `FormData`)
        # envía, y el único que soporta adjuntos en la misma petición.
        # `request.POST` por sí solo también aceptaría silenciosamente
        # `application/x-www-form-urlencoded` (Django lo parsea igual),
        # lo cual contradice esa intención — se rechaza aquí explícitamente
        # con un error claro, en vez de dejar que un campo "faltante"
        # (`request.POST` vacío) oculte la causa real.
        if not request.content_type.startswith("multipart/form-data"):
            raise ApiError(
                f"Se requiere 'Content-Type: multipart/form-data' (se recibió {request.content_type!r})."
            )

        data = request.POST
        doctor = _get_doctor_or_400(_parse_int(_require_field(data, "doctor_id"), "doctor_id"))
        clinic = _get_clinic_or_400(_parse_int(_require_field(data, "clinic_id"), "clinic_id"))
        start_at = _parse_iso_datetime(_require_field(data, "start"), "start")
        end_at = _parse_iso_datetime(_require_field(data, "end"), "end")
        motivo = _require_field(data, "motivo")
        padecimiento = data.get("padecimiento", "")
        descripcion = data.get("descripcion", "")

        patient_id_raw = data.get("patient_id")
        patient_id = _parse_int(patient_id_raw, "patient_id") if patient_id_raw else None

        uploaded_files = request.FILES.getlist("attachments")
        if len(uploaded_files) > MAX_ATTACHMENTS:
            raise ApiError(f"Máximo {MAX_ATTACHMENTS} archivos por solicitud.")
        attachments = [(f.read(), f.name) for f in uploaded_files]

        idempotency_key = request.headers.get("Idempotency-Key", "")

        result = care_request_service.create(
            actor=request.user, doctor=doctor, clinic=clinic, start_at=start_at, end_at=end_at,
            motivo=motivo, padecimiento=padecimiento, descripcion=descripcion,
            patient_id=patient_id, attachments=attachments, idempotency_key=idempotency_key,
        )
        # Siempre 201, incluso en replay — mismo criterio que
        # `AppointmentCollectionView.post` (`appointments/api.py`), que no
        # distingue "creado" de "resultado ya existente" en el código de
        # estado.
        return JsonResponse(_serialize_result(result), status=201)

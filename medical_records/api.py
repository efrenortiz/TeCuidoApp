"""JSON HTTP API for the clinical domain (docs/design/clinical-api-contracts.md).

Same pattern as `appointments/api.py` (§45/API-174-177, corregido en la
auditoría de cierre a favor de este patrón, no DRF): plain Django views +
`JsonResponse`, a shared base view that centralizes domain-error → HTTP
translation, thin views that only parse/validate input, call a service,
and serialize the result.

Field names: the JSON wire format uses the Spanish names fixed by
`clinical-api-contracts.md` §25 (D-002) for `ClinicalEncounter`'s clinical
content — that table is "la única fuente autoritativa" for that mapping.
`MedicalRecord`'s longitudinal fields have no equivalent closed mapping
anywhere in the contract (§25 is explicitly scoped to "campos clínicos
del encuentro", and API-075's own example already uses the English
`patient_id`/`id` for `MedicalRecord`'s identity) — so its fields are
exposed under their internal (English) names verbatim, matching API-075's
own example rather than inventing an uncommitted translation.
"""

import json

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views import View

from appointments.models import Appointment
from medical_records.models import AuditEvent, ClinicalEncounter
from medical_records.services import audit as audit_service
from medical_records.services import encounter as encounter_service
from medical_records.services import record as record_service
from medical_records.services.permissions import can_view_audit_log
from medical_records.services.exceptions import (
    ClinicalAuditError,
    ClinicalConcurrencyError,
    ClinicalContentPlaceholder,
    ClinicalError,
    ClinicalNotAuthorized,
    ClinicalNotFound,
    ClinicalRecordIntegrityError,
    ClinicalRecordNotFound,
    EncounterAlreadyCompleted,
    EncounterAlreadyStarted,
    EncounterAppointmentMismatch,
    EncounterNotInProgress,
    EncounterNotStartable,
    IncompleteClinicalContent,
    InvalidClinicalData,
)
from patients.models import Patient

# --- Domain error -> HTTP translation (clinical-api-contracts.md §19) -------

_ERROR_MAP = {
    ClinicalNotFound: (404, "CLINICAL_RESOURCE_NOT_FOUND", "El recurso clínico no existe o no está disponible."),
    ClinicalNotAuthorized: (403, "CLINICAL_ACCESS_DENIED", "No tienes autorización para esta operación clínica."),
    EncounterNotStartable: (
        409, "APPOINTMENT_STATE_INVALID", "La cita no está en un estado válido para iniciar la consulta.",
    ),
    EncounterAlreadyStarted: (409, "ENCOUNTER_ALREADY_STARTED", "El encuentro ya fue iniciado."),
    EncounterNotInProgress: (409, "ENCOUNTER_NOT_IN_PROGRESS", "El encuentro no está en progreso."),
    EncounterAlreadyCompleted: (
        409, "ENCOUNTER_COMPLETED", "El encuentro ya fue completado y no admite esta operación.",
    ),
    IncompleteClinicalContent: (
        422, "REQUIRED_CLINICAL_CONTENT", "Faltan campos clínicos obligatorios para completar la consulta.",
    ),
    ClinicalContentPlaceholder: (
        422, "INVALID_PLACEHOLDER_CONTENT", "Uno o más campos obligatorios contiene un valor de relleno no válido.",
    ),
    InvalidClinicalData: (400, "VALIDATION_ERROR", "Los datos enviados no son válidos."),
    EncounterAppointmentMismatch: (
        409, "CLINICAL_REFERENCE_INCONSISTENCY", "La cita y el encuentro son inconsistentes entre sí.",
    ),
    ClinicalRecordNotFound: (404, "RESOURCE_NOT_FOUND", "El expediente clínico no existe."),
    ClinicalRecordIntegrityError: (
        409, "CLINICAL_REFERENCE_INCONSISTENCY", "El expediente presenta una inconsistencia de integridad.",
    ),
    ClinicalConcurrencyError: (409, "CLINICAL_CONCURRENCY_CONFLICT", "Ocurrió un conflicto de concurrencia."),
    ClinicalAuditError: (500, "CLINICAL_AUDIT_ERROR", "No se pudo registrar la auditoría de este acceso."),
}


class ApiError(Exception):
    """View-layer error for structurally invalid requests (400) — never a
    business rule, just malformed/missing/unrecognized input."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _error_response(status, code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JsonResponse(body, status=status)


class JsonApiView(View):
    def dispatch(self, request, *args, **kwargs):
        # API-013 — ninguna ruta clínica pública en F3. API-015 (usuario
        # inactivo no opera) ya la garantiza `ModelBackend.get_user`: una
        # sesión de un usuario `is_active=False` se resuelve como
        # `AnonymousUser` antes de llegar aquí, así que no hace falta un
        # segundo chequeo — sería código muerto (mismo precedente que
        # appointments/api.py).
        if not request.user.is_authenticated:
            return _error_response(401, "AUTHENTICATION_REQUIRED", "Se requiere autenticación.")
        response = self._dispatch(request, *args, **kwargs)
        # API-110/111 — ninguna respuesta clínica se cachea, ni por el
        # navegador ni por un proxy/caché compartido (TS-103/158: un
        # "atrás" del navegador después de logout no debe reexponer datos
        # clínicos desde caché).
        response["Cache-Control"] = "no-store"
        return response

    def _dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except ApiError as exc:
            return _error_response(400, "VALIDATION_ERROR", exc.message)
        except ValueError as exc:
            return _error_response(400, "VALIDATION_ERROR", str(exc) or "Datos inválidos.")
        except ClinicalError as exc:
            status, code, message = _ERROR_MAP.get(type(exc), (400, "DOMAIN_ERROR", "No se pudo completar la operación."))
            details = {"fields": exc.fields} if hasattr(exc, "fields") else None
            return _error_response(status, code, message, details)


# --- Request parsing helpers --------------------------------------------------


def _parse_json_body(request):
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ApiError("El cuerpo de la petición no es JSON válido.") from exc
    if not isinstance(data, dict):
        raise ApiError("El cuerpo de la petición debe ser un objeto JSON.")
    return data


def _parse_int(value, field):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(f"El parámetro '{field}' debe ser un entero.") from exc


def _parse_optional_datetime(value, field):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        raise ApiError(f"El parámetro '{field}' debe ser una fecha/hora ISO-8601 válida.")
    return parsed


# --- Field mapping (clinical-api-contracts.md §25, D-002) --------------------

_CLINICAL_FIELD_MAP = {
    "reason_for_visit": "motivo_consulta",
    "present_illness": "padecimiento_actual",
    "physical_exam": "exploracion_fisica",
    "assessment": "evaluacion_diagnostico",
    "plan": "plan_indicaciones",
    "vital_signs": "signos_vitales",
    "weight_kg": "peso",
    "height_cm": "talla",
    "relevant_history": "antecedentes_relevantes",
    "studies": "estudios",
    "observations": "observaciones",
}
_CLINICAL_FIELD_MAP_REVERSE = {api_name: internal for internal, api_name in _CLINICAL_FIELD_MAP.items()}
_DECIMAL_INTERNAL_FIELDS = {"weight_kg", "height_cm"}


def _translate_encounter_payload(data):
    """Español (API) -> inglés (interno/ADR-012). Un campo no reconocido
    en ninguna de las dos vías se rechaza aquí (API-175 — campos
    desconocidos son responsabilidad del serializer, no del dominio)."""
    translated = {}
    for api_name, value in data.items():
        internal_name = _CLINICAL_FIELD_MAP_REVERSE.get(api_name)
        if internal_name is None:
            raise ApiError(f"Campo no reconocido: '{api_name}'.")
        translated[internal_name] = value
    return translated


# --- Serialization -------------------------------------------------------------


def _serialize_encounter(e):
    clinical = {}
    for internal, api_name in _CLINICAL_FIELD_MAP.items():
        value = getattr(e, internal)
        if internal in _DECIMAL_INTERNAL_FIELDS:
            clinical[api_name] = float(value) if value is not None else None
        else:
            clinical[api_name] = value
    return {
        "id": e.pk,
        "appointment_id": e.appointment_id,
        "patient_id": e.patient.pk,
        "doctor_id": e.doctor_id,
        "status": e.status,
        "created_at": e.created_at.isoformat(),
        "started_at": e.started_at.isoformat(),
        "updated_at": e.updated_at.isoformat(),
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "clinical": clinical,
    }


def _serialize_encounter_summary(e):
    """Para la colección de historial (API-086) — sin el detalle completo
    de `clinical`, solo lo necesario para una lista."""
    return {
        "id": e.pk,
        "appointment_id": e.appointment_id,
        "doctor_id": e.doctor_id,
        "status": e.status,
        "started_at": e.started_at.isoformat(),
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
    }


def _serialize_medical_record(record):
    data = {"id": record.pk, "patient_id": record.patient_id}
    for field in record_service.RECORD_FIELDS:
        data[field] = getattr(record, field)
    data["created_at"] = record.created_at.isoformat()
    data["updated_at"] = record.updated_at.isoformat()
    return data


# --- Encounter ------------------------------------------------------------------


class EncounterStartView(JsonApiView):
    def post(self, request, appointment_id):
        appointment = Appointment.objects.filter(pk=appointment_id).first()
        if appointment is None:
            return _error_response(404, "RESOURCE_NOT_FOUND", "La cita no existe.")

        # API-031/032 — 201 si se crea un encuentro nuevo, 200 si la
        # solicitud es idempotente sobre uno ya existente. Esta
        # comprobación es solo para elegir el código HTTP: la corrección
        # real (no duplicar) la garantiza `start_encounter` bajo lock.
        already_existed = ClinicalEncounter.objects.filter(appointment_id=appointment_id).exists()

        encounter = encounter_service.start_encounter(actor=request.user, appointment=appointment)
        return JsonResponse(_serialize_encounter(encounter), status=200 if already_existed else 201)


class EncounterDetailView(JsonApiView):
    def get(self, request, pk):
        encounter = encounter_service.get_encounter(actor=request.user, encounter_id=pk)
        return JsonResponse(_serialize_encounter(encounter), status=200)

    def patch(self, request, pk):
        data = _parse_json_body(request)
        translated = _translate_encounter_payload(data)
        encounter = encounter_service.save_encounter(
            actor=request.user, encounter=ClinicalEncounter(pk=pk), data=translated,
        )
        return JsonResponse(_serialize_encounter(encounter), status=200)


class EncounterCompleteView(JsonApiView):
    def post(self, request, pk):
        data = _parse_json_body(request)
        translated = _translate_encounter_payload(data)
        encounter = encounter_service.complete_encounter(
            actor=request.user, encounter=ClinicalEncounter(pk=pk), data=translated,
        )
        return JsonResponse(_serialize_encounter(encounter), status=200)


# --- MedicalRecord --------------------------------------------------------------


class MedicalRecordDetailView(JsonApiView):
    def get(self, request, patient_id):
        patient = Patient.objects.filter(pk=patient_id).first()
        if patient is None:
            return _error_response(404, "RESOURCE_NOT_FOUND", "El paciente no existe.")

        record = record_service.get_medical_record(actor=request.user, patient=patient)
        if record is None:
            # API-073/D-005 — la API es la única responsable de traducir
            # la ausencia explícita (`None`) a 404.
            return _error_response(404, "RESOURCE_NOT_FOUND", "El paciente todavía no tiene expediente clínico.")
        return JsonResponse(_serialize_medical_record(record), status=200)

    def patch(self, request, patient_id):
        patient = Patient.objects.filter(pk=patient_id).first()
        if patient is None:
            return _error_response(404, "RESOURCE_NOT_FOUND", "El paciente no existe.")

        data = _parse_json_body(request)
        unknown = set(data) - set(record_service.RECORD_FIELDS)
        if unknown:
            # API-092 — campos no permitidos (id/patient_id/created_at
            # y cualquier otro no listado) se rechazan aquí, en el
            # serializer, no en el dominio.
            raise ApiError(f"Campos no permitidos: {sorted(unknown)}")

        record = record_service.update_medical_record(actor=request.user, patient=patient, data=data)
        return JsonResponse(_serialize_medical_record(record), status=200)


class PatientEncounterHistoryView(JsonApiView):
    _PAGE_SIZE_DEFAULT = 20
    _PAGE_SIZE_MAX = 100

    def get(self, request, patient_id):
        patient = Patient.objects.filter(pk=patient_id).first()
        if patient is None:
            return _error_response(404, "RESOURCE_NOT_FOUND", "El paciente no existe.")

        ordering = request.GET.get("ordering") or "-started_at"
        queryset = encounter_service.list_encounters_for_patient(
            actor=request.user, patient=patient, ordering=ordering,
        )

        page_size = (
            min(_parse_int(request.GET["page_size"], "page_size"), self._PAGE_SIZE_MAX)
            if request.GET.get("page_size") else self._PAGE_SIZE_DEFAULT
        )
        page_number = _parse_int(request.GET["page"], "page") if request.GET.get("page") else 1

        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(page_number)
        return JsonResponse(
            {
                "count": paginator.count,
                "next": page.next_page_number() if page.has_next() else None,
                "previous": page.previous_page_number() if page.has_previous() else None,
                "results": [_serialize_encounter_summary(e) for e in page.object_list],
            },
            status=200,
        )


def _serialize_audit_event(event):
    """docs/design/phase-6-audit-api-contracts.md §4 — nunca el contenido
    clínico ni secretos; solo metadatos de trazabilidad."""
    return {
        "id": event.pk,
        "occurred_at": event.occurred_at.isoformat(),
        "actor_id": event.actor_id,
        "actor_role": event.actor_role,
        "action": event.action,
        "result": event.result,
        "reason_code": event.reason_code,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "patient_id": event.patient_id,
    }


class AuditEventListView(JsonApiView):
    """F6-D05 (docs/design/phase-6-audit-api-contracts.md) — consulta
    administrativa del audit trail. `list_audit_events` ya aplica
    `can_view_audit_log` (solo `is_superuser`); un actor no autorizado
    recibe el mismo 403 uniforme que el resto de la API clínica, sin
    revelar si el audit trail existiría para él."""

    _PAGE_SIZE_DEFAULT = 20
    _PAGE_SIZE_MAX = 100

    def get(self, request):
        # La autorización debe evaluarse antes de cualquier respuesta
        # temprana — un `patient_id` inexistente no puede convertirse en un
        # atajo que devuelva 200 a un actor no autorizado sin pasar por
        # `can_view_audit_log` (bug encontrado en revisión de seguridad,
        # docs/phases/phase-6-implementation-summary.md §9).
        if not can_view_audit_log(request.user):
            raise ClinicalNotAuthorized()

        patient = None
        if request.GET.get("patient_id"):
            patient_id = _parse_int(request.GET["patient_id"], "patient_id")
            patient = Patient.objects.filter(pk=patient_id).first()
            if patient is None:
                return JsonResponse({"count": 0, "next": None, "previous": None, "results": []}, status=200)

        action = request.GET.get("action") or None
        if action is not None and action not in AuditEvent.Action.values:
            raise ApiError(f"'action' debe ser uno de {AuditEvent.Action.values!r}.")

        result = request.GET.get("result") or None
        if result is not None and result not in AuditEvent.Result.values:
            raise ApiError(f"'result' debe ser uno de {AuditEvent.Result.values!r}.")

        date_from = _parse_optional_datetime(request.GET.get("date_from"), "date_from")
        date_to = _parse_optional_datetime(request.GET.get("date_to"), "date_to")

        queryset = audit_service.list_audit_events(
            actor=request.user, patient=patient, action=action, result=result,
            date_from=date_from, date_to=date_to,
        )

        page_size = (
            min(_parse_int(request.GET["page_size"], "page_size"), self._PAGE_SIZE_MAX)
            if request.GET.get("page_size") else self._PAGE_SIZE_DEFAULT
        )
        page_number = _parse_int(request.GET["page"], "page") if request.GET.get("page") else 1

        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(page_number)
        return JsonResponse(
            {
                "count": paginator.count,
                "next": page.next_page_number() if page.has_next() else None,
                "previous": page.previous_page_number() if page.has_previous() else None,
                "results": [_serialize_audit_event(e) for e in page.object_list],
            },
            status=200,
        )

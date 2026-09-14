"""Infraestructura HTTP compartida por las tres APIs de Fase 4
(`prescriptions`, `study_orders`, `clinical_documents`) — mismo patrón que
`medical_records.api.JsonApiView`, centralizado aquí porque los tres
comparten la MISMA taxonomía de errores de dominio (ADR-029,
`phase-4-service-contracts.md` §7) — a diferencia de `medical_records`/
`appointments`, que tienen taxonomías propias y por eso no comparten base.
"""

import json

from django.http import JsonResponse
from django.views import View

from medical_records.services.exceptions import (
    DocumentConflict,
    DocumentError,
    DocumentImmutableResource,
    DocumentInvalidState,
    DocumentNotFound,
    DocumentPermissionDenied,
    DocumentReferenceInconsistency,
    DocumentStorageError,
    DocumentValidationError,
)

# --- Domain error -> HTTP translation (phase-4-api-contracts.md §7, corrección M-01) ---

_ERROR_MAP = {
    DocumentNotFound: (404, "CLINICAL_RESOURCE_NOT_FOUND", "El recurso no existe o no está disponible."),
    DocumentPermissionDenied: (403, "CLINICAL_ACCESS_DENIED", "No tienes autorización para esta operación."),
    DocumentInvalidState: (409, "INVALID_STATE", "La operación no es válida en el estado actual del recurso."),
    DocumentValidationError: (400, "VALIDATION_ERROR", "Los datos enviados no son válidos."),
    DocumentConflict: (409, "CONFLICT", "Conflicto de idempotencia o concurrencia."),
    DocumentImmutableResource: (409, "IMMUTABLE_RESOURCE", "El recurso ya no admite esta mutación."),
    DocumentReferenceInconsistency: (422, "REFERENCE_INCONSISTENCY", "Las referencias del recurso son inconsistentes."),
    DocumentStorageError: (503, "DOCUMENT_STORAGE_ERROR", "No se pudo completar la operación de almacenamiento."),
}


class ApiError(Exception):
    """Error de capa de vista (payload estructuralmente inválido) — nunca
    una regla de negocio."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def error_response(status, code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JsonResponse(body, status=status)


class DocumentJsonApiView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return error_response(401, "AUTHENTICATION_REQUIRED", "Se requiere autenticación.")
        response = self._dispatch(request, *args, **kwargs)
        # TS-103/158 (por analogía) — ninguna respuesta clínica se cachea.
        response["Cache-Control"] = "no-store"
        return response

    def _dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except ApiError as exc:
            return error_response(400, "VALIDATION_ERROR", exc.message)
        except ValueError as exc:
            return error_response(400, "VALIDATION_ERROR", str(exc) or "Datos inválidos.")
        except DocumentError as exc:
            status, code, message = _ERROR_MAP.get(
                type(exc), (400, "DOMAIN_ERROR", "No se pudo completar la operación.")
            )
            return error_response(status, code, message)


def parse_json_body(request):
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ApiError("El cuerpo de la petición no es JSON válido.") from exc
    if not isinstance(data, dict):
        raise ApiError("El cuerpo de la petición debe ser un objeto JSON.")
    return data

"""JSON HTTP API mínima de consentimientos (Fase 6, F6-D04,
docs/design/phase-6-consent-domain.md §9). Mismo patrón que
`medical_records/api.py`/`appointments/api.py`: Django puro + `JsonResponse`,
sin DRF, sin wrappers innecesarios."""

import json

from django.http import JsonResponse
from django.views import View

from accounts.services import consent as consent_service


def _error_response(status, code, message):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


class JsonApiView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _error_response(401, "AUTHENTICATION_REQUIRED", "Se requiere autenticación.")
        response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class ConsentAcceptView(JsonApiView):
    """POST /.../consent/accept/ — nunca acepta `user`/`accepted_at` desde
    el cliente (docs/design/phase-6-consent-domain.md §9): ambos se
    determinan en servidor."""

    def post(self, request):
        try:
            data = json.loads(request.body or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _error_response(400, "VALIDATION_ERROR", "El cuerpo de la petición no es JSON válido.")

        policy_type = data.get("policy_type")
        policy_version = data.get("policy_version")
        if not policy_type or not policy_version:
            return _error_response(400, "VALIDATION_ERROR", "'policy_type' y 'policy_version' son obligatorios.")

        try:
            acceptance = consent_service.record_acceptance(
                user=request.user, policy_type=policy_type, policy_version=policy_version,
            )
        except consent_service.UnknownPolicyType:
            return _error_response(400, "UNKNOWN_POLICY_TYPE", "'policy_type' no es reconocido.")
        except consent_service.UnknownPolicyVersion:
            return _error_response(400, "UNKNOWN_POLICY_VERSION", "'policy_version' no es la versión vigente.")

        return JsonResponse(
            {
                "policy_type": acceptance.policy_type,
                "policy_version": acceptance.policy_version,
                "accepted_at": acceptance.accepted_at.isoformat(),
            },
            status=200,
        )


class ConsentStatusView(JsonApiView):
    """GET /.../consent/status/ — aceptaciones vigentes del usuario
    autenticado; nunca de otro usuario (sin parámetro de identidad en la
    petición, docs/design/phase-6-consent-domain.md §9)."""

    def get(self, request):
        return JsonResponse(consent_service.acceptance_status(user=request.user), status=200)

"""JSON HTTP API for `StudyOrder` (docs/design/phase-4-api-contracts.md §3).

Same pattern as `prescriptions/api.py`.
"""

from django.http import JsonResponse

from clinical_documents.api_common import ApiError, DocumentJsonApiView, error_response, parse_json_body
from medical_records.models import ClinicalEncounter
from study_orders.models import StudyOrder
from study_orders.services import study_order as study_order_service


def _serialize_item(item):
    return {
        "position": item.position,
        "study_name": item.study_name,
        "specific_instructions": item.specific_instructions,
    }


def _serialize(order):
    return {
        "id": order.pk,
        "patient_id": order.patient_id,
        "doctor_id": order.doctor_id,
        "clinical_encounter_id": order.clinical_encounter_id,
        "status": order.status,
        "study_type": order.study_type,
        "indications": order.indications,
        "observations": order.observations,
        "issued_at": order.issued_at.isoformat(),
        "version_number": order.version_number,
        "previous_version_id": order.previous_version_id,
        "is_current_version": order.is_current_version,
        "voided_at": order.voided_at.isoformat() if order.voided_at else None,
        "void_reason": order.void_reason,
        "items": [_serialize_item(item) for item in order.items.order_by("position")],
    }


def _json(order, status):
    return JsonResponse(_serialize(order), status=status)


class StudyOrderListCreateView(DocumentJsonApiView):
    def post(self, request):
        data = parse_json_body(request)
        encounter_id = data.get("clinical_encounter_id")
        if not encounter_id:
            raise ApiError("'clinical_encounter_id' es obligatorio.")
        encounter = ClinicalEncounter.objects.select_related("appointment").filter(pk=encounter_id).first()
        if encounter is None:
            return error_response(404, "CLINICAL_RESOURCE_NOT_FOUND", "El encuentro clínico no existe.")

        study_type = data.get("study_type")
        if not study_type:
            raise ApiError("'study_type' es obligatorio.")
        items = data.get("items")
        if not isinstance(items, list):
            raise ApiError("'items' debe ser una lista.")
        idempotency_key = data.get("idempotency_key", "") or ""

        already_existed = (
            bool(idempotency_key)
            and StudyOrder.objects.filter(doctor=encounter.doctor, idempotency_key=idempotency_key).exists()
        )
        order = study_order_service.issue(
            actor=request.user, clinical_encounter=encounter, study_type=study_type, items=items,
            indications=data.get("indications", "") or "", observations=data.get("observations", "") or "",
            idempotency_key=idempotency_key,
        )
        return _json(order, 200 if already_existed else 201)


class StudyOrderDetailView(DocumentJsonApiView):
    def get(self, request, pk):
        order = study_order_service.get(actor=request.user, study_order_id=pk)
        return _json(order, 200)


class StudyOrderVersionsView(DocumentJsonApiView):
    def post(self, request, pk):
        data = parse_json_body(request)
        items = data.get("items")
        if not isinstance(items, list):
            raise ApiError("'items' debe ser una lista.")
        reason = data.get("reason", "") or ""
        new_version = study_order_service.create_version(
            actor=request.user, study_order_id=pk, items=items, reason=reason,
            indications=data.get("indications"), observations=data.get("observations"),
        )
        return _json(new_version, 201)


class StudyOrderVoidView(DocumentJsonApiView):
    def post(self, request, pk):
        data = parse_json_body(request)
        reason = data.get("reason", "") or ""
        if not reason:
            raise ApiError("'reason' es obligatorio para anular.")
        voided = study_order_service.void(actor=request.user, study_order_id=pk, reason=reason)
        return _json(voided, 200)

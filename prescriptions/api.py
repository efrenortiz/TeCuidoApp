"""JSON HTTP API for `Prescription` (docs/design/phase-4-api-contracts.md §2).

Same pattern as `medical_records/api.py` — plain Django views + `JsonResponse`,
thin views delegating to `prescriptions.services.prescription`.
"""

from django.http import JsonResponse

from clinical_documents.api_common import ApiError, DocumentJsonApiView, error_response, parse_json_body
from medical_records.models import ClinicalEncounter
from prescriptions.models import Prescription
from prescriptions.services import prescription as prescription_service


def _serialize_item(item):
    return {
        "position": item.position,
        "medication_name": item.medication_name,
        "presentation": item.presentation,
        "dose": item.dose,
        "dose_unit": item.dose_unit,
        "route": item.route,
        "frequency": item.frequency,
        "duration": item.duration,
        "instructions": item.instructions,
    }


def _serialize(prescription):
    return {
        "id": prescription.pk,
        "patient_id": prescription.patient_id,
        "doctor_id": prescription.doctor_id,
        "clinical_encounter_id": prescription.clinical_encounter_id,
        "status": prescription.status,
        "issued_at": prescription.issued_at.isoformat(),
        "version_number": prescription.version_number,
        "previous_version_id": prescription.previous_version_id,
        "is_current_version": prescription.is_current_version,
        "voided_at": prescription.voided_at.isoformat() if prescription.voided_at else None,
        "void_reason": prescription.void_reason,
        "items": [_serialize_item(item) for item in prescription.items.order_by("position")],
    }


def _json(prescription, status):
    return JsonResponse(_serialize(prescription), status=status)


class PrescriptionListCreateView(DocumentJsonApiView):
    def post(self, request):
        data = parse_json_body(request)
        encounter_id = data.get("clinical_encounter_id")
        if not encounter_id:
            raise ApiError("'clinical_encounter_id' es obligatorio.")
        encounter = ClinicalEncounter.objects.select_related("appointment").filter(pk=encounter_id).first()
        if encounter is None:
            return error_response(404, "CLINICAL_RESOURCE_NOT_FOUND", "El encuentro clínico no existe.")

        items = data.get("items")
        if not isinstance(items, list):
            raise ApiError("'items' debe ser una lista.")
        idempotency_key = data.get("idempotency_key", "") or ""

        already_existed = (
            bool(idempotency_key)
            and Prescription.objects.filter(doctor=encounter.doctor, idempotency_key=idempotency_key).exists()
        )
        prescription = prescription_service.issue(
            actor=request.user, clinical_encounter=encounter, items=items, idempotency_key=idempotency_key,
        )
        return _json(prescription, 200 if already_existed else 201)


class PrescriptionDetailView(DocumentJsonApiView):
    def get(self, request, pk):
        prescription = prescription_service.get(actor=request.user, prescription_id=pk)
        return _json(prescription, 200)


class PrescriptionVersionsView(DocumentJsonApiView):
    def post(self, request, pk):
        data = parse_json_body(request)
        items = data.get("items")
        if not isinstance(items, list):
            raise ApiError("'items' debe ser una lista.")
        reason = data.get("reason", "") or ""
        new_version = prescription_service.create_version(
            actor=request.user, prescription_id=pk, items=items, reason=reason,
        )
        return _json(new_version, 201)


class PrescriptionVoidView(DocumentJsonApiView):
    def post(self, request, pk):
        data = parse_json_body(request)
        reason = data.get("reason", "") or ""
        if not reason:
            raise ApiError("'reason' es obligatorio para anular.")
        voided = prescription_service.void(actor=request.user, prescription_id=pk, reason=reason)
        return _json(voided, 200)

"""JSON HTTP API for `ClinicalDocument` (docs/design/phase-4-api-contracts.md §4).

Upload usa `multipart/form-data` (contrato §4); los demás endpoints usan
JSON salvo descarga, que sirve el binario directamente.
"""

from datetime import datetime

from django.core.paginator import Paginator
from django.http import FileResponse, JsonResponse
from django.utils.http import content_disposition_header

from clinical_documents.api_common import ApiError, DocumentJsonApiView, error_response
from clinical_documents.models import ClinicalDocument
from clinical_documents.services import document as document_service
from medical_records.models import ClinicalEncounter
from patients.models import Patient

_PAGE_SIZE_DEFAULT = 20
_PAGE_SIZE_MAX = 100

_VALID_DOCUMENT_TYPES = {choice for choice, _ in ClinicalDocument.DocumentType.choices}


def _serialize(document):
    return {
        "id": document.pk,
        "patient_id": document.patient_id,
        "appointment_id": document.appointment_id,
        "clinical_encounter_id": document.clinical_encounter_id,
        "prescription_id": document.prescription_id,
        "study_order_id": document.study_order_id,
        "document_type": document.document_type,
        "origin": document.origin,
        "status": document.status,
        "original_filename": document.original_filename,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "created_by_id": document.created_by_id,
        "created_at": document.created_at.isoformat(),
        "version_number": document.version_number,
        "previous_version_id": document.previous_version_id,
        "is_current_version": document.is_current_version,
    }


def _parse_date(value, field):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ApiError(f"'{field}' debe tener formato YYYY-MM-DD.") from exc


class ClinicalDocumentListCreateView(DocumentJsonApiView):
    def post(self, request):
        patient_id = request.POST.get("patient_id")
        if not patient_id:
            raise ApiError("'patient_id' es obligatorio.")
        patient = Patient.objects.filter(pk=patient_id).first()
        if patient is None:
            return error_response(404, "CLINICAL_RESOURCE_NOT_FOUND", "El paciente no existe.")

        document_type = request.POST.get("document_type")
        if document_type not in _VALID_DOCUMENT_TYPES:
            raise ApiError("'document_type' inválido.")

        uploaded = request.FILES.get("file")
        if uploaded is None:
            raise ApiError("Se requiere un archivo ('file').")

        clinical_encounter = None
        encounter_id = request.POST.get("clinical_encounter_id")
        if encounter_id:
            clinical_encounter = ClinicalEncounter.objects.select_related("appointment").filter(
                pk=encounter_id
            ).first()
            if clinical_encounter is None:
                return error_response(404, "CLINICAL_RESOURCE_NOT_FOUND", "El encuentro clínico no existe.")

        document = document_service.upload(
            actor=request.user, patient=patient, content=uploaded.read(),
            original_filename=uploaded.name, document_type=document_type,
            appointment=clinical_encounter.appointment if clinical_encounter else None,
            clinical_encounter=clinical_encounter,
        )
        return JsonResponse(_serialize(document), status=201)

    def get(self, request):
        patient_id = request.GET.get("patient")
        if not patient_id:
            raise ApiError("El parámetro 'patient' es obligatorio.")
        patient = Patient.objects.filter(pk=patient_id).first()
        if patient is None:
            return error_response(404, "CLINICAL_RESOURCE_NOT_FOUND", "El paciente no existe.")

        document_type = request.GET.get("type")
        if document_type and document_type not in _VALID_DOCUMENT_TYPES:
            raise ApiError("'type' inválido.")

        queryset = document_service.list_for_patient(actor=request.user, patient=patient, document_type=document_type)

        from_date = request.GET.get("from")
        to_date = request.GET.get("to")
        if from_date:
            queryset = queryset.filter(created_at__date__gte=_parse_date(from_date, "from"))
        if to_date:
            queryset = queryset.filter(created_at__date__lte=_parse_date(to_date, "to"))

        page_size = min(
            int(request.GET["page_size"]) if request.GET.get("page_size", "").isdigit() else _PAGE_SIZE_DEFAULT,
            _PAGE_SIZE_MAX,
        )
        page_number = int(request.GET["page"]) if request.GET.get("page", "").isdigit() else 1
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(page_number)
        return JsonResponse(
            {
                "count": paginator.count,
                "next": page.next_page_number() if page.has_next() else None,
                "previous": page.previous_page_number() if page.has_previous() else None,
                "results": [_serialize(d) for d in page.object_list],
            },
            status=200,
        )


class ClinicalDocumentDetailView(DocumentJsonApiView):
    def get(self, request, pk):
        document = document_service.get(actor=request.user, document_id=pk)
        return JsonResponse(_serialize(document), status=200)


class ClinicalDocumentDownloadView(DocumentJsonApiView):
    def get(self, request, pk):
        document, content = document_service.download(actor=request.user, document_id=pk)
        response = FileResponse(
            iter([content]), content_type=document.mime_type,
        )
        response["Content-Disposition"] = content_disposition_header(True, document.original_filename)
        return response

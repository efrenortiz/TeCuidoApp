"""Server-rendered UI para `ClinicalDocument` (S5/S6, phase-4-screens.md)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from clinical_documents.models import ClinicalDocument
from clinical_documents.services import document as document_service
from medical_records.services.exceptions import DocumentError, DocumentNotFound, DocumentPermissionDenied
from patients.models import Patient

_FRIENDLY_MESSAGES = {
    DocumentNotFound: "No se encontró el documento solicitado.",
    DocumentPermissionDenied: "No tienes permiso para ver estos documentos.",
}


def _friendly_message(exc):
    return _FRIENDLY_MESSAGES.get(type(exc), "No se pudo completar la operación.")


class ClinicalDocumentUiView(LoginRequiredMixin, View):
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class DocumentListView(ClinicalDocumentUiView):
    """S5 — Documentos del paciente: lista paginada, más reciente primero,
    filtros mínimos por tipo y fecha (phase-4-documents.md §18)."""

    _PAGE_SIZE = 20

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        document_type = request.GET.get("type") or None
        try:
            queryset = document_service.list_for_patient(actor=request.user, patient=patient, document_type=document_type)
        except DocumentError:
            raise Http404

        from_date = request.GET.get("from")
        to_date = request.GET.get("to")
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)

        page = Paginator(queryset, self._PAGE_SIZE).get_page(request.GET.get("page") or 1)
        return render(request, "clinical_documents/document_list.html", {
            "patient": patient, "page": page,
            "document_types": ClinicalDocument.DocumentType.choices,
            "selected_type": document_type or "",
        })


class DocumentUploadView(ClinicalDocumentUiView):
    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        return render(request, "clinical_documents/document_upload.html", {
            "patient": patient, "document_types": ClinicalDocument.DocumentType.choices,
        })

    def post(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        uploaded = request.FILES.get("file")
        document_type = request.POST.get("document_type", "")
        if uploaded is None:
            messages.error(request, "Selecciona un archivo.")
            return redirect("clinical_documents_ui:document_upload", patient_id=patient_id)
        try:
            document = document_service.upload(
                actor=request.user, patient=patient, content=uploaded.read(),
                original_filename=uploaded.name, document_type=document_type,
            )
        except DocumentError as exc:
            messages.error(request, _friendly_message(exc))
            return render(request, "clinical_documents/document_upload.html", {
                "patient": patient, "document_types": ClinicalDocument.DocumentType.choices,
            })
        messages.success(request, "Documento cargado.")
        return redirect("clinical_documents_ui:document_detail", pk=document.pk)


class DocumentDetailView(ClinicalDocumentUiView):
    """S6 — metadatos, origen, relaciones clínicas, versión, descarga."""

    def get(self, request, pk):
        try:
            document = document_service.get(actor=request.user, document_id=pk)
        except DocumentNotFound:
            raise Http404
        return render(request, "clinical_documents/document_detail.html", {
            "document": document, "patient": document.patient,
        })

"""Server-rendered UI para `Prescription` (docs/design/phase-4-ux.md,
docs/design/phase-4-screens.md — S1/S2). Mismo patrón que
`medical_records/views.py`: llama a los servicios de dominio directamente,
nunca a la API JSON."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from medical_records.models import ClinicalEncounter
from medical_records.services.exceptions import DocumentError, DocumentNotFound, DocumentPermissionDenied
from prescriptions.services import prescription as prescription_service

_FRIENDLY_MESSAGES = {
    DocumentNotFound: "No se encontró la receta solicitada.",
    DocumentPermissionDenied: "No tienes permiso para realizar esta acción.",
}


def _friendly_message(exc):
    return _FRIENDLY_MESSAGES.get(type(exc), "No se pudo completar la operación.")


class PrescriptionUiView(LoginRequiredMixin, View):
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


def _collect_items(post_data):
    """Formulario con filas repetidas `item-N-<campo>` (S1,
    `phase-4-screens.md` — "lista editable de medicamentos, orden explícito")."""
    items = []
    index = 1
    while post_data.get(f"item-{index}-medication_name") is not None:
        items.append({
            "medication_name": post_data.get(f"item-{index}-medication_name", ""),
            "presentation": post_data.get(f"item-{index}-presentation", ""),
            "dose": post_data.get(f"item-{index}-dose", ""),
            "dose_unit": post_data.get(f"item-{index}-dose_unit", ""),
            "route": post_data.get(f"item-{index}-route", ""),
            "frequency": post_data.get(f"item-{index}-frequency", ""),
            "duration": post_data.get(f"item-{index}-duration", ""),
            "instructions": post_data.get(f"item-{index}-instructions", ""),
        })
        index += 1
    return [item for item in items if item["medication_name"]]


class PrescriptionCreateView(PrescriptionUiView):
    """S1 — Crear receta, dentro del contexto de un `ClinicalEncounter`."""

    def get(self, request, encounter_id):
        encounter = get_object_or_404(ClinicalEncounter, pk=encounter_id)
        return render(request, "prescriptions/prescription_create.html", {
            "encounter": encounter, "patient": encounter.patient, "items": [{}], "errors": None,
        })

    def post(self, request, encounter_id):
        encounter = get_object_or_404(ClinicalEncounter, pk=encounter_id)
        items = _collect_items(request.POST)
        try:
            prescription = prescription_service.issue(actor=request.user, clinical_encounter=encounter, items=items)
        except DocumentError as exc:
            messages.error(request, _friendly_message(exc))
            return render(request, "prescriptions/prescription_create.html", {
                "encounter": encounter, "patient": encounter.patient, "items": items or [{}],
            })
        messages.success(request, "Receta emitida.")
        return redirect("prescriptions_ui:prescription_detail", pk=prescription.pk)


class PrescriptionDetailView(PrescriptionUiView):
    """S2 — Receta emitida: estado, versión, acciones Ver PDF/Descargar,
    Nueva versión y Anular cuando estén permitidas (autorización real
    verificada por el servicio, no sólo ocultando botones)."""

    def get(self, request, pk):
        try:
            prescription = prescription_service.get(actor=request.user, prescription_id=pk)
        except DocumentNotFound:
            raise Http404
        document = prescription.clinical_documents.filter(origin="GENERATED").first()
        return render(request, "prescriptions/prescription_detail.html", {
            "prescription": prescription, "patient": prescription.patient, "document": document,
        })


class PrescriptionVersionView(PrescriptionUiView):
    def get(self, request, pk):
        try:
            prescription = prescription_service.get(actor=request.user, prescription_id=pk)
        except DocumentNotFound:
            raise Http404
        items = [
            {
                "medication_name": item.medication_name, "presentation": item.presentation, "dose": item.dose,
                "dose_unit": item.dose_unit, "route": item.route, "frequency": item.frequency,
                "duration": item.duration, "instructions": item.instructions,
            }
            for item in prescription.items.order_by("position")
        ] or [{}]
        return render(request, "prescriptions/prescription_version.html", {
            "prescription": prescription, "patient": prescription.patient, "items": items,
        })

    def post(self, request, pk):
        items = _collect_items(request.POST)
        reason = request.POST.get("reason", "")
        try:
            new_version = prescription_service.create_version(
                actor=request.user, prescription_id=pk, items=items, reason=reason,
            )
        except DocumentError as exc:
            messages.error(request, _friendly_message(exc))
            return redirect("prescriptions_ui:prescription_version", pk=pk)
        messages.success(request, "Nueva versión creada.")
        return redirect("prescriptions_ui:prescription_detail", pk=new_version.pk)


class PrescriptionVoidView(PrescriptionUiView):
    def post(self, request, pk):
        reason = request.POST.get("reason", "")
        try:
            prescription_service.void(actor=request.user, prescription_id=pk, reason=reason)
        except DocumentError as exc:
            messages.error(request, _friendly_message(exc))
        else:
            messages.success(request, "Receta anulada.")
        return redirect("prescriptions_ui:prescription_detail", pk=pk)

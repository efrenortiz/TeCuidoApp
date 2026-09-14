"""Server-rendered UI para `StudyOrder` — mismo patrón que
`prescriptions/views.py` (ver ese módulo para el razonamiento)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from medical_records.models import ClinicalEncounter
from medical_records.services.exceptions import DocumentError, DocumentNotFound, DocumentPermissionDenied
from study_orders.models import StudyOrder
from study_orders.services import study_order as study_order_service

_FRIENDLY_MESSAGES = {
    DocumentNotFound: "No se encontró la solicitud de estudio.",
    DocumentPermissionDenied: "No tienes permiso para realizar esta acción.",
}


def _friendly_message(exc):
    return _FRIENDLY_MESSAGES.get(type(exc), "No se pudo completar la operación.")


class StudyOrderUiView(LoginRequiredMixin, View):
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


def _collect_items(post_data):
    items = []
    index = 1
    while post_data.get(f"item-{index}-study_name") is not None:
        items.append({
            "study_name": post_data.get(f"item-{index}-study_name", ""),
            "specific_instructions": post_data.get(f"item-{index}-specific_instructions", ""),
        })
        index += 1
    return [item for item in items if item["study_name"]]


class StudyOrderCreateView(StudyOrderUiView):
    """S3 — Solicitar estudios."""

    def get(self, request, encounter_id):
        encounter = get_object_or_404(ClinicalEncounter, pk=encounter_id)
        return render(request, "study_orders/study_order_create.html", {
            "encounter": encounter, "patient": encounter.patient, "items": [{}],
            "study_types": StudyOrder.StudyType.choices,
        })

    def post(self, request, encounter_id):
        encounter = get_object_or_404(ClinicalEncounter, pk=encounter_id)
        items = _collect_items(request.POST)
        try:
            order = study_order_service.issue(
                actor=request.user, clinical_encounter=encounter,
                study_type=request.POST.get("study_type", ""), items=items,
                indications=request.POST.get("indications", ""),
                observations=request.POST.get("observations", ""),
            )
        except DocumentError as exc:
            messages.error(request, _friendly_message(exc))
            return render(request, "study_orders/study_order_create.html", {
                "encounter": encounter, "patient": encounter.patient, "items": items or [{}],
                "study_types": StudyOrder.StudyType.choices,
            })
        messages.success(request, "Solicitud de estudio emitida.")
        return redirect("study_orders_ui:study_order_detail", pk=order.pk)


class StudyOrderDetailView(StudyOrderUiView):
    """S4 — Orden emitida."""

    def get(self, request, pk):
        try:
            order = study_order_service.get(actor=request.user, study_order_id=pk)
        except DocumentNotFound:
            raise Http404
        document = order.clinical_documents.filter(origin="GENERATED").first()
        return render(request, "study_orders/study_order_detail.html", {
            "order": order, "patient": order.patient, "document": document,
        })


class StudyOrderVersionView(StudyOrderUiView):
    def get(self, request, pk):
        try:
            order = study_order_service.get(actor=request.user, study_order_id=pk)
        except DocumentNotFound:
            raise Http404
        items = [
            {"study_name": item.study_name, "specific_instructions": item.specific_instructions}
            for item in order.items.order_by("position")
        ] or [{}]
        return render(request, "study_orders/study_order_version.html", {
            "order": order, "patient": order.patient, "items": items,
        })

    def post(self, request, pk):
        items = _collect_items(request.POST)
        reason = request.POST.get("reason", "")
        try:
            new_version = study_order_service.create_version(
                actor=request.user, study_order_id=pk, items=items, reason=reason,
                indications=request.POST.get("indications"), observations=request.POST.get("observations"),
            )
        except DocumentError as exc:
            messages.error(request, _friendly_message(exc))
            return redirect("study_orders_ui:study_order_version", pk=pk)
        messages.success(request, "Nueva versión creada.")
        return redirect("study_orders_ui:study_order_detail", pk=new_version.pk)


class StudyOrderVoidView(StudyOrderUiView):
    def post(self, request, pk):
        reason = request.POST.get("reason", "")
        try:
            study_order_service.void(actor=request.user, study_order_id=pk, reason=reason)
        except DocumentError as exc:
            messages.error(request, _friendly_message(exc))
        else:
            messages.success(request, "Solicitud anulada.")
        return redirect("study_orders_ui:study_order_detail", pk=pk)

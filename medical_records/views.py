"""Server-rendered UI for the clinical domain (docs/phases/phase-3-clinical-ux.md,
docs/design/clinical-screens.md).

These views call the domain services directly, exactly like
`appointments/views.py` does for Agenda — never the JSON API in
`medical_records/api.py`, which exists for programmatic/JS clients. No
screen here needs client-side fetch(): unlike Agenda's slot picker (which
genuinely needs live availability), a clinical encounter is edited on a
single page with plain form submits (SCREEN-066's "sin salto de scroll"
requirement is satisfied by re-rendering directly instead of redirecting
after save — see `EncounterSaveView`/`EncounterCompleteView` below — not
by adding JavaScript).

Screen inventory (clinical-screens.md §3, §38 — routing is explicitly not
mandated to be 1:1 with screen IDs): S-01 "Agenda clínica" is not a new
parallel agenda (SCREEN-016) — it's `appointments/appointment_detail.html`
extended with clinical action buttons (see that template and
`AppointmentDetailView`'s new `is_clinical_actor` context var). S-03
(`IN_PROGRESS` editing), S-04 (`COMPLETED` read-only) and S-07 (historical
detail, read-only) are ONE view/template (`EncounterDetailView`), branched
on `can_edit` — they are the same resource in different states/reader
contexts, not different screens.
"""

import datetime as dt

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as dj_timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from appointments.models import Appointment
from appointments.services.permissions import is_assigned_doctor
from medical_records.models import AuditEvent, ClinicalEncounter
from medical_records.services import encounter as encounter_service
from medical_records.services import record as record_service
from medical_records.services.exceptions import (
    ClinicalContentPlaceholder,
    ClinicalError,
    ClinicalNotAuthorized,
    ClinicalNotFound,
    ClinicalRecordNotFound,
    EncounterAlreadyCompleted,
    EncounterNotStartable,
    IncompleteClinicalContent,
    InvalidClinicalData,
)
from medical_records.services import audit as audit_service
from medical_records.services.permissions import can_edit_patient_record
from patients.models import Patient

# --- Shared helpers -----------------------------------------------------------

# SCREEN §9/UX §10 — traducir errores de dominio a lenguaje llano, nunca
# internals de Postgres/Django. SCREEN-158: microcopy exacto para 403.
_FRIENDLY_MESSAGES = {
    ClinicalNotAuthorized: "No tienes permiso para realizar esta acción.",
    ClinicalNotFound: "No se encontró la consulta o el expediente solicitado.",
    EncounterNotStartable: "La cita ya no está en un estado que permita iniciar la consulta.",
    EncounterAlreadyCompleted: "Esta consulta ya fue completada y no admite más cambios.",
    InvalidClinicalData: "Los datos enviados no son válidos.",
    ClinicalRecordNotFound: "El expediente clínico todavía no existe para este paciente.",
}

_FIELD_LABELS = {
    "reason_for_visit": "Motivo de consulta",
    "present_illness": "Padecimiento actual",
    "physical_exam": "Exploración física",
    "assessment": "Evaluación / diagnóstico",
    "plan": "Plan / indicaciones",
}


def _friendly_message(exc):
    return _FRIENDLY_MESSAGES.get(type(exc), "No se pudo completar la operación.")


def _encounter_form_values(encounter):
    values = {field: getattr(encounter, field) for field in encounter_service.CORE_FIELDS}
    values.update({field: getattr(encounter, field) for field in encounter_service.OPTIONAL_TEXT_FIELDS})
    for field in encounter_service.DECIMAL_FIELDS:
        value = getattr(encounter, field)
        values[field] = "" if value is None else str(value)
    return values


def _collect_encounter_form_data(post_data):
    """Recolecta únicamente los campos clínicos conocidos — nunca status,
    ids ni timestamps (SCREEN-063/064/065, controlados por servidor).
    Un textarea vacío se envía igual (guardado parcial válido, SC-039); un
    campo decimal vacío se envía como `None` explícito (el usuario borró
    el valor deliberadamente) en vez de omitirse silenciosamente."""
    data = {}
    for field in encounter_service.CORE_FIELDS + encounter_service.OPTIONAL_TEXT_FIELDS:
        if field in post_data:
            data[field] = post_data.get(field, "")
    for field in encounter_service.DECIMAL_FIELDS:
        if field in post_data:
            raw = post_data.get(field, "").strip()
            data[field] = raw if raw else None
    return data


def _render_encounter_detail(request, encounter, *, can_edit, form_values=None, field_errors=None, last_saved_at=None):
    return render(
        request,
        "medical_records/encounter_detail.html",
        {
            "encounter": encounter,
            "patient": encounter.patient,
            "can_edit": can_edit,
            "form_values": form_values or _encounter_form_values(encounter),
            "field_errors": field_errors or {},
            "last_saved_at": last_saved_at,
        },
    )


def _can_edit_encounter(request, encounter):
    return (
        encounter.status == ClinicalEncounter.Status.IN_PROGRESS
        and is_assigned_doctor(request.user, appointment=encounter.appointment)
    )


def _get_encounter_or_404(request, pk):
    try:
        return encounter_service.get_encounter(actor=request.user, encounter_id=pk)
    except ClinicalNotFound:
        # SC-068/SCREEN-127 — IDOR: no distinguir "no existe" de "no
        # autorizado", el mismo 404 genérico de Django para ambos casos.
        raise Http404


class ClinicalView(LoginRequiredMixin, View):
    """TS-103/158 — ninguna pantalla clínica queda disponible por caché
    del navegador/proxy después de logout o cambio de usuario
    (`never_cache`: agrega `Cache-Control: no-cache, no-store,
    must-revalidate`, `Pragma: no-cache`, `Expires: 0`)."""

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


# --- Iniciar consulta (S-02) -----------------------------------------------------


class EncounterStartView(ClinicalView):
    """Entrada clínica desde Agenda (S-01/S-02) — ver
    `appointments/appointment_detail.html`, botón "Iniciar consulta"."""

    def post(self, request, appointment_id):
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        try:
            encounter = encounter_service.start_encounter(actor=request.user, appointment=appointment)
        except ClinicalError as exc:
            messages.error(request, _friendly_message(exc))
            return redirect("appointments:appointment_detail", pk=appointment_id)
        return redirect("clinical_ui:encounter_detail", pk=encounter.pk)


# --- Consulta IN_PROGRESS / COMPLETED / histórica (S-03/S-04/S-07) ---------------


class EncounterDetailView(ClinicalView):
    def get(self, request, pk):
        encounter = _get_encounter_or_404(request, pk)
        return _render_encounter_detail(request, encounter, can_edit=_can_edit_encounter(request, encounter))


class EncounterSaveView(ClinicalView):
    def post(self, request, pk):
        encounter = _get_encounter_or_404(request, pk)
        if not _can_edit_encounter(request, encounter):
            messages.error(request, _friendly_message(ClinicalNotAuthorized()))
            return _render_encounter_detail(request, encounter, can_edit=False)

        data = _collect_encounter_form_data(request.POST)
        try:
            encounter = encounter_service.save_encounter(actor=request.user, encounter=encounter, data=data)
        except ClinicalContentPlaceholder as exc:
            messages.error(request, "Uno o más campos contiene un valor de relleno no válido (como 'N/A').")
            field_errors = {f: "Este campo contiene un valor de relleno no válido." for f in exc.fields}
            return _render_encounter_detail(request, encounter, can_edit=True, form_values=data, field_errors=field_errors)
        except ClinicalError as exc:
            messages.error(request, _friendly_message(exc))
            return _render_encounter_detail(request, encounter, can_edit=_can_edit_encounter(request, encounter), form_values=data)

        messages.success(request, "Guardado.")
        return _render_encounter_detail(
            request, encounter, can_edit=True, last_saved_at=dj_timezone.localtime(),
        )


class EncounterCompleteView(ClinicalView):
    def post(self, request, pk):
        encounter = _get_encounter_or_404(request, pk)
        if not _can_edit_encounter(request, encounter):
            messages.error(request, _friendly_message(ClinicalNotAuthorized()))
            return _render_encounter_detail(request, encounter, can_edit=False)

        data = _collect_encounter_form_data(request.POST)
        try:
            encounter = encounter_service.complete_encounter(actor=request.user, encounter=encounter, data=data)
        except (IncompleteClinicalContent, ClinicalContentPlaceholder) as exc:
            # SCREEN-072/073 — por-campo y el encuentro permanece
            # IN_PROGRESS con el contenido capturado intacto.
            labels = [_FIELD_LABELS.get(f, f) for f in exc.fields]
            messages.error(request, f"Revisa estos campos obligatorios: {', '.join(labels)}.")
            field_errors = {f: "Obligatorio para completar la consulta." for f in exc.fields}
            return _render_encounter_detail(request, encounter, can_edit=True, form_values=data, field_errors=field_errors)
        except ClinicalError as exc:
            messages.error(request, _friendly_message(exc))
            return _render_encounter_detail(request, encounter, can_edit=_can_edit_encounter(request, encounter), form_values=data)

        messages.success(request, "Consulta completada.")
        return _render_encounter_detail(request, encounter, can_edit=False)


# --- Expediente (S-05) ------------------------------------------------------------


class MedicalRecordView(ClinicalView):
    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        try:
            record = record_service.get_medical_record(actor=request.user, patient=patient)
        except ClinicalNotAuthorized:
            raise Http404
        return render(request, "medical_records/medical_record.html", self._context(request, patient, record))

    def post(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        if not can_edit_patient_record(request.user, patient):
            raise Http404

        data = {field: request.POST.get(field, "") for field in record_service.RECORD_FIELDS if field in request.POST}
        try:
            record = record_service.update_medical_record(actor=request.user, patient=patient, data=data)
        except ClinicalError as exc:
            messages.error(request, _friendly_message(exc))
            record = record_service.get_medical_record(actor=request.user, patient=patient)
        else:
            messages.success(request, "Expediente actualizado.")
        return render(request, "medical_records/medical_record.html", self._context(request, patient, record))

    def _context(self, request, patient, record):
        can_edit = record is not None and can_edit_patient_record(request.user, patient)
        last_encounter = None
        try:
            last_encounter = encounter_service.list_encounters_for_patient(
                actor=request.user, patient=patient, ordering="-started_at",
            ).first()
        except ClinicalNotAuthorized:
            pass
        return {
            "patient": patient,
            "record": record,
            "record_fields": record_service.RECORD_FIELDS,
            "can_edit": can_edit,
            "last_encounter": last_encounter,
        }


# --- Historial clínico (S-06) ------------------------------------------------------


class PatientEncounterHistoryView(ClinicalView):
    _PAGE_SIZE = 20

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        try:
            # SCREEN-097/UX-078 — del más reciente al más antiguo, sin
            # selector de orden en la UI (la API sí lo permite; la
            # interfaz no necesita exponer esa complejidad).
            queryset = encounter_service.list_encounters_for_patient(
                actor=request.user, patient=patient, ordering="-started_at",
            )
        except ClinicalNotAuthorized:
            raise Http404

        page_number = request.GET.get("page") or 1
        paginator = Paginator(queryset, self._PAGE_SIZE)
        page = paginator.get_page(page_number)
        return render(
            request,
            "medical_records/encounter_history.html",
            {"patient": patient, "page": page},
        )


# --- Audit trail administrativo (Fase 6, S6-AUDIT / F6-D05) -----------------


def _parse_ui_date(raw, *, end_of_day):
    """Convierte un `YYYY-MM-DD` de un `<input type="date">` a un datetime
    aware — inicio o fin de ese día en la zona horaria activa. `None`/valor
    inválido se ignora silenciosamente (mismo criterio permisivo que un
    filtro de UI opcional, no un endpoint que deba validar estrictamente)."""
    if not raw:
        return None
    parsed_date = parse_date(raw)
    if parsed_date is None:
        return None
    time_part = dt.time.max if end_of_day else dt.time.min
    return dj_timezone.make_aware(dt.datetime.combine(parsed_date, time_part))


class AuditTrailView(ClinicalView):
    """docs/design/phase-6-screens.md §2 — exclusiva de Administrador
    autorizado (F6-D05). `list_audit_events` ya aplica `can_view_audit_log`;
    un actor no autorizado recibe 404 uniforme (IDOR — mismo patrón ya
    usado en `_get_encounter_or_404`), nunca un 403 que confirme que la
    pantalla existe para roles no autorizados."""

    _PAGE_SIZE = 25

    def get(self, request):
        """Hallazgo 12.8 (docs/phases/phase-6-implementation-summary.md):
        la UI debe ofrecer los mismos filtros que el contrato compromete —
        `phase-6-audit-api-contracts.md` §3 incluye `date_from`/`date_to`,
        que antes de esta corrección solo existían en `AuditEventListView`
        (API), no aquí."""
        action = request.GET.get("action") or None
        result = request.GET.get("result") or None
        patient_id = request.GET.get("patient_id") or None
        date_from_raw = request.GET.get("date_from") or None
        date_to_raw = request.GET.get("date_to") or None

        patient = None
        if patient_id:
            # C-020 (prompt 2/4, validación browser/UI de Fase 6): un
            # `patient_id` no numérico (p. ej. un typo) hacía que
            # `Patient.objects.filter(pk=patient_id)` propagara un
            # `ValueError` sin capturar — 500 no controlado en una pantalla
            # de administrador. Mismo criterio permisivo ya usado por
            # `_parse_ui_date` arriba: un filtro de UI opcional con un
            # valor inválido se ignora, no rompe la pantalla. La API
            # (`AuditEventListView._parse_int`) ya validaba esto con un 400
            # controlado — esta corrección solo alinea la UI con ese mismo
            # estándar, no introduce una regla nueva.
            try:
                patient = Patient.objects.filter(pk=int(patient_id)).first()
            except (TypeError, ValueError):
                patient = None

        date_from = _parse_ui_date(date_from_raw, end_of_day=False)
        date_to = _parse_ui_date(date_to_raw, end_of_day=True)

        try:
            queryset = audit_service.list_audit_events(
                actor=request.user, patient=patient, action=action, result=result,
                date_from=date_from, date_to=date_to,
            )
        except ClinicalNotAuthorized:
            raise Http404

        page_number = request.GET.get("page") or 1
        paginator = Paginator(queryset, self._PAGE_SIZE)
        page = paginator.get_page(page_number)
        return render(
            request,
            "medical_records/audit_trail.html",
            {
                "page": page,
                "action_choices": AuditEvent.Action.choices,
                "result_choices": AuditEvent.Result.choices,
                "filters": {
                    "action": action, "result": result, "patient_id": patient_id,
                    "date_from": date_from_raw, "date_to": date_to_raw,
                },
            },
        )

"""JSON HTTP API for Agenda (docs/design/agenda-api-contracts.md).

Plain Django views + JsonResponse — no Django REST Framework. Fase 1 has
no DRF usage anywhere in the project and the contract here (plain JSON in,
JSON out, no schema/browsable-API requirement) doesn't need it; adding a
new dependency for this would violate CLAUDE.md §13's dependency
discipline. `docs/architecture.md` §28 only prescribes a layering *when*
DRF is used, it doesn't mandate DRF itself.

Every view here follows §2.3: parse/validate request shape → call a
domain service → translate the result or exception to HTTP. No business
rule is implemented in this module.

CSRF: these endpoints are session-authenticated (not token/API-key based),
so standard Django CSRF protection applies unmodified — no `csrf_exempt`
anywhere here, matching CLAUDE.md §11.
"""

import json

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone as dj_timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.views import View

from appointments.models import Appointment, Availability, Hold
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from appointments.services.exceptions import (
    AgendaError,
    AppointmentAlreadyCancelled,
    AppointmentConflict,
    AppointmentNotCancellable,
    AppointmentNotCompletable,
    AppointmentNotFound,
    AppointmentNotReschedulable,
    AppointmentNotStartable,
    AvailabilityBeyondBookingHorizon,
    AvailabilityConflict,
    AvailabilityHasAppointments,
    AvailabilityHasIncompatibleAppointments,
    AvailabilityNotFound,
    AvailabilityStartInPast,
    BookingWindowExpired,
    DoctorClinicRequired,
    DurationIncompatible,
    HoldAlreadyExists,
    HoldConflict,
    HoldExpired,
    HoldNotActive,
    HoldNotFound,
    HoldNotOwned,
    IdempotencyKeyConflict,
    InvalidAvailabilityInterval,
    InvalidDoctorClinic,
    InvalidPatient,
    InvalidSlot,
    NoShowNotAllowed,
    NotAuthorized,
    SlotUnavailable,
)
from clinics.models import Clinic
from doctors.models import Doctor
from patients.models import Patient

# --- Domain error -> HTTP translation ---------------------------------------
#
# (status, code, default message). `HoldNotOwned` intentionally shares
# HoldNotFound's code/status — §13's 404 definition covers "no existe o no
# debe revelarse al actor", and revealing that a hold belongs to someone
# else would leak its existence to a non-owner.
_ERROR_MAP = {
    NotAuthorized: (403, "NOT_AUTHORIZED", "No tienes autorización para esta operación."),
    DoctorClinicRequired: (422, "DOCTOR_CLINIC_REQUIRED", "No existe una relación médico-consultorio vigente."),
    AvailabilityStartInPast: (422, "AVAILABILITY_START_IN_PAST", "La disponibilidad no puede iniciar en el pasado."),
    AvailabilityBeyondBookingHorizon: (
        422, "AVAILABILITY_BEYOND_BOOKING_HORIZON", "La fecha excede el horizonte de 6 meses.",
    ),
    InvalidAvailabilityInterval: (422, "INVALID_AVAILABILITY_INTERVAL", "El intervalo de disponibilidad no es válido."),
    AvailabilityConflict: (409, "AVAILABILITY_CONFLICT", "El médico ya tiene disponibilidad en ese horario."),
    AvailabilityNotFound: (404, "AVAILABILITY_NOT_FOUND", "La disponibilidad no existe."),
    AvailabilityHasAppointments: (
        422, "AVAILABILITY_HAS_APPOINTMENTS", "La disponibilidad tiene citas asociadas.",
    ),
    AvailabilityHasIncompatibleAppointments: (
        422, "AVAILABILITY_HAS_INCOMPATIBLE_APPOINTMENTS",
        "El nuevo intervalo ya no contiene una cita existente.",
    ),
    InvalidSlot: (422, "INVALID_SLOT", "El horario solicitado no corresponde a un slot válido."),
    SlotUnavailable: (409, "SLOT_UNAVAILABLE", "El horario seleccionado ya no está disponible."),
    BookingWindowExpired: (422, "BOOKING_WINDOW_EXPIRED", "El plazo para reservar este horario ya venció."),
    HoldAlreadyExists: (409, "HOLD_ALREADY_EXISTS", "Ya tienes otro horario en espera."),
    HoldConflict: (409, "HOLD_CONFLICT", "Otro usuario ya tiene este horario en espera."),
    HoldNotFound: (404, "HOLD_NOT_FOUND", "El hold no existe."),
    HoldNotOwned: (404, "HOLD_NOT_FOUND", "El hold no existe."),
    HoldNotActive: (409, "HOLD_NOT_ACTIVE", "El hold ya no está activo."),
    HoldExpired: (409, "HOLD_EXPIRED", "El hold expiró."),
    AppointmentConflict: (409, "APPOINTMENT_CONFLICT", "El horario ya fue ocupado por otra cita."),
    InvalidPatient: (422, "INVALID_PATIENT", "No puedes reservar una cita para este paciente."),
    InvalidDoctorClinic: (422, "INVALID_DOCTOR_CLINIC", "La combinación médico-consultorio no es válida."),
    IdempotencyKeyConflict: (
        409, "IDEMPOTENCY_CONFLICT", "Esta clave de idempotencia ya se usó para una operación distinta.",
    ),
    AppointmentNotFound: (404, "APPOINTMENT_NOT_FOUND", "La cita no existe."),
    AppointmentNotCancellable: (422, "APPOINTMENT_NOT_CANCELLABLE", "La cita no puede cancelarse."),
    AppointmentAlreadyCancelled: (409, "APPOINTMENT_ALREADY_CANCELLED", "La cita ya está cancelada."),
    AppointmentNotReschedulable: (422, "APPOINTMENT_NOT_RESCHEDULABLE", "La cita no puede reprogramarse."),
    DurationIncompatible: (422, "DURATION_INCOMPATIBLE", "La duración de la cita no es compatible con ese consultorio."),
    AppointmentNotStartable: (409, "APPOINTMENT_ALREADY_STARTED", "La cita ya fue iniciada o no puede iniciarse."),
    AppointmentNotCompletable: (422, "APPOINTMENT_NOT_COMPLETABLE", "La cita no puede finalizarse."),
    NoShowNotAllowed: (422, "NO_SHOW_NOT_ALLOWED", "Todavía no se puede marcar esta cita como NO_SHOW."),
}


class ApiError(Exception):
    """View-layer error for structurally invalid requests (§13, 400 Bad
    Request) — never a business rule, just malformed/missing input."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _error_response(status, code, message):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


class JsonApiView(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _error_response(401, "NOT_AUTHENTICATED", "Se requiere autenticación.")
        try:
            return super().dispatch(request, *args, **kwargs)
        except ApiError as exc:
            return _error_response(400, "BAD_REQUEST", exc.message)
        except ValueError as exc:
            return _error_response(400, "BAD_REQUEST", str(exc) or "Datos inválidos.")
        except AgendaError as exc:
            status, code, message = _ERROR_MAP.get(type(exc), (400, "DOMAIN_ERROR", "No se pudo completar la operación."))
            return _error_response(status, code, message)


# --- Request parsing helpers -------------------------------------------------


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


def _require_field(data, field):
    value = data.get(field)
    if value in (None, ""):
        raise ApiError(f"El campo '{field}' es obligatorio.")
    return value


def _parse_int(value, field):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(f"El campo '{field}' debe ser un entero.") from exc


def _parse_iso_date(value, field):
    parsed = parse_date(value) if isinstance(value, str) else None
    if parsed is None:
        raise ApiError(f"El campo '{field}' debe ser una fecha ISO 8601 (YYYY-MM-DD).")
    return parsed


def _parse_iso_time(value, field):
    parsed = parse_time(value) if isinstance(value, str) else None
    if parsed is None:
        raise ApiError(f"El campo '{field}' debe ser una hora ISO 8601 (HH:MM).")
    return parsed


def _parse_iso_datetime(value, field):
    parsed = parse_datetime(value) if isinstance(value, str) else None
    if parsed is None or dj_timezone.is_naive(parsed):
        raise ApiError(f"El campo '{field}' debe ser un datetime ISO 8601 con zona horaria.")
    return parsed


def _require_query_param(request, field):
    value = request.GET.get(field)
    if not value:
        raise ApiError(f"El parámetro '{field}' es obligatorio.")
    return value


def _get_doctor_or_400(doctor_id):
    doctor = Doctor.objects.filter(pk=doctor_id).first()
    if doctor is None:
        raise ApiError("doctor_id no corresponde a un médico existente.")
    return doctor


def _get_clinic_or_400(clinic_id):
    clinic = Clinic.objects.filter(pk=clinic_id).first()
    if clinic is None:
        raise ApiError("clinic_id no corresponde a un consultorio existente.")
    return clinic


def _get_patient_or_400(patient_id):
    patient = Patient.objects.filter(pk=patient_id).first()
    if patient is None:
        raise ApiError("patient_id no corresponde a un paciente existente.")
    return patient


# --- Serialization ------------------------------------------------------------


def _serialize_availability(a):
    return {
        "id": a.pk,
        "doctor_id": a.doctor_id,
        "clinic_id": a.clinic_id,
        "date": a.date.isoformat(),
        "start_time": a.start_time.strftime("%H:%M"),
        "end_time": a.end_time.strftime("%H:%M"),
        "duration_minutes": a.duration_minutes,
        "is_active": a.is_active,
    }


def _serialize_hold(h):
    return {
        "id": h.pk,
        "doctor_id": h.doctor_id,
        "clinic_id": h.clinic_id,
        "start": h.start_at.isoformat(),
        "end": h.end_at.isoformat(),
        "status": h.status,
        "created_at": h.created_at.isoformat(),
        "expires_at": h.expires_at.isoformat(),
    }


def _serialize_appointment(a, *, detail=False):
    data = {
        "id": a.pk,
        "patient_id": a.patient_id,
        "doctor_id": a.doctor_id,
        "clinic_id": a.clinic_id,
        "start": a.start_at.isoformat(),
        "end": a.end_at.isoformat(),
        "duration_minutes": a.duration_minutes,
        "status": a.status,
    }
    if detail:
        data["created_by"] = a.created_by_id
        data["created_at"] = a.created_at.isoformat()
        if a.status == Appointment.Status.CANCELLED:
            data["cancellation"] = {
                "cancelled_at": a.cancelled_at.isoformat(),
                "cancelled_by": a.cancelled_by_id,
                "reason": a.cancellation_reason,
            }
        if a.status == Appointment.Status.NO_SHOW:
            data["no_show"] = {
                "no_show_at": a.no_show_at.isoformat(),
                "no_show_by": a.no_show_by_id,
            }
    return data


# --- Availability -------------------------------------------------------------


class AvailabilityCreateView(JsonApiView):
    def post(self, request):
        data = _parse_json_body(request)
        doctor = _get_doctor_or_400(_parse_int(_require_field(data, "doctor_id"), "doctor_id"))
        clinic = _get_clinic_or_400(_parse_int(_require_field(data, "clinic_id"), "clinic_id"))
        date_value = _parse_iso_date(_require_field(data, "date"), "date")
        start_time = _parse_iso_time(_require_field(data, "start_time"), "start_time")
        end_time = _parse_iso_time(_require_field(data, "end_time"), "end_time")

        availability = availability_service.create_availability(
            actor=request.user, doctor=doctor, clinic=clinic,
            date=date_value, start_time=start_time, end_time=end_time,
        )
        return JsonResponse(_serialize_availability(availability), status=201)


class AvailabilityDetailView(JsonApiView):
    def patch(self, request, pk):
        availability = Availability.objects.filter(pk=pk).select_related("doctor", "clinic").first()
        if availability is None:
            return _error_response(404, "AVAILABILITY_NOT_FOUND", "La disponibilidad no existe.")

        data = _parse_json_body(request)
        date_value = _parse_iso_date(_require_field(data, "date"), "date")
        start_time = _parse_iso_time(_require_field(data, "start_time"), "start_time")
        end_time = _parse_iso_time(_require_field(data, "end_time"), "end_time")

        updated = availability_service.update_availability(
            actor=request.user, availability=availability,
            date=date_value, start_time=start_time, end_time=end_time,
        )
        return JsonResponse(_serialize_availability(updated), status=200)


class AvailabilityDeactivateView(JsonApiView):
    def post(self, request, pk):
        availability = Availability.objects.filter(pk=pk).select_related("doctor", "clinic").first()
        if availability is None:
            return _error_response(404, "AVAILABILITY_NOT_FOUND", "La disponibilidad no existe.")

        updated = availability_service.deactivate_availability(actor=request.user, availability=availability)
        return JsonResponse({"id": updated.pk, "is_active": updated.is_active}, status=200)


class SlotsView(JsonApiView):
    def get(self, request):
        doctor = _get_doctor_or_400(_parse_int(_require_query_param(request, "doctor_id"), "doctor_id"))
        clinic = _get_clinic_or_400(_parse_int(_require_query_param(request, "clinic_id"), "clinic_id"))
        date_value = _parse_iso_date(_require_query_param(request, "date"), "date")

        slots = availability_service.get_available_slots(
            actor=request.user, doctor=doctor, clinic=clinic, date=date_value
        )
        return JsonResponse(
            {
                "doctor_id": doctor.pk,
                "clinic_id": clinic.pk,
                "date": date_value.isoformat(),
                "slots": [
                    {"start": s["start"].isoformat(), "end": s["end"].isoformat(), "status": s["status"]}
                    for s in slots
                ],
            },
            status=200,
        )


# --- Hold -----------------------------------------------------------------------


class HoldCreateView(JsonApiView):
    def post(self, request):
        data = _parse_json_body(request)
        doctor = _get_doctor_or_400(_parse_int(_require_field(data, "doctor_id"), "doctor_id"))
        clinic = _get_clinic_or_400(_parse_int(_require_field(data, "clinic_id"), "clinic_id"))
        start_at = _parse_iso_datetime(_require_field(data, "start"), "start")
        end_at = _parse_iso_datetime(_require_field(data, "end"), "end")

        # §6.1 lists an Idempotency-Key header, but §8's idempotency
        # section only requires it for cita creation/reprogramación, and
        # `Hold` has no idempotency_key field (Etapa 1 design) — the
        # header is accepted (never rejected) but has no effect here.
        hold = hold_service.create_hold(
            actor=request.user, doctor=doctor, clinic=clinic, start_at=start_at, end_at=end_at
        )
        return JsonResponse(_serialize_hold(hold), status=201)


class HoldReleaseView(JsonApiView):
    def post(self, request, pk):
        hold = hold_service.release_hold(actor=request.user, hold=Hold(pk=pk))
        return JsonResponse({"id": hold.pk, "status": hold.status}, status=200)


# --- Appointment ------------------------------------------------------------------


_PAGE_SIZE_DEFAULT = 25
_PAGE_SIZE_MAX = 100


class AppointmentCollectionView(JsonApiView):
    """`POST /api/appointments/` (§7.1, crear desde hold) and
    `GET /api/appointments/` (§7.2, listar) share the same URL — one
    resource collection, split by HTTP method, not by path."""

    def post(self, request):
        data = _parse_json_body(request)
        hold_id = _parse_int(_require_field(data, "hold_id"), "hold_id")
        patient_id = _parse_int(_require_field(data, "patient_id"), "patient_id")

        hold = Hold.objects.filter(pk=hold_id).select_related("doctor", "clinic").first()
        if hold is None:
            return _error_response(404, "HOLD_NOT_FOUND", "El hold no existe.")
        patient = _get_patient_or_400(patient_id)

        idempotency_key = request.headers.get("Idempotency-Key", "")
        appointment = appointment_service.create_appointment_from_hold(
            actor=request.user, hold=hold, patient=patient, doctor=hold.doctor, clinic=hold.clinic,
            idempotency_key=idempotency_key,
        )
        return JsonResponse(_serialize_appointment(appointment), status=201)

    def get(self, request):
        params = request.GET

        status_value = params.get("status") or None
        if status_value and status_value not in Appointment.Status.values:
            raise ApiError("El parámetro 'status' no es un estado válido.")

        date_from = _parse_iso_date(params["date_from"], "date_from") if params.get("date_from") else None
        date_to = _parse_iso_date(params["date_to"], "date_to") if params.get("date_to") else None
        patient_id = _parse_int(params["patient_id"], "patient_id") if params.get("patient_id") else None
        doctor_id = _parse_int(params["doctor_id"], "doctor_id") if params.get("doctor_id") else None
        clinic_id = _parse_int(params["clinic_id"], "clinic_id") if params.get("clinic_id") else None

        qs = appointment_service.list_appointments_for_actor(
            request.user, status=status_value, date_from=date_from, date_to=date_to,
            patient_id=patient_id, doctor_id=doctor_id, clinic_id=clinic_id,
        )

        page_size = min(_parse_int(params["page_size"], "page_size"), _PAGE_SIZE_MAX) if params.get("page_size") else _PAGE_SIZE_DEFAULT
        page_number = _parse_int(params["page"], "page") if params.get("page") else 1

        paginator = Paginator(qs, page_size)
        page = paginator.get_page(page_number)
        return JsonResponse(
            {
                "count": paginator.count,
                "next": page.next_page_number() if page.has_next() else None,
                "previous": page.previous_page_number() if page.has_previous() else None,
                "results": [_serialize_appointment(a) for a in page.object_list],
            },
            status=200,
        )


class AppointmentDetailView(JsonApiView):
    def get(self, request, pk):
        appointment = appointment_service.get_appointment_detail(request.user, appointment_id=pk)
        return JsonResponse(_serialize_appointment(appointment, detail=True), status=200)


class AppointmentCancelView(JsonApiView):
    def post(self, request, pk):
        data = _parse_json_body(request)
        reason = _require_field(data, "reason")

        appointment = appointment_service.cancel_appointment(
            actor=request.user, appointment=Appointment(pk=pk), reason=reason,
        )
        return JsonResponse(
            {
                "id": appointment.pk,
                "status": appointment.status,
                "cancelled_at": appointment.cancelled_at.isoformat(),
                "cancelled_by": appointment.cancelled_by_id,
                "cancellation_reason": appointment.cancellation_reason,
            },
            status=200,
        )


class AppointmentRescheduleView(JsonApiView):
    def post(self, request, pk):
        data = _parse_json_body(request)
        clinic = _get_clinic_or_400(_parse_int(_require_field(data, "clinic_id"), "clinic_id"))
        new_start_at = _parse_iso_datetime(_require_field(data, "start"), "start")
        reason = _require_field(data, "reason")
        # "end" is accepted for format validation only — the backend
        # always derives the true end from the appointment's frozen
        # duration (§9.1: "la duración efectiva debe mantenerse
        # congelada"), never from a client-supplied value.
        if data.get("end"):
            _parse_iso_datetime(data["end"], "end")

        idempotency_key = request.headers.get("Idempotency-Key", "")
        appointment = appointment_service.reschedule_appointment(
            actor=request.user, appointment=Appointment(pk=pk), new_clinic=clinic,
            new_start_at=new_start_at, reason=reason, idempotency_key=idempotency_key,
        )
        return JsonResponse(
            {
                "id": appointment.pk,
                "doctor_id": appointment.doctor_id,
                "clinic_id": appointment.clinic_id,
                "start": appointment.start_at.isoformat(),
                "end": appointment.end_at.isoformat(),
                "duration_minutes": appointment.duration_minutes,
                "status": appointment.status,
            },
            status=200,
        )


class AppointmentStartView(JsonApiView):
    def post(self, request, pk):
        appointment = appointment_service.start_appointment(actor=request.user, appointment=Appointment(pk=pk))
        return JsonResponse(
            {
                "id": appointment.pk,
                "status": appointment.status,
                "started_at": appointment.started_at.isoformat(),
                "started_by": appointment.started_by_id,
            },
            status=200,
        )


class AppointmentCompleteView(JsonApiView):
    def post(self, request, pk):
        appointment = appointment_service.complete_appointment(actor=request.user, appointment=Appointment(pk=pk))
        return JsonResponse(
            {
                "id": appointment.pk,
                "status": appointment.status,
                "completed_at": appointment.completed_at.isoformat(),
                "completed_by": appointment.completed_by_id,
            },
            status=200,
        )


class AppointmentNoShowView(JsonApiView):
    def post(self, request, pk):
        appointment = appointment_service.mark_no_show(actor=request.user, appointment=Appointment(pk=pk))
        return JsonResponse(
            {
                "id": appointment.pk,
                "status": appointment.status,
                "no_show_at": appointment.no_show_at.isoformat(),
                "no_show_by": appointment.no_show_by_id,
            },
            status=200,
        )

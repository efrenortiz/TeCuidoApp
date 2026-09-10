"""Server-rendered UI for Agenda (docs/design/phase-2-agenda-ux.md).

These views call the domain services directly (same as Fase 1's views) —
never the JSON API in `appointments/api.py`, which exists for programmatic/
JS clients. The one interactive exception is the slot-picker/hold flow
(`BookingView`/`RescheduleView` templates), which legitimately needs
real-time fetch() calls against that same JSON API for live slot status
and the 15-minute hold countdown (docs/design/phase-2-agenda-ux.md §10-15).
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.utils.dateparse import parse_date
from django.views import View

from appointments.forms import AvailabilityForm, CancelAppointmentForm
from appointments.models import Appointment, Availability
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services.exceptions import (
    AgendaError,
    AppointmentAlreadyCancelled,
    AppointmentNotCancellable,
    AppointmentNotCompletable,
    AppointmentNotFound,
    AppointmentNotReschedulable,
    AppointmentNotStartable,
    AvailabilityHasAppointments,
    AvailabilityHasIncompatibleAppointments,
    HoldConflict,
    HoldExpired,
    NoShowNotAllowed,
    NotAuthorized,
    SlotUnavailable,
)
from appointments.services.permissions import (
    can_manage_availability,
    doctor_profile,
    is_assigned_doctor,
    patient_profile,
    responsible_profile,
)
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import Patient, ResponsiblePatientRelationship

# --- Shared helpers -----------------------------------------------------------

# phase-2-agenda-ux.md §25 — translate domain errors to plain language,
# never PostgreSQL/Django internals.
_FRIENDLY_MESSAGES = {
    NotAuthorized: "No tienes autorización para realizar esta acción.",
    HoldConflict: "Este horario ya fue reservado temporalmente por otro usuario.",
    HoldExpired: "El tiempo de reserva terminó. Selecciona nuevamente un horario.",
    SlotUnavailable: "El horario dejó de estar disponible. Selecciona otro.",
    AvailabilityHasAppointments: (
        "Esta disponibilidad no puede desactivarse porque ya tiene citas asociadas."
    ),
    AvailabilityHasIncompatibleAppointments: (
        "Esta disponibilidad tiene citas asociadas y no puede modificarse con este nuevo "
        "horario. Primero deben reprogramarse las citas afectadas."
    ),
    AppointmentNotCancellable: "La cita ya comenzó y no puede cancelarse.",
    AppointmentAlreadyCancelled: "La cita ya está cancelada.",
    AppointmentNotReschedulable: "La cita ya comenzó y no puede reprogramarse.",
    AppointmentNotStartable: "La cita ya fue iniciada o no puede iniciarse.",
    AppointmentNotCompletable: "La cita no puede finalizarse en su estado actual.",
    NoShowNotAllowed: "Todavía no se puede marcar esta cita como 'No se presentó'.",
}


def _friendly_message(exc):
    return _FRIENDLY_MESSAGES.get(type(exc), "No se pudo completar la operación.")


def _doctor_clinic_choices(doctor):
    return [
        (dc.clinic_id, f"{dc.clinic.name} ({dc.appointment_duration_minutes} min)")
        for dc in DoctorClinic.objects.filter(doctor=doctor, is_active=True).select_related("clinic")
    ]


def _parse_day(request, default=None):
    raw = request.GET.get("date")
    parsed = parse_date(raw) if raw else None
    return parsed or default or dj_timezone.localdate()


def _agenda_redirect_url(request, doctor, day):
    doctor_qs = f"&doctor_id={doctor.pk}" if request.user.is_superuser and doctor_profile(request.user) is None else ""
    return f"{reverse('appointments:doctor_agenda')}?date={day.isoformat()}{doctor_qs}"


def _resolve_managed_doctor(request):
    """The Doctor whose agenda/disponibilidad `request.user` is managing
    (phase-2-agenda-ux.md §3.3-3.4): the doctor themself, or — for an
    administrator, who isn't a doctor — whichever Doctor is named by
    `doctor_id` in the query/POST data. Returns `None` when an
    administrator hasn't picked one yet (caller sends them to the picker);
    raises `Http404` for anyone else."""
    doctor = doctor_profile(request.user)
    if doctor is not None:
        return doctor
    if not request.user.is_superuser:
        raise Http404
    doctor_id = request.GET.get("doctor_id") or request.POST.get("doctor_id")
    if not doctor_id:
        return None
    return get_object_or_404(Doctor, pk=doctor_id)


# --- Médico: agenda + disponibilidad --------------------------------------------


class DoctorAgendaView(LoginRequiredMixin, View):
    """phase-2-agenda-ux.md §4 — día → disponibilidades → slots → citas."""

    def get(self, request):
        doctor = _resolve_managed_doctor(request)
        if doctor is None:
            return redirect("appointments:admin_doctor_picker")
        day = _parse_day(request)

        availabilities = (
            Availability.objects.filter(doctor=doctor, date=day, is_active=True)
            .select_related("clinic")
            .order_by("start_time")
        )
        appointments_by_start = {
            a.start_at: a
            for a in Appointment.objects.filter(doctor=doctor, start_at__date=day).select_related(
                "patient__person", "clinic"
            )
        }

        blocks = []
        for availability in availabilities:
            slots = availability_service.get_available_slots(
                actor=request.user, doctor=doctor, clinic=availability.clinic, date=day
            )
            enriched_slots = [
                {**slot, "appointment": appointments_by_start.get(slot["start"])} for slot in slots
            ]
            has_appointments = any(s["appointment"] is not None for s in enriched_slots)
            blocks.append(
                {"availability": availability, "slots": enriched_slots, "has_appointments": has_appointments}
            )

        is_admin_managed = doctor_profile(request.user) is None
        return render(
            request,
            "appointments/doctor_agenda.html",
            {
                "doctor": doctor,
                "day": day,
                "prev_day": day - timedelta(days=1),
                "next_day": day + timedelta(days=1),
                "blocks": blocks,
                "is_admin_managed": is_admin_managed,
                "doctor_qs": f"&doctor_id={doctor.pk}" if is_admin_managed else "",
            },
        )


class AvailabilityCreateView(LoginRequiredMixin, View):
    def get(self, request):
        doctor = _resolve_managed_doctor(request)
        if doctor is None:
            return redirect("appointments:admin_doctor_picker")
        form = AvailabilityForm(clinic_choices=_doctor_clinic_choices(doctor))
        return render(
            request, "appointments/availability_form.html",
            {"form": form, "mode": "create", "managed_doctor": doctor},
        )

    def post(self, request):
        doctor = _resolve_managed_doctor(request)
        if doctor is None:
            return redirect("appointments:admin_doctor_picker")
        clinic_choices = _doctor_clinic_choices(doctor)
        form = AvailabilityForm(request.POST, clinic_choices=clinic_choices)
        if not form.is_valid():
            return render(
                request, "appointments/availability_form.html",
                {"form": form, "mode": "create", "managed_doctor": doctor},
            )

        clinic = get_object_or_404(Clinic, pk=form.cleaned_data["clinic_id"])
        try:
            availability = availability_service.create_availability(
                actor=request.user, doctor=doctor, clinic=clinic,
                date=form.cleaned_data["date"], start_time=form.cleaned_data["start_time"],
                end_time=form.cleaned_data["end_time"],
            )
        except AgendaError as exc:
            messages.error(request, _friendly_message(exc))
            return render(
                request, "appointments/availability_form.html",
                {"form": form, "mode": "create", "managed_doctor": doctor},
            )

        messages.success(request, "Disponibilidad creada.")
        return redirect(_agenda_redirect_url(request, doctor, availability.date))


class AvailabilityUpdateView(LoginRequiredMixin, View):
    def _get_availability(self, request, pk):
        availability = get_object_or_404(Availability, pk=pk)
        if not can_manage_availability(request.user, doctor=availability.doctor):
            raise Http404
        return availability

    def get(self, request, pk):
        availability = self._get_availability(request, pk)
        # phase-2-agenda-ux.md §6 — editing is hidden entirely, not just
        # restricted, whenever the availability has any occupying cita.
        if availability.appointments.filter(status__in=Appointment.OCCUPYING_STATUSES).exists():
            messages.error(request, _friendly_message(AvailabilityHasIncompatibleAppointments()))
            return redirect(_agenda_redirect_url(request, availability.doctor, availability.date))

        form = AvailabilityForm(
            clinic_choices=_doctor_clinic_choices(availability.doctor),
            initial={
                "clinic_id": availability.clinic_id, "date": availability.date,
                "start_time": availability.start_time, "end_time": availability.end_time,
            },
        )
        return render(
            request, "appointments/availability_form.html",
            {"form": form, "mode": "edit", "availability": availability},
        )

    def post(self, request, pk):
        availability = self._get_availability(request, pk)
        clinic_choices = _doctor_clinic_choices(availability.doctor)
        form = AvailabilityForm(request.POST, clinic_choices=clinic_choices)
        if not form.is_valid():
            return render(
                request, "appointments/availability_form.html",
                {"form": form, "mode": "edit", "availability": availability},
            )
        if str(availability.clinic_id) != form.cleaned_data["clinic_id"]:
            # The domain doesn't support changing an Availability's clinic
            # (docs/design/availability-rules.md) — the UI simply doesn't
            # offer it (clinic field stays but is effectively read-only in
            # the template; this is a defensive backstop).
            messages.error(request, "No es posible cambiar el consultorio de una disponibilidad existente.")
            return render(
                request, "appointments/availability_form.html",
                {"form": form, "mode": "edit", "availability": availability},
            )

        try:
            updated = availability_service.update_availability(
                actor=request.user, availability=availability,
                date=form.cleaned_data["date"], start_time=form.cleaned_data["start_time"],
                end_time=form.cleaned_data["end_time"],
            )
        except AgendaError as exc:
            messages.error(request, _friendly_message(exc))
            return render(
                request, "appointments/availability_form.html",
                {"form": form, "mode": "edit", "availability": availability},
            )

        messages.success(request, "Disponibilidad actualizada.")
        return redirect(_agenda_redirect_url(request, updated.doctor, updated.date))


class AvailabilityDeactivateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        availability = get_object_or_404(Availability, pk=pk)
        if not can_manage_availability(request.user, doctor=availability.doctor):
            raise Http404
        try:
            availability_service.deactivate_availability(actor=request.user, availability=availability)
        except AgendaError as exc:
            messages.error(request, _friendly_message(exc))
        else:
            messages.success(request, "La disponibilidad fue desactivada. Se conserva su historial.")
        return redirect(_agenda_redirect_url(request, availability.doctor, availability.date))


class AdminDoctorPickerView(LoginRequiredMixin, View):
    """phase-2-agenda-ux.md §3.4 — an administrator isn't a doctor and
    must pick which médico's agenda/disponibilidad to manage."""

    def get(self, request):
        if not request.user.is_superuser:
            raise Http404
        doctors = Doctor.objects.filter(is_active=True).select_related("person").order_by(
            "person__last_name_paterno", "person__first_name"
        )
        return render(request, "appointments/admin_doctor_picker.html", {"doctors": doctors})


# --- Reserva de cita (interactive: slot picker + hold) --------------------------


class BookingView(LoginRequiredMixin, View):
    """phase-2-agenda-ux.md §10-15, §30-31 — the slot grid, hold
    countdown, and final confirmation are all driven client-side by
    `static/js/agenda-booking.js` against the JSON API; this view only
    renders the shell and the actor-appropriate patient selector."""

    def get(self, request):
        patient_actor = patient_profile(request.user)
        responsible = responsible_profile(request.user)
        doctor_actor = doctor_profile(request.user)

        patient_mode = None
        fixed_patient = None
        responsible_patients = []

        if patient_actor is not None:
            patient_mode = "self"
            fixed_patient = patient_actor
        elif responsible is not None:
            patient_mode = "responsible"
            responsible_patients = list(
                Patient.objects.filter(
                    responsible_relationships__responsible=responsible,
                    responsible_relationships__status=ResponsiblePatientRelationship.Status.ACTIVE,
                ).select_related("person")
            )
            requested_patient_id = request.GET.get("patient_id")
            if requested_patient_id:
                fixed_patient = next(
                    (p for p in responsible_patients if str(p.pk) == requested_patient_id), None
                )
        elif doctor_actor is not None or request.user.is_superuser:
            patient_mode = "manual"
        else:
            raise Http404

        doctor_clinic_pairs = [
            {
                "doctor_id": dc.doctor_id,
                "doctor_name": str(dc.doctor.person),
                "clinic_id": dc.clinic_id,
                "clinic_name": dc.clinic.name,
            }
            for dc in DoctorClinic.objects.filter(is_active=True, doctor__is_active=True).select_related(
                "doctor__person", "clinic"
            )
        ]

        booking_config = {
            "patientMode": patient_mode,
            "fixedPatientId": fixed_patient.pk if fixed_patient else None,
            "slotsApiUrl": reverse("appointments_api:availability_slots"),
            "holdsApiUrl": reverse("appointments_api:hold_create"),
            "appointmentsApiUrl": reverse("appointments_api:appointment_create_or_list"),
        }

        return render(
            request,
            "appointments/booking.html",
            {
                "patient_mode": patient_mode,
                "fixed_patient": fixed_patient,
                "responsible_patients": responsible_patients,
                "doctor_clinic_pairs": doctor_clinic_pairs,
                "booking_config": booking_config,
            },
        )


class RescheduleView(LoginRequiredMixin, View):
    """phase-2-agenda-ux.md §19-20 — no hold: the slot picker submits
    straight to the reschedule endpoint, and the doctor is fixed (frozen
    per docs/design/agenda-permissions.md §14)."""

    def get(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        try:
            appointment_service.get_appointment_detail(request.user, appointment_id=pk)
        except AppointmentNotFound:
            raise Http404

        clinic_choices = [
            {"clinic_id": dc.clinic_id, "clinic_name": dc.clinic.name}
            for dc in DoctorClinic.objects.filter(doctor=appointment.doctor, is_active=True).select_related(
                "clinic"
            )
        ]
        reschedule_config = {
            "slotsApiUrl": reverse("appointments_api:availability_slots"),
            "rescheduleApiUrl": reverse("appointments_api:appointment_reschedule", args=[appointment.pk]),
            "doctorId": appointment.doctor_id,
            "currentClinicId": appointment.clinic_id,
        }

        return render(
            request,
            "appointments/reschedule.html",
            {"appointment": appointment, "clinics": clinic_choices, "reschedule_config": reschedule_config},
        )


# --- Mis citas ------------------------------------------------------------------


class MyAppointmentsView(LoginRequiredMixin, View):
    """phase-2-agenda-ux.md §16-17 — 'Próximas' / 'Historial'."""

    def get(self, request):
        responsible = responsible_profile(request.user)
        patient_id = request.GET.get("patient_id")

        if responsible is not None and not patient_id:
            return redirect("appointments:responsible_patients")

        qs = appointment_service.list_appointments_for_actor(
            request.user, patient_id=int(patient_id) if patient_id else None
        ).select_related("patient__person", "doctor__person", "clinic")

        upcoming = [a for a in qs if a.status in (Appointment.Status.SCHEDULED, Appointment.Status.IN_CONSULTATION)]
        history = [a for a in qs if a.status not in (Appointment.Status.SCHEDULED, Appointment.Status.IN_CONSULTATION)]

        return render(
            request,
            "appointments/my_appointments.html",
            {"upcoming": upcoming, "history": history, "patient_id": patient_id},
        )


class ResponsiblePatientPickerView(LoginRequiredMixin, View):
    def get(self, request):
        responsible = responsible_profile(request.user)
        if responsible is None:
            raise Http404
        patients_qs = Patient.objects.filter(
            responsible_relationships__responsible=responsible,
            responsible_relationships__status=ResponsiblePatientRelationship.Status.ACTIVE,
        ).select_related("person")
        return render(request, "appointments/responsible_patient_picker.html", {"patients": patients_qs})


class AppointmentDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            appointment = appointment_service.get_appointment_detail(request.user, appointment_id=pk)
        except AppointmentNotFound:
            raise Http404
        return render(
            request,
            "appointments/appointment_detail.html",
            {
                "appointment": appointment,
                "is_assigned_doctor": is_assigned_doctor(request.user, appointment=appointment),
                "now": dj_timezone.now(),
            },
        )


class AppointmentCancelView(LoginRequiredMixin, View):
    def get(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        form = CancelAppointmentForm()
        return render(request, "appointments/appointment_cancel.html", {"appointment": appointment, "form": form})

    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        form = CancelAppointmentForm(request.POST)
        if not form.is_valid():
            return render(request, "appointments/appointment_cancel.html", {"appointment": appointment, "form": form})

        try:
            appointment_service.cancel_appointment(
                actor=request.user, appointment=appointment, reason=form.cleaned_data["reason"]
            )
        except AgendaError as exc:
            messages.error(request, _friendly_message(exc))
            return render(request, "appointments/appointment_cancel.html", {"appointment": appointment, "form": form})

        messages.success(request, "La cita fue cancelada y el horario quedó disponible nuevamente.")
        return redirect("appointments:appointment_detail", pk=pk)


class AppointmentStartView(LoginRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        try:
            appointment_service.start_appointment(actor=request.user, appointment=appointment)
        except AgendaError as exc:
            messages.error(request, _friendly_message(exc))
        else:
            messages.success(request, "Consulta iniciada.")
        return redirect("appointments:appointment_detail", pk=pk)


class AppointmentCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        try:
            appointment_service.complete_appointment(actor=request.user, appointment=appointment)
        except AgendaError as exc:
            messages.error(request, _friendly_message(exc))
        else:
            messages.success(request, "Consulta finalizada.")
        return redirect("appointments:appointment_detail", pk=pk)


class AppointmentNoShowView(LoginRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        try:
            appointment_service.mark_no_show(actor=request.user, appointment=appointment)
        except AgendaError as exc:
            messages.error(request, _friendly_message(exc))
        else:
            messages.success(request, "Se registró que el paciente no se presentó.")
        return redirect("appointments:appointment_detail", pk=pk)

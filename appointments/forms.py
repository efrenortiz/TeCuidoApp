from django import forms

from appointments.models import RequestReason


class AvailabilityForm(forms.Form):
    """Crear/editar disponibilidad (phase-2-agenda-ux.md §5-6). `clinic_id`
    choices are populated per-request from the doctor's active
    `DoctorClinic` set — never a static/global list."""

    clinic_id = forms.ChoiceField(label="Consultorio")
    date = forms.DateField(label="Fecha", widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(label="Hora inicio", widget=forms.TimeInput(attrs={"type": "time"}))
    end_time = forms.TimeField(label="Hora fin", widget=forms.TimeInput(attrs={"type": "time"}))

    def __init__(self, *args, clinic_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["clinic_id"].choices = clinic_choices

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")
        # The service re-validates this authoritatively — this is only the
        # UI-level early check phase-2-agenda-ux.md §5 allows.
        if start_time and end_time and start_time >= end_time:
            self.add_error("end_time", "La hora fin debe ser posterior a la hora inicio.")
        return cleaned


class CancelAppointmentForm(forms.Form):
    reason = forms.ChoiceField(label="Motivo de cancelación", choices=RequestReason.choices)

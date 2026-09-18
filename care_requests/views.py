"""Server-rendered UI para `CareRequest` — mismo patrón que
`appointments.views.BookingView` (el selector de slot se reutiliza tal
cual, vía el mismo endpoint `availability/slots/`); a diferencia de la
reserva directa de Agenda, aquí no hay panel de Hold/countdown visible: la
operación completa (`Hold` → `Appointment` → `ClinicalDocument` →
`CONVERTIDA`) es una sola llamada atómica a
`POST /api/v1/care-requests/` (`docs/design/care-request-service-contracts.md`).

Solo paciente o responsable pueden usar esta pantalla — nunca médico o
administrador (`requirements.md` §12; mismo criterio que
`care_requests.services.care_request._resolve_patient`)."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from appointments.services.permissions import patient_profile, responsible_profile
from care_requests.api import MAX_ATTACHMENTS
from clinical_documents.services.storage import ALLOWED_MIME_TO_EXTENSIONS, max_size_bytes
from clinics.models import DoctorClinic
from patients.models import Patient, ResponsiblePatientRelationship


class CareRequestCreateView(LoginRequiredMixin, View):
    def get(self, request):
        patient_actor = patient_profile(request.user)
        responsible = responsible_profile(request.user)

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
        else:
            # Médico/administrador: la reserva directa de Fase 2 ya les
            # sirve — CareRequest es exclusivamente autoservicio.
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

        # Límites de adjuntos reutilizados tal cual de sus fuentes reales
        # (docs/design/care-request-ux.md §10: "coincide con las reglas de
        # servidor ya existentes") — nunca hardcodeados por separado en el
        # JavaScript, para que un cambio futuro en esas constantes no deje
        # la validación de cliente desincronizada de la del servidor.
        allowed_extensions = sorted(
            {ext for extensions in ALLOWED_MIME_TO_EXTENSIONS.values() for ext in extensions}
        )
        care_request_config = {
            "patientMode": patient_mode,
            "fixedPatientId": fixed_patient.pk if fixed_patient else None,
            "slotsApiUrl": reverse("appointments_api:availability_slots"),
            "createApiUrl": reverse("care_requests_api:care_request_create"),
            "maxAttachments": MAX_ATTACHMENTS,
            "maxAttachmentSizeBytes": max_size_bytes(),
            "allowedAttachmentExtensions": allowed_extensions,
        }

        return render(request, "care_requests/care_request_create.html", {
            "patient_mode": patient_mode,
            "fixed_patient": fixed_patient,
            "responsible_patients": responsible_patients,
            "doctor_clinic_pairs": doctor_clinic_pairs,
            "care_request_config": care_request_config,
        })

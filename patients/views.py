from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.roles import DOCTOR, PATIENT, RESPONSIBLE, RoleRequiredMixin
from patients.forms import MinorPatientForm, MinorRelationshipForm, PatientProfileForm
from patients.models import Patient, ResponsiblePatientRelationship
from patients.services import minors
from patients.services.permissions import can_view_patient

_GENERIC_MATCH_MESSAGE = (
    "Ya existe un registro relacionado con estos datos. Contacta a tu médico o al "
    "consultorio para continuar."
)

_WIZARD_STEPS = [
    {"label": "Datos del menor"},
    {"label": "Relación"},
    {"label": "Confirmación"},
]


def _wizard_context(current, **extra):
    return {"steps": _WIZARD_STEPS, "current": current, **extra}


class DoctorRequiredMixin(RoleRequiredMixin):
    required_role = DOCTOR


class ResponsibleRequiredMixin(RoleRequiredMixin):
    required_role = RESPONSIBLE


class PatientRequiredMixin(RoleRequiredMixin):
    required_role = PATIENT


class PatientDetailView(LoginRequiredMixin, View):
    """Minimal object-authorized read view.

    Returns 404 both when the patient doesn't exist and when the requester
    isn't authorized to see it — an ID guessed/incremented in the URL never
    distinguishes "not found" from "not yours" (anti-enumeration). Not
    role-gated: authorization here is entirely object-level
    (can_view_patient), since a doctor, a responsible, or the patient
    themself may all legitimately reach this same view.
    """

    def get(self, request, pk):
        try:
            patient = Patient.objects.select_related("person").get(pk=pk)
        except Patient.DoesNotExist:
            raise Http404

        if not can_view_patient(request.user, patient):
            raise Http404

        return render(request, "patients/patient_detail.html", {"patient": patient})


class PatientListView(DoctorRequiredMixin, View):
    """Médico — 'Mis pacientes' (docs/design/screens.md §6.4)."""

    def get(self, request):
        doctor = request.user.person.doctor_profile
        patients_qs = (
            Patient.objects.filter(
                doctor_relationships__doctor=doctor, doctor_relationships__is_active=True
            )
            .select_related("person")
            .distinct()
            .order_by("person__last_name_paterno", "person__first_name")
        )

        query = request.GET.get("q", "").strip()
        if query:
            patients_qs = patients_qs.filter(
                Q(person__first_name__icontains=query)
                | Q(person__last_name_paterno__icontains=query)
                | Q(person__last_name_materno__icontains=query)
                | Q(person__phone__icontains=query)
                | Q(person__user__email__icontains=query)
            )

        return render(
            request, "patients/patient_list.html", {"patients": patients_qs, "query": query}
        )


class PatientProfileView(PatientRequiredMixin, View):
    """Paciente — 'Mi perfil' (docs/design/screens.md §6.6). `email` is
    never accepted here, even though the template doesn't render it — the
    form simply has no field for it (defense in depth, not just hidden UI)."""

    def get(self, request):
        patient = request.user.person.patient_profile
        form = PatientProfileForm(person=patient.person, patient=patient)
        return render(request, "patients/my_profile.html", {"form": form})

    def post(self, request):
        patient = request.user.person.patient_profile
        form = PatientProfileForm(request.POST, person=patient.person, patient=patient)
        if not form.is_valid():
            return render(request, "patients/my_profile.html", {"form": form})
        form.save()
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("patients:my_profile")


class ResponsiblePatientListView(ResponsibleRequiredMixin, View):
    """Responsable — 'Mis pacientes a cargo' (docs/design/screens.md §6.7):
    the patients this responsible actively manages, plus any PENDING
    co-responsable requests on those same patients that this responsible
    can approve or reject."""

    def get(self, request):
        responsible = request.user.person.responsible_profile

        relationships = (
            ResponsiblePatientRelationship.objects.filter(
                responsible=responsible,
                status=ResponsiblePatientRelationship.Status.ACTIVE,
            )
            .select_related("patient__person")
            .order_by("patient__person__first_name")
        )

        managed_patient_ids = relationships.values_list("patient_id", flat=True)
        pending_requests = (
            ResponsiblePatientRelationship.objects.filter(
                patient_id__in=list(managed_patient_ids),
                status=ResponsiblePatientRelationship.Status.PENDING,
            )
            .exclude(responsible=responsible)
            .select_related("patient__person", "responsible__person")
        )

        return render(
            request,
            "patients/my_dependents.html",
            {"relationships": relationships, "pending_requests": pending_requests},
        )


class _RelationshipRequestActionView(ResponsibleRequiredMixin, View):
    """Shared POST-only base for approve/reject — subclasses set `service_fn`."""

    service_fn = staticmethod(lambda **kwargs: None)
    success_message = ""

    def post(self, request, pk):
        relationship = get_object_or_404(
            ResponsiblePatientRelationship,
            pk=pk,
            status=ResponsiblePatientRelationship.Status.PENDING,
        )
        responsible = request.user.person.responsible_profile
        try:
            self.service_fn(relationship=relationship, approving_responsible=responsible)
        except minors.NotAuthorizedToDecide:
            raise Http404
        except minors.MinorRegistrationError:
            raise Http404
        messages.success(request, self.success_message)
        return redirect("patients:my_dependents")


class ApproveRelationshipRequestView(_RelationshipRequestActionView):
    service_fn = staticmethod(minors.approve_relationship_request)
    success_message = "Solicitud aprobada."


class RejectRelationshipRequestView(_RelationshipRequestActionView):
    service_fn = staticmethod(minors.reject_relationship_request)
    success_message = "Solicitud rechazada."


_MINOR_SESSION_KEY = "register_minor_data"
_MINOR_RESULT_SESSION_KEY = "register_minor_result"


class RegisterMinorPersonalDataView(ResponsibleRequiredMixin, View):
    """Wizard paso 1 de 3 — datos del menor (docs/design/screens.md §6.8)."""

    def get(self, request):
        return render(
            request,
            "patients/register_minor_step1.html",
            _wizard_context(1, form=MinorPatientForm()),
        )

    def post(self, request):
        form = MinorPatientForm(request.POST)
        if not form.is_valid():
            return render(
                request, "patients/register_minor_step1.html", _wizard_context(1, form=form)
            )

        person_data = form.person_data()
        patient_data = form.patient_data()

        # Read-only early feedback — never the only defense. The service
        # re-validates everything, atomically, when step 2 is submitted.
        match, confidence = minors.find_existing_patient_match(
            curp=patient_data.get("curp", ""),
            first_name=person_data["first_name"],
            last_name_paterno=person_data["last_name_paterno"],
            last_name_materno=person_data.get("last_name_materno", ""),
            birth_date=person_data["birth_date"],
        )
        blocks_self_service = confidence == "name_dob" or (
            confidence == "curp" and match.person.user_id is not None
        )
        if blocks_self_service:
            form.add_error(None, _GENERIC_MATCH_MESSAGE)
            return render(
                request, "patients/register_minor_step1.html", _wizard_context(1, form=form)
            )

        request.session[_MINOR_SESSION_KEY] = {
            "person_data": {**person_data, "birth_date": person_data["birth_date"].isoformat()},
            "patient_data": patient_data,
        }
        return redirect("patients:register_minor_step2")


class RegisterMinorRelationshipView(ResponsibleRequiredMixin, View):
    """Wizard paso 2 de 3 — relación con el menor; al enviarse, crea (o
    solicita vincular) el paciente atómicamente."""

    def get(self, request):
        if _MINOR_SESSION_KEY not in request.session:
            return redirect("patients:register_minor_step1")
        return render(
            request,
            "patients/register_minor_step2.html",
            _wizard_context(2, form=MinorRelationshipForm()),
        )

    def post(self, request):
        session_data = request.session.get(_MINOR_SESSION_KEY)
        if session_data is None:
            return redirect("patients:register_minor_step1")

        form = MinorRelationshipForm(request.POST)
        if not form.is_valid():
            return render(
                request, "patients/register_minor_step2.html", _wizard_context(2, form=form)
            )

        person_data = dict(session_data["person_data"])
        person_data["birth_date"] = date.fromisoformat(person_data["birth_date"])
        patient_data = session_data["patient_data"]
        responsible = request.user.person.responsible_profile

        try:
            patient, _relationship, outcome = minors.register_minor_patient(
                responsible=responsible,
                person_data=person_data,
                patient_data=patient_data,
                relationship_type=form.cleaned_data["relationship_type"],
            )
        except minors.ResponsibleSelfRegistrationNotAllowed:
            form.add_error(None, "No puedes registrarte a ti mismo como el menor.")
            return render(
                request, "patients/register_minor_step2.html", _wizard_context(2, form=form)
            )
        except minors.ExistingPatientRequiresManualReview:
            form.add_error(None, _GENERIC_MATCH_MESSAGE)
            return render(
                request, "patients/register_minor_step2.html", _wizard_context(2, form=form)
            )
        except minors.AlreadyLinked:
            del request.session[_MINOR_SESSION_KEY]
            messages.info(request, "Ya tienes acceso a este paciente.")
            return redirect("patients:my_dependents")

        del request.session[_MINOR_SESSION_KEY]
        request.session[_MINOR_RESULT_SESSION_KEY] = {
            "patient_id": patient.pk,
            "outcome": outcome,
        }
        return redirect("patients:register_minor_step3")


class RegisterMinorConfirmView(ResponsibleRequiredMixin, View):
    """Wizard paso 3 de 3 — confirmación (solo lectura, sin formulario)."""

    def get(self, request):
        result = request.session.pop(_MINOR_RESULT_SESSION_KEY, None)
        if result is None:
            return redirect("patients:register_minor_step1")
        patient = get_object_or_404(Patient, pk=result["patient_id"])
        return render(
            request,
            "patients/register_minor_step3.html",
            _wizard_context(3, patient=patient, outcome=result["outcome"]),
        )

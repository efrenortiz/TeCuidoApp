import datetime as dt

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from accounts.forms import InvitationAcceptForm, InvitationCreateForm
from accounts.models import Invitation, PolicyAcceptance
from accounts.roles import DOCTOR, RoleRequiredMixin, user_roles
from accounts.services import consent as consent_service
from accounts.services import email_verification, invitations
from medical_records.models import AuditEvent
from medical_records.services import audit as audit_service
from notifications import services as notification_service


class AuditedLoginView(auth_views.LoginView):
    """Fase 6 (docs/design/phase-6-audit-domain.md §3/§4, catálogo base
    `LOGIN`). Auditoría explícita en el punto exacto donde se conoce el
    resultado real (mismo principio que AH-156 en
    `medical_records/services/audit.py`: nunca delegar auditoría a un
    signal genérico) — nunca dispersa en un handler que no sabe si el login
    fue aceptado o rechazado y por qué.

    ITD-008 (docs/phases/phase-6-implementation-summary.md): `record_event`
    exige un `actor` real (AH-086, invariante ya cerrada de Fase 3) — un
    intento con credenciales inválidas o un correo que no existe no tiene
    ningún `User` real al que atribuir el evento, así que no se audita.
    Sí se audita un rechazo cuando las credenciales eran correctas pero
    `confirm_login_allowed` los rechaza por otra razón (p. ej. correo no
    verificado) — ahí `form.get_user()` sí resuelve un actor real."""

    def form_valid(self, form):
        response = super().form_valid(form)
        audit_service.safe_record_event(
            actor=self.request.user,
            action=AuditEvent.Action.LOGIN,
            result=AuditEvent.Result.SUCCESS,
            resource_type=AuditEvent.ResourceType.USER,
            resource_id=self.request.user.pk,
        )
        return response

    def form_invalid(self, form):
        user = form.get_user() if hasattr(form, "get_user") else None
        if user is not None:
            audit_service.safe_record_event(
                actor=user,
                action=AuditEvent.Action.LOGIN,
                result=AuditEvent.Result.DENIED,
                resource_type=AuditEvent.ResourceType.USER,
                resource_id=user.pk,
            )
        return super().form_invalid(form)


class HomeView(LoginRequiredMixin, View):
    """Minimal authenticated landing page.

    Fase 1 has no dashboard (that's Fase 5) — this only exists so
    LOGIN_REDIRECT_URL points at a real page instead of a 404.
    """

    def get(self, request):
        return render(request, "accounts/home.html", {"roles": user_roles(request.user)})


class DoctorRequiredMixin(RoleRequiredMixin):
    """ADR-004 §36: invitation creation is Doctor-only in Fase 1 — Admin's
    authority here is explicitly undefined and not assumed."""

    required_role = DOCTOR


class InvitationListView(DoctorRequiredMixin, View):
    """Médico — 'Listado de invitaciones' (docs/design/screens.md §6.3)."""

    def get(self, request):
        doctor = request.user.person.doctor_profile
        invitations_qs = Invitation.objects.filter(doctor=doctor).order_by("-created_at")
        return render(request, "accounts/invitation_list.html", {"invitations": invitations_qs})


class InvitationCreateView(DoctorRequiredMixin, View):
    def get(self, request):
        return render(request, "accounts/invitation_form.html", {"form": InvitationCreateForm()})

    def post(self, request):
        form = InvitationCreateForm(request.POST)
        if not form.is_valid():
            return render(request, "accounts/invitation_form.html", {"form": form})

        doctor = request.user.person.doctor_profile
        invitation, raw_token = invitations.create_invitation(
            doctor=doctor, email=form.cleaned_data["email"]
        )
        accept_url = request.build_absolute_uri(
            reverse("accounts:invitation_accept", args=[raw_token])
        )
        notification_service.create_registration_invitation_notification(
            recipient_address=invitation.email, accept_url=accept_url
        )
        messages.success(request, "Invitación enviada.")
        return redirect("accounts:invitation_create")


class InvitationAcceptView(View):
    def _validated_invitation_or_response(self, request, token):
        """Returns (invitation, None) or (None, error_response)."""
        try:
            return invitations.validate_invitation(token), None
        except invitations.InvitationNotFound:
            return None, render(request, "accounts/invitation_invalid.html", status=404)
        except invitations.InvitationNotUsable as exc:
            return None, render(
                request, "accounts/invitation_invalid.html", {"status": exc.status}, status=410
            )

    def get(self, request, token):
        _invitation, error_response = self._validated_invitation_or_response(request, token)
        if error_response is not None:
            return error_response
        return render(request, "accounts/invitation_accept.html", {"form": InvitationAcceptForm()})

    def post(self, request, token):
        _invitation, error_response = self._validated_invitation_or_response(request, token)
        if error_response is not None:
            return error_response

        form = InvitationAcceptForm(request.POST)
        if not form.is_valid():
            return render(request, "accounts/invitation_accept.html", {"form": form})

        try:
            patient = invitations.accept_invitation(
                token,
                password=form.cleaned_data["password"],
                person_data=form.person_data(),
                patient_data=form.patient_data(),
            )
        except invitations.InvitationNotUsable as exc:
            return render(
                request, "accounts/invitation_invalid.html", {"status": exc.status}, status=410
            )
        except invitations.InvitationNotFound:
            return render(request, "accounts/invitation_invalid.html", status=404)
        except invitations.EmailAlreadyRegistered:
            form.add_error(
                None, "Ya existe una cuenta con este correo. Inicia sesión en su lugar."
            )
            return render(request, "accounts/invitation_accept.html", {"form": form})

        user = patient.person.user
        verification_token = email_verification.generate_email_verification_token(user)
        verify_url = request.build_absolute_uri(
            reverse("accounts:verify_email", args=[verification_token])
        )
        notification_service.create_email_verification_notification(user=user, verify_url=verify_url)
        return render(request, "accounts/invitation_accept_success.html")


class EmailVerificationView(View):
    def get(self, request, token):
        try:
            email_verification.verify_email_token(token)
        except email_verification.VerificationTokenExpired:
            return render(
                request, "accounts/verify_email_result.html", {"ok": False, "reason": "expired"}
            )
        except email_verification.InvalidVerificationToken:
            return render(
                request, "accounts/verify_email_result.html", {"ok": False, "reason": "invalid"}
            )
        except email_verification.EmailAlreadyVerified:
            return render(
                request,
                "accounts/verify_email_result.html",
                {"ok": False, "reason": "already_verified"},
            )
        return render(request, "accounts/verify_email_result.html", {"ok": True})


class ConsentView(LoginRequiredMixin, View):
    """S6-01/S6-02 (docs/design/phase-6-screens.md §1, F6-D04). Aceptación
    de documentos de plataforma — nunca consentimientos clínicos."""

    def get(self, request):
        return render(request, "accounts/consent.html", self._context(request))

    def post(self, request):
        policy_type = request.POST.get("policy_type")
        current_version = consent_service.CURRENT_POLICY_VERSIONS.get(policy_type)
        if current_version is not None:
            consent_service.record_acceptance(
                user=request.user, policy_type=policy_type, policy_version=current_version,
            )
            messages.success(request, "Documento aceptado.")
        return redirect("accounts:consent")

    def _context(self, request):
        """PD-006 / hallazgo 12.9: la pantalla debe mostrar qué documento,
        qué versión, la referencia canónica externa y (si ya se aceptó)
        cuándo — no solo un booleano de "aceptado/pendiente"."""
        status = consent_service.acceptance_status(user=request.user)
        return {
            "documents": [
                {
                    "policy_type": policy_type,
                    "label": PolicyAcceptance.PolicyType(policy_type).label,
                    "version": info["version"],
                    "accepted": info["accepted"],
                    "document_url": info["document_url"],
                    # dj_timezone.datetime.fromisoformat en vez de
                    # |date: sobre el string ISO devuelto por
                    # acceptance_status (pensado para JSON) — el template
                    # necesita un objeto datetime real para formatear.
                    "accepted_at": (
                        dt.datetime.fromisoformat(info["accepted_at"]) if info["accepted_at"] else None
                    ),
                }
                for policy_type, info in status.items()
            ],
        }

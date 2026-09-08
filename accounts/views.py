from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from accounts.forms import InvitationAcceptForm, InvitationCreateForm
from accounts.models import Invitation
from accounts.roles import DOCTOR, RoleRequiredMixin, user_roles
from accounts.services import email_verification, invitations


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
        send_mail(
            subject="Invitación a TeCuidoApp",
            message=f"Completa tu registro aquí: {accept_url}",
            from_email=None,
            recipient_list=[invitation.email],
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
        send_mail(
            subject="Verifica tu correo — TeCuidoApp",
            message=f"Verifica tu correo aquí: {verify_url}",
            from_email=None,
            recipient_list=[user.email],
        )
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

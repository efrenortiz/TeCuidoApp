"""Role derivation (ADR-004 / requirements.md §3.1).

Roles are not stored as a separate flag to keep in sync: they are derived
from actual domain state (which functional profiles a Person has, and
Django's native `is_superuser` for the Administrator role). This keeps a
single source of truth and lets one Person hold several roles at once
(e.g. Patient + Responsible, explicitly required by ADR-002 §15).
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

ADMINISTRATOR = "ADMINISTRATOR"
DOCTOR = "DOCTOR"
PATIENT = "PATIENT"
RESPONSIBLE = "RESPONSIBLE"


def user_roles(user):
    """Return the list of role labels applicable to `user` right now."""
    if not getattr(user, "is_authenticated", False):
        return []

    roles = []
    if user.is_superuser:
        roles.append(ADMINISTRATOR)

    person = getattr(user, "person", None)
    if person is not None:
        if hasattr(person, "doctor_profile"):
            roles.append(DOCTOR)
        if hasattr(person, "patient_profile"):
            roles.append(PATIENT)
        if hasattr(person, "responsible_profile"):
            roles.append(RESPONSIBLE)

    return roles


def has_role(user, role):
    return role in user_roles(user)


class RoleRequiredMixin(LoginRequiredMixin):
    """Functional-permission gate shared by every role-restricted view
    (ADR-004): subclasses set `required_role` to one of the constants
    above. An unauthenticated request still gets LoginRequiredMixin's
    redirect-to-login; an authenticated request without the role gets a
    403, never a silent redirect that could be mistaken for "not found"."""

    required_role = None

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not has_role(request.user, self.required_role):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

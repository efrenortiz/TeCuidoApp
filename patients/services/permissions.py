"""Object-level authorization for Patient data (ADR-004).

Centralized here so views (and later, serializers/templates) share one rule
instead of re-implementing it. Deny by default: any path that doesn't
explicitly match returns False.

NOTE: Administrator access to patient data is functional-global (ADR-004
§17) but must be paired with an audit trail for sensitive clinical access
(requirements.md §3.1). Audit logging is a Fase 6 concern and is not
implemented yet — this is a known, documented gap, not a silent omission.
"""

from patients.models import DoctorPatientRelationship, ResponsiblePatientRelationship


def _doctor_profile(user):
    person = getattr(user, "person", None)
    return getattr(person, "doctor_profile", None)


def _patient_profile(user):
    person = getattr(user, "person", None)
    return getattr(person, "patient_profile", None)


def _responsible_profile(user):
    person = getattr(user, "person", None)
    return getattr(person, "responsible_profile", None)


def can_view_patient(user, patient):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    patient_profile = _patient_profile(user)
    if patient_profile is not None and patient_profile.pk == patient.pk:
        return True

    doctor_profile = _doctor_profile(user)
    if doctor_profile is not None and doctor_profile.is_active:
        if DoctorPatientRelationship.objects.filter(
            doctor=doctor_profile, patient=patient, is_active=True
        ).exists():
            return True

    responsible_profile = _responsible_profile(user)
    if responsible_profile is not None and responsible_profile.is_active:
        if ResponsiblePatientRelationship.objects.filter(
            responsible=responsible_profile,
            patient=patient,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        ).exists():
            return True

    return False


def can_edit_patient(user, patient):
    # Fase 1 defines the same authorized set for view and edit — requirements.md
    # does not specify a stricter edit-only subset yet. Kept as its own function
    # so a future phase can diverge here without touching call sites.
    return can_view_patient(user, patient)


def responsible_has_active_relationship(responsible, patient):
    """Used to authorize approving/rejecting a co-responsable request
    (ADR-007 §3.7) — narrower than can_view_patient: only an ACTIVE
    Responsible profile with an ACTIVE relationship to this exact patient
    may act on a pending request for it."""
    if responsible is None or not responsible.is_active:
        return False
    return ResponsiblePatientRelationship.objects.filter(
        responsible=responsible,
        patient=patient,
        status=ResponsiblePatientRelationship.Status.ACTIVE,
    ).exists()

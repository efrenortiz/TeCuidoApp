"""Object-level authorization for Agenda (docs/design/agenda-permissions.md).

Agenda reuses Fase 1's identity/profile/relationship model — it never
builds a parallel authorization system (docs/design/agenda-permissions.md
§2.1). Deny by default: any path that doesn't explicitly match returns
False.

Administrator scope (2026-09-10): `docs/design/agenda-permissions.md`
originally described a per-clinic administrator scope that doesn't exist
anywhere in Fase 1 or Fase 2 and directly contradicted
`docs/adr/ADR-004-role-and-object-permissions.md` §8 (Administrator has
global functional access). That contradiction was corrected in the
documentation — Administrator here is simply `user.is_superuser`, exactly
as everywhere else in the app. The real, non-redundant check for admin
operations is that a valid `DoctorClinic` exists for the doctor+clinic
involved — not because the admin is scoped to that clinic, but because
the combination must be operationally valid for anyone acting on it.
"""

from clinics.models import DoctorClinic
from patients.services.permissions import responsible_has_active_relationship


def doctor_profile(user):
    person = getattr(user, "person", None)
    return getattr(person, "doctor_profile", None)


def patient_profile(user):
    person = getattr(user, "person", None)
    return getattr(person, "patient_profile", None)


def responsible_profile(user):
    person = getattr(user, "person", None)
    return getattr(person, "responsible_profile", None)


def is_administrator(user):
    return bool(getattr(user, "is_authenticated", False) and user.is_superuser)


def is_own_doctor(user, doctor):
    """True when `user` is the authenticated identity behind `doctor`."""
    profile = doctor_profile(user)
    return profile is not None and profile.pk == doctor.pk


def doctor_clinic_is_active(doctor, clinic):
    return DoctorClinic.objects.filter(doctor=doctor, clinic=clinic, is_active=True).exists()


def can_manage_availability(user, *, doctor):
    """Create/modify/deactivate Availability for `doctor`
    (docs/design/agenda-permissions.md §6-8): the doctor themself (active),
    or an administrator (global access). Deliberately does **not** check
    `DoctorClinic` here — that's a separate resource-validity precondition
    (`DoctorClinicRequired`), not an authorization question, and callers
    must check it on its own so the two failure modes stay distinguishable
    (docs/design/agenda-service-contracts.md §5.1 lists them as separate
    preconditions with separate error codes)."""
    if not doctor.is_active:
        return False
    if is_own_doctor(user, doctor):
        return True
    return is_administrator(user)


def can_initiate_booking(user, *, doctor, clinic):
    """Whether `user` is, in principle, one of the four actor types that
    may start a reservation for this doctor+clinic (docs/design/
    agenda-permissions.md §11, docs/design/booking-and-concurrency.md §4).

    This gate is deliberately patient-agnostic: `Hold` creation
    (docs/design/agenda-api-contracts.md §6.1) never takes a `patient_id`
    — the specific ResponsiblePatientRelationship.ACTIVE check for a given
    patient only makes sense once a patient is named, which happens at
    `create_appointment_from_hold` (Etapa 4), not here. A hold never
    "amplía ni sustituye la autorización sobre el paciente o la cita"
    (agenda-permissions.md §11)."""
    patient = patient_profile(user)
    if patient is not None and patient.is_active:
        return True

    responsible = responsible_profile(user)
    if responsible is not None and responsible.is_active:
        return True

    doctor_actor = doctor_profile(user)
    if doctor_actor is not None and doctor_actor.pk == doctor.pk and doctor_actor.is_active:
        return doctor_clinic_is_active(doctor, clinic)

    if is_administrator(user):
        return doctor_clinic_is_active(doctor, clinic)

    return False


def can_book_for_patient(user, *, patient):
    """Whether the named `patient` is a valid target for `user` to book an
    appointment (or hold) for (docs/design/agenda-permissions.md §9): a
    patient may only book for themself; a responsible only for a patient
    they hold an ACTIVE `ResponsiblePatientRelationship` with; a doctor or
    administrator may book for any active patient — deliberately no
    `DoctorPatientRelationship` requirement (closing decision, 2026-09-09;
    see [[hold-service]]'s `can_initiate_booking` docstring for why this
    check is separate from that role-eligibility gate)."""
    if not patient.is_active:
        return False

    patient_actor = patient_profile(user)
    if patient_actor is not None:
        return patient_actor.pk == patient.pk

    responsible = responsible_profile(user)
    if responsible is not None:
        return responsible_has_active_relationship(responsible, patient)

    if doctor_profile(user) is not None or is_administrator(user):
        return True

    return False


def can_manage_appointment(user, *, appointment):
    """Whether `user` may cancel or reschedule `appointment` (docs/design/
    agenda-permissions.md §13-14): the patient themself, a responsible with
    an ACTIVE relationship to the patient, the assigned doctor (active), or
    an administrator with a valid DoctorClinic for the appointment's
    doctor+clinic. Deliberately identical actor set for cancel and
    reschedule — the doc treats both as "autorización sobre la cita"."""
    patient_actor = patient_profile(user)
    if patient_actor is not None:
        return patient_actor.pk == appointment.patient_id

    responsible = responsible_profile(user)
    if responsible is not None:
        return responsible_has_active_relationship(responsible, appointment.patient)

    doctor_actor = doctor_profile(user)
    if doctor_actor is not None:
        return doctor_actor.pk == appointment.doctor_id and appointment.doctor.is_active

    if is_administrator(user):
        return doctor_clinic_is_active(appointment.doctor, appointment.clinic)

    return False


def can_view_appointment(user, *, appointment):
    """Whether `user` may read `appointment` (docs/design/
    agenda-permissions.md §10). Deliberately broader than
    `can_manage_appointment` for the administrator case — viewing is
    global for any administrator (no `DoctorClinic` gate; §10 states this
    explicitly), unlike creating/cancelling/rescheduling."""
    patient_actor = patient_profile(user)
    if patient_actor is not None:
        return patient_actor.pk == appointment.patient_id

    responsible = responsible_profile(user)
    if responsible is not None:
        return responsible_has_active_relationship(responsible, appointment.patient)

    doctor_actor = doctor_profile(user)
    if doctor_actor is not None:
        return doctor_actor.pk == appointment.doctor_id

    return is_administrator(user)


def is_assigned_doctor(user, *, appointment):
    """Whether `user` is the doctor assigned to `appointment` — the sole
    actor allowed to start/complete the consultation or mark NO_SHOW
    (docs/design/agenda-permissions.md §15-17). Explicitly narrower than
    `can_manage_appointment`: patient, responsible and administrator are
    excluded from all three of these operations, no exceptions."""
    doctor_actor = doctor_profile(user)
    return (
        doctor_actor is not None
        and doctor_actor.pk == appointment.doctor_id
        and appointment.doctor.is_active
    )

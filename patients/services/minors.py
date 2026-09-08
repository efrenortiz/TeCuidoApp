"""Responsible-initiated minor patient registration (ADR-007,
requirements.md §7.2).

`register_minor_patient` is the single atomic entry point. It either
creates a brand-new Patient, or — when the captured data matches an
existing one by CURP — creates a PENDING relationship request instead of a
duplicate. No code path here ever grants access on a mere data match: a
match only ever produces a request that an already-authorized Responsible
must approve via approve_relationship_request (ADR-007 §3.7).

Explicitly NOT covered here — do not assume or half-implement any of these
without a real functional decision first (requirements.md §7.2.9,
ADR-007 §5):
  - whether/when a minor patient may have their own email;
  - who authorizes a (minor or now-adult) patient to get their own User;
  - the consent mechanism for linking a responsible to a patient who
    already manages their own account (see the `user_id is not None`
    branch below — it only ever escalates, never links);
  - what happens when a CURP match has no active responsible left to ask
    for approval (inherits ADR-004 §36's open question about Admin scope).
"""

from django.db import transaction

from accounts.models import Person
from patients.models import Patient, ResponsiblePatientRelationship
from patients.services.permissions import responsible_has_active_relationship


class MinorRegistrationError(Exception):
    """Base error for the responsible-registers-a-minor flow."""


class ResponsibleSelfRegistrationNotAllowed(MinorRegistrationError):
    """A responsible tried to register themselves as the minor
    (requirements.md §7.2.5) — this flow is exclusively for incorporating
    a third party."""


class ExistingPatientRequiresManualReview(MinorRegistrationError):
    """Either a low-confidence match (name + birth date, no CURP), or a
    match against a patient who already manages their own account (their
    consent isn't designed yet — requirements.md §7.2.10). Neither can be
    resolved by self-service. Callers must show a generic message — never
    reveal which case it was or any detail of the existing record
    (anti-enumeration, requirements.md §7.2.7)."""


class AlreadyLinked(MinorRegistrationError):
    """This responsible already has a relationship (pending or active) with
    the matched patient. Not a privacy case — there's just nothing new to
    create."""

    def __init__(self, relationship):
        self.relationship = relationship
        super().__init__("Responsible is already linked to this patient")


class NotAuthorizedToDecide(MinorRegistrationError):
    """Raised by approve/reject when the acting responsible has no active
    relationship on the patient the request is about."""


def _normalize(value):
    return (value or "").strip().casefold()


def _matches_person(person, *, first_name, last_name_paterno, last_name_materno, birth_date):
    return (
        _normalize(person.first_name) == _normalize(first_name)
        and _normalize(person.last_name_paterno) == _normalize(last_name_paterno)
        and _normalize(person.last_name_materno) == _normalize(last_name_materno)
        and person.birth_date == birth_date
    )


def find_existing_patient_match(
    *, curp, first_name, last_name_paterno, last_name_materno, birth_date
):
    """Returns (patient_or_None, confidence) where confidence is
    "curp" | "name_dob" | None. Exact normalized matching only — never
    fuzzy (requirements.md §7.2.7)."""
    curp = (curp or "").strip()
    if curp:
        match = (
            Patient.objects.exclude(curp="")
            .filter(curp__iexact=curp)
            .select_related("person")
            .first()
        )
        if match:
            return match, "curp"

    match = (
        Patient.objects.select_related("person")
        .filter(
            person__first_name__iexact=(first_name or "").strip(),
            person__last_name_paterno__iexact=(last_name_paterno or "").strip(),
            person__last_name_materno__iexact=(last_name_materno or "").strip(),
            person__birth_date=birth_date,
        )
        .first()
    )
    if match:
        return match, "name_dob"

    return None, None


@transaction.atomic
def register_minor_patient(*, responsible, person_data, patient_data, relationship_type):
    """Create (or request linking to) a minor Patient on behalf of
    `responsible`. Returns (patient, relationship, outcome) where outcome
    is "created" or "pending"."""
    first_name = person_data["first_name"]
    last_name_paterno = person_data["last_name_paterno"]
    last_name_materno = person_data.get("last_name_materno", "")
    birth_date = person_data["birth_date"]
    curp = patient_data.get("curp", "")

    if _matches_person(
        responsible.person,
        first_name=first_name,
        last_name_paterno=last_name_paterno,
        last_name_materno=last_name_materno,
        birth_date=birth_date,
    ):
        raise ResponsibleSelfRegistrationNotAllowed()

    match, confidence = find_existing_patient_match(
        curp=curp,
        first_name=first_name,
        last_name_paterno=last_name_paterno,
        last_name_materno=last_name_materno,
        birth_date=birth_date,
    )

    if confidence == "name_dob":
        raise ExistingPatientRequiresManualReview()

    if confidence == "curp":
        # Checked before the "has their own account" gate below: if this
        # responsible is already linked, that's just a fact worth telling
        # them — it doesn't grant anything new, so the stricter gate
        # shouldn't suppress it.
        existing_relationship = ResponsiblePatientRelationship.objects.filter(
            responsible=responsible, patient=match
        ).first()
        if existing_relationship is not None:
            raise AlreadyLinked(existing_relationship)

        if match.person.user_id is not None:
            raise ExistingPatientRequiresManualReview()

        relationship = ResponsiblePatientRelationship.objects.create(
            responsible=responsible,
            patient=match,
            relationship_type=relationship_type,
            status=ResponsiblePatientRelationship.Status.PENDING,
        )
        return match, relationship, "pending"

    person = Person.objects.create(**person_data)
    patient = Patient.objects.create(person=person, **patient_data)
    relationship = ResponsiblePatientRelationship.objects.create(
        responsible=responsible,
        patient=patient,
        relationship_type=relationship_type,
        status=ResponsiblePatientRelationship.Status.ACTIVE,
    )
    return patient, relationship, "created"


def _transition_pending(*, relationship, approving_responsible, new_status):
    if relationship.status != ResponsiblePatientRelationship.Status.PENDING:
        raise MinorRegistrationError("Relationship is not pending approval")
    if not responsible_has_active_relationship(approving_responsible, relationship.patient):
        raise NotAuthorizedToDecide()
    relationship.status = new_status
    relationship.save(update_fields=["status"])
    return relationship


def approve_relationship_request(*, relationship, approving_responsible):
    return _transition_pending(
        relationship=relationship,
        approving_responsible=approving_responsible,
        new_status=ResponsiblePatientRelationship.Status.ACTIVE,
    )


def reject_relationship_request(*, relationship, approving_responsible):
    return _transition_pending(
        relationship=relationship,
        approving_responsible=approving_responsible,
        new_status=ResponsiblePatientRelationship.Status.INACTIVE,
    )

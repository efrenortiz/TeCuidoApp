"""Invitation issuance and acceptance (ADR-003 + ADR-006).

`accept_invitation` is the single atomic entry point that turns a prospect
into a Patient: User -> Person -> Patient -> DoctorPatientRelationship,
then marks the Invitation USED. It runs inside `transaction.atomic()` with
`select_for_update()` on the Invitation row so two concurrent requests
cannot both consume the same invitation.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import Invitation, Person, User
from patients.models import DoctorPatientRelationship, Patient


class InvitationError(Exception):
    """Base error for invitation flow failures."""


class InvitationNotFound(InvitationError):
    pass


class InvitationNotUsable(InvitationError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Invitation is not usable (status={status})")


class EmailAlreadyRegistered(InvitationError):
    """The invitation's email already has a User account.

    Fase 1 does not define what should happen here (e.g. link the existing
    account to this doctor vs. reject outright) — requirements.md doesn't
    cover a prospect who already registered through a different doctor's
    invitation. Raised explicitly rather than left to surface as a raw
    IntegrityError/500.
    """


def _hash_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_invitation(*, doctor, email):
    """Create a PENDING invitation and return (invitation, raw_token).

    The raw token is only returned here — it is never persisted. Callers
    are responsible for delivering it (e.g. embedded in an email link) and
    must not log it.
    """
    raw_token = secrets.token_urlsafe(32)
    invitation = Invitation.objects.create(
        doctor=doctor,
        email=email.strip().lower(),
        token_hash=_hash_token(raw_token),
        expires_at=timezone.now() + timedelta(hours=settings.INVITATION_TTL_HOURS),
    )
    return invitation, raw_token


def _resolve_status(invitation):
    """Effective status, accounting for expiry that hasn't been persisted yet."""
    if invitation.status == Invitation.Status.PENDING and invitation.expires_at <= timezone.now():
        return Invitation.Status.EXPIRED
    return invitation.status


def validate_invitation(raw_token):
    """Read-only lookup used to render the registration form. Raises
    InvitationNotFound / InvitationNotUsable without locking or mutating."""
    token_hash = _hash_token(raw_token)
    try:
        invitation = Invitation.objects.select_related("doctor").get(token_hash=token_hash)
    except Invitation.DoesNotExist:
        raise InvitationNotFound()

    status = _resolve_status(invitation)
    if status != Invitation.Status.PENDING:
        raise InvitationNotUsable(status)
    return invitation


def accept_invitation(raw_token, *, password, person_data, patient_data=None):
    """Atomically accept an invitation and create the Patient it describes.

    On any failure inside the creation chain, the whole operation rolls back
    — no User/Person/Patient is left half-created and the Invitation stays
    exactly as it was. The one deliberate exception is expiry: marking the
    Invitation EXPIRED must survive even though we then raise, so that state
    transition happens in its own transaction, not the creation one (a
    raise inside `transaction.atomic()` rolls back everything written in
    that block, including a status change made just before raising).
    """
    patient_data = patient_data or {}
    token_hash = _hash_token(raw_token)

    with transaction.atomic():
        try:
            invitation = Invitation.objects.select_for_update().get(token_hash=token_hash)
        except Invitation.DoesNotExist:
            raise InvitationNotFound()

        if invitation.status != Invitation.Status.PENDING:
            raise InvitationNotUsable(invitation.status)

        if invitation.expires_at > timezone.now():
            try:
                # Nested atomic() = savepoint: an IntegrityError here would
                # otherwise poison the whole outer transaction, making any
                # further ORM call in this block fail even after we catch it.
                with transaction.atomic():
                    user = User.objects.create_user(email=invitation.email, password=password)
            except IntegrityError as exc:
                raise EmailAlreadyRegistered() from exc
            person = Person.objects.create(user=user, **person_data)
            patient = Patient.objects.create(person=person, **patient_data)
            DoctorPatientRelationship.objects.create(
                doctor=invitation.doctor,
                patient=patient,
                relationship_type=DoctorPatientRelationship.RelationType.TRATANTE,
            )
            invitation.status = Invitation.Status.USED
            invitation.used_at = timezone.now()
            invitation.save(update_fields=["status", "used_at"])
            # Returning here commits the block (and releases the row lock).
            return patient

    # Only reachable when the invitation was PENDING but already past its
    # expiry: the block above committed without writing anything. Persisting
    # EXPIRED must stay outside that block — raising inside `atomic()` would
    # roll back the very status change we want to keep.
    invitation.status = Invitation.Status.EXPIRED
    invitation.save(update_fields=["status"])
    raise InvitationNotUsable(Invitation.Status.EXPIRED)


def cancel_invitation(invitation):
    """Cancel a PENDING invitation. CANCELLED is terminal (never reverts)."""
    if invitation.status != Invitation.Status.PENDING:
        raise InvitationNotUsable(invitation.status)
    invitation.status = Invitation.Status.CANCELLED
    invitation.save(update_fields=["status"])
    return invitation

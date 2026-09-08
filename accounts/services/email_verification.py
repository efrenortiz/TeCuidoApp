"""Email verification tokens (ADR-003 §14: distinct from Invitation tokens).

Stateless: uses Django's `TimestampSigner` instead of a dedicated DB table.
Single-use is enforced by flipping `User.email_verified` — once verified,
any token (fresh or reused) for that user is rejected.
"""

from django.conf import settings
from django.core import signing

from accounts.models import User

_SALT = "accounts.email-verification"


class EmailVerificationError(Exception):
    pass


class InvalidVerificationToken(EmailVerificationError):
    pass


class VerificationTokenExpired(EmailVerificationError):
    pass


class EmailAlreadyVerified(EmailVerificationError):
    pass


def _signer():
    return signing.TimestampSigner(salt=_SALT)


def generate_email_verification_token(user):
    return _signer().sign(str(user.pk))


def verify_email_token(token):
    """Validate `token` and mark the corresponding user as verified.

    Returns the User on success. Raises InvalidVerificationToken,
    VerificationTokenExpired, or EmailAlreadyVerified otherwise.
    """
    max_age = settings.EMAIL_VERIFICATION_TTL_HOURS * 3600
    try:
        raw_pk = _signer().unsign(token, max_age=max_age)
    except signing.SignatureExpired as exc:
        raise VerificationTokenExpired() from exc
    except signing.BadSignature as exc:
        raise InvalidVerificationToken() from exc

    try:
        user = User.objects.get(pk=int(raw_pk))
    except (User.DoesNotExist, ValueError) as exc:
        raise InvalidVerificationToken() from exc

    if user.email_verified:
        raise EmailAlreadyVerified()

    user.email_verified = True
    user.save(update_fields=["email_verified"])
    return user

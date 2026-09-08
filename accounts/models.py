from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager for the email-based User model (ADR-001)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio.")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, email):
        # Case-insensitive lookup so login matches however the stored email
        # was cased, mirroring the case-insensitive uniqueness constraint.
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": email})

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Central authentication identity (ADR-001).

    Holds only what authentication/authorization needs. Clinical or
    role-specific data must never live here — it belongs to Person or to the
    corresponding functional profile (Doctor/Patient/Responsible).
    """

    username = None
    # unique=True is required by Django's auth.E003 check for USERNAME_FIELD
    # (case-sensitive index); the Meta.constraints entry below adds the
    # case-insensitive guarantee that field-level uniqueness doesn't give.
    email = models.EmailField("email", unique=True)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Single point of normalization: applies to every save path,
        # including the Django admin's own user form (which calls
        # user.save() directly, not the manager) — a case-insensitive DB
        # constraint alone isn't enough if two different casings could each
        # get stored and then fail to compare as equal in application code.
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Person(models.Model):
    """Shared personal data (ADR-002): name, contact, address.

    A Person may exist without a linked User (e.g. a minor Patient managed
    entirely by a Responsible) — the link is intentionally nullable.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="person",
        null=True,
        blank=True,
    )

    first_name = models.CharField("nombre(s)", max_length=150)
    last_name_paterno = models.CharField("apellido paterno", max_length=100)
    last_name_materno = models.CharField("apellido materno", max_length=100, blank=True)
    birth_date = models.DateField("fecha de nacimiento")

    phone = models.CharField("teléfono celular", max_length=20, blank=True)
    alternative_phone = models.CharField("teléfono alternativo", max_length=20, blank=True)

    street = models.CharField("calle", max_length=150, blank=True)
    exterior_number = models.CharField("número", max_length=20, blank=True)
    neighborhood = models.CharField("colonia", max_length=100, blank=True)
    postal_code = models.CharField("código postal", max_length=10, blank=True)
    municipality = models.CharField("municipio/alcaldía", max_length=100, blank=True)
    state = models.CharField("estado", max_length=100, blank=True)
    country = models.CharField("país", max_length=100, blank=True, default="México")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "persona"
        verbose_name_plural = "personas"

    def __str__(self):
        return f"{self.first_name} {self.last_name_paterno} {self.last_name_materno}".strip()

    @property
    def full_name(self):
        return str(self)

    @property
    def age(self):
        """Computed on every access from birth_date — never stored, never
        updated by a scheduled job (ADR-007 §3.6, §3.8)."""
        today = timezone.now().date()
        had_birthday = (today.month, today.day) >= (self.birth_date.month, self.birth_date.day)
        return today.year - self.birth_date.year - (0 if had_birthday else 1)

    @property
    def is_minor(self):
        return self.age < 18


class Invitation(models.Model):
    """Doctor-issued registration invitation for a prospect (ADR-003).

    The token is never stored in plaintext: only its SHA-256 hash
    (`token_hash`) is persisted, so a leaked database dump cannot be used to
    accept invitations.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        USED = "USED", "Utilizada"
        EXPIRED = "EXPIRED", "Expirada"
        CANCELLED = "CANCELLED", "Cancelada"

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        related_name="invitations",
    )
    email = models.EmailField("email del prospecto")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "invitación"
        verbose_name_plural = "invitaciones"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["email"]),
        ]
        constraints = [
            # Nested classes don't see Invitation.Status by name here (class
            # bodies aren't a closure for other nested blocks) — "USED" must
            # match Status.USED.value.
            models.CheckConstraint(
                condition=models.Q(used_at__isnull=True) | models.Q(status="USED"),
                name="invitation_used_at_requires_used_status",
            ),
        ]

    def __str__(self):
        return f"Invitation({self.email}, {self.status})"

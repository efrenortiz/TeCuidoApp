from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import Invitation, Person, PolicyAcceptance, User
from medical_records.models import AuditEvent
from medical_records.services import audit as audit_service


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Único punto de entrada real hoy para `DISABLE_USER`/`CHANGE_PERMISSIONS`
    (docs/design/phase-6-audit-domain.md §3). `is_active`/`is_staff`/
    `is_superuser` se auditan en `save_model` (campos propios de `User`);
    `groups`/`user_permissions` son M2M y Django Admin los persiste después,
    en `save_related` — se auditan ahí, comparando antes/después."""

    ordering = ["email"]
    list_display = ["email", "is_active", "email_verified", "is_staff", "last_login"]
    search_fields = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Estado", {"fields": ("is_active", "email_verified", "is_staff", "is_superuser")}),
        ("Permisos", {"fields": ("groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
    readonly_fields = ["last_login", "date_joined"]
    filter_horizontal = ["groups", "user_permissions"]

    def save_model(self, request, obj, form, change):
        previous = User.objects.filter(pk=obj.pk).first() if change else None
        super().save_model(request, obj, form, change)
        if previous is None:
            return
        if previous.is_active and not obj.is_active:
            audit_service.record_event(
                actor=request.user,
                action=AuditEvent.Action.DISABLE_USER,
                result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.USER,
                resource_id=obj.pk,
            )
        if previous.is_staff != obj.is_staff or previous.is_superuser != obj.is_superuser:
            audit_service.record_event(
                actor=request.user,
                action=AuditEvent.Action.CHANGE_PERMISSIONS,
                result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.USER,
                resource_id=obj.pk,
                reason_code="STAFF_OR_SUPERUSER_FLAG",
            )

    def save_related(self, request, form, formsets, change):
        obj = form.instance
        previous_groups = set(obj.groups.values_list("pk", flat=True)) if change else set()
        previous_permissions = (
            set(obj.user_permissions.values_list("pk", flat=True)) if change else set()
        )
        super().save_related(request, form, formsets, change)
        if not change:
            return
        new_groups = set(obj.groups.values_list("pk", flat=True))
        new_permissions = set(obj.user_permissions.values_list("pk", flat=True))
        if new_groups != previous_groups or new_permissions != previous_permissions:
            audit_service.record_event(
                actor=request.user,
                action=AuditEvent.Action.CHANGE_PERMISSIONS,
                result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.USER,
                resource_id=obj.pk,
                reason_code="GROUPS_OR_PERMISSIONS",
            )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """Hallazgo 12.6 (docs/phases/phase-6-implementation-summary.md): editar
    la `Person` de un paciente (nombre, teléfono, dirección...) es también
    una modificación de información del paciente, aunque el formulario sea
    el de `Person` y no el de `Patient` — antes de esta corrección,
    `PatientAdmin.save_model` era el único hook de `MODIFY_PATIENT`, y este
    camino la evitaba por completo."""

    list_display = ["full_name", "user", "phone", "birth_date"]
    search_fields = ["first_name", "last_name_paterno", "last_name_materno", "user__email"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            return
        patient = getattr(obj, "patient_profile", None)
        if patient is not None:
            audit_service.record_event(
                actor=request.user,
                action=AuditEvent.Action.MODIFY_PATIENT,
                result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.PATIENT,
                resource_id=patient.pk,
                patient=patient,
                reason_code="PERSON_FIELDS",
            )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "doctor", "status", "created_at", "expires_at", "used_at"]
    list_filter = ["status"]
    search_fields = ["email"]
    readonly_fields = ["token_hash", "created_at", "used_at"]


@admin.register(PolicyAcceptance)
class PolicyAcceptanceAdmin(admin.ModelAdmin):
    """F6-D04 — inmutable (docs/design/phase-6-consent-domain.md §4):
    ninguna aceptación se edita ni se borra desde aquí."""

    list_display = ["user", "policy_type", "policy_version", "accepted_at"]
    list_filter = ["policy_type", "policy_version"]
    search_fields = ["user__email"]
    readonly_fields = [f.name for f in PolicyAcceptance._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

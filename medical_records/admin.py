from django.contrib import admin

from medical_records.models import AuditEvent, ClinicalEncounter, MedicalRecord


@admin.register(ClinicalEncounter)
class ClinicalEncounterAdmin(admin.ModelAdmin):
    list_display = ("id", "appointment", "doctor", "status", "started_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("appointment__id", "doctor__person__first_name", "doctor__person__last_name_paterno")


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "created_at", "updated_at")
    search_fields = ("patient__person__first_name", "patient__person__last_name_paterno")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """AH-082/083 (cerrado) — append-only, sin edición ni borrado desde
    ninguna interfaz de administración.

    Corrección post-implementación de Fase 6 (hallazgo 12.1,
    docs/phases/phase-6-implementation-summary.md): el acceso a `/admin/`
    en general solo exige `is_staff`, pero F6-D05 exige exclusivamente
    Administrador (`is_superuser`) para el audit trail — igual que
    `medical_records.services.permissions.can_view_audit_log`,
    `AuditEventListView` (API) y `AuditTrailView` (UI). Antes de esta
    corrección, cualquier usuario `is_staff=True` (no necesariamente
    `is_superuser`) podía ver el audit trail completo vía este registro de
    Django Admin — inconsistente con la política ya aplicada en API/UI. Se
    restringe explícitamente aquí para que los tres puntos de acceso
    (API, UI propia, Django Admin) apliquen la misma regla."""

    list_display = ("id", "occurred_at", "actor", "actor_role", "action", "result", "resource_type", "patient")
    list_filter = ("action", "result", "resource_type")
    search_fields = ("actor__email", "patient__person__first_name", "patient__person__last_name_paterno")
    date_hierarchy = "occurred_at"

    def has_module_permission(self, request):
        return bool(getattr(request.user, "is_superuser", False))

    def has_view_permission(self, request, obj=None):
        return bool(getattr(request.user, "is_superuser", False))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

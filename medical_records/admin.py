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
    ninguna interfaz de administración. El acceso al propio `/admin/` ya
    exige `is_staff`/`is_superuser` (Administrador — P-041/AH-107)."""

    list_display = ("id", "occurred_at", "actor", "actor_role", "action", "result", "resource_type", "patient")
    list_filter = ("action", "result", "resource_type")
    search_fields = ("actor__email", "patient__person__first_name", "patient__person__last_name_paterno")
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

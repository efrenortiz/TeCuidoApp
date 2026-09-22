from django.contrib import admin

from medical_records.models import AuditEvent
from medical_records.services import audit as audit_service
from patients.models import (
    DoctorPatientRelationship,
    Patient,
    Responsible,
    ResponsiblePatientRelationship,
)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """`save_model` es el único punto de entrada real hoy para modificar un
    `Patient` administrativamente (docs/design/phase-6-audit-domain.md §3,
    acción `MODIFY_PATIENT`) — se audita aquí, explícitamente, dentro de la
    misma transacción que ya envuelve `_changeform_view` de Django Admin."""

    list_display = ["person", "sex", "regime", "is_active", "created_at"]
    list_filter = ["is_active", "sex", "regime"]
    search_fields = ["person__first_name", "person__last_name_paterno", "curp"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            audit_service.record_event(
                actor=request.user,
                action=AuditEvent.Action.MODIFY_PATIENT,
                result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.PATIENT,
                resource_id=obj.pk,
                patient=obj,
            )


@admin.register(Responsible)
class ResponsibleAdmin(admin.ModelAdmin):
    list_display = ["person", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["person__first_name", "person__last_name_paterno"]


@admin.register(DoctorPatientRelationship)
class DoctorPatientRelationshipAdmin(admin.ModelAdmin):
    list_display = ["doctor", "patient", "relationship_type", "is_active"]
    list_filter = ["relationship_type", "is_active"]


@admin.register(ResponsiblePatientRelationship)
class ResponsiblePatientRelationshipAdmin(admin.ModelAdmin):
    list_display = ["responsible", "patient", "relationship_type", "status", "deactivation_reason"]
    list_filter = ["relationship_type", "status", "deactivation_reason"]

from django.contrib import admin

from patients.models import (
    DoctorPatientRelationship,
    Patient,
    Responsible,
    ResponsiblePatientRelationship,
)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["person", "sex", "is_active", "created_at"]
    list_filter = ["is_active", "sex"]
    search_fields = ["person__first_name", "person__last_name_paterno", "curp"]


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
    list_display = ["responsible", "patient", "relationship_type", "status"]
    list_filter = ["relationship_type", "status"]

from django.contrib import admin

from clinics.models import Clinic, DoctorClinic


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(DoctorClinic)
class DoctorClinicAdmin(admin.ModelAdmin):
    list_display = ["doctor", "clinic", "is_active"]
    list_filter = ["is_active"]

from django.contrib import admin

from prescriptions.models import Prescription, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "status", "version_number", "is_current_version", "issued_at")
    list_filter = ("status", "is_current_version")
    search_fields = ("patient__person__first_name", "patient__person__last_name_paterno")
    inlines = [PrescriptionItemInline]

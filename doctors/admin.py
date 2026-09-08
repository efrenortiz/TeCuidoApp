from django.contrib import admin

from doctors.models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ["person", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["person__first_name", "person__last_name_paterno"]

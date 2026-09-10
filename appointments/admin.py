from django.contrib import admin

from appointments.models import (
    Appointment,
    AppointmentRescheduleHistory,
    Availability,
    Hold,
)


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ["doctor", "clinic", "date", "start_time", "end_time", "is_active"]
    list_filter = ["is_active", "clinic"]
    search_fields = ["doctor__person__first_name", "doctor__person__last_name_paterno"]


@admin.register(Hold)
class HoldAdmin(admin.ModelAdmin):
    list_display = ["user", "doctor", "clinic", "start_at", "status", "expires_at"]
    list_filter = ["status"]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["patient", "doctor", "clinic", "start_at", "status"]
    list_filter = ["status", "clinic"]
    search_fields = ["patient__person__first_name", "patient__person__last_name_paterno"]


@admin.register(AppointmentRescheduleHistory)
class AppointmentRescheduleHistoryAdmin(admin.ModelAdmin):
    list_display = ["appointment", "old_start_at", "new_start_at", "rescheduled_by", "reason"]

from django.contrib import admin

from notifications.models import Notification, ReminderWindow


@admin.register(ReminderWindow)
class ReminderWindowAdmin(admin.ModelAdmin):
    list_display = ["offset_days", "is_active", "updated_at"]
    list_filter = ["is_active"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Solo lectura operativa (docs/design/phase-6-notification-api-contracts.md §2):
    diagnóstico administrativo, nunca un canal para crear/editar intenciones
    manualmente desde aquí."""

    list_display = [
        "event_type", "recipient_address", "status", "scheduled_for", "attempt_count", "sent_at",
    ]
    list_filter = ["event_type", "status", "channel"]
    search_fields = ["recipient_address", "dedupe_key"]
    readonly_fields = [f.name for f in Notification._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

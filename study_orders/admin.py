from django.contrib import admin

from study_orders.models import StudyOrder, StudyOrderItem


class StudyOrderItemInline(admin.TabularInline):
    model = StudyOrderItem
    extra = 0


@admin.register(StudyOrder)
class StudyOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "study_type", "status", "version_number", "is_current_version", "issued_at")
    list_filter = ("status", "study_type", "is_current_version")
    search_fields = ("patient__person__first_name", "patient__person__last_name_paterno")
    inlines = [StudyOrderItemInline]

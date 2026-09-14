from django.contrib import admin

from clinical_documents.models import ClinicalDocument


@admin.register(ClinicalDocument)
class ClinicalDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "document_type", "origin", "status", "created_by", "created_at")
    list_filter = ("document_type", "origin", "status")
    search_fields = ("patient__person__first_name", "patient__person__last_name_paterno", "original_filename")

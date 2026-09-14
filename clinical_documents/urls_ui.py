from django.urls import path

from clinical_documents import views

app_name = "clinical_documents_ui"

urlpatterns = [
    path("pacientes/<int:patient_id>/documentos/", views.DocumentListView.as_view(), name="document_list"),
    path("pacientes/<int:patient_id>/documentos/subir/", views.DocumentUploadView.as_view(), name="document_upload"),
    path("documentos/<int:pk>/", views.DocumentDetailView.as_view(), name="document_detail"),
]

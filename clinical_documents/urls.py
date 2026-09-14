from django.urls import path

from clinical_documents import api

app_name = "clinical_documents_api"

urlpatterns = [
    path("documents/", api.ClinicalDocumentListCreateView.as_view(), name="document_list_create"),
    path("documents/<int:pk>/", api.ClinicalDocumentDetailView.as_view(), name="document_detail"),
    path("documents/<int:pk>/download/", api.ClinicalDocumentDownloadView.as_view(), name="document_download"),
]

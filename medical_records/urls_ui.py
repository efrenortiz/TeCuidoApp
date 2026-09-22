from django.urls import path

from medical_records import views

app_name = "clinical_ui"

urlpatterns = [
    path(
        "citas/<int:appointment_id>/iniciar/",
        views.EncounterStartView.as_view(),
        name="encounter_start",
    ),
    path("encuentros/<int:pk>/", views.EncounterDetailView.as_view(), name="encounter_detail"),
    path("encuentros/<int:pk>/guardar/", views.EncounterSaveView.as_view(), name="encounter_save"),
    path("encuentros/<int:pk>/completar/", views.EncounterCompleteView.as_view(), name="encounter_complete"),
    path(
        "pacientes/<int:patient_id>/expediente/",
        views.MedicalRecordView.as_view(),
        name="medical_record",
    ),
    path(
        "pacientes/<int:patient_id>/historial/",
        views.PatientEncounterHistoryView.as_view(),
        name="encounter_history",
    ),
    # Fase 6 — F6-D05
    path("auditoria/", views.AuditTrailView.as_view(), name="audit_trail"),
]

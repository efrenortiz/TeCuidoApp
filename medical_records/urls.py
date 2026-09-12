from django.urls import path

from medical_records import api

app_name = "clinical_api"

urlpatterns = [
    path(
        "appointments/<int:appointment_id>/encounter/start/",
        api.EncounterStartView.as_view(),
        name="encounter_start",
    ),
    path("encounters/<int:pk>/", api.EncounterDetailView.as_view(), name="encounter_detail"),
    path("encounters/<int:pk>/complete/", api.EncounterCompleteView.as_view(), name="encounter_complete"),
    path(
        "patients/<int:patient_id>/medical-record/",
        api.MedicalRecordDetailView.as_view(),
        name="medical_record_detail",
    ),
    path(
        "patients/<int:patient_id>/encounters/",
        api.PatientEncounterHistoryView.as_view(),
        name="patient_encounter_history",
    ),
]

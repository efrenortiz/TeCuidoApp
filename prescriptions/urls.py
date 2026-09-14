from django.urls import path

from prescriptions import api

app_name = "prescriptions_api"

urlpatterns = [
    path("prescriptions/", api.PrescriptionListCreateView.as_view(), name="prescription_list_create"),
    path("prescriptions/<int:pk>/", api.PrescriptionDetailView.as_view(), name="prescription_detail"),
    path("prescriptions/<int:pk>/versions/", api.PrescriptionVersionsView.as_view(), name="prescription_versions"),
    path("prescriptions/<int:pk>/void/", api.PrescriptionVoidView.as_view(), name="prescription_void"),
]

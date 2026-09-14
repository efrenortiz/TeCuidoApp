from django.urls import path

from prescriptions import views

app_name = "prescriptions_ui"

urlpatterns = [
    path("encuentros/<int:encounter_id>/recetas/nueva/", views.PrescriptionCreateView.as_view(), name="prescription_create"),
    path("recetas/<int:pk>/", views.PrescriptionDetailView.as_view(), name="prescription_detail"),
    path("recetas/<int:pk>/nueva-version/", views.PrescriptionVersionView.as_view(), name="prescription_version"),
    path("recetas/<int:pk>/anular/", views.PrescriptionVoidView.as_view(), name="prescription_void"),
]

from django.urls import path

from study_orders import views

app_name = "study_orders_ui"

urlpatterns = [
    path("encuentros/<int:encounter_id>/estudios/nueva/", views.StudyOrderCreateView.as_view(), name="study_order_create"),
    path("estudios/<int:pk>/", views.StudyOrderDetailView.as_view(), name="study_order_detail"),
    path("estudios/<int:pk>/nueva-version/", views.StudyOrderVersionView.as_view(), name="study_order_version"),
    path("estudios/<int:pk>/anular/", views.StudyOrderVoidView.as_view(), name="study_order_void"),
]

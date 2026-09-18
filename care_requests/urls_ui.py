from django.urls import path

from care_requests import views

app_name = "care_requests_ui"

urlpatterns = [
    path("nueva/", views.CareRequestCreateView.as_view(), name="care_request_create"),
]

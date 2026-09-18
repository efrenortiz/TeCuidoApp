from django.urls import path

from care_requests import api

app_name = "care_requests_api"

urlpatterns = [
    path("care-requests/", api.CareRequestCreateView.as_view(), name="care_request_create"),
]

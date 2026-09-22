from django.urls import path

from accounts import api

app_name = "consent_api"

urlpatterns = [
    path("accept/", api.ConsentAcceptView.as_view(), name="accept"),
    path("status/", api.ConsentStatusView.as_view(), name="status"),
]

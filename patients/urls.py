from django.urls import path

from patients import views

app_name = "patients"

urlpatterns = [
    path("<int:pk>/", views.PatientDetailView.as_view(), name="patient_detail"),
    path(
        "<int:pk>/transition-to-adult/",
        views.TransitionPatientToAdultView.as_view(),
        name="transition_to_adult",
    ),
    path("mine/", views.PatientListView.as_view(), name="patient_list"),
    path("me/", views.PatientProfileView.as_view(), name="my_profile"),
    path(
        "responsible/mine/",
        views.ResponsiblePatientListView.as_view(),
        name="my_dependents",
    ),
    path(
        "responsible/register-minor/step-1/",
        views.RegisterMinorPersonalDataView.as_view(),
        name="register_minor_step1",
    ),
    path(
        "responsible/register-minor/step-2/",
        views.RegisterMinorRelationshipView.as_view(),
        name="register_minor_step2",
    ),
    path(
        "responsible/register-minor/step-3/",
        views.RegisterMinorConfirmView.as_view(),
        name="register_minor_step3",
    ),
    path(
        "responsible/requests/<int:pk>/approve/",
        views.ApproveRelationshipRequestView.as_view(),
        name="approve_relationship_request",
    ),
    path(
        "responsible/requests/<int:pk>/reject/",
        views.RejectRelationshipRequestView.as_view(),
        name="reject_relationship_request",
    ),
]

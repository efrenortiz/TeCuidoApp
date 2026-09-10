from django.urls import path

from appointments import api

app_name = "appointments_api"

urlpatterns = [
    path("availability/", api.AvailabilityCreateView.as_view(), name="availability_create"),
    path("availability/slots/", api.SlotsView.as_view(), name="availability_slots"),
    path("availability/<int:pk>/", api.AvailabilityDetailView.as_view(), name="availability_detail"),
    path(
        "availability/<int:pk>/deactivate/",
        api.AvailabilityDeactivateView.as_view(),
        name="availability_deactivate",
    ),
    path("holds/", api.HoldCreateView.as_view(), name="hold_create"),
    path("holds/<int:pk>/release/", api.HoldReleaseView.as_view(), name="hold_release"),
    path("appointments/", api.AppointmentCollectionView.as_view(), name="appointment_create_or_list"),
    path("appointments/<int:pk>/", api.AppointmentDetailView.as_view(), name="appointment_detail"),
    path("appointments/<int:pk>/cancel/", api.AppointmentCancelView.as_view(), name="appointment_cancel"),
    path(
        "appointments/<int:pk>/reschedule/",
        api.AppointmentRescheduleView.as_view(),
        name="appointment_reschedule",
    ),
    path("appointments/<int:pk>/start/", api.AppointmentStartView.as_view(), name="appointment_start"),
    path("appointments/<int:pk>/complete/", api.AppointmentCompleteView.as_view(), name="appointment_complete"),
    path("appointments/<int:pk>/no-show/", api.AppointmentNoShowView.as_view(), name="appointment_no_show"),
]

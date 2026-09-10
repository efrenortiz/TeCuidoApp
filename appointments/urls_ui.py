from django.urls import path

from appointments import views

app_name = "appointments"

urlpatterns = [
    path("", views.DoctorAgendaView.as_view(), name="doctor_agenda"),
    path("medicos/", views.AdminDoctorPickerView.as_view(), name="admin_doctor_picker"),
    path("disponibilidad/nueva/", views.AvailabilityCreateView.as_view(), name="availability_create"),
    path("disponibilidad/<int:pk>/editar/", views.AvailabilityUpdateView.as_view(), name="availability_edit"),
    path(
        "disponibilidad/<int:pk>/desactivar/",
        views.AvailabilityDeactivateView.as_view(),
        name="availability_deactivate",
    ),
    path("reservar/", views.BookingView.as_view(), name="booking"),
    path("mis-citas/", views.MyAppointmentsView.as_view(), name="my_appointments"),
    path(
        "responsable/pacientes/",
        views.ResponsiblePatientPickerView.as_view(),
        name="responsible_patients",
    ),
    path("citas/<int:pk>/", views.AppointmentDetailView.as_view(), name="appointment_detail"),
    path("citas/<int:pk>/cancelar/", views.AppointmentCancelView.as_view(), name="appointment_cancel"),
    path("citas/<int:pk>/reprogramar/", views.RescheduleView.as_view(), name="appointment_reschedule"),
    path("citas/<int:pk>/iniciar/", views.AppointmentStartView.as_view(), name="appointment_start"),
    path("citas/<int:pk>/finalizar/", views.AppointmentCompleteView.as_view(), name="appointment_complete"),
    path("citas/<int:pk>/no-show/", views.AppointmentNoShowView.as_view(), name="appointment_no_show"),
]

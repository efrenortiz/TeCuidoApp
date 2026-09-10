from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment, Availability, RequestReason
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import Patient, Responsible, ResponsiblePatientRelationship


def _make_person(email, first_name="Test", birth_date=date(1990, 1, 1)):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=birth_date
    )


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_patient(email):
    return Patient.objects.create(
        person=_make_person(email, "Pat"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT
    )


def _make_responsible(email):
    return Responsible.objects.create(person=_make_person(email, "Resp"))


def _make_clinic(name="Consultorio UI"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class AgendaUiTestCase(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("ui-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        self.availability = availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("ui-patient@example.com")
        self.patient_user = self.patient.person.user

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(hours=1)

    def _book(self, actor, patient, hour=9):
        start_at, end_at = self._slot(hour)
        hold = hold_service.create_hold(
            actor=actor, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at
        )
        return appointment_service.create_appointment_from_hold(
            actor=actor, hold=hold, patient=patient, doctor=self.doctor, clinic=self.clinic,
        )


class DoctorAgendaUiTests(AgendaUiTestCase):
    def test_doctor_sees_own_agenda(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("appointments:doctor_agenda"), {"date": self.day.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.clinic.name)

    def test_patient_cannot_view_doctor_agenda(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("appointments:doctor_agenda"))
        self.assertEqual(response.status_code, 404)

    def test_admin_without_doctor_id_is_redirected_to_picker(self):
        admin = User.objects.create_superuser(email="ui-admin@example.com", password="s3cure-pass!")
        self.client.force_login(admin)
        response = self.client.get(reverse("appointments:doctor_agenda"))
        self.assertRedirects(response, reverse("appointments:admin_doctor_picker"))

    def test_admin_with_doctor_id_sees_that_doctors_agenda(self):
        admin = User.objects.create_superuser(email="ui-admin2@example.com", password="s3cure-pass!")
        self.client.force_login(admin)
        response = self.client.get(
            reverse("appointments:doctor_agenda"), {"date": self.day.isoformat(), "doctor_id": self.doctor.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.clinic.name)

    def test_admin_doctor_picker_lists_active_doctors(self):
        admin = User.objects.create_superuser(email="ui-admin3@example.com", password="s3cure-pass!")
        self.client.force_login(admin)
        response = self.client.get(reverse("appointments:admin_doctor_picker"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.doctor.person))


class AvailabilityUiTests(AgendaUiTestCase):
    def test_create_availability_form_submits(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("appointments:availability_create"),
            {
                "clinic_id": self.clinic.pk, "date": self.day.isoformat(),
                "start_time": "14:00", "end_time": "16:00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Availability.objects.filter(doctor=self.doctor, start_time=time(14, 0)).exists()
        )

    def test_edit_blocked_when_has_appointments(self):
        self._book(self.patient_user, self.patient)
        self.client.force_login(self.doctor_user)
        response = self.client.get(
            reverse("appointments:availability_edit", args=[self.availability.pk]), follow=True
        )
        self.assertContains(response, "no puede modificarse")

    def test_deactivate_availability(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("appointments:availability_deactivate", args=[self.availability.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.availability.refresh_from_db()
        self.assertFalse(self.availability.is_active)

    def test_other_doctor_cannot_edit(self):
        other_doctor = _make_doctor("ui-doc2@example.com")
        self.client.force_login(other_doctor.person.user)
        response = self.client.get(reverse("appointments:availability_edit", args=[self.availability.pk]))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_create_availability_for_chosen_doctor(self):
        admin = User.objects.create_superuser(email="ui-admin4@example.com", password="s3cure-pass!")
        self.client.force_login(admin)
        response = self.client.post(
            reverse("appointments:availability_create"),
            {
                "doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk,
                "date": self.day.isoformat(), "start_time": "16:00", "end_time": "18:00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Availability.objects.filter(doctor=self.doctor, start_time=time(16, 0)).exists()
        )


class BookingUiTests(AgendaUiTestCase):
    def test_patient_booking_page_renders(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("appointments:booking"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "booking-app")

    def test_responsible_without_patients_sees_empty_select(self):
        responsible = _make_responsible("ui-resp@example.com")
        self.client.force_login(responsible.person.user)
        response = self.client.get(reverse("appointments:booking"))
        self.assertEqual(response.status_code, 200)

    def test_doctor_booking_page_uses_manual_patient_mode(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("appointments:booking"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "patient-id-input")


class MyAppointmentsUiTests(AgendaUiTestCase):
    def test_patient_sees_own_appointments(self):
        appointment = self._book(self.patient_user, self.patient)
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("appointments:my_appointments"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.doctor.person.first_name)

    def test_responsible_without_patient_id_redirects_to_picker(self):
        responsible = _make_responsible("ui-resp2@example.com")
        self.client.force_login(responsible.person.user)
        response = self.client.get(reverse("appointments:my_appointments"))
        self.assertRedirects(response, reverse("appointments:responsible_patients"))

    def test_responsible_patient_picker_lists_active_relationships(self):
        responsible = _make_responsible("ui-resp3@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=responsible, patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        self.client.force_login(responsible.person.user)
        response = self.client.get(reverse("appointments:responsible_patients"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.patient.person))


class AppointmentDetailUiTests(AgendaUiTestCase):
    def test_detail_view_shows_cancel_and_reschedule_for_patient(self):
        appointment = self._book(self.patient_user, self.patient)
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("appointments:appointment_detail", args=[appointment.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancelar cita")
        self.assertContains(response, "Reprogramar")

    def test_detail_view_shows_start_for_assigned_doctor(self):
        appointment = self._book(self.patient_user, self.patient)
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("appointments:appointment_detail", args=[appointment.pk]))
        self.assertContains(response, "Iniciar consulta")

    def test_detail_view_404_for_bystander(self):
        appointment = self._book(self.patient_user, self.patient)
        bystander = User.objects.create_user(email="ui-bystander@example.com", password="s3cure-pass!")
        self.client.force_login(bystander)
        response = self.client.get(reverse("appointments:appointment_detail", args=[appointment.pk]))
        self.assertEqual(response.status_code, 404)

    def test_cancel_flow(self):
        appointment = self._book(self.patient_user, self.patient)
        self.client.force_login(self.patient_user)
        response = self.client.post(
            reverse("appointments:appointment_cancel", args=[appointment.pk]),
            {"reason": RequestReason.PATIENT_REQUEST},
        )
        self.assertRedirects(response, reverse("appointments:appointment_detail", args=[appointment.pk]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)

    def test_reschedule_page_renders(self):
        appointment = self._book(self.patient_user, self.patient)
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("appointments:appointment_reschedule", args=[appointment.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "reschedule-app")

    def test_start_complete_no_show_actions(self):
        appointment = self._book(self.patient_user, self.patient)
        self.client.force_login(self.doctor_user)

        start_response = self.client.post(
            reverse("appointments:appointment_start", args=[appointment.pk])
        )
        self.assertRedirects(start_response, reverse("appointments:appointment_detail", args=[appointment.pk]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.IN_CONSULTATION)

        complete_response = self.client.post(
            reverse("appointments:appointment_complete", args=[appointment.pk])
        )
        self.assertRedirects(complete_response, reverse("appointments:appointment_detail", args=[appointment.pk]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

    def test_no_show_action_shows_friendly_error_when_too_early(self):
        appointment = self._book(self.patient_user, self.patient)
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("appointments:appointment_no_show", args=[appointment.pk]), follow=True
        )
        self.assertContains(response, "Todavía no se puede marcar")

import json
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment, Availability, Hold, RequestReason
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import Patient


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


def _make_clinic(name="Consultorio API"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class AgendaApiTestCase(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("api-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        self.availability = availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("api-patient@example.com")
        self.patient_user = self.patient.person.user

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(hours=1)

    def _post_json(self, url, data, **extra):
        return self.client.post(url, data=json.dumps(data), content_type="application/json", **extra)

    def _patch_json(self, url, data, **extra):
        return self.client.patch(url, data=json.dumps(data), content_type="application/json", **extra)


class AuthenticationTests(AgendaApiTestCase):
    def test_unauthenticated_request_returns_401(self):
        response = self.client.get(reverse("appointments_api:availability_slots"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "NOT_AUTHENTICATED")


class AvailabilityApiTests(AgendaApiTestCase):
    def test_create_availability(self):
        self.client.force_login(self.doctor_user)
        response = self._post_json(
            reverse("appointments_api:availability_create"),
            {
                "doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk,
                "date": self.day.isoformat(), "start_time": "14:00", "end_time": "16:00",
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["duration_minutes"], 60)
        self.assertTrue(body["is_active"])

    def test_create_availability_missing_field_is_400(self):
        self.client.force_login(self.doctor_user)
        response = self._post_json(
            reverse("appointments_api:availability_create"),
            {"doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk, "date": self.day.isoformat()},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "BAD_REQUEST")

    def test_create_availability_invalid_doctor_id_is_400(self):
        self.client.force_login(self.doctor_user)
        response = self._post_json(
            reverse("appointments_api:availability_create"),
            {
                "doctor_id": 999999, "clinic_id": self.clinic.pk,
                "date": self.day.isoformat(), "start_time": "14:00", "end_time": "16:00",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_unrelated_doctor_cannot_create_availability_for_another_doctor(self):
        other_doctor = _make_doctor("api-doc2@example.com")
        self.client.force_login(other_doctor.person.user)
        response = self._post_json(
            reverse("appointments_api:availability_create"),
            {
                "doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk,
                "date": self.day.isoformat(), "start_time": "14:00", "end_time": "16:00",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "NOT_AUTHORIZED")

    def test_patch_availability(self):
        self.client.force_login(self.doctor_user)
        response = self._patch_json(
            reverse("appointments_api:availability_detail", args=[self.availability.pk]),
            {"date": self.day.isoformat(), "start_time": "09:00", "end_time": "14:00"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["end_time"], "14:00")

    def test_patch_nonexistent_availability_is_404(self):
        self.client.force_login(self.doctor_user)
        response = self._patch_json(
            reverse("appointments_api:availability_detail", args=[999999]),
            {"date": self.day.isoformat(), "start_time": "09:00", "end_time": "14:00"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "AVAILABILITY_NOT_FOUND")

    def test_deactivate_availability(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("appointments_api:availability_deactivate", args=[self.availability.pk])
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["is_active"])


class SlotsApiTests(AgendaApiTestCase):
    def test_get_slots(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(
            reverse("appointments_api:availability_slots"),
            {"doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk, "date": self.day.isoformat()},
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(len(body["slots"]), 4)
        self.assertEqual(body["slots"][0]["status"], "AVAILABLE")

    def test_get_slots_missing_param_is_400(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(
            reverse("appointments_api:availability_slots"), {"doctor_id": self.doctor.pk}
        )
        self.assertEqual(response.status_code, 400)


class HoldApiTests(AgendaApiTestCase):
    def test_create_hold(self):
        self.client.force_login(self.patient_user)
        start_at, end_at = self._slot()
        response = self._post_json(
            reverse("appointments_api:hold_create"),
            {
                "doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk,
                "start": start_at.isoformat(), "end": end_at.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["status"], "ACTIVE")

    def test_create_hold_naive_datetime_is_400(self):
        self.client.force_login(self.patient_user)
        start_at, end_at = self._slot()
        response = self._post_json(
            reverse("appointments_api:hold_create"),
            {
                "doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk,
                "start": start_at.replace(tzinfo=None).isoformat(), "end": end_at.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_second_hold_by_same_user_is_409(self):
        self.client.force_login(self.patient_user)
        start_at, end_at = self._slot(9)
        self._post_json(
            reverse("appointments_api:hold_create"),
            {
                "doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk,
                "start": start_at.isoformat(), "end": end_at.isoformat(),
            },
        )
        start_at2, end_at2 = self._slot(10)
        response = self._post_json(
            reverse("appointments_api:hold_create"),
            {
                "doctor_id": self.doctor.pk, "clinic_id": self.clinic.pk,
                "start": start_at2.isoformat(), "end": end_at2.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "HOLD_ALREADY_EXISTS")

    def test_release_hold(self):
        self.client.force_login(self.patient_user)
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at,
        )
        response = self.client.post(reverse("appointments_api:hold_release", args=[hold.pk]))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "RELEASED")

    def test_release_hold_not_owned_is_404(self):
        other_patient = _make_patient("api-patient2@example.com")
        start_at, end_at = self._slot()
        hold = hold_service.create_hold(
            actor=other_patient.person.user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        self.client.force_login(self.patient_user)
        response = self.client.post(reverse("appointments_api:hold_release", args=[hold.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "HOLD_NOT_FOUND")


class AppointmentCreateApiTests(AgendaApiTestCase):
    def _hold(self, actor, hour=9):
        start_at, end_at = self._slot(hour)
        return hold_service.create_hold(
            actor=actor, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at
        )

    def test_create_appointment_from_hold(self):
        self.client.force_login(self.patient_user)
        hold = self._hold(self.patient_user)
        response = self._post_json(
            reverse("appointments_api:appointment_create_or_list"),
            {"hold_id": hold.pk, "patient_id": self.patient.pk},
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["status"], "SCHEDULED")
        self.assertEqual(body["patient_id"], self.patient.pk)

    def test_create_appointment_never_trusts_client_doctor_clinic(self):
        """§18 — the request body has no doctor_id/clinic_id at all; the
        API derives them from the hold regardless of what else is sent."""
        self.client.force_login(self.patient_user)
        hold = self._hold(self.patient_user)
        response = self._post_json(
            reverse("appointments_api:appointment_create_or_list"),
            {
                "hold_id": hold.pk, "patient_id": self.patient.pk,
                "doctor_id": 999999, "clinic_id": 999999,
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["doctor_id"], self.doctor.pk)
        self.assertEqual(response.json()["clinic_id"], self.clinic.pk)

    def test_idempotent_replay_returns_same_appointment(self):
        self.client.force_login(self.patient_user)
        hold = self._hold(self.patient_user)
        headers = {"HTTP_IDEMPOTENCY_KEY": "api-retry-1"}
        first = self._post_json(
            reverse("appointments_api:appointment_create_or_list"),
            {"hold_id": hold.pk, "patient_id": self.patient.pk}, **headers,
        )
        second = self._post_json(
            reverse("appointments_api:appointment_create_or_list"),
            {"hold_id": hold.pk, "patient_id": self.patient.pk}, **headers,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(Appointment.objects.count(), 1)

    def test_create_appointment_nonexistent_hold_is_404(self):
        self.client.force_login(self.patient_user)
        response = self._post_json(
            reverse("appointments_api:appointment_create_or_list"),
            {"hold_id": 999999, "patient_id": self.patient.pk},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "HOLD_NOT_FOUND")

    def test_doctor_can_create_first_appointment_without_relationship(self):
        hold = self._hold(self.doctor_user)
        self.client.force_login(self.doctor_user)
        response = self._post_json(
            reverse("appointments_api:appointment_create_or_list"),
            {"hold_id": hold.pk, "patient_id": self.patient.pk},
        )
        self.assertEqual(response.status_code, 201, response.content)


class AppointmentReadApiTests(AgendaApiTestCase):
    def _book(self, hour=9):
        start_at, end_at = self._slot(hour)
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at,
        )
        from appointments.services import appointment as appointment_service

        return appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient, doctor=self.doctor, clinic=self.clinic,
        )

    def test_list_appointments_scoped_to_patient(self):
        self._book()
        other_patient = _make_patient("api-patient3@example.com")
        other_hold = hold_service.create_hold(
            actor=other_patient.person.user, doctor=self.doctor, clinic=self.clinic,
            start_at=self._slot(10)[0], end_at=self._slot(10)[1],
        )
        from appointments.services import appointment as appointment_service

        appointment_service.create_appointment_from_hold(
            actor=other_patient.person.user, hold=other_hold, patient=other_patient,
            doctor=self.doctor, clinic=self.clinic,
        )

        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("appointments_api:appointment_create_or_list"))
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["patient_id"], self.patient.pk)

    def test_list_filter_by_patient_id_never_widens_scope(self):
        appointment = self._book()
        other_patient = _make_patient("api-patient4@example.com")
        self.client.force_login(other_patient.person.user)
        response = self.client.get(
            reverse("appointments_api:appointment_create_or_list"), {"patient_id": self.patient.pk}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["count"], 0)

    def test_detail_view(self):
        appointment = self._book()
        self.client.force_login(self.patient_user)
        response = self.client.get(
            reverse("appointments_api:appointment_detail", args=[appointment.pk])
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["created_by"], self.patient_user.id)

    def test_detail_view_unauthorized_is_404(self):
        appointment = self._book()
        bystander = User.objects.create_user(email="api-bystander@example.com", password="s3cure-pass!")
        self.client.force_login(bystander)
        response = self.client.get(
            reverse("appointments_api:appointment_detail", args=[appointment.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "APPOINTMENT_NOT_FOUND")


class AppointmentMutationApiTests(AgendaApiTestCase):
    def _book(self, hour=9):
        start_at, end_at = self._slot(hour)
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at,
        )
        from appointments.services import appointment as appointment_service

        return appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient, doctor=self.doctor, clinic=self.clinic,
        )

    def test_cancel_appointment(self):
        appointment = self._book()
        self.client.force_login(self.patient_user)
        response = self._post_json(
            reverse("appointments_api:appointment_cancel", args=[appointment.pk]),
            {"reason": RequestReason.PATIENT_REQUEST},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "CANCELLED")

    def test_cancel_appointment_missing_reason_is_400(self):
        appointment = self._book()
        self.client.force_login(self.patient_user)
        response = self._post_json(
            reverse("appointments_api:appointment_cancel", args=[appointment.pk]), {}
        )
        self.assertEqual(response.status_code, 400)

    def test_cancel_appointment_invalid_reason_is_400(self):
        appointment = self._book()
        self.client.force_login(self.patient_user)
        response = self._post_json(
            reverse("appointments_api:appointment_cancel", args=[appointment.pk]),
            {"reason": "NOT_A_REASON"},
        )
        self.assertEqual(response.status_code, 400)

    def test_reschedule_appointment(self):
        appointment = self._book(hour=9)
        self.client.force_login(self.patient_user)
        new_start_at, new_end_at = self._slot(hour=11)
        response = self._post_json(
            reverse("appointments_api:appointment_reschedule", args=[appointment.pk]),
            {
                "clinic_id": self.clinic.pk, "start": new_start_at.isoformat(),
                "end": new_end_at.isoformat(), "reason": RequestReason.PATIENT_REQUEST,
            },
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["start"], new_start_at.isoformat())

    def test_start_complete_flow(self):
        appointment = self._book()
        self.client.force_login(self.doctor_user)

        start_response = self.client.post(
            reverse("appointments_api:appointment_start", args=[appointment.pk])
        )
        self.assertEqual(start_response.status_code, 200, start_response.content)
        self.assertEqual(start_response.json()["status"], "IN_CONSULTATION")

        complete_response = self.client.post(
            reverse("appointments_api:appointment_complete", args=[appointment.pk])
        )
        self.assertEqual(complete_response.status_code, 200, complete_response.content)
        self.assertEqual(complete_response.json()["status"], "COMPLETED")

    def test_patient_cannot_start_appointment(self):
        appointment = self._book()
        self.client.force_login(self.patient_user)
        response = self.client.post(
            reverse("appointments_api:appointment_start", args=[appointment.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "NOT_AUTHORIZED")

    def test_no_show(self):
        appointment = self._book()
        Appointment.objects.filter(pk=appointment.pk).update(
            start_at=dj_timezone.now() - timedelta(minutes=2)
        )
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("appointments_api:appointment_no_show", args=[appointment.pk])
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "NO_SHOW")

    def test_no_show_too_early_is_422(self):
        appointment = self._book()
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("appointments_api:appointment_no_show", args=[appointment.pk])
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "NO_SHOW_NOT_ALLOWED")

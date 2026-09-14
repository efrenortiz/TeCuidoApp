"""ETAPA 7 — Smoke suite de Fase 3 (phase-3-testing-strategy.md §38):
un único recorrido rápido, de punta a punta vía HTTP real (test Client,
no llamadas directas a servicios), que cubre los 9 puntos mínimos
exigidos: login de médico, cita elegible, inicio, guardado parcial,
completion válido, lectura de expediente, historial del encuentro,
acceso denegado para paciente ajeno, edición post-completion rechazada.
"""

import json
from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.models import ClinicalEncounter
from patients.models import DoctorPatientRelationship, Patient


def _make_person(email, first_name="Test", birth_date=date(1990, 1, 1)):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=birth_date
    )


class Fase3SmokeTests(TestCase):
    def test_nominal_clinical_journey_end_to_end(self):
        # --- fixtures ---------------------------------------------------
        doctor = Doctor.objects.create(person=_make_person("smoke-doc@example.com", "Doc"))
        doctor_user = doctor.person.user
        clinic = Clinic.objects.create(name="Consultorio Smoke", timezone="America/Mexico_City")
        DoctorClinic.objects.create(doctor=doctor, clinic=clinic, appointment_duration_minutes=60)

        day = (dj_timezone.now() + timedelta(days=5)).date()
        availability_service.create_availability(
            actor=doctor_user, doctor=doctor, clinic=clinic,
            date=day, start_time=time(9, 0), end_time=time(13, 0),
        )

        patient = Patient.objects.create(
            person=_make_person("smoke-patient@example.com", "Pat"),
            sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT,
        )
        patient_user = patient.person.user

        other_patient = Patient.objects.create(
            person=_make_person("smoke-other-patient@example.com", "Otra"),
            sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT,
        )
        other_patient_user = other_patient.person.user

        start_at = availability_service.combine_local(day, time(9, 0), clinic)
        end_at = start_at + timedelta(hours=1)
        hold = hold_service.create_hold(
            actor=patient_user, doctor=doctor, clinic=clinic, start_at=start_at, end_at=end_at,
        )
        appointment = appointment_service.create_appointment_from_hold(
            actor=patient_user, hold=hold, patient=patient, doctor=doctor, clinic=clinic,
        )

        # 1. Login de médico.
        logged_in = self.client.login(username="smoke-doc@example.com", password="s3cure-pass!")
        self.assertTrue(logged_in)

        # 2. Appointment elegible visible en el contexto de Agenda.
        detail = self.client.get(reverse("appointments:appointment_detail", args=[appointment.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Iniciar consulta")

        # 3. Inicio.
        start_response = self.client.post(reverse("clinical_ui:encounter_start", args=[appointment.pk]))
        encounter = ClinicalEncounter.objects.get(appointment=appointment)
        self.assertRedirects(start_response, reverse("clinical_ui:encounter_detail", args=[encounter.pk]))
        self.assertEqual(encounter.status, ClinicalEncounter.Status.IN_PROGRESS)

        # 4. Guardado parcial.
        save_response = self.client.post(
            reverse("clinical_ui:encounter_save", args=[encounter.pk]),
            {"reason_for_visit": "Dolor abdominal de 3 días de evolución"},
        )
        self.assertEqual(save_response.status_code, 200)
        encounter.refresh_from_db()
        self.assertEqual(encounter.reason_for_visit, "Dolor abdominal de 3 días de evolución")
        self.assertEqual(encounter.status, ClinicalEncounter.Status.IN_PROGRESS)

        # 5. Completion válido.
        complete_response = self.client.post(
            reverse("clinical_ui:encounter_complete", args=[encounter.pk]),
            {
                "reason_for_visit": "Dolor abdominal de 3 días de evolución",
                "present_illness": "Inicia hace 3 días con dolor difuso, sin fiebre",
                "physical_exam": "Abdomen blando, depresible, doloroso a la palpación en FID",
                "assessment": "Probable apendicitis, se solicita USG",
                "plan": "Referencia a urgencias para valoración quirúrgica",
            },
        )
        self.assertEqual(complete_response.status_code, 200)
        encounter.refresh_from_db()
        appointment.refresh_from_db()
        self.assertEqual(encounter.status, ClinicalEncounter.Status.COMPLETED)
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

        # 6. Lectura de expediente (creado lazy en el paso 3).
        DoctorPatientRelationship.objects.create(doctor=doctor, patient=patient, is_active=True)
        record_response = self.client.get(reverse("clinical_ui:medical_record", args=[patient.pk]))
        self.assertEqual(record_response.status_code, 200)
        self.assertContains(record_response, "Resumen clínico")

        # 7. Historial del encuentro.
        history_response = self.client.get(reverse("clinical_ui:encounter_history", args=[patient.pk]))
        self.assertEqual(history_response.status_code, 200)
        self.assertContains(history_response, f'encuentros/{encounter.pk}/')

        # 8. Acceso denegado para paciente ajeno.
        self.client.logout()
        self.client.login(username="smoke-other-patient@example.com", password="s3cure-pass!")
        denied_response = self.client.get(reverse("clinical_ui:encounter_detail", args=[encounter.pk]))
        self.assertEqual(denied_response.status_code, 404)
        denied_api_response = self.client.get(
            reverse("clinical_api:medical_record_detail", args=[patient.pk])
        )
        self.assertEqual(denied_api_response.status_code, 403)

        # 9. Edición post-completion rechazada (por el médico asignado, ya
        # sin poder editar una consulta cerrada).
        self.client.logout()
        self.client.login(username="smoke-doc@example.com", password="s3cure-pass!")
        post_completion_edit = self.client.patch(
            reverse("clinical_api:encounter_detail", args=[encounter.pk]),
            data=json.dumps({"observaciones": "Intento tardío"}), content_type="application/json",
        )
        self.assertEqual(post_completion_edit.status_code, 409)
        encounter.refresh_from_db()
        self.assertEqual(encounter.observations, "")

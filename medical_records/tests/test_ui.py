"""ETAPA 5 — UX/UI (Gate 5): inicio, captura, guardado, interrupción,
reanudación, completion, pantalla bloqueada tras completion, lectura
histórica, permisos visibles y efectivos — validado end-to-end vía el
test client de Django (equivalente automatizado de la validación manual
exigida por Gate 5, siguiendo el mismo patrón que
appointments/tests/test_ui.py).
"""

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
from medical_records.models import ClinicalEncounter, MedicalRecord
from medical_records.services import encounter as encounter_service
from patients.models import DoctorPatientRelationship, Patient


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


def _make_clinic(name="Consultorio UI Clínica"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


VALID_FORM = {
    "reason_for_visit": "Dolor abdominal de 3 días de evolución",
    "present_illness": "Inicia hace 3 días con dolor difuso, sin fiebre",
    "physical_exam": "Abdomen blando, depresible, doloroso a la palpación en FID",
    "assessment": "Probable apendicitis, se solicita USG",
    "plan": "Referencia a urgencias para valoración quirúrgica",
}


class ClinicalUiTestCase(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("clinui-doc@example.com")
        self.other_doctor = _make_doctor("clinui-other-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        DoctorClinic.objects.create(doctor=self.other_doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.other_doctor_user = self.other_doctor.person.user

        self.day = _future_date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )

        self.patient = _make_patient("clinui-patient@example.com")
        self.patient_user = self.patient.person.user
        self.appointment = self._book()

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(hours=1)

    def _book(self, hour=9):
        start_at, end_at = self._slot(hour)
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic, start_at=start_at, end_at=end_at,
        )
        return appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient, doctor=self.doctor, clinic=self.clinic,
        )

    def _appointment_detail_url(self, appointment=None):
        return reverse("appointments:appointment_detail", args=[(appointment or self.appointment).pk])


class AgendaEntryPointTests(ClinicalUiTestCase):
    """S-01/S-02 — contexto desde Agenda e inicio."""

    def test_scheduled_appointment_shows_start_button(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._appointment_detail_url())
        self.assertContains(response, "Iniciar consulta")
        self.assertNotContains(response, "Continuar consulta")

    def test_start_creates_encounter_and_redirects_to_workspace(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(reverse("clinical_ui:encounter_start", args=[self.appointment.pk]))
        encounter = ClinicalEncounter.objects.get(appointment=self.appointment)
        self.assertRedirects(response, reverse("clinical_ui:encounter_detail", args=[encounter.pk]))
        self.assertEqual(encounter.status, ClinicalEncounter.Status.IN_PROGRESS)

    def test_double_click_start_is_idempotent_not_an_error_screen(self):
        """SCREEN-024/UX-031 — un segundo clic no produce un error, lleva
        al mismo encuentro."""
        self.client.force_login(self.doctor_user)
        first = self.client.post(reverse("clinical_ui:encounter_start", args=[self.appointment.pk]))
        second = self.client.post(reverse("clinical_ui:encounter_start", args=[self.appointment.pk]))
        self.assertEqual(first.url, second.url)
        self.assertEqual(ClinicalEncounter.objects.filter(appointment=self.appointment).count(), 1)

    def test_invalid_state_start_shows_friendly_error(self):
        """SCREEN-034/UX-030 — cita ya no iniciable: mensaje llano, sin
        internals, sin encuentro creado."""
        appointment = self._book(hour=11)
        appointment_service.cancel_appointment(actor=self.doctor_user, appointment=appointment, reason="DOCTOR_REQUEST")
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_ui:encounter_start", args=[appointment.pk]), follow=True,
        )
        self.assertContains(response, "no está en un estado")
        self.assertFalse(ClinicalEncounter.objects.filter(appointment=appointment).exists())

    def test_in_consultation_shows_continue_button_for_assigned_doctor(self):
        encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._appointment_detail_url())
        self.assertContains(response, "Continuar consulta")
        self.assertContains(response, reverse("clinical_ui:encounter_detail", args=[encounter.pk]))

    def test_completed_shows_view_button_not_continue(self):
        encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=encounter, data=VALID_FORM)
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._appointment_detail_url())
        self.assertContains(response, "Ver consulta")
        self.assertNotContains(response, "Continuar consulta")
        self.assertNotContains(response, "Finalizar consulta")

    def test_cancelled_appointment_has_no_clinical_action(self):
        appointment = self._book(hour=10)
        appointment_service.cancel_appointment(actor=self.doctor_user, appointment=appointment, reason="DOCTOR_REQUEST")
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._appointment_detail_url(appointment))
        self.assertNotContains(response, "Iniciar consulta")
        self.assertNotContains(response, "Continuar consulta")
        self.assertNotContains(response, "Ver consulta")

    def test_administrator_does_not_see_clinical_action_button(self):
        """SCREEN-117 — ser administrador no activa automáticamente el
        modo de UX clínico."""
        admin = User.objects.create_superuser(email="clinui-admin@example.com", password="s3cure-pass!")
        self.client.force_login(admin)
        response = self.client.get(self._appointment_detail_url())
        self.assertNotContains(response, "Iniciar consulta")


class EncounterWorkspaceTests(ClinicalUiTestCase):
    """S-03 — captura, guardado, interrupción, reanudación."""

    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def _url(self):
        return reverse("clinical_ui:encounter_detail", args=[self.encounter.pk])

    def test_workspace_shows_editable_five_core_fields(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._url())
        for label in ["Motivo de consulta", "Padecimiento actual", "Exploración física",
                      "Evaluación / diagnóstico", "Plan / indicaciones", "Datos complementarios"]:
            self.assertContains(response, label)
        self.assertContains(response, "<textarea", count=9)  # 5 core + 4 texto opcional (peso/talla son <input>)

    def test_partial_save_persists_and_shows_confirmation(self):
        """Captura + guardado parcial (SC-035/SCREEN-054)."""
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_ui:encounter_save", args=[self.encounter.pk]),
            {"reason_for_visit": "Dolor abdominal"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guardado")
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.reason_for_visit, "Dolor abdominal")
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.IN_PROGRESS)

    def test_interruption_then_resumption_preserves_partial_content(self):
        """Interrupción (guardar y salir) + reanudación (volver a
        GET la misma pantalla) — el contenido persistido se recupera."""
        self.client.force_login(self.doctor_user)
        self.client.post(
            reverse("clinical_ui:encounter_save", args=[self.encounter.pk]),
            {"reason_for_visit": "Motivo capturado antes de interrumpir"},
        )
        # Reanudación: nueva request GET, como si el médico hubiera vuelto más tarde.
        response = self.client.get(self._url())
        self.assertContains(response, "Motivo capturado antes de interrumpir")

    def test_placeholder_in_save_is_rejected_with_field_error(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_ui:encounter_save", args=[self.encounter.pk]),
            {"reason_for_visit": "N/A"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "valor de relleno")
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.reason_for_visit, "")

    def test_unrelated_doctor_gets_404_not_editable_workspace(self):
        """P-009/P-010 — sin relación ni asignación, ni siquiera 200 de
        solo lectura: IDOR-safe 404 (misma política que
        `HistoricalReadTests.test_unauthorized_other_doctor_gets_404_no_leak`)."""
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_doctor_with_relationship_sees_read_only_not_editable(self):
        """P-013/P-045 — otro médico con relación activa SÍ puede leer un
        encuentro IN_PROGRESS ajeno, pero nunca editarlo (SCREEN-108/109)."""
        DoctorPatientRelationship.objects.create(doctor=self.other_doctor, patient=self.patient, is_active=True)
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="reason_for_visit"')
        self.assertNotContains(response, "Completar consulta")

    def test_patient_cannot_reach_editable_workspace_while_in_progress(self):
        """SCREEN-112/UX-093/P-017/018 — el paciente no ve un encuentro
        IN_PROGRESS en absoluto (ni siquiera de solo lectura)."""
        self.client.force_login(self.patient_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)


class EncounterCompletionTests(ClinicalUiTestCase):
    """S-03/S-04 — completion y pantalla bloqueada después de completion."""

    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_complete_without_prior_save_succeeds(self):
        """SCREEN-071/UX-070 — no exige un Guardar previo."""
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_ui:encounter_complete", args=[self.encounter.pk]), VALID_FORM,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Consulta completada")
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.COMPLETED)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_complete_with_missing_fields_shows_which_ones_and_stays_editable(self):
        incomplete = {k: v for k, v in VALID_FORM.items() if k not in ("plan", "assessment")}
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_ui:encounter_complete", args=[self.encounter.pk]), incomplete,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Plan / indicaciones")
        self.assertContains(response, "Evaluación / diagnóstico")
        self.assertContains(response, 'name="reason_for_visit"')  # sigue editable
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.IN_PROGRESS)
        # el contenido capturado no se pierde:
        self.assertContains(response, VALID_FORM["reason_for_visit"])

    def test_locked_screen_after_completion_has_no_edit_controls(self):
        """Pantalla bloqueada después de completion (Gate 5)."""
        self.client.force_login(self.doctor_user)
        self.client.post(reverse("clinical_ui:encounter_complete", args=[self.encounter.pk]), VALID_FORM)

        response = self.client.get(reverse("clinical_ui:encounter_detail", args=[self.encounter.pk]))
        self.assertNotContains(response, 'name="reason_for_visit"')
        self.assertNotContains(response, "Completar consulta")
        self.assertNotContains(response, "Guardar")
        self.assertContains(response, VALID_FORM["reason_for_visit"])

    def test_save_attempt_after_completion_is_rejected(self):
        self.client.force_login(self.doctor_user)
        self.client.post(reverse("clinical_ui:encounter_complete", args=[self.encounter.pk]), VALID_FORM)
        response = self.client.post(
            reverse("clinical_ui:encounter_save", args=[self.encounter.pk]), {"observations": "tarde"},
        )
        self.assertEqual(response.status_code, 200)
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.observations, "")


class HistoricalReadTests(ClinicalUiTestCase):
    """S-04/S-07 — lectura histórica por otros actores autorizados."""

    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_FORM)

    def test_patient_can_view_own_completed_encounter_read_only(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("clinical_ui:encounter_detail", args=[self.encounter.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, VALID_FORM["reason_for_visit"])
        self.assertNotContains(response, 'name="reason_for_visit"')

    def test_authorized_other_doctor_can_view_read_only(self):
        DoctorPatientRelationship.objects.create(doctor=self.other_doctor, patient=self.patient, is_active=True)
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("clinical_ui:encounter_detail", args=[self.encounter.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="reason_for_visit"')

    def test_unauthorized_other_doctor_gets_404_no_leak(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("clinical_ui:encounter_detail", args=[self.encounter.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(VALID_FORM["reason_for_visit"].encode(), response.content)


class MedicalRecordUiTests(ClinicalUiTestCase):
    def test_empty_state_before_any_encounter(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_ui:medical_record", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "todavía no tiene expediente")
        self.assertFalse(MedicalRecord.objects.filter(patient=self.patient).exists())

    def test_record_view_after_lazy_creation_has_three_sections(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_ui:medical_record", args=[self.patient.pk]))
        self.assertContains(response, "Resumen clínico")
        self.assertContains(response, "Datos longitudinales")
        self.assertContains(response, "Historial")
        self.assertNotContains(response, "Diagnóstico actual")

    def test_update_longitudinal_field(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.doctor_user)
        response = self.client.post(
            reverse("clinical_ui:medical_record", args=[self.patient.pk]),
            {"family_history": "Madre con diabetes mellitus tipo 2"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Madre con diabetes mellitus tipo 2")

    def test_patient_sees_no_edit_form(self):
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.patient_user)
        response = self.client.get(reverse("clinical_ui:medical_record", args=[self.patient.pk]))
        self.assertNotContains(response, 'name="family_history"')

    def test_unrelated_doctor_gets_404(self):
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(reverse("clinical_ui:medical_record", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 404)


class EncounterHistoryUiTests(ClinicalUiTestCase):
    def setUp(self):
        super().setUp()
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.completed = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.completed, data=VALID_FORM)
        self.in_progress = encounter_service.start_encounter(actor=self.doctor_user, appointment=self._book(hour=10))

    def _url(self):
        return reverse("clinical_ui:encounter_history", args=[self.patient.pk])

    def test_doctor_sees_most_recent_first(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(self._url())
        content = response.content.decode()
        self.assertLess(content.index(f'encuentros/{self.in_progress.pk}/'), content.index(f'encuentros/{self.completed.pk}/'))

    def test_patient_sees_only_completed_encounters(self):
        self.client.force_login(self.patient_user)
        response = self.client.get(self._url())
        self.assertContains(response, f'encuentros/{self.completed.pk}/')
        self.assertNotContains(response, f'encuentros/{self.in_progress.pk}/')

    def test_empty_history_shows_empty_state(self):
        other_patient = _make_patient("clinui-other-patient@example.com")
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=other_patient, is_active=True)
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("clinical_ui:encounter_history", args=[other_patient.pk]))
        self.assertContains(response, "Todavía no existen encuentros clínicos accesibles")

    def test_unrelated_doctor_gets_404(self):
        self.client.force_login(self.other_doctor_user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)


class AuthenticationTests(ClinicalUiTestCase):
    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse("clinical_ui:medical_record", args=[self.patient.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url.lower())

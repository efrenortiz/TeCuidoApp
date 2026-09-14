"""ETAPA 6 — Auditoría, seguridad y endurecimiento (Gate 6): evidencia de
operaciones auditadas, accesos no autorizados rechazados (y registrados),
y ausencia de contenido clínico/secretos en los eventos de auditoría.
"""

from datetime import date, time, timedelta
from unittest import mock

from django.db import DatabaseError
from django.test import TestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.models import AuditEvent, ClinicalEncounter
from medical_records.services import audit as audit_service
from medical_records.services import encounter as encounter_service
from medical_records.services import record as record_service
from medical_records.services.exceptions import ClinicalNotAuthorized
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


def _make_clinic(name="Consultorio Auditoría"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


VALID_DATA = {
    "reason_for_visit": "Dolor abdominal de 3 días de evolución",
    "present_illness": "Inicia hace 3 días con dolor difuso, sin fiebre",
    "physical_exam": "Abdomen blando, depresible, doloroso a la palpación en FID",
    "assessment": "Probable apendicitis, se solicita USG",
    "plan": "Referencia a urgencias para valoración quirúrgica",
}


class AuditTestCase(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("audit-doc@example.com")
        self.other_doctor = _make_doctor("audit-other-doc@example.com")
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

        self.patient = _make_patient("audit-patient@example.com")
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


class StartEncounterAuditTests(AuditTestCase):
    def test_successful_start_is_audited(self):
        encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        event = AuditEvent.objects.get(action=AuditEvent.Action.START_ENCOUNTER)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.doctor_user)
        self.assertEqual(event.actor_role, "DOCTOR")
        self.assertEqual(event.clinical_encounter_id, encounter.pk)
        self.assertEqual(event.patient_id, self.patient.pk)
        self.assertEqual(event.appointment_id, self.appointment.pk)

    def test_lazy_medical_record_creation_is_audited(self):
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        event = AuditEvent.objects.get(action=AuditEvent.Action.CREATE_MEDICAL_RECORD)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.doctor_user)
        self.assertEqual(event.patient_id, self.patient.pk)

    def test_denied_start_is_audited_and_survives_the_rollback(self):
        """La parte crítica de Gate 6: un intento rechazado por
        autorización queda registrado — y ese registro NO puede
        perderse por el rollback de la transacción que también aborta
        (verifica que el diseño try/except-fuera-del-atomic funciona de
        verdad, no solo en teoría)."""
        with self.assertRaises(ClinicalNotAuthorized):
            encounter_service.start_encounter(actor=self.other_doctor_user, appointment=self.appointment)

        self.assertFalse(ClinicalEncounter.objects.filter(appointment=self.appointment).exists())
        event = AuditEvent.objects.get(action=AuditEvent.Action.START_ENCOUNTER)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)
        self.assertEqual(event.actor, self.other_doctor_user)
        self.assertEqual(event.appointment_id, self.appointment.pk)

    def test_idempotent_repeat_does_not_duplicate_success_event(self):
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)
        self.assertEqual(
            AuditEvent.objects.filter(action=AuditEvent.Action.START_ENCOUNTER, result=AuditEvent.Result.SUCCESS).count(),
            1,
        )


class SaveCompleteAuditTests(AuditTestCase):
    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_successful_save_is_audited(self):
        encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter, data={"reason_for_visit": "Dolor abdominal"},
        )
        event = AuditEvent.objects.get(action=AuditEvent.Action.SAVE_ENCOUNTER)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.clinical_encounter_id, self.encounter.pk)

    def test_denied_save_is_audited(self):
        with self.assertRaises(ClinicalNotAuthorized):
            encounter_service.save_encounter(
                actor=self.other_doctor_user, encounter=self.encounter, data={"reason_for_visit": "x"},
            )
        event = AuditEvent.objects.get(action=AuditEvent.Action.SAVE_ENCOUNTER)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)
        self.assertEqual(event.actor, self.other_doctor_user)

    def test_successful_completion_is_audited_only_after_both_transitions_confirm(self):
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA)
        event = AuditEvent.objects.get(action=AuditEvent.Action.COMPLETE_ENCOUNTER)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.encounter.refresh_from_db()
        self.appointment.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.COMPLETED)
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_rejected_completion_produces_no_success_event(self):
        """AH-065/184 — si la transacción de cierre no se confirma
        (contenido incompleto), no existe evento de éxito."""
        incomplete = {k: v for k, v in VALID_DATA.items() if k != "plan"}
        with self.assertRaises(Exception):
            encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=incomplete)
        self.assertFalse(AuditEvent.objects.filter(action=AuditEvent.Action.COMPLETE_ENCOUNTER).exists())
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.IN_PROGRESS)

    def test_denied_completion_is_audited(self):
        with self.assertRaises(ClinicalNotAuthorized):
            encounter_service.complete_encounter(actor=self.other_doctor_user, encounter=self.encounter, data=VALID_DATA)
        event = AuditEvent.objects.get(action=AuditEvent.Action.COMPLETE_ENCOUNTER)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)


class ReadAuditTests(AuditTestCase):
    def setUp(self):
        super().setUp()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_authorized_read_is_audited(self):
        encounter_service.get_encounter(actor=self.doctor_user, encounter_id=self.encounter.pk)
        event = AuditEvent.objects.get(action=AuditEvent.Action.READ_CLINICAL_ENCOUNTER)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        # AH-086 — el actor persistido es la identidad real del usuario
        # autenticado que ejecutó la lectura, nunca un sustituto artificial.
        self.assertEqual(event.actor, self.doctor_user)
        self.assertEqual(event.actor_id, self.doctor_user.pk)
        self.assertIsNotNone(event.actor_id)
        self.assertEqual(event.actor_role, "DOCTOR")
        self.assertNotIn(event.actor_role, ("UNKNOWN", "SYSTEM", "ANONYMOUS"))
        self.assertEqual(event.resource_type, AuditEvent.ResourceType.CLINICAL_ENCOUNTER)
        self.assertEqual(event.resource_id, self.encounter.pk)

    def test_denied_read_is_audited_idor_safe(self):
        """Gate 6 — 'accesos no autorizados rechazados': el rechazo (404
        genérico al cliente) queda registrado internamente sin que la
        respuesta al cliente revele nada distinto de un 404 normal —
        cubierto por medical_records.tests.test_api/test_ui; aquí se
        confirma el lado de auditoría."""
        with self.assertRaises(Exception):
            encounter_service.get_encounter(actor=self.other_doctor_user, encounter_id=self.encounter.pk)
        event = AuditEvent.objects.get(action=AuditEvent.Action.READ_CLINICAL_ENCOUNTER)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)
        self.assertEqual(event.actor, self.other_doctor_user)

    def test_read_never_stores_clinical_content(self):
        """AH-012/071/126/178 — el evento nunca duplica el contenido
        clínico, solo referencias."""
        encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter, data={"reason_for_visit": VALID_DATA["reason_for_visit"]},
        )
        encounter_service.get_encounter(actor=self.doctor_user, encounter_id=self.encounter.pk)
        for event in AuditEvent.objects.all():
            for field in (event.actor_role, event.action, event.result, event.reason_code, event.resource_type):
                self.assertNotIn(VALID_DATA["reason_for_visit"], str(field))

    def test_medical_record_read_audited_success_and_denied(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        record_service.get_medical_record(actor=self.doctor_user, patient=self.patient)
        success = AuditEvent.objects.get(action=AuditEvent.Action.READ_MEDICAL_RECORD)
        self.assertEqual(success.result, AuditEvent.Result.SUCCESS)

        with self.assertRaises(ClinicalNotAuthorized):
            record_service.get_medical_record(actor=self.other_doctor_user, patient=self.patient)
        denied = AuditEvent.objects.filter(
            action=AuditEvent.Action.READ_MEDICAL_RECORD, result=AuditEvent.Result.DENIED,
        ).get()
        self.assertEqual(denied.actor, self.other_doctor_user)

    def test_history_read_audited_success_and_denied(self):
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        list(encounter_service.list_encounters_for_patient(actor=self.doctor_user, patient=self.patient))
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.READ_CLINICAL_HISTORY, result=AuditEvent.Result.SUCCESS,
            ).exists()
        )

        with self.assertRaises(ClinicalNotAuthorized):
            encounter_service.list_encounters_for_patient(actor=self.other_doctor_user, patient=self.patient)
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.READ_CLINICAL_HISTORY, result=AuditEvent.Result.DENIED,
            ).exists()
        )


class MedicalRecordUpdateAuditTests(AuditTestCase):
    def setUp(self):
        super().setUp()
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_successful_update_is_audited(self):
        record_service.update_medical_record(
            actor=self.doctor_user, patient=self.patient, data={"family_history": "Madre con diabetes"},
        )
        event = AuditEvent.objects.get(action=AuditEvent.Action.UPDATE_MEDICAL_RECORD)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertNotIn("diabetes", event.reason_code)

    def test_denied_update_is_audited(self):
        with self.assertRaises(ClinicalNotAuthorized):
            record_service.update_medical_record(
                actor=self.other_doctor_user, patient=self.patient, data={"family_history": "x"},
            )
        event = AuditEvent.objects.get(action=AuditEvent.Action.UPDATE_MEDICAL_RECORD)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)


class AuditLogAccessTests(AuditTestCase):
    """P-041/AH-107/182 (cerrado) — el log de auditoría solo lo lee el
    Administrador."""

    def setUp(self):
        super().setUp()
        encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

    def test_administrator_can_list_audit_events(self):
        admin = User.objects.create_superuser(email="audit-admin@example.com", password="s3cure-pass!")
        events = list(audit_service.list_audit_events(actor=admin))
        self.assertGreater(len(events), 0)

    def test_doctor_cannot_list_audit_events(self):
        with self.assertRaises(ClinicalNotAuthorized):
            audit_service.list_audit_events(actor=self.doctor_user)

    def test_patient_cannot_list_audit_events(self):
        with self.assertRaises(ClinicalNotAuthorized):
            audit_service.list_audit_events(actor=self.patient_user)

    def test_admin_can_filter_by_patient(self):
        admin = User.objects.create_superuser(email="audit-admin2@example.com", password="s3cure-pass!")
        events = audit_service.list_audit_events(actor=admin, patient=self.patient)
        self.assertTrue(all(e.patient_id == self.patient.pk for e in events))


class AuditEventIntegrityTests(AuditTestCase):
    def test_audit_event_has_no_update_or_delete_service(self):
        """AH-082/083 — append-only por construcción: el módulo de
        servicio no expone ninguna función de actualización/borrado."""
        self.assertFalse(hasattr(audit_service, "update_event"))
        self.assertFalse(hasattr(audit_service, "delete_event"))

    def test_admin_registration_is_read_only(self):
        from medical_records.admin import AuditEventAdmin
        from django.contrib import admin as django_admin

        admin_instance = AuditEventAdmin(AuditEvent, django_admin.site)
        self.assertFalse(admin_instance.has_add_permission(None))
        self.assertFalse(admin_instance.has_change_permission(None))
        self.assertFalse(admin_instance.has_delete_permission(None))

    def test_safe_record_event_raises_on_missing_actor(self):
        """AH-086/AH-088 — un actor ausente es un bug de propagación de
        identidad (la sesión ya autenticó a alguien), no el tipo de fallo
        "del mecanismo auxiliar" que AH-089 tolera silenciar en una
        lectura: debe fallar de forma explícita e inequívoca, nunca
        maquillarse como una auditoría exitosa silenciosa ni dejar
        llegar un `actor=None` al `INSERT` (que violaría el NOT NULL de
        `actor_id`)."""
        with self.assertRaises(ValueError):
            audit_service.safe_record_event(
                actor=None, action=AuditEvent.Action.READ_CLINICAL_ENCOUNTER, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER,
            )
        self.assertFalse(AuditEvent.objects.filter(action=AuditEvent.Action.READ_CLINICAL_ENCOUNTER).exists())

    def test_record_event_raises_on_missing_actor(self):
        """Misma regla que el test anterior, pero para `record_event`
        (mutaciones): tampoco debe intentar nunca un `INSERT` con
        `actor=None`."""
        with self.assertRaises(ValueError):
            audit_service.record_event(
                actor=None, action=AuditEvent.Action.START_ENCOUNTER, result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER,
            )
        self.assertFalse(AuditEvent.objects.filter(action=AuditEvent.Action.START_ENCOUNTER).exists())

    def test_safe_record_event_still_swallows_unrelated_persistence_failure(self):
        """AH-089 — con un actor real presente, una lectura clínica
        legítima no debe bloquearse por un fallo genuino e inesperado del
        mecanismo auxiliar de persistencia (a diferencia del caso
        anterior, que es un bug del llamador, no un fallo del
        mecanismo)."""
        with mock.patch(
            "medical_records.services.audit.AuditEvent.objects.create",
            side_effect=DatabaseError("simulated outage"),
        ):
            result = audit_service.safe_record_event(
                actor=self.doctor_user, action=AuditEvent.Action.READ_CLINICAL_ENCOUNTER,
                result=AuditEvent.Result.SUCCESS,
                resource_type=AuditEvent.ResourceType.CLINICAL_ENCOUNTER,
            )
        self.assertIsNone(result)

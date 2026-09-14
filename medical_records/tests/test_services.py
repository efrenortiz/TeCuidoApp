from datetime import date, time, timedelta
from decimal import Decimal

from django.test import TestCase
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
from medical_records.services import record as record_service
from medical_records.services.exceptions import (
    ClinicalContentPlaceholder,
    ClinicalNotAuthorized,
    ClinicalNotFound,
    ClinicalRecordNotFound,
    EncounterAlreadyCompleted,
    EncounterNotStartable,
    IncompleteClinicalContent,
    InvalidClinicalData,
)
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


def _make_clinic(name="Consultorio SVC"):
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


class ClinicalServiceTestCase(TestCase):
    """Fixture compartida: una Appointment real, SCHEDULED, lista para
    iniciarse — igual que medical_records/tests/test_models.py, reutilizando
    hold_service/appointment_service de Fase 2 en vez de crear datos a mano."""

    def setUp(self):
        self.doctor = _make_doctor("svc-doc@example.com")
        self.other_doctor = _make_doctor("svc-other-doc@example.com")
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

        self.patient = _make_patient("svc-patient@example.com")
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

    def _start(self, appointment=None, actor=None):
        return encounter_service.start_encounter(
            actor=actor or self.doctor_user, appointment=appointment or self.appointment,
        )


class StartEncounterTests(ClinicalServiceTestCase):
    def test_normal_start_creates_in_progress_encounter(self):
        encounter = self._start()
        self.assertEqual(encounter.status, ClinicalEncounter.Status.IN_PROGRESS)
        self.assertEqual(encounter.appointment_id, self.appointment.pk)
        self.assertEqual(encounter.created_at, encounter.started_at)

    def test_start_transitions_appointment_atomically(self):
        self._start()
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.IN_CONSULTATION)

    def test_start_identity_matches_appointment(self):
        """SC-030 — el encuentro nunca puede tener paciente/médico que
        contradigan la cita."""
        encounter = self._start()
        self.assertEqual(encounter.patient.pk, self.appointment.patient.pk)
        self.assertEqual(encounter.clinic.pk, self.appointment.clinic.pk)
        self.assertEqual(encounter.doctor_id, self.appointment.doctor_id)

    def test_double_start_is_idempotent(self):
        """SC-022/SC-029 — no se duplica el encuentro."""
        first = self._start()
        second = self._start()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ClinicalEncounter.objects.filter(appointment=self.appointment).count(), 1)

    def test_start_by_unassigned_doctor_is_rejected(self):
        with self.assertRaises(ClinicalNotAuthorized):
            self._start(actor=self.other_doctor_user)
        self.assertFalse(ClinicalEncounter.objects.filter(appointment=self.appointment).exists())

    def test_start_by_patient_is_rejected(self):
        with self.assertRaises(ClinicalNotAuthorized):
            self._start(actor=self.patient_user)

    def test_cannot_start_a_cancelled_appointment(self):
        appointment = self._book(hour=10)
        appointment_service.cancel_appointment(actor=self.doctor_user, appointment=appointment, reason="DOCTOR_REQUEST")
        with self.assertRaises(EncounterNotStartable):
            self._start(appointment=appointment)

    def test_start_creates_medical_record_lazily(self):
        """CR-002/003 — primera operación clínica real dispara la creación
        del expediente."""
        self.assertFalse(MedicalRecord.objects.filter(patient=self.patient).exists())
        self._start()
        self.assertTrue(MedicalRecord.objects.filter(patient=self.patient).exists())

    def test_start_does_not_create_doctor_patient_relationship(self):
        """P-031/P-032 — start() no crea ni exige relación previa."""
        self._start()
        self.assertFalse(
            DoctorPatientRelationship.objects.filter(doctor=self.doctor, patient=self.patient).exists()
        )

    def test_failed_start_rolls_back_appointment_transition(self):
        """Atomicidad: una autorización fallida no dejar a la cita en un
        estado intermedio ni crea un encuentro huérfano."""
        with self.assertRaises(ClinicalNotAuthorized):
            self._start(actor=self.other_doctor_user)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.SCHEDULED)


class SaveEncounterTests(ClinicalServiceTestCase):
    def setUp(self):
        super().setUp()
        self.encounter = self._start()

    def test_partial_save_allowed(self):
        """SC-035 — no requiere los cinco campos."""
        updated = encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter,
            data={"reason_for_visit": "Dolor abdominal"},
        )
        self.assertEqual(updated.reason_for_visit, "Dolor abdominal")
        self.assertEqual(updated.present_illness, "")

    def test_save_normalizes_whitespace(self):
        updated = encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter,
            data={"reason_for_visit": "  Dolor abdominal  "},
        )
        self.assertEqual(updated.reason_for_visit, "Dolor abdominal")

    def test_save_rejects_placeholder_in_core_field(self):
        with self.assertRaises(ClinicalContentPlaceholder):
            encounter_service.save_encounter(
                actor=self.doctor_user, encounter=self.encounter, data={"reason_for_visit": "N/A"},
            )

    def test_save_allows_blank_core_field(self):
        updated = encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter, data={"reason_for_visit": ""},
        )
        self.assertEqual(updated.reason_for_visit, "")

    def test_save_rejects_unknown_field(self):
        with self.assertRaises(InvalidClinicalData):
            encounter_service.save_encounter(
                actor=self.doctor_user, encounter=self.encounter, data={"diagnosis_code": "K35"},
            )

    def test_save_rejects_non_positive_weight(self):
        with self.assertRaises(InvalidClinicalData):
            encounter_service.save_encounter(
                actor=self.doctor_user, encounter=self.encounter, data={"weight_kg": "0"},
            )

    def test_save_accepts_valid_optional_fields(self):
        updated = encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter,
            data={"weight_kg": "65.5", "height_cm": "165"},
        )
        self.assertEqual(updated.weight_kg, Decimal("65.5"))

    def test_save_by_unassigned_doctor_is_rejected(self):
        with self.assertRaises(ClinicalNotAuthorized):
            encounter_service.save_encounter(
                actor=self.other_doctor_user, encounter=self.encounter,
                data={"reason_for_visit": "Intento ajeno"},
            )

    def test_save_by_patient_is_rejected(self):
        with self.assertRaises(ClinicalNotAuthorized):
            encounter_service.save_encounter(
                actor=self.patient_user, encounter=self.encounter, data={"reason_for_visit": "x"},
            )

    def test_save_does_not_change_status(self):
        """SC-044."""
        encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter, data={"reason_for_visit": "x"},
        )
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.IN_PROGRESS)


class CompleteEncounterTests(ClinicalServiceTestCase):
    def setUp(self):
        super().setUp()
        self.encounter = self._start()

    def test_complete_with_all_fields_succeeds(self):
        completed = encounter_service.complete_encounter(
            actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA,
        )
        self.assertEqual(completed.status, ClinicalEncounter.Status.COMPLETED)
        self.assertIsNotNone(completed.completed_at)

    def test_complete_transitions_appointment_atomically(self):
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_complete_merges_previously_saved_fields(self):
        """SC-052 — `data` es el último conjunto de cambios, no un
        reemplazo total: un campo guardado antes debe seguir contando."""
        encounter_service.save_encounter(
            actor=self.doctor_user, encounter=self.encounter,
            data={"reason_for_visit": VALID_DATA["reason_for_visit"]},
        )
        remaining = {k: v for k, v in VALID_DATA.items() if k != "reason_for_visit"}
        completed = encounter_service.complete_encounter(
            actor=self.doctor_user, encounter=self.encounter, data=remaining,
        )
        self.assertEqual(completed.status, ClinicalEncounter.Status.COMPLETED)
        self.assertEqual(completed.reason_for_visit, VALID_DATA["reason_for_visit"])

    def test_complete_rejects_missing_core_field(self):
        incomplete = {k: v for k, v in VALID_DATA.items() if k != "plan"}
        with self.assertRaises(IncompleteClinicalContent):
            encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=incomplete)
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.IN_PROGRESS)

    def test_complete_rejects_placeholder_core_field(self):
        data = dict(VALID_DATA, plan="No aplica")
        with self.assertRaises(ClinicalContentPlaceholder):
            encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=data)

    def test_complete_by_unassigned_doctor_is_rejected(self):
        with self.assertRaises(ClinicalNotAuthorized):
            encounter_service.complete_encounter(actor=self.other_doctor_user, encounter=self.encounter, data=VALID_DATA)

    def test_double_completion_with_same_content_is_idempotent(self):
        """SC-065/D-001."""
        first = encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA)
        second = encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA)
        self.assertEqual(first.completed_at, second.completed_at)

    def test_double_completion_with_different_content_is_rejected(self):
        """SC-065/D-001 — contenido distinto sobre un encuentro ya cerrado."""
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA)
        different = dict(VALID_DATA, plan="Plan modificado tras el cierre")
        with self.assertRaises(EncounterAlreadyCompleted):
            encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=different)

    def test_save_after_completion_is_rejected(self):
        """SC-046."""
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA)
        with self.assertRaises(EncounterAlreadyCompleted):
            encounter_service.save_encounter(
                actor=self.doctor_user, encounter=self.encounter, data={"reason_for_visit": "Cambio tardío"},
            )

    def test_complete_failure_rolls_back_appointment(self):
        """Atomicidad — un rechazo por contenido incompleto no deja la
        cita en IN_CONSULTATION con el encuentro completado."""
        incomplete = {k: v for k, v in VALID_DATA.items() if k != "assessment"}
        with self.assertRaises(IncompleteClinicalContent):
            encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=incomplete)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.IN_CONSULTATION)


class GetEncounterTests(ClinicalServiceTestCase):
    def setUp(self):
        super().setUp()
        self.encounter = self._start()

    def test_assigned_doctor_can_read(self):
        result = encounter_service.get_encounter(actor=self.doctor_user, encounter_id=self.encounter.pk)
        self.assertEqual(result.pk, self.encounter.pk)

    def test_unrelated_doctor_cannot_read_in_progress_encounter(self):
        with self.assertRaises(ClinicalNotFound):
            encounter_service.get_encounter(actor=self.other_doctor_user, encounter_id=self.encounter.pk)

    def test_doctor_with_active_relationship_can_read_in_progress_encounter(self):
        DoctorPatientRelationship.objects.create(doctor=self.other_doctor, patient=self.patient, is_active=True)
        result = encounter_service.get_encounter(actor=self.other_doctor_user, encounter_id=self.encounter.pk)
        self.assertEqual(result.pk, self.encounter.pk)

    def test_patient_cannot_read_in_progress_encounter(self):
        """P-017 — un encuentro IN_PROGRESS no es visible para el paciente."""
        with self.assertRaises(ClinicalNotFound):
            encounter_service.get_encounter(actor=self.patient_user, encounter_id=self.encounter.pk)

    def test_patient_can_read_own_completed_encounter(self):
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA)
        result = encounter_service.get_encounter(actor=self.patient_user, encounter_id=self.encounter.pk)
        self.assertEqual(result.reason_for_visit, VALID_DATA["reason_for_visit"])

    def test_unknown_encounter_id_raises_not_found(self):
        with self.assertRaises(ClinicalNotFound):
            encounter_service.get_encounter(actor=self.doctor_user, encounter_id=999999)


class MedicalRecordServiceTests(ClinicalServiceTestCase):
    def test_get_medical_record_returns_none_when_absent(self):
        """D-005/SC-083a — lectura pura, nunca crea. El médico debe estar
        autorizado (relación activa) para poder siquiera intentar la
        lectura; eso es independiente de si el expediente ya existe."""
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.assertIsNone(record_service.get_medical_record(actor=self.doctor_user, patient=self.patient))
        self.assertFalse(MedicalRecord.objects.filter(patient=self.patient).exists())

    def test_get_medical_record_denies_unrelated_doctor(self):
        with self.assertRaises(ClinicalNotAuthorized):
            record_service.get_medical_record(actor=self.other_doctor_user, patient=self.patient)

    def test_get_or_create_is_idempotent(self):
        first = record_service.get_or_create_for_patient(patient=self.patient)
        second = record_service.get_or_create_for_patient(patient=self.patient)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(MedicalRecord.objects.filter(patient=self.patient).count(), 1)

    def test_update_medical_record_by_doctor_with_clinical_contact(self):
        self._start()
        updated = record_service.update_medical_record(
            actor=self.doctor_user, patient=self.patient,
            data={"family_history": "Madre con diabetes mellitus tipo 2"},
        )
        self.assertEqual(updated.family_history, "Madre con diabetes mellitus tipo 2")

    def test_update_medical_record_does_not_silently_create_record(self):
        """API-095 — un doctor autorizado (relación activa) pero para un
        paciente sin expediente todavía (ningún encuentro se ha iniciado
        nunca) debe recibir `ClinicalRecordNotFound`, no una creación
        implícita."""
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.assertFalse(MedicalRecord.objects.filter(patient=self.patient).exists())
        with self.assertRaises(ClinicalRecordNotFound):
            record_service.update_medical_record(
                actor=self.doctor_user, patient=self.patient, data={"family_history": "x"},
            )
        self.assertFalse(MedicalRecord.objects.filter(patient=self.patient).exists())

    def test_update_medical_record_denies_doctor_without_contact(self):
        with self.assertRaises(ClinicalNotAuthorized):
            record_service.update_medical_record(
                actor=self.other_doctor_user, patient=self.patient, data={"family_history": "x"},
            )

    def test_update_medical_record_denies_patient(self):
        with self.assertRaises(ClinicalNotAuthorized):
            record_service.update_medical_record(
                actor=self.patient_user, patient=self.patient, data={"family_history": "x"},
            )

    def test_update_medical_record_rejects_unknown_field(self):
        self._start()
        with self.assertRaises(InvalidClinicalData):
            record_service.update_medical_record(
                actor=self.doctor_user, patient=self.patient, data={"cie10": "E11"},
            )


class ContentValidationExceptionPayloadTests(ClinicalServiceTestCase):
    """API-103 — las excepciones deben transportar TODOS los campos
    afectados, no solo el primero encontrado."""

    def setUp(self):
        super().setUp()
        self.encounter = self._start()

    def test_incomplete_content_lists_every_missing_field(self):
        incomplete = {k: v for k, v in VALID_DATA.items() if k not in ("present_illness", "plan")}
        with self.assertRaises(IncompleteClinicalContent) as ctx:
            encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=incomplete)
        self.assertCountEqual(ctx.exception.fields, ["present_illness", "plan"])

    def test_placeholder_lists_every_offending_field(self):
        data = dict(VALID_DATA, present_illness="N/A", plan="Sin datos")
        with self.assertRaises(ClinicalContentPlaceholder) as ctx:
            encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=data)
        self.assertCountEqual(ctx.exception.fields, ["present_illness", "plan"])


class ListEncountersForPatientTests(ClinicalServiceTestCase):
    """P-009/P-010 — haber atendido una cita puntual (sin
    `DoctorPatientRelationship`) no concede acceso al historial
    longitudinal (a diferencia de `get_encounter`, que sí concede lectura
    del encuentro propio vía P-011/012 sin relación previa) — por eso la
    fixture establece una relación activa explícita para `self.doctor`."""

    def setUp(self):
        super().setUp()
        DoctorPatientRelationship.objects.create(doctor=self.doctor, patient=self.patient, is_active=True)
        self.completed = self._start()
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.completed, data=VALID_DATA)
        self.in_progress = self._start(appointment=self._book(hour=10))

    def test_assigned_doctor_sees_all_statuses(self):
        results = list(encounter_service.list_encounters_for_patient(actor=self.doctor_user, patient=self.patient))
        self.assertEqual({e.pk for e in results}, {self.completed.pk, self.in_progress.pk})

    def test_patient_sees_only_completed(self):
        results = list(encounter_service.list_encounters_for_patient(actor=self.patient_user, patient=self.patient))
        self.assertEqual({e.pk for e in results}, {self.completed.pk})

    def test_unrelated_doctor_is_denied(self):
        with self.assertRaises(ClinicalNotAuthorized):
            encounter_service.list_encounters_for_patient(actor=self.other_doctor_user, patient=self.patient)

    def test_ordering_is_deterministic_most_recent_first(self):
        results = list(
            encounter_service.list_encounters_for_patient(
                actor=self.doctor_user, patient=self.patient, ordering="-started_at",
            )
        )
        self.assertEqual([e.pk for e in results], [self.in_progress.pk, self.completed.pk])

    def test_unsupported_ordering_is_rejected(self):
        with self.assertRaises(InvalidClinicalData):
            encounter_service.list_encounters_for_patient(
                actor=self.doctor_user, patient=self.patient, ordering="doctor__person__first_name",
            )

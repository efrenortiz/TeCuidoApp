from datetime import date, time, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.models import ClinicalEncounter, MedicalRecord
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


def _make_clinic(name="Consultorio MR"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class ClinicalEncounterModelTestCase(TestCase):
    """Base fixture: a real, scheduled Appointment (reused across tests
    rather than mocked — the invariants under test are precisely about
    Appointment/ClinicalEncounter integrity)."""

    def setUp(self):
        self.doctor = _make_doctor("mr-model-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        self.availability = availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("mr-model-patient@example.com")
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

    def _make_encounter(self, **overrides):
        # created_at y started_at deben fijarse al mismo `now` capturado
        # una sola vez — clinical-encounter-domain.md §49.1. Nunca usar
        # auto_now_add aquí (ver nota en medical_records/models.py).
        now = dj_timezone.now()
        defaults = {
            "appointment": self.appointment,
            "doctor": self.doctor,
            "status": ClinicalEncounter.Status.IN_PROGRESS,
            "created_at": now,
            "started_at": now,
        }
        defaults.update(overrides)
        return ClinicalEncounter.objects.create(**defaults)


class ClinicalEncounterCreationTests(ClinicalEncounterModelTestCase):
    def test_creates_with_minimal_fields(self):
        encounter = self._make_encounter()
        self.assertEqual(encounter.status, ClinicalEncounter.Status.IN_PROGRESS)
        self.assertIsNone(encounter.completed_at)

    def test_partial_save_allowed_with_blank_core_fields(self):
        """clinical-encounter-domain.md I-017 — los cinco campos pueden
        estar vacíos mientras IN_PROGRESS; la validación de contenido
        real vive en el servicio, no en el modelo."""
        encounter = self._make_encounter()
        self.assertEqual(encounter.reason_for_visit, "")
        self.assertEqual(encounter.present_illness, "")
        self.assertEqual(encounter.physical_exam, "")
        self.assertEqual(encounter.assessment, "")
        self.assertEqual(encounter.plan, "")

    def test_appointment_is_required(self):
        now = dj_timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalEncounter.objects.create(
                    appointment=None, doctor=self.doctor,
                    status=ClinicalEncounter.Status.IN_PROGRESS, created_at=now, started_at=now,
                )

    def test_doctor_is_required(self):
        now = dj_timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalEncounter.objects.create(
                    appointment=self.appointment, doctor=None,
                    status=ClinicalEncounter.Status.IN_PROGRESS, created_at=now, started_at=now,
                )


class ClinicalEncounterUniquenessTests(ClinicalEncounterModelTestCase):
    def test_appointment_is_unique(self):
        """I-002 — una Appointment tiene como máximo un ClinicalEncounter."""
        self._make_encounter()
        other_doctor = _make_doctor("mr-model-doc2@example.com")
        now = dj_timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalEncounter.objects.create(
                    appointment=self.appointment, doctor=other_doctor,
                    status=ClinicalEncounter.Status.IN_PROGRESS, created_at=now, started_at=now,
                )


class ClinicalEncounterStatusConstraintTests(ClinicalEncounterModelTestCase):
    def test_status_must_be_valid_choice(self):
        now = dj_timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalEncounter.objects.create(
                    appointment=self.appointment, doctor=self.doctor,
                    status="BOGUS", created_at=now, started_at=now,
                )

    def test_completed_status_requires_completed_at(self):
        now = dj_timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalEncounter.objects.create(
                    appointment=self.appointment, doctor=self.doctor,
                    status=ClinicalEncounter.Status.COMPLETED, created_at=now, started_at=now,
                    completed_at=None,
                )

    def test_in_progress_status_forbids_completed_at(self):
        now = dj_timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalEncounter.objects.create(
                    appointment=self.appointment, doctor=self.doctor,
                    status=ClinicalEncounter.Status.IN_PROGRESS, created_at=now, started_at=now,
                    completed_at=now,
                )

    def test_completed_with_completed_at_is_valid(self):
        now = dj_timezone.now()
        encounter = self._make_encounter(
            status=ClinicalEncounter.Status.COMPLETED, created_at=now, started_at=now, completed_at=now,
        )
        self.assertEqual(encounter.status, ClinicalEncounter.Status.COMPLETED)


class ClinicalEncounterTemporalConstraintTests(ClinicalEncounterModelTestCase):
    def test_started_at_before_created_at_is_rejected(self):
        """DM-042 — started_at >= created_at."""
        created = dj_timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalEncounter.objects.create(
                    appointment=self.appointment, doctor=self.doctor,
                    status=ClinicalEncounter.Status.IN_PROGRESS,
                    created_at=created, started_at=created - timedelta(days=1),
                )

    def test_completed_at_before_started_at_is_rejected(self):
        started = dj_timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalEncounter.objects.create(
                    appointment=self.appointment, doctor=self.doctor,
                    status=ClinicalEncounter.Status.COMPLETED,
                    created_at=started, started_at=started, completed_at=started - timedelta(minutes=5),
                )

    def test_completed_at_equal_to_started_at_is_valid(self):
        started = dj_timezone.now()
        encounter = self._make_encounter(
            status=ClinicalEncounter.Status.COMPLETED,
            created_at=started, started_at=started, completed_at=started,
        )
        self.assertEqual(encounter.completed_at, started)


class ClinicalEncounterOptionalFieldConstraintTests(ClinicalEncounterModelTestCase):
    def test_weight_kg_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_encounter(weight_kg=Decimal("0"))

    def test_negative_weight_kg_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_encounter(weight_kg=Decimal("-5"))

    def test_height_cm_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_encounter(height_cm=Decimal("0"))

    def test_positive_weight_and_height_are_valid(self):
        encounter = self._make_encounter(weight_kg=Decimal("65.50"), height_cm=Decimal("165.00"))
        self.assertEqual(encounter.weight_kg, Decimal("65.50"))

    def test_null_weight_and_height_are_valid(self):
        encounter = self._make_encounter()
        self.assertIsNone(encounter.weight_kg)
        self.assertIsNone(encounter.height_cm)


class ClinicalEncounterReferentialIntegrityTests(ClinicalEncounterModelTestCase):
    def test_r008_patient_matches_appointment_patient(self):
        """R-008 — ClinicalEncounter.patient == Appointment.patient,
        garantizado por construcción vía property derivada (ver
        docstring de resolución de contradicción en medical_records/models.py)."""
        encounter = self._make_encounter()
        self.assertEqual(encounter.patient, self.appointment.patient)
        self.assertEqual(encounter.patient.pk, self.patient.pk)

    def test_r008_clinic_matches_appointment_clinic(self):
        encounter = self._make_encounter()
        self.assertEqual(encounter.clinic, self.appointment.clinic)
        self.assertEqual(encounter.clinic.pk, self.clinic.pk)

    def test_doctor_matches_appointment_doctor_by_convention(self):
        """No es un CHECK de BD (doctor_id es una columna independiente
        por razones de consulta/autorización, per clinical-data-model.md
        §25.2) — la coherencia con Appointment.doctor es responsabilidad
        del servicio de dominio (Etapa 2), no del modelo."""
        encounter = self._make_encounter()
        self.assertEqual(encounter.doctor_id, self.appointment.doctor_id)

    def test_cannot_delete_appointment_with_encounter(self):
        self._make_encounter()
        with self.assertRaises(Exception):
            with transaction.atomic():
                self.appointment.delete()

    def test_cannot_delete_doctor_with_encounter(self):
        self._make_encounter()
        with self.assertRaises(Exception):
            with transaction.atomic():
                self.doctor.delete()


class MedicalRecordModelTestCase(TestCase):
    def setUp(self):
        self.patient = _make_patient("mr-record-patient@example.com")


class MedicalRecordCreationTests(MedicalRecordModelTestCase):
    def test_creates_with_minimal_fields(self):
        record = MedicalRecord.objects.create(patient=self.patient)
        self.assertEqual(record.patient, self.patient)
        self.assertEqual(record.family_history, "")

    def test_patient_is_required(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MedicalRecord.objects.create(patient=None)

    def test_longitudinal_fields_are_optional(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            family_history="Madre con diabetes mellitus tipo 2",
        )
        self.assertEqual(record.personal_pathological_history, "")
        self.assertNotEqual(record.family_history, "")


class MedicalRecordUniquenessTests(MedicalRecordModelTestCase):
    def test_patient_is_unique(self):
        """ADR-011 — Patient 1 ─── 1 MedicalRecord; como máximo un
        expediente por paciente."""
        MedicalRecord.objects.create(patient=self.patient)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MedicalRecord.objects.create(patient=self.patient)

    def test_cannot_delete_patient_with_medical_record(self):
        MedicalRecord.objects.create(patient=self.patient)
        with self.assertRaises(Exception):
            with transaction.atomic():
                self.patient.delete()

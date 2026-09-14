"""ETAPA 7 — Concurrencia e idempotencia de Prescription (Gate 7).

`TransactionTestCase` (no `TestCase`) — mismo patrón que
`medical_records/tests/test_concurrency.py`: las carreras reales necesitan
conexiones de BD que confirmen (`commit`) de forma independiente entre
hilos.
"""

import threading
from datetime import date, time, timedelta

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.models import AuditEvent
from medical_records.services import encounter as encounter_service
from patients.models import Patient
from prescriptions.models import Prescription
from prescriptions.services import prescription as prescription_service

VALID_ITEM = {
    "medication_name": "Paracetamol", "dose": "500", "dose_unit": "mg",
    "route": "Oral", "frequency": "c/8h", "instructions": "",
}


def _make_person(email):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(user=user, first_name="T", last_name_paterno="T", birth_date=date(1990, 1, 1))


class PrescriptionConcurrencyTestCase(TransactionTestCase):
    reset_sequences = False

    def setUp(self):
        self.doctor = Doctor.objects.create(person=_make_person("f4-race-doc@example.com"))
        self.clinic = Clinic.objects.create(name="Consultorio Concurrencia F4", timezone="America/Mexico_City")
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.day = (dj_timezone.now() + timedelta(days=5)).date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = Patient.objects.create(
            person=_make_person("f4-race-patient@example.com"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT,
        )
        self.patient_user = self.patient.person.user
        start_at = availability_service.combine_local(self.day, time(9, 0), self.clinic)
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=start_at + timedelta(hours=1),
        )
        appointment = appointment_service.create_appointment_from_hold(
            actor=self.patient_user, hold=hold, patient=self.patient, doctor=self.doctor, clinic=self.clinic,
        )
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=appointment)


class DoubleIssueRaceTests(PrescriptionConcurrencyTestCase):
    def test_concurrent_issue_with_same_idempotency_key_never_duplicates(self):
        """Doble emisión concurrente con el mismo Idempotency-Key: ambas
        deben tener éxito (idempotencia), pero nunca debe existir más de
        una `Prescription` real."""
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                prescription = prescription_service.issue(
                    actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
                    idempotency_key="race-key-1",
                )
                results[key] = ("success", prescription.pk)
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = (f"error: {exc!r}", None)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=attempt, args=(k,)) for k in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        outcomes = [outcome for outcome, _ in results.values()]
        self.assertEqual(outcomes.count("success"), 2, results)
        pks = {pk for _, pk in results.values()}
        self.assertEqual(len(pks), 1, results)
        self.assertEqual(Prescription.objects.count(), 1)
        self.assertEqual(
            AuditEvent.objects.filter(action=AuditEvent.Action.ISSUE_PRESCRIPTION, result=AuditEvent.Result.SUCCESS).count(),
            1,
        )


class DoubleVersionRaceTests(PrescriptionConcurrencyTestCase):
    def test_concurrent_corrections_never_produce_two_current_versions(self):
        """Dos correcciones concurrentes sobre la MISMA versión vigente:
        exactamente una debe ganar; la otra debe perder de forma segura
        (nunca silenciosa, nunca produciendo una versión inconsistente)."""
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key, dose):
            try:
                barrier.wait(timeout=5)
                new_version = prescription_service.create_version(
                    actor=self.doctor_user, prescription_id=prescription.pk,
                    items=[{**VALID_ITEM, "dose": dose}], reason=f"corrección {key}",
                )
                results[key] = ("success", new_version.pk)
            except Exception as exc:
                results[key] = (type(exc).__name__, None)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=attempt, args=("a", "111")), threading.Thread(target=attempt, args=("b", "222"))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        outcomes = [outcome for outcome, _ in results.values()]
        self.assertEqual(outcomes.count("success"), 1, results)
        # La perdedora nunca debe "desaparecer en silencio" — debe fallar
        # con un error de dominio identificable.
        self.assertIn("DocumentImmutableResource", outcomes, results)

        # Invariante de Gate 7: nunca dos versiones vigentes ni versiones
        # inconsistentes (huérfanas sin `previous_version`, o dos filas
        # apuntando a la misma `previous_version`).
        self.assertEqual(Prescription.objects.filter(previous_version=prescription).count(), 1)
        current_versions = Prescription.objects.filter(patient=self.patient, is_current_version=True)
        self.assertEqual(current_versions.count(), 1)


class DoubleVoidRaceTests(PrescriptionConcurrencyTestCase):
    def test_concurrent_void_with_same_reason_is_idempotent_not_duplicated(self):
        """Doble anulación concurrente con el MISMO motivo: ambas deben
        tener éxito (idempotente), pero sólo un evento `SUCCESS` de
        anulación debe quedar auditado."""
        prescription = prescription_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter, items=[VALID_ITEM],
        )
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                voided = prescription_service.void(
                    actor=self.doctor_user, prescription_id=prescription.pk, reason="Motivo compartido",
                )
                results[key] = ("success", voided.status)
            except Exception as exc:
                results[key] = (type(exc).__name__, None)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=attempt, args=(k,)) for k in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        outcomes = [outcome for outcome, _ in results.values()]
        self.assertEqual(outcomes.count("success"), 2, results)
        prescription.refresh_from_db()
        self.assertEqual(prescription.status, Prescription.Status.VOIDED)
        self.assertEqual(
            AuditEvent.objects.filter(action=AuditEvent.Action.VOID_PRESCRIPTION, result=AuditEvent.Result.SUCCESS).count(),
            1,
        )

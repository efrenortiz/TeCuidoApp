"""ETAPA 7 — Concurrencia e idempotencia de StudyOrder (Gate 7) — mismo
patrón que `prescriptions/tests/test_concurrency.py`. `StudyOrderService`
implementa su propia copia (independiente) del locking `select_for_update`
+ `is_current_version`, por lo que se verifica aquí de forma independiente
en vez de asumir que "es el mismo código que Prescription"."""

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
from medical_records.services import encounter as encounter_service
from patients.models import Patient
from study_orders.models import StudyOrder
from study_orders.services import study_order as study_order_service

VALID_ITEM = {"study_name": "Biometría hemática"}


def _make_person(email):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(user=user, first_name="T", last_name_paterno="T", birth_date=date(1990, 1, 1))


class StudyOrderConcurrencyTestCase(TransactionTestCase):
    reset_sequences = False

    def setUp(self):
        self.doctor = Doctor.objects.create(person=_make_person("f4-so-race-doc@example.com"))
        self.clinic = Clinic.objects.create(name="Consultorio Concurrencia SO", timezone="America/Mexico_City")
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.day = (dj_timezone.now() + timedelta(days=5)).date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = Patient.objects.create(
            person=_make_person("f4-so-race-patient@example.com"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT,
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


class DoubleIssueRaceTests(StudyOrderConcurrencyTestCase):
    def test_concurrent_issue_with_same_idempotency_key_never_duplicates(self):
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                order = study_order_service.issue(
                    actor=self.doctor_user, clinical_encounter=self.encounter,
                    study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM], idempotency_key="so-race-key-1",
                )
                results[key] = ("success", order.pk)
            except Exception as exc:
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
        self.assertEqual(len({pk for _, pk in results.values()}), 1, results)
        self.assertEqual(StudyOrder.objects.count(), 1)


class DoubleVersionRaceTests(StudyOrderConcurrencyTestCase):
    def test_concurrent_corrections_never_produce_two_current_versions(self):
        order = study_order_service.issue(
            actor=self.doctor_user, clinical_encounter=self.encounter,
            study_type=StudyOrder.StudyType.LABORATORY, items=[VALID_ITEM],
        )
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key, name):
            try:
                barrier.wait(timeout=5)
                new_version = study_order_service.create_version(
                    actor=self.doctor_user, study_order_id=order.pk,
                    items=[{"study_name": name}], reason=f"corrección {key}",
                )
                results[key] = ("success", new_version.pk)
            except Exception as exc:
                results[key] = (type(exc).__name__, None)
            finally:
                connections.close_all()

        threads = [
            threading.Thread(target=attempt, args=("a", "Estudio A")),
            threading.Thread(target=attempt, args=("b", "Estudio B")),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        outcomes = [outcome for outcome, _ in results.values()]
        self.assertEqual(outcomes.count("success"), 1, results)
        self.assertIn("DocumentImmutableResource", outcomes, results)
        current_versions = StudyOrder.objects.filter(patient=self.patient, is_current_version=True)
        self.assertEqual(current_versions.count(), 1)

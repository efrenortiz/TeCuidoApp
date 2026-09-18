import threading
from datetime import date, time, timedelta

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from appointments.services import availability as availability_service
from care_requests.models import CareRequest
from care_requests.services import care_request as care_request_service
from care_requests.services.exceptions import CareRequestRateLimitExceeded
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from patients.models import Patient


def _make_person(email, first_name="Test"):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1)
    )


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_patient(email):
    return Patient.objects.create(
        person=_make_person(email, "Pat"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT
    )


def _make_clinic(name="Consultorio CareRequest Concurrencia"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class CareRequestConcurrencyTestCase(TransactionTestCase):
    """`TransactionTestCase` (no `TestCase`) — necesita conexiones de base
    de datos reales e independientes por hilo, algo que el wrap-en-una-
    transacción de `TestCase` ocultaría (docs/design/
    care-request-service-contracts.md §14)."""

    reset_sequences = False

    def setUp(self):
        self.doctor = _make_doctor("cr-conc-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(
            doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=30
        )
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic, date=self.day,
            start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("cr-conc-patient@example.com")
        self.patient_user = self.patient.person.user

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(minutes=30)


class IdempotencyRaceTests(CareRequestConcurrencyTestCase):
    def test_two_concurrent_identical_requests_same_key_one_creates_one_replays(self):
        start_at, end_at = self._slot()
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                result = care_request_service.create(
                    actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                    start_at=start_at, end_at=end_at, motivo="Control",
                    idempotency_key="race-key",
                )
                results[key] = result
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = f"error: {exc!r}"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a",))
        t2 = threading.Thread(target=attempt, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(CareRequest.objects.count(), 1, results)
        self.assertEqual(Appointment.objects.count(), 1, results)
        # Ambos hilos deben terminar con el MISMO resultado (uno lo crea,
        # el otro hace replay) — nunca un IntegrityError crudo.
        self.assertEqual(results["a"], results["b"], results)


class RateLimitRaceTests(CareRequestConcurrencyTestCase):
    def test_two_concurrent_requests_never_exceed_the_limit(self):
        # Ya al tope (2 previas + 1 nueva concurrente no debería empujar a 4
        # si ambos hilos compitieran) — se deja el límite exacto en 3 para
        # esta prueba: 2 secuenciales + 2 concurrentes, exactamente una de
        # las concurrentes debe ganar.
        for hour in (9, 10):
            care_request_service.create(
                actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                start_at=self._slot(hour=hour)[0], end_at=self._slot(hour=hour)[1],
                motivo="Control",
            )

        start_a, end_a = self._slot(hour=11)
        start_b, end_b = self._slot(hour=12)
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key, start_at, end_at):
            try:
                barrier.wait(timeout=5)
                care_request_service.create(
                    actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
                    start_at=start_at, end_at=end_at, motivo="Control",
                )
                results[key] = "success"
            except CareRequestRateLimitExceeded:
                results[key] = "rate_limited"
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = f"error: {exc!r}"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a", start_a, end_a))
        t2 = threading.Thread(target=attempt, args=("b", start_b, end_b))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = list(results.values())
        self.assertEqual(outcomes.count("success"), 1, results)
        self.assertEqual(outcomes.count("rate_limited"), 1, results)
        self.assertEqual(CareRequest.objects.count(), 3)

"""ETAPA 3 — Concurrencia e integridad transaccional
(docs/phases/phase-3-prompt_programacion.md, Gate 3).

`TransactionTestCase` (no `TestCase`): las carreras reales necesitan
conexiones de BD que confirmen (`commit`) de forma independiente entre
hilos — el patrón exacto ya usado en
`appointments/tests/test_appointment_clinical_ops.py` para
start/complete_appointment.

Invariante de Gate 3 verificada en cada test: nunca queda persistido
`ClinicalEncounter COMPLETED` + `Appointment IN_CONSULTATION`, ni
`Appointment IN_CONSULTATION` + `ClinicalEncounter` inexistente, para una
operación de inicio clínico procesada como válida.
"""

import threading
from datetime import date, time, timedelta

from django.db import IntegrityError, connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.models import ClinicalEncounter
from medical_records.services import encounter as encounter_service
from medical_records.services.exceptions import EncounterAlreadyCompleted
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


def _make_clinic(name="Consultorio Concurrencia"):
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


class ClinicalConcurrencyTestCase(TransactionTestCase):
    """`TransactionTestCase` — igual que
    `appointments.tests.test_appointment_clinical_ops.ClinicalOpsTestCase`:
    la carrera necesita conexiones que confirmen de forma independiente."""

    reset_sequences = False

    def setUp(self):
        self.doctor = _make_doctor("mr-race-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("mr-race-patient@example.com")
        self.patient_user = self.patient.person.user

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


class StartEncounterRaceTests(ClinicalConcurrencyTestCase):
    def test_concurrent_start_requests_do_not_duplicate_encounter(self):
        """SC-022/SC-023/SC-029 — dos `start` concurrentes sobre la misma
        cita: ambos deben tener éxito (idempotencia), pero nunca deben
        producir dos `ClinicalEncounter`."""
        appointment = self._book()
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=appointment)
                results[key] = ("success", encounter.pk)
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = (f"error: {exc!r}", None)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a",))
        t2 = threading.Thread(target=attempt, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = [outcome for outcome, _ in results.values()]
        self.assertEqual(outcomes.count("success"), 2, results)
        pks = {pk for _, pk in results.values()}
        self.assertEqual(len(pks), 1, results)

        self.assertEqual(ClinicalEncounter.objects.filter(appointment=appointment).count(), 1)
        appointment.refresh_from_db()
        # Gate 3 — nunca IN_CONSULTATION sin su encuentro correspondiente.
        self.assertEqual(appointment.status, Appointment.Status.IN_CONSULTATION)
        self.assertTrue(ClinicalEncounter.objects.filter(appointment=appointment, status="IN_PROGRESS").exists())


class ClinicalEncounterUniqueConstraintRaceTests(ClinicalConcurrencyTestCase):
    def test_concurrent_direct_creates_hit_unique_constraint(self):
        """Backstop de integridad a nivel de base de datos
        (clinical-data-model.md §25.2, `OneToOneField(appointment)`):
        incluso si se evitara el locking de aplicación (creación directa
        vía el modelo, sin pasar por el servicio), la unicidad de
        `appointment` impide que existan dos `ClinicalEncounter` para la
        misma cita."""
        appointment = self._book()
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            now = dj_timezone.now()
            try:
                barrier.wait(timeout=5)
                with transaction.atomic():
                    ClinicalEncounter.objects.create(
                        appointment=appointment, doctor=self.doctor,
                        status=ClinicalEncounter.Status.IN_PROGRESS, created_at=now, started_at=now,
                    )
                results[key] = "success"
            except IntegrityError:
                results[key] = "integrity_error"
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

        outcomes = list(results.values())
        self.assertEqual(outcomes.count("success"), 1, results)
        self.assertEqual(outcomes.count("integrity_error"), 1, results)
        self.assertEqual(ClinicalEncounter.objects.filter(appointment=appointment).count(), 1)


class StartedEncounterConcurrencyTestCase(ClinicalConcurrencyTestCase):
    def setUp(self):
        super().setUp()
        self.appointment = self._book()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)


class CompleteEncounterRaceTests(StartedEncounterConcurrencyTestCase):
    def test_concurrent_completion_with_identical_content_is_idempotent(self):
        """SC-065/D-001 bajo carrera real: dos `complete` concurrentes con
        el mismo contenido deben tener éxito y coincidir en `completed_at`
        — ninguno reabre ni reejecuta el cierre."""
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key):
            try:
                barrier.wait(timeout=5)
                completed = encounter_service.complete_encounter(
                    actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA,
                )
                results[key] = ("success", completed.completed_at)
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = (f"error: {exc!r}", None)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a",))
        t2 = threading.Thread(target=attempt, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = [outcome for outcome, _ in results.values()]
        self.assertEqual(outcomes.count("success"), 2, results)
        timestamps = {ts for _, ts in results.values()}
        self.assertEqual(len(timestamps), 1, results)

        self.encounter.refresh_from_db()
        self.appointment.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.COMPLETED)
        # Gate 3 — nunca completado sin que la cita también haya cerrado.
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_concurrent_completion_with_different_content_only_one_wins(self):
        """SC-065/D-001 — contenido distinto sobre un cierre que ya ganó
        la carrera se rechaza como `EncounterAlreadyCompleted`, nunca
        sobrescribe el cierre ya persistido."""
        data_b = dict(VALID_DATA, plan="Plan alterno enviado por una segunda solicitud")
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key, data):
            try:
                barrier.wait(timeout=5)
                completed = encounter_service.complete_encounter(
                    actor=self.doctor_user, encounter=self.encounter, data=data,
                )
                results[key] = ("success", completed.plan)
            except EncounterAlreadyCompleted:
                results[key] = ("already_completed", None)
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = (f"error: {exc!r}", None)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a", VALID_DATA))
        t2 = threading.Thread(target=attempt, args=("b", data_b))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        outcomes = [outcome for outcome, _ in results.values()]
        self.assertEqual(outcomes.count("success"), 1, results)
        self.assertEqual(outcomes.count("already_completed"), 1, results)

        self.encounter.refresh_from_db()
        self.appointment.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.COMPLETED)
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)
        # El plan persistido corresponde exactamente al ganador de la carrera.
        winning_plan = next(plan for outcome, plan in results.values() if outcome == "success")
        self.assertEqual(self.encounter.plan, winning_plan)


class SaveEncounterRaceTests(StartedEncounterConcurrencyTestCase):
    def test_concurrent_saves_on_different_fields_both_persist(self):
        """El bloqueo de fila (`select_for_update`) serializa los dos
        guardados: ninguno pierde el cambio del otro (sin esto, un
        `save()` completo de Django sobrescribiría el campo ajeno con un
        valor obsoleto — "lost update")."""
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key, data):
            try:
                barrier.wait(timeout=5)
                encounter_service.save_encounter(actor=self.doctor_user, encounter=self.encounter, data=data)
                results[key] = "success"
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = f"error: {exc!r}"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a", {"reason_for_visit": "Motivo capturado en hilo A"}))
        t2 = threading.Thread(target=attempt, args=("b", {"present_illness": "Padecimiento capturado en hilo B"}))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(list(results.values()).count("success"), 2, results)
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.reason_for_visit, "Motivo capturado en hilo A")
        self.assertEqual(self.encounter.present_illness, "Padecimiento capturado en hilo B")

    def test_concurrent_saves_on_same_field_last_writer_wins_without_corruption(self):
        """ADR-019 — last-write-wins documentado para guardados
        concurrentes: bajo carrera real, el valor final debe ser
        exactamente uno de los dos enviados, nunca una mezcla corrupta."""
        results = {}
        barrier = threading.Barrier(2)

        def attempt(key, value):
            try:
                barrier.wait(timeout=5)
                encounter_service.save_encounter(
                    actor=self.doctor_user, encounter=self.encounter, data={"observations": value},
                )
                results[key] = "success"
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results[key] = f"error: {exc!r}"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=attempt, args=("a", "Observación A"))
        t2 = threading.Thread(target=attempt, args=("b", "Observación B"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(list(results.values()).count("success"), 2, results)
        self.encounter.refresh_from_db()
        self.assertIn(self.encounter.observations, ("Observación A", "Observación B"))


class SaveVsCompleteRaceTests(StartedEncounterConcurrencyTestCase):
    def test_concurrent_save_and_completion_never_corrupt_state(self):
        """Gate 3 — sin importar el orden de la carrera, `complete`
        siempre tiene éxito (su contenido es autosuficiente) y el estado
        final nunca deja el encuentro completado con la cita todavía
        `IN_CONSULTATION`. `save` puede ganar (su valor persiste antes del
        cierre) o perder (`EncounterAlreadyCompleted`) — ambos son
        resultados correctos."""
        results = {}
        barrier = threading.Barrier(2)

        def do_save():
            try:
                barrier.wait(timeout=5)
                encounter_service.save_encounter(
                    actor=self.doctor_user, encounter=self.encounter, data={"observations": "Nota tardía"},
                )
                results["save"] = "success"
            except EncounterAlreadyCompleted:
                results["save"] = "already_completed"
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results["save"] = f"error: {exc!r}"
            finally:
                connections.close_all()

        def do_complete():
            try:
                barrier.wait(timeout=5)
                encounter_service.complete_encounter(
                    actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA,
                )
                results["complete"] = "success"
            except Exception as exc:  # pragma: no cover - diagnostic aid
                results["complete"] = f"error: {exc!r}"
            finally:
                connections.close_all()

        t1 = threading.Thread(target=do_save)
        t2 = threading.Thread(target=do_complete)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(results["complete"], "success", results)
        self.assertIn(results["save"], ("success", "already_completed"), results)

        self.encounter.refresh_from_db()
        self.appointment.refresh_from_db()
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.COMPLETED)
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)
        if results["save"] == "success":
            self.assertEqual(self.encounter.observations, "Nota tardía")
        else:
            self.assertEqual(self.encounter.observations, "")


class RequestAfterCompletionTests(StartedEncounterConcurrencyTestCase):
    def test_save_request_arriving_right_after_completion_is_rejected(self):
        """"Request posterior a completion": una vez que el cierre ya
        confirmó, cualquier `save` que llegue después —aunque sea
        inmediatamente después, sin ninguna carrera real involucrada—
        debe rechazarse sin corromper el cierre ya persistido."""
        encounter_service.complete_encounter(actor=self.doctor_user, encounter=self.encounter, data=VALID_DATA)

        with self.assertRaises(EncounterAlreadyCompleted):
            encounter_service.save_encounter(
                actor=self.doctor_user, encounter=self.encounter, data={"observations": "Demasiado tarde"},
            )

        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.observations, "")
        self.assertEqual(self.encounter.status, ClinicalEncounter.Status.COMPLETED)

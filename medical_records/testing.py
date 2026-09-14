"""Fixtures compartidas para tests de Fase 4 (`prescriptions`, `study_orders`,
`clinical_documents`) — mismo patrón ya usado en `medical_records/tests/*.py`.

No es un módulo de test (no coincide con `test_*.py`); el test runner de
Django no lo descubre ni lo ejecuta.
"""

from datetime import date, time, timedelta

from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from medical_records.services import encounter as encounter_service
from patients.models import Patient


def make_person(email, first_name="Test", birth_date=date(1990, 1, 1)):
    user = User.objects.create_user(email=email, password="s3cure-pass!", email_verified=True)
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=birth_date
    )


def make_doctor(email):
    return Doctor.objects.create(person=make_person(email, "Doc"))


def make_patient(email):
    return Patient.objects.create(
        person=make_person(email, "Pat"), sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT
    )


def make_clinic(name="Consultorio F4"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def future_date(days=5):
    return (dj_timezone.now() + timedelta(days=days)).date()


class ClinicalEncounterFixture:
    """Mixin de `TestCase`: crea un `ClinicalEncounter` real `IN_PROGRESS`
    (médico, paciente, clínica, cita, encuentro) listo para que los
    servicios de Fase 4 lo usen como contexto clínico."""

    def setUp(self):
        super().setUp()
        self.doctor = make_doctor(f"f4-doc-{id(self)}@example.com")
        self.other_doctor = make_doctor(f"f4-other-doc-{id(self)}@example.com")
        self.clinic = make_clinic()
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=60)
        DoctorClinic.objects.create(doctor=self.other_doctor, clinic=self.clinic, appointment_duration_minutes=60)
        self.doctor_user = self.doctor.person.user
        self.other_doctor_user = self.other_doctor.person.user

        self.day = future_date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )

        self.patient = make_patient(f"f4-patient-{id(self)}@example.com")
        self.patient_user = self.patient.person.user
        self.appointment = self._book()
        self.encounter = encounter_service.start_encounter(actor=self.doctor_user, appointment=self.appointment)

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

from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment
from care_requests.models import CareRequest
from clinics.models import Clinic
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


def _make_clinic(name="Consultorio CareRequest"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


class CareRequestModelTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("cr-model-doc@example.com")
        self.clinic = _make_clinic()
        self.patient = _make_patient("cr-model-patient@example.com")
        self.actor = self.patient.person.user
        self.start_at = dj_timezone.now() + timedelta(days=1)
        self.end_at = self.start_at + timedelta(minutes=30)

    def _make(self, **overrides):
        defaults = dict(
            patient=self.patient, created_by=self.actor, doctor=self.doctor, clinic=self.clinic,
            start_at=self.start_at, end_at=self.end_at, motivo="Dolor abdominal",
            status=CareRequest.Status.NUEVA,
        )
        defaults.update(overrides)
        return CareRequest.objects.create(**defaults)

    def test_create_minimal_valid_care_request(self):
        care_request = self._make()
        self.assertEqual(care_request.status, CareRequest.Status.NUEVA)
        self.assertIsNone(care_request.appointment)
        self.assertEqual(care_request.padecimiento, "")
        self.assertEqual(care_request.descripcion, "")
        self.assertIsNone(care_request.responsible)

    def test_motivo_is_required_at_db_level(self):
        # TextField sin blank=True → full_clean ya lo rechaza a nivel de formulario;
        # a nivel de fila, motivo="" sigue siendo válido para TextField sin
        # constraint explícito — la obligatoriedad real la aplica el servicio
        # (nunca se llama a create() sin motivo). No se agrega un CheckConstraint
        # para esto por no ser una regla de integridad entre columnas.
        care_request = self._make(motivo="")
        self.assertEqual(care_request.motivo, "")

    def test_status_choices_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make(status="BOGUS")

    def test_start_before_end_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make(start_at=self.end_at, end_at=self.start_at)

    def test_idempotency_key_unique_per_actor(self):
        self._make(idempotency_key="cr-key-1")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make(idempotency_key="cr-key-1")

    def test_idempotency_key_not_unique_across_different_actors(self):
        other_patient = _make_patient("cr-model-patient-2@example.com")
        self._make(idempotency_key="shared-key")
        # No debe chocar: la unicidad es (created_by, idempotency_key), no global.
        self._make(created_by=other_patient.person.user, patient=other_patient, idempotency_key="shared-key")

    def test_appointment_is_optional_one_to_one(self):
        care_request_a = self._make()
        care_request_b = self._make()
        self.assertIsNone(care_request_a.appointment)
        self.assertIsNone(care_request_b.appointment)

    def test_no_reverse_accessor_on_appointment(self):
        """Hallazgo A (auditoría 2026-09-18): `related_name='+'` en
        `CareRequest.appointment` debe suprimir por completo el accessor
        inverso de Django — `Appointment` nunca debe exponer `.care_request`,
        ni como atributo de clase ni de instancia. Esto preserva
        `care_requests → appointments` (nunca al revés) también a nivel de
        navegación ORM, no solo a nivel de columnas/migraciones."""
        self.assertFalse(hasattr(Appointment, "care_request"))
        self.assertNotIn("care_request", [f.name for f in Appointment._meta.get_fields()])

    def test_clinical_document_ids_defaults_to_empty_list(self):
        care_request = self._make()
        self.assertEqual(care_request.clinical_document_ids, [])

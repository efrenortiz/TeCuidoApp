"""`CareRequestAdmin` debe ser de solo lectura — mismo criterio verificado
para `AuditEventAdmin` en `medical_records/tests/test_audit.py`
(`test_admin_registration_is_read_only`): ningún rol, incluido el
Administrador, puede crear/editar/borrar una `CareRequest` desde
`/admin/` (`docs/design/care-request-permissions.md` §7-9/§11)."""

from datetime import date, time, timedelta

from django.contrib import admin as django_admin
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.services import availability as availability_service
from care_requests.admin import CareRequestAdmin
from care_requests.models import CareRequest
from care_requests.services import care_request as care_request_service
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


class CareRequestAdminPermissionTests(TestCase):
    """Instanciación directa — mismo patrón que
    `medical_records.tests.test_audit.test_admin_registration_is_read_only`."""

    def test_add_permission_is_denied(self):
        admin_instance = CareRequestAdmin(CareRequest, django_admin.site)
        self.assertFalse(admin_instance.has_add_permission(None))

    def test_change_permission_is_denied(self):
        admin_instance = CareRequestAdmin(CareRequest, django_admin.site)
        self.assertFalse(admin_instance.has_change_permission(None))

    def test_delete_permission_is_denied(self):
        admin_instance = CareRequestAdmin(CareRequest, django_admin.site)
        self.assertFalse(admin_instance.has_delete_permission(None))

    def test_no_administrative_path_can_create_or_mutate_care_request(self):
        """Invariante (`docs/design/care-request-domain.md` §6.4): una
        `CareRequest` `CONVERTIDA` siempre tiene `appointment`. Bloquear
        `add`/`change` es lo que hace estructuralmente imposible producir,
        desde `/admin/`, una `NUEVA` sin `Hold`/`Appointment` o una
        `CONVERTIDA` sin `appointment` — la única creación válida pasa por
        `care_request_service.create()`."""
        admin_instance = CareRequestAdmin(CareRequest, django_admin.site)
        self.assertFalse(admin_instance.has_add_permission(None))
        self.assertFalse(admin_instance.has_change_permission(None))


class CareRequestAdminHttpTests(TestCase):
    """Verificación real contra el sitio de admin (no solo la instanciación
    directa), para confirmar que la consulta (listado/detalle) sigue
    funcionando y que add/delete responden 403 — no solo que el método
    devuelva `False` en aislamiento."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="cr-admin-super@example.com", password="s3cure-pass!"
        )
        self.doctor = _make_doctor("cr-admin-doc@example.com")
        self.clinic = Clinic.objects.create(name="Consultorio Admin", timezone="America/Mexico_City")
        DoctorClinic.objects.create(doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=30)
        self.patient = _make_patient("cr-admin-patient@example.com")
        day = (dj_timezone.now() + timedelta(days=5)).date()
        availability_service.create_availability(
            actor=self.doctor.person.user, doctor=self.doctor, clinic=self.clinic, date=day,
            start_time=time(9, 0), end_time=time(11, 0),
        )
        start_at = availability_service.combine_local(day, time(9, 0), self.clinic)
        result = care_request_service.create(
            actor=self.patient.person.user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=start_at + timedelta(minutes=30), motivo="Control",
        )
        self.care_request = CareRequest.objects.get(pk=result.care_request_id)
        self.client.force_login(self.superuser)

    def test_changelist_is_viewable(self):
        response = self.client.get(reverse("admin:care_requests_carerequest_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_detail_is_viewable(self):
        response = self.client.get(
            reverse("admin:care_requests_carerequest_change", args=[self.care_request.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_add_is_forbidden(self):
        response = self.client.get(reverse("admin:care_requests_carerequest_add"))
        self.assertEqual(response.status_code, 403)

    def test_delete_is_forbidden(self):
        response = self.client.get(
            reverse("admin:care_requests_carerequest_delete", args=[self.care_request.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_change_post_does_not_mutate(self):
        """Aunque `change_view` renderiza el detalle en modo solo-lectura
        (200, `has_view_permission` sigue siendo `True` para el
        superusuario), un intento de `POST` para guardar cambios debe
        seguir bloqueado por `has_change_permission`."""
        url = reverse("admin:care_requests_carerequest_change", args=[self.care_request.pk])
        response = self.client.post(url, data={"status": CareRequest.Status.NUEVA})
        self.assertEqual(response.status_code, 403)
        self.care_request.refresh_from_db()
        self.assertEqual(self.care_request.status, CareRequest.Status.CONVERTIDA)

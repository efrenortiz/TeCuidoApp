"""Fase 6 — catálogo transversal de auditoría (F6-D05/F6-D06):
LOGIN/MODIFY_PATIENT/CHANGE_PERMISSIONS/DISABLE_USER, y el endpoint
administrativo de consulta del audit trail (docs/design/phase-6-audit-domain.md,
docs/design/phase-6-audit-api-contracts.md)."""

from datetime import date

from django.test import Client, TestCase

from accounts.models import Person, User
from medical_records.models import AuditEvent
from patients.models import Patient, Responsible


def _make_person(email, first_name="Test"):
    user = User.objects.create_user(email=email, password="s3cure-pass!", email_verified=True)
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=date(1990, 1, 1)
    )


class LoginAuditTests(TestCase):
    def setUp(self):
        self.person = _make_person("login-audit@example.com")
        self.user = self.person.user
        self.client = Client()

    def test_successful_login_is_audited(self):
        response = self.client.post(
            "/accounts/login/", {"username": self.user.email, "password": "s3cure-pass!"},
        )
        self.assertEqual(response.status_code, 302)
        event = AuditEvent.objects.filter(action=AuditEvent.Action.LOGIN, actor=self.user).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)

    def test_login_rejected_for_unverified_email_is_audited_as_denied(self):
        self.user.email_verified = False
        self.user.save(update_fields=["email_verified"])
        response = self.client.post(
            "/accounts/login/", {"username": self.user.email, "password": "s3cure-pass!"},
        )
        self.assertEqual(response.status_code, 200)  # form_invalid re-renders
        event = AuditEvent.objects.filter(action=AuditEvent.Action.LOGIN, actor=self.user).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.result, AuditEvent.Result.DENIED)

    def test_wrong_password_against_unknown_identity_is_not_audited(self):
        """ITD-008 (docs/phases/phase-6-implementation-summary.md):
        `record_event` exige un actor real (AH-086); un intento contra un
        correo que no existe no tiene ningún `User` al que atribuirlo."""
        self.client.post("/accounts/login/", {"username": "nadie@example.com", "password": "x"})
        self.assertFalse(AuditEvent.objects.filter(action=AuditEvent.Action.LOGIN).exists())


class AdminModelAuditTests(TestCase):
    def setUp(self):
        self.admin_person = _make_person("admin-audit@example.com", "Admin")
        self.admin_user = self.admin_person.user
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.client = Client()
        self.client.force_login(self.admin_user)

        patient_person = _make_person("patient-audit@example.com", "Pat")
        self.patient = Patient.objects.create(
            person=patient_person, sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT,
        )

    def test_modify_patient_via_admin_is_audited(self):
        url = f"/admin/patients/patient/{self.patient.pk}/change/"
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)

        response = self.client.post(
            url,
            {
                "person": self.patient.person_id,
                "sex": "F",
                "regime": "ADULT",
                "is_active": "on",
                "curp": "MODIFIED123",
                "nationality": "Mexicana",
                "emergency_contact_name": "",
                "_save": "Save",
            },
        )
        self.assertIn(response.status_code, (200, 302))
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.MODIFY_PATIENT, resource_id=self.patient.pk,
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_id, self.admin_user.pk)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)

    def test_modify_person_of_a_patient_via_admin_is_audited(self):
        """Hallazgo 12.6: editar la Person de un paciente desde
        `PersonAdmin` también debe auditarse como MODIFY_PATIENT."""
        url = f"/admin/accounts/person/{self.patient.person_id}/change/"
        response = self.client.post(
            url,
            {
                "user": self.patient.person.user_id,
                "first_name": "NuevoNombre",
                "last_name_paterno": self.patient.person.last_name_paterno,
                "last_name_materno": "",
                "birth_date": "1990-01-01",
                "phone": "5555555555",
                "country": "México",
                "_save": "Save",
            },
        )
        self.assertIn(response.status_code, (200, 302))
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.MODIFY_PATIENT, resource_id=self.patient.pk,
            reason_code="PERSON_FIELDS",
        ).first()
        self.assertIsNotNone(event)

    def test_disable_user_via_admin_is_audited(self):
        target_person = _make_person("to-disable@example.com", "Target")
        target_user = target_person.user
        url = f"/admin/accounts/user/{target_user.pk}/change/"

        response = self.client.post(
            url,
            {
                "email": target_user.email,
                "is_active": "",  # unchecked -> False
                "is_staff": "",
                "email_verified": "on",
                "date_joined_0": "2026-01-01", "date_joined_1": "00:00:00",
            },
        )
        self.assertIn(response.status_code, (200, 302))
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.DISABLE_USER, resource_id=target_user.pk,
        ).first()
        self.assertIsNotNone(event)


class AuditTrailAccessTests(TestCase):
    def setUp(self):
        self.admin_person = _make_person("admin-trail@example.com", "Admin")
        self.admin_user = self.admin_person.user
        self.admin_user.is_superuser = True
        self.admin_user.is_staff = True
        self.admin_user.save()

        self.doctor_person = _make_person("doctor-trail@example.com", "Doc")

        AuditEvent.objects.create(
            actor=self.admin_user, actor_role="ADMINISTRATOR", action=AuditEvent.Action.LOGIN,
            result=AuditEvent.Result.SUCCESS, resource_type=AuditEvent.ResourceType.USER,
            resource_id=self.admin_user.pk,
        )

    def test_administrator_can_query_api(self):
        client = Client()
        client.force_login(self.admin_user)
        response = client.get("/api/v1/clinical/audit/events/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)

    def test_non_administrator_is_denied(self):
        client = Client()
        client.force_login(self.doctor_person.user)
        response = client.get("/api/v1/clinical/audit/events/")
        self.assertEqual(response.status_code, 403)

    def test_response_never_exposes_clinical_content_fields(self):
        client = Client()
        client.force_login(self.admin_user)
        response = client.get("/api/v1/clinical/audit/events/")
        body = response.json()
        for event in body["results"]:
            self.assertNotIn("reason_for_visit", event)
            self.assertNotIn("family_history", event)

    def test_non_administrator_is_denied_even_with_nonexistent_patient_id(self):
        """Regresión: la autorización debe evaluarse antes de cualquier
        respuesta temprana — un `patient_id` inexistente no debe
        convertirse en un atajo que devuelva 200 a un actor no autorizado
        sin pasar por `can_view_audit_log` (hallazgo de la revisión de
        seguridad de esta fase)."""
        client = Client()
        client.force_login(self.doctor_person.user)
        response = client.get("/api/v1/clinical/audit/events/?patient_id=999999")
        self.assertEqual(response.status_code, 403)

    def test_ui_screen_requires_administrator(self):
        client = Client()
        client.force_login(self.doctor_person.user)
        response = client.get("/clinica/auditoria/")
        self.assertEqual(response.status_code, 404)

        admin_client = Client()
        admin_client.force_login(self.admin_user)
        response = admin_client.get("/clinica/auditoria/")
        self.assertEqual(response.status_code, 200)

    def test_ui_supports_date_range_filter_like_the_api(self):
        """Hallazgo 12.8: la UI debe ofrecer los mismos filtros que el API
        (date_from/date_to)."""
        import datetime as dt

        client = Client()
        client.force_login(self.admin_user)

        old_event = AuditEvent.objects.create(
            actor=self.admin_user, actor_role="ADMINISTRATOR", action=AuditEvent.Action.LOGIN,
            result=AuditEvent.Result.SUCCESS, resource_type=AuditEvent.ResourceType.USER,
            resource_id=self.admin_user.pk,
        )
        AuditEvent.objects.filter(pk=old_event.pk).update(
            occurred_at=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)
        )

        response = client.get("/clinica/auditoria/", {"date_from": "2026-01-01"})
        self.assertEqual(response.status_code, 200)
        event_ids = [e.pk for e in response.context["page"].object_list]
        self.assertNotIn(old_event.pk, event_ids)

    def test_no_cache_headers_on_api(self):
        client = Client()
        client.force_login(self.admin_user)
        response = client.get("/api/v1/clinical/audit/events/")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_patient_is_denied_audit_trail(self):
        """Prompt 2 de la corrección post-implementación: cobertura
        explícita por rol, no solo genérica con un médico."""
        patient_person = _make_person("patient-trail@example.com", "Pat")
        patient = Patient.objects.create(
            person=patient_person, sex=Patient.Sex.FEMALE, regime=Patient.Regime.ADULT,
        )
        client = Client()
        client.force_login(patient.person.user)
        self.assertEqual(client.get("/api/v1/clinical/audit/events/").status_code, 403)
        self.assertEqual(client.get("/clinica/auditoria/").status_code, 404)

    def test_responsible_is_denied_audit_trail(self):
        responsible_person = _make_person("responsible-trail@example.com", "Resp")
        responsible = Responsible.objects.create(person=responsible_person)
        client = Client()
        client.force_login(responsible.person.user)
        self.assertEqual(client.get("/api/v1/clinical/audit/events/").status_code, 403)
        self.assertEqual(client.get("/clinica/auditoria/").status_code, 404)

    def test_inactive_user_is_denied_audit_trail(self):
        self.doctor_person.user.is_active = False
        self.doctor_person.user.save(update_fields=["is_active"])
        client = Client()
        logged_in = client.login(username=self.doctor_person.user.email, password="s3cure-pass!")
        self.assertFalse(logged_in)  # ModelBackend ya rechaza usuarios inactivos al autenticar
        self.assertEqual(client.get("/api/v1/clinical/audit/events/").status_code, 401)

    def test_django_admin_staff_without_superuser_cannot_see_audit_trail(self):
        """Hallazgo 12.1: `is_staff=True` (acceso genérico a `/admin/`) no
        debe bastar para ver el audit trail vía Django Admin — la regla
        debe ser consistente con la API/UI propias (solo `is_superuser`).
        Antes de la corrección, `AuditEventAdmin` solo dependía del gate
        genérico de `/admin/`."""
        staff_person = _make_person("staff-not-admin@example.com", "Staff")
        staff_user = staff_person.user
        staff_user.is_staff = True
        staff_user.is_superuser = False
        staff_user.save()

        client = Client()
        client.force_login(staff_user)
        response = client.get("/admin/medical_records/auditevent/")
        self.assertEqual(response.status_code, 403)

    def test_django_admin_superuser_can_see_audit_trail(self):
        client = Client()
        client.force_login(self.admin_user)
        response = client.get("/admin/medical_records/auditevent/")
        self.assertEqual(response.status_code, 200)


class RejectionAuditCoverageTests(TestCase):
    """Hallazgo 12.2 / PD-002: los rechazos que sí alcanzan el boundary
    instrumentado deben auditarse; casos explícitos de actor sin permiso,
    usuario inactivo y acceso administrativo no autorizado."""

    def setUp(self):
        self.admin_person = _make_person("admin-rej@example.com", "Admin")
        self.admin_user = self.admin_person.user
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.doctor_person = _make_person("doctor-rej@example.com", "Doc")

    def test_inactive_user_login_is_not_a_success_event(self):
        self.doctor_person.user.is_active = False
        self.doctor_person.user.save(update_fields=["is_active"])
        client = Client()
        client.post(
            "/accounts/login/",
            {"username": self.doctor_person.user.email, "password": "s3cure-pass!"},
        )
        self.assertFalse(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.LOGIN, result=AuditEvent.Result.SUCCESS,
                actor=self.doctor_person.user,
            ).exists()
        )

    def test_non_administrator_role_denied_admin_audit_api_is_not_logged_as_success(self):
        client = Client()
        client.force_login(self.doctor_person.user)
        response = client.get("/api/v1/clinical/audit/events/")
        self.assertEqual(response.status_code, 403)
        # El rechazo mismo no genera un evento SUCCESS de ninguna acción del
        # catálogo (no hay una acción "leer audit trail" en el catálogo
        # base; el rechazo lo demuestra el propio 403 uniforme, PD-002).
        self.assertFalse(
            AuditEvent.objects.filter(actor=self.doctor_person.user, result=AuditEvent.Result.SUCCESS).exists()
        )

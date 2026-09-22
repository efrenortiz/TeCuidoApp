from datetime import date, time, timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone as dj_timezone

from accounts.models import Person, User
from appointments.models import Appointment, RequestReason
from appointments.services import appointment as appointment_service
from appointments.services import availability as availability_service
from appointments.services import hold as hold_service
from clinics.models import Clinic, DoctorClinic
from doctors.models import Doctor
from notifications import services as notification_service
from notifications.models import Notification, ReminderWindow
from patients.models import Patient, Responsible, ResponsiblePatientRelationship


def _make_person(email, first_name="Test", birth_date=date(1990, 1, 1)):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    return Person.objects.create(
        user=user, first_name=first_name, last_name_paterno="Test", birth_date=birth_date
    )


def _make_doctor(email):
    return Doctor.objects.create(person=_make_person(email, "Doc"))


def _make_patient(email, birth_date=date(1990, 1, 1)):
    return Patient.objects.create(
        person=_make_person(email, "Pat", birth_date=birth_date),
        sex=Patient.Sex.FEMALE,
        regime=Patient.Regime.ADULT if birth_date <= date(2010, 1, 1) else Patient.Regime.MINOR,
    )


def _make_responsible(email):
    return Responsible.objects.create(person=_make_person(email, "Resp"))


def _make_clinic(name="Consultorio Notificaciones"):
    return Clinic.objects.create(name=name, timezone="America/Mexico_City")


def _future_date(days=20):
    return (dj_timezone.now() + timedelta(days=days)).date()


class NotificationServiceTestCase(TestCase):
    """`captureOnCommitCallbacks(execute=True)` es obligatorio aquí: las
    señales de `appointments` se despachan dentro de `transaction.on_commit`
    (docs/phases/phase-6-implementation-summary.md ITD-002), que
    `TestCase` normalmente nunca ejecuta porque envuelve cada test en un
    `atomic()` que se revierte, no se confirma."""

    def setUp(self):
        self.doctor = _make_doctor("notif-doc@example.com")
        self.clinic = _make_clinic()
        DoctorClinic.objects.create(
            doctor=self.doctor, clinic=self.clinic, appointment_duration_minutes=30
        )
        self.doctor_user = self.doctor.person.user
        self.day = _future_date()
        self.availability = availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=self.day, start_time=time(9, 0), end_time=time(13, 0),
        )
        self.patient = _make_patient("notif-patient@example.com")
        self.patient_user = self.patient.person.user
        self.responsible = _make_responsible("notif-resp@example.com")
        ResponsiblePatientRelationship.objects.create(
            responsible=self.responsible, patient=self.patient,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )

    def _slot(self, hour=9):
        start_at = availability_service.combine_local(self.day, time(hour, 0), self.clinic)
        return start_at, start_at + timedelta(minutes=30)

    def _book(self, actor=None, hour=9):
        start_at, end_at = self._slot(hour)
        hold = hold_service.create_hold(
            actor=actor or self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        with self.captureOnCommitCallbacks(execute=True):
            appointment = appointment_service.create_appointment_from_hold(
                actor=actor or self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )
        return appointment


class AppointmentCreatedNotificationTests(NotificationServiceTestCase):
    """F6-D01."""

    def test_notifies_patient_responsible_and_doctor(self):
        appointment = self._book()
        recipients = set(
            Notification.objects.filter(
                event_type=Notification.EventType.APPOINTMENT_CREATED,
                resource_id=appointment.pk,
            ).values_list("recipient_user_id", flat=True)
        )
        self.assertEqual(
            recipients,
            {self.patient_user.pk, self.responsible.person.user_id, self.doctor_user.pk},
        )

    def test_notification_status_is_sent_via_console_backend(self):
        appointment = self._book()
        notification = Notification.objects.get(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk,
            recipient_user=self.patient_user,
        )
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertIsNotNone(notification.sent_at)

    def test_duplicate_dispatch_is_idempotent(self):
        appointment = self._book()
        count_before = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED, resource_id=appointment.pk,
        ).count()
        # Un segundo despacho manual del mismo evento (p. ej. un reintento
        # de infraestructura) no debe duplicar filas.
        notification_service.notify_appointment_created(appointment)
        count_after = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED, resource_id=appointment.pk,
        ).count()
        self.assertEqual(count_before, count_after)

    def test_transport_failure_does_not_revert_appointment(self):
        with mock.patch.object(
            notification_service._TRANSPORT, "send",
            side_effect=RuntimeError("SMTP caído"),
        ):
            appointment = self._book()
        self.assertTrue(Appointment.objects.filter(pk=appointment.pk).exists())
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)

    def test_minor_patient_without_user_is_skipped_silently(self):
        minor = _make_patient("notif-minor-noemail@example.com", birth_date=date(2020, 1, 1))
        minor.person.user = None
        minor.person.save(update_fields=["user"])
        # El propio responsable, no el paciente, hace la reserva.
        ResponsiblePatientRelationship.objects.create(
            responsible=self.responsible, patient=minor,
            relationship_type=ResponsiblePatientRelationship.RelationType.MADRE,
            status=ResponsiblePatientRelationship.Status.ACTIVE,
        )
        start_at, end_at = self._slot(hour=10)
        hold = hold_service.create_hold(
            actor=self.responsible.person.user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        with self.captureOnCommitCallbacks(execute=True):
            appointment = appointment_service.create_appointment_from_hold(
                actor=self.responsible.person.user, hold=hold, patient=minor,
                doctor=self.doctor, clinic=self.clinic,
            )
        recipients = set(
            Notification.objects.filter(
                event_type=Notification.EventType.APPOINTMENT_CREATED, resource_id=appointment.pk,
            ).values_list("recipient_user_id", flat=True)
        )
        self.assertNotIn(None, recipients)
        self.assertIn(self.responsible.person.user_id, recipients)


class ReminderSchedulingTests(NotificationServiceTestCase):
    """F6-D02."""

    def test_reminders_created_only_for_patient_and_responsible_not_doctor(self):
        appointment = self._book()
        reminders = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER, resource_id=appointment.pk,
        )
        recipients = set(reminders.values_list("recipient_user_id", flat=True))
        self.assertIn(self.patient_user.pk, recipients)
        self.assertIn(self.responsible.person.user_id, recipients)
        self.assertNotIn(self.doctor_user.pk, recipients)

    def test_four_windows_used_when_appointment_far_enough(self):
        appointment = self._book()
        offsets = sorted(w.offset_days for w in ReminderWindow.objects.filter(is_active=True))
        self.assertEqual(offsets, [1, 5, 10, 15])
        reminder_count_for_patient = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).count()
        self.assertEqual(reminder_count_for_patient, 4)

    def test_windows_that_already_elapsed_are_not_scheduled(self):
        # La cita está a `_future_date()` (20 días) por defecto en setUp,
        # pero aquí se reserva una cita a solo 3 días — únicamente la
        # ventana de 1 día cabe.
        near_day = (dj_timezone.now() + timedelta(days=3)).date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=near_day, start_time=time(9, 0), end_time=time(13, 0),
        )
        start_at = availability_service.combine_local(near_day, time(9, 0), self.clinic)
        end_at = start_at + timedelta(minutes=30)
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        with self.captureOnCommitCallbacks(execute=True):
            appointment = appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )
        reminder_count = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).count()
        self.assertEqual(reminder_count, 1)


class CancellationAndRescheduleTests(NotificationServiceTestCase):
    def test_cancellation_notifies_and_cancels_pending_reminders(self):
        appointment = self._book()
        with self.captureOnCommitCallbacks(execute=True):
            appointment_service.cancel_appointment(
                actor=self.patient_user, appointment=appointment,
                reason=RequestReason.PATIENT_REQUEST,
            )
        cancelled_notif = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CANCELLED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        self.assertIsNotNone(cancelled_notif)
        remaining_pending_reminders = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, status=Notification.Status.PENDING,
        )
        self.assertFalse(remaining_pending_reminders.exists())

    def test_reschedule_notifies_with_distinct_dedupe_key_and_recomputes_reminders(self):
        appointment = self._book()
        original_reminder = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
            dedupe_key__endswith=":1",
        ).first()
        original_scheduled_for = original_reminder.scheduled_for

        new_day = (dj_timezone.now() + timedelta(days=25)).date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=new_day, start_time=time(9, 0), end_time=time(13, 0),
        )
        new_start_at = availability_service.combine_local(new_day, time(9, 0), self.clinic)
        with self.captureOnCommitCallbacks(execute=True):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )

        modified_notifs = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_MODIFIED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        )
        self.assertEqual(modified_notifs.count(), 1)

        original_reminder.refresh_from_db()
        self.assertNotEqual(original_reminder.scheduled_for, original_scheduled_for)


class ReminderWindowReconfigurationTests(NotificationServiceTestCase):
    """PD-004 (prompt 1/4, corrección funcional post-implementación,
    C-019): "nueva configuración de ReminderWindow aplica a nuevas citas y
    a citas reprogramadas posteriormente" — sin reconciliación retroactiva
    global de citas ya existentes que no se reprogramen."""

    def _reconfigure(self, offsets):
        ReminderWindow.objects.update(is_active=False)
        for offset in offsets:
            ReminderWindow.objects.update_or_create(
                offset_days=offset, defaults={"is_active": True}
            )

    def _book_days_ahead(self, days_ahead):
        day = (dj_timezone.now() + timedelta(days=days_ahead)).date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=day, start_time=time(9, 0), end_time=time(13, 0),
        )
        start_at = availability_service.combine_local(day, time(9, 0), self.clinic)
        end_at = start_at + timedelta(minutes=30)
        hold = hold_service.create_hold(
            actor=self.patient_user, doctor=self.doctor, clinic=self.clinic,
            start_at=start_at, end_at=end_at,
        )
        with self.captureOnCommitCallbacks(execute=True):
            appointment = appointment_service.create_appointment_from_hold(
                actor=self.patient_user, hold=hold, patient=self.patient,
                doctor=self.doctor, clinic=self.clinic,
            )
        return appointment

    def _reschedule(self, appointment, days_ahead):
        new_day = (dj_timezone.now() + timedelta(days=days_ahead)).date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=new_day, start_time=time(9, 0), end_time=time(13, 0),
        )
        new_start_at = availability_service.combine_local(new_day, time(9, 0), self.clinic)
        with self.captureOnCommitCallbacks(execute=True):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )
        appointment.refresh_from_db()
        return appointment

    def _reminder_offsets(self, appointment, user, statuses=None):
        qs = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=user,
        )
        if statuses is not None:
            qs = qs.filter(status__in=statuses)
        else:
            qs = qs.exclude(status=Notification.Status.CANCELLED)
        return {int(dk.rsplit(":", 1)[-1]) for dk in qs.values_list("dedupe_key", flat=True)}

    def test_case1_default_config_creates_reminders_matching_active_offsets(self):
        appointment = self._book_days_ahead(40)
        self.assertEqual(self._reminder_offsets(appointment, self.patient_user), {15, 10, 5, 1})

    def test_case2_new_appointment_uses_config_active_at_creation(self):
        self._reconfigure([20, 10, 3, 1])
        appointment = self._book_days_ahead(40)
        self.assertEqual(self._reminder_offsets(appointment, self.patient_user), {20, 10, 3, 1})

    def test_case3_reschedule_applies_config_changed_after_original_booking(self):
        appointment = self._book_days_ahead(40)  # config vigente: 15/10/5/1
        self.assertEqual(self._reminder_offsets(appointment, self.patient_user), {15, 10, 5, 1})

        self._reconfigure([20, 10, 3, 1])
        appointment = self._reschedule(appointment, days_ahead=45)

        self.assertEqual(self._reminder_offsets(appointment, self.patient_user), {20, 10, 3, 1})
        # Los offsets que dejaron de estar activos (15, 5) quedan
        # cancelados explícitamente, no simplemente huérfanos.
        cancelled = self._reminder_offsets(
            appointment, self.patient_user, statuses=[Notification.Status.CANCELLED]
        )
        self.assertEqual(cancelled, {15, 5})
        cancelled_rows = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
            status=Notification.Status.CANCELLED, dedupe_key__endswith=":15",
        )
        self.assertEqual(
            cancelled_rows.first().reason_code, "REMINDER_WINDOW_NO_LONGER_ACTIVE"
        )

    def test_case4_repeated_reschedule_does_not_duplicate_notifications(self):
        appointment = self._book_days_ahead(40)
        self._reconfigure([20, 10, 3, 1])
        appointment = self._reschedule(appointment, days_ahead=45)
        count_after_first = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER, resource_id=appointment.pk,
        ).count()

        appointment = self._reschedule(appointment, days_ahead=50)
        count_after_second = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER, resource_id=appointment.pk,
        ).count()

        self.assertEqual(count_after_first, count_after_second)
        self.assertEqual(self._reminder_offsets(appointment, self.patient_user), {20, 10, 3, 1})

    def test_case5_sent_and_sending_reminders_are_never_touched_failed_follows_active_config(self):
        appointment = self._book_days_ahead(40)  # config vigente: 15/10/5/1

        sent = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
            dedupe_key__endswith=":1",
        ).first()
        sent.status = Notification.Status.SENT
        sent.sent_at = dj_timezone.now()
        sent.save(update_fields=["status", "sent_at"])
        sent_scheduled_before = sent.scheduled_for

        sending = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
            dedupe_key__endswith=":5",
        ).first()
        sending.status = Notification.Status.SENDING
        sending.save(update_fields=["status"])
        sending_scheduled_before = sending.scheduled_for

        failed = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
            dedupe_key__endswith=":10",
        ).first()
        failed.status = Notification.Status.FAILED
        failed.attempt_count = 1
        failed.save(update_fields=["status", "attempt_count"])
        failed_scheduled_before = failed.scheduled_for

        # Offset 5 (de la fila SENDING) deja de estar activo en la nueva
        # configuración — si la reprogramación tocara SENDING, aquí se
        # notaría.
        self._reconfigure([20, 10, 3, 1])
        appointment = self._reschedule(appointment, days_ahead=45)

        sent.refresh_from_db()
        self.assertEqual(sent.status, Notification.Status.SENT)
        self.assertEqual(sent.scheduled_for, sent_scheduled_before)

        sending.refresh_from_db()
        self.assertEqual(sending.status, Notification.Status.SENDING)
        self.assertEqual(sending.scheduled_for, sending_scheduled_before)
        self.assertEqual(sending.reason_code, "")

        failed.refresh_from_db()
        self.assertEqual(failed.status, Notification.Status.FAILED)  # sigue elegible, no reenviado aquí
        self.assertNotEqual(failed.scheduled_for, failed_scheduled_before)  # recalculado (offset 10 sigue activo)

    def test_case6_exhausted_reminder_is_not_reactivated_by_reschedule(self):
        appointment = self._book_days_ahead(40)  # config sin cambios: 15/10/5/1
        exhausted = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
            dedupe_key__endswith=":10",
        ).first()
        exhausted.status = Notification.Status.FAILED
        exhausted.attempt_count = notification_service.MAX_DELIVERY_ATTEMPTS
        exhausted.reason_code = "MAX_ATTEMPTS_EXCEEDED:TRANSPORT_ERROR"
        exhausted.save(update_fields=["status", "attempt_count", "reason_code"])
        scheduled_before = exhausted.scheduled_for

        self._reschedule(appointment, days_ahead=45)

        exhausted.refresh_from_db()
        self.assertEqual(exhausted.status, Notification.Status.FAILED)
        self.assertEqual(exhausted.scheduled_for, scheduled_before)
        self.assertEqual(exhausted.attempt_count, notification_service.MAX_DELIVERY_ATTEMPTS)
        self.assertEqual(exhausted.reason_code, "MAX_ATTEMPTS_EXCEEDED:TRANSPORT_ERROR")


class ProcessDueNotificationsTests(NotificationServiceTestCase):
    def test_reminder_skipped_when_appointment_no_longer_scheduled(self):
        appointment = self._book()
        reminder = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        # Fuerza la elegibilidad temporal sin pasar por reschedule/cancel
        # (evita disparar de nuevo el flujo completo de señales).
        reminder.scheduled_for = dj_timezone.now() - timedelta(minutes=1)
        reminder.save(update_fields=["scheduled_for"])
        Appointment.objects.filter(pk=appointment.pk).update(
            status=Appointment.Status.CANCELLED,
            cancelled_at=dj_timezone.now(),
            cancelled_by=self.patient_user,
            cancellation_reason=RequestReason.PATIENT_REQUEST,
        )

        result = notification_service.process_due_notifications()

        reminder.refresh_from_db()
        self.assertEqual(reminder.status, Notification.Status.CANCELLED)
        self.assertEqual(result["skipped"], 1)

    def test_reminder_skipped_when_recipient_relationship_revoked(self):
        appointment = self._book()
        reminder = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.responsible.person.user,
        ).first()
        reminder.scheduled_for = dj_timezone.now() - timedelta(minutes=1)
        reminder.save(update_fields=["scheduled_for"])
        ResponsiblePatientRelationship.objects.filter(
            responsible=self.responsible, patient=self.patient
        ).update(
            status=ResponsiblePatientRelationship.Status.INACTIVE,
            deactivated_at=dj_timezone.now(),
            deactivation_reason=ResponsiblePatientRelationship.DeactivationReason.OTHER,
        )

        notification_service.process_due_notifications()

        reminder.refresh_from_db()
        self.assertEqual(reminder.status, Notification.Status.CANCELLED)

    def test_due_reminder_is_sent(self):
        appointment = self._book()
        reminder = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        reminder.scheduled_for = dj_timezone.now() - timedelta(minutes=1)
        reminder.save(update_fields=["scheduled_for"])

        result = notification_service.process_due_notifications()

        reminder.refresh_from_db()
        self.assertEqual(reminder.status, Notification.Status.SENT)
        self.assertGreaterEqual(result["sent"], 1)


class NoOptOutTests(TestCase):
    """F6-D03: no debe existir ningún mecanismo de exclusión voluntaria."""

    def test_notification_model_has_no_opt_out_field(self):
        field_names = {f.name for f in Notification._meta.get_fields()}
        opt_out_like = {n for n in field_names if "opt" in n.lower() or "unsubscribe" in n.lower()}
        self.assertEqual(opt_out_like, set())


class EmailContentTests(NotificationServiceTestCase):
    """PD-005: información esencial + enlace, nunca contenido clínico;
    corrección de "Cita confirmada" -> "Cita reservada"."""

    _CLINICAL_TERMS = ["diagnóstico", "receta", "estudio", "padecimiento", "expediente", "nota clínica"]

    def test_created_email_has_essentials_link_and_no_clinical_content(self):
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        subject, message = notification_service._render(notification)
        self.assertNotIn("Cita confirmada", subject)
        self.assertIn("reservada", subject.lower())
        self.assertIn(str(self.doctor), message)
        self.assertIn(self.clinic.name, message)
        self.assertIn(notification_service._appointment_url(appointment), message)
        for term in self._CLINICAL_TERMS:
            self.assertNotIn(term, message.lower())

    def test_cancelled_email_content(self):
        appointment = self._book()
        with self.captureOnCommitCallbacks(execute=True):
            appointment_service.cancel_appointment(
                actor=self.patient_user, appointment=appointment, reason=RequestReason.PATIENT_REQUEST,
            )
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CANCELLED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        subject, message = notification_service._render(notification)
        self.assertIn("cancelada", subject.lower())
        self.assertIn(notification_service._appointment_url(appointment), message)
        for term in self._CLINICAL_TERMS:
            self.assertNotIn(term, message.lower())

    def test_reminder_email_content(self):
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        subject, message = notification_service._render(notification)
        self.assertIn(str(self.doctor), message)
        self.assertIn(notification_service._appointment_url(appointment), message)

    def test_modified_email_content(self):
        """Prompt 4 de la corrección post-implementación: cobertura
        explícita del cuarto tipo de evento (creada/cancelada/recordatorio
        ya estaban cubiertos; modificada no lo estaba)."""
        appointment = self._book()
        new_day = (dj_timezone.now() + timedelta(days=25)).date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=new_day, start_time=time(9, 0), end_time=time(13, 0),
        )
        new_start_at = availability_service.combine_local(new_day, time(9, 0), self.clinic)
        with self.captureOnCommitCallbacks(execute=True):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_MODIFIED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        subject, message = notification_service._render(notification)
        self.assertIn("modificada", subject.lower())
        self.assertIn(str(self.doctor), message)
        self.assertIn(self.clinic.name, message)
        self.assertIn(notification_service._appointment_url(appointment), message)
        for term in self._CLINICAL_TERMS:
            self.assertNotIn(term, message.lower())

    def test_link_points_to_authorization_protected_view_no_bypass(self):
        """Prompt 4, "no bypass de autorización": el enlace del correo
        apunta a la misma vista ya protegida de Agenda (LoginRequiredMixin
        + autorización por objeto) — no crea una ruta nueva sin
        autorización propia."""
        from django.urls import reverse

        appointment = self._book()
        url = notification_service._appointment_url(appointment)
        self.assertIn(reverse("appointments:appointment_detail", args=[appointment.pk]), url)

        anonymous_client = self.client_class()
        response = anonymous_client.get(
            reverse("appointments:appointment_detail", args=[appointment.pk])
        )
        self.assertEqual(response.status_code, 302)  # LoginRequiredMixin redirige a login


class RetryBackoffTests(NotificationServiceTestCase):
    """PD-007 — reintentos limitados + backoff; hallazgos 12.3/12.4/12.5/12.7."""

    def test_failed_attempt_reschedules_with_backoff_not_immediate_retry(self):
        before = dj_timezone.now()
        with mock.patch.object(notification_service._TRANSPORT, "send",
                                return_value=notification_service.TransportResult(ok=False, reason_code="X")):
            appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertEqual(notification.attempt_count, 1)
        self.assertGreater(notification.scheduled_for, before)

    def test_notification_permanently_failed_after_max_attempts(self):
        with mock.patch.object(notification_service._TRANSPORT, "send",
                                return_value=notification_service.TransportResult(ok=False, reason_code="X")):
            appointment = self._book()
            notification = Notification.objects.filter(
                event_type=Notification.EventType.APPOINTMENT_CREATED,
                resource_id=appointment.pk, recipient_user=self.patient_user,
            ).first()
            for _ in range(notification_service.MAX_DELIVERY_ATTEMPTS - 1):
                notification.scheduled_for = dj_timezone.now() - timedelta(seconds=1)
                notification.save(update_fields=["scheduled_for"])
                notification_service._attempt_send(notification)
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertIn("MAX_ATTEMPTS_EXCEEDED", notification.reason_code)
        self.assertEqual(notification.attempt_count, notification_service.MAX_DELIVERY_ATTEMPTS)

    def test_exhausted_notification_is_not_reclaimed_by_process_due_notifications(self):
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        notification.status = Notification.Status.FAILED
        notification.attempt_count = notification_service.MAX_DELIVERY_ATTEMPTS
        notification.scheduled_for = dj_timezone.now() - timedelta(minutes=1)
        notification.reason_code = "MAX_ATTEMPTS_EXCEEDED:X"
        notification.save()

        notification_service.process_due_notifications()

        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertEqual(notification.attempt_count, notification_service.MAX_DELIVERY_ATTEMPTS)

    def test_orphaned_sending_retryable_notification_is_reclaimed(self):
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        # Simula un proceso interrumpido a media ejecución (hallazgo 12.3).
        notification.status = Notification.Status.SENDING
        notification.last_attempt_at = (
            dj_timezone.now() - notification_service.SENDING_LEASE_TIMEOUT - timedelta(minutes=1)
        )
        notification.save(update_fields=["status", "last_attempt_at"])

        result = notification_service.process_due_notifications()

        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertGreaterEqual(result["sent"], 1)

    def test_orphaned_sending_non_retryable_notification_is_closed_without_resend(self):
        notification = Notification.objects.create(
            event_type=Notification.EventType.EMAIL_VERIFICATION,
            recipient_user=self.patient_user, recipient_address=self.patient_user.email,
            scheduled_for=dj_timezone.now(), status=Notification.Status.SENDING,
            attempt_count=1,
            last_attempt_at=dj_timezone.now() - notification_service.SENDING_LEASE_TIMEOUT - timedelta(minutes=1),
        )
        with mock.patch.object(notification_service._TRANSPORT, "send") as mocked_send:
            notification_service.process_due_notifications()
            mocked_send.assert_not_called()
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertEqual(notification.reason_code, "ORPHANED_NON_RETRYABLE_SENDING")

    def test_orphaned_sending_at_max_attempts_is_not_reclaimed_for_another_attempt(self):
        """Regresión (Prompt 1, corrección post-implementación): una fila
        SENDING huérfana que ya alcanzó MAX_DELIVERY_ATTEMPTS en su último
        intento (proceso interrumpido justo tras incrementar attempt_count)
        nunca debe recibir un intento adicional."""
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        notification.status = Notification.Status.SENDING
        notification.attempt_count = notification_service.MAX_DELIVERY_ATTEMPTS
        notification.last_attempt_at = (
            dj_timezone.now() - notification_service.SENDING_LEASE_TIMEOUT - timedelta(minutes=1)
        )
        notification.save(update_fields=["status", "attempt_count", "last_attempt_at"])

        with mock.patch.object(notification_service._TRANSPORT, "send") as mocked_send:
            result = notification_service.process_due_notifications()
            mocked_send.assert_not_called()

        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertIn("MAX_ATTEMPTS_EXCEEDED", notification.reason_code)
        self.assertEqual(notification.attempt_count, notification_service.MAX_DELIVERY_ATTEMPTS)
        self.assertEqual(result["skipped"], 1)

    def test_invalid_recipient_format_fails_permanently_without_waiting_for_max_attempts(self):
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        notification.status = Notification.Status.PENDING
        notification.attempt_count = 0
        notification.recipient_address = "not-an-email"
        notification.save(update_fields=["status", "attempt_count", "recipient_address"])

        notification_service._attempt_send(notification)

        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertTrue(notification.reason_code.startswith("PERMANENT:"))
        self.assertEqual(notification.attempt_count, 1)

    def test_permanently_failed_notification_is_never_reclaimed(self):
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        notification.status = Notification.Status.FAILED
        notification.attempt_count = 1
        notification.reason_code = "PERMANENT:INVALID_RECIPIENT_FORMAT"
        notification.scheduled_for = dj_timezone.now() - timedelta(minutes=1)
        notification.save()

        with mock.patch.object(notification_service._TRANSPORT, "send") as mocked_send:
            notification_service.process_due_notifications()
            mocked_send.assert_not_called()

        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertEqual(notification.attempt_count, 1)

    def test_retry_after_orphan_recovery_does_not_duplicate_notification_row(self):
        """Idempotencia (Prompt 1, §5): recuperar una SENDING huérfana y
        reenviarla con éxito no debe crear una segunda fila de Notification
        ni un segundo intento de correo además del que efectivamente ocurre."""
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        dedupe_key = notification.dedupe_key
        notification.status = Notification.Status.SENDING
        notification.last_attempt_at = (
            dj_timezone.now() - notification_service.SENDING_LEASE_TIMEOUT - timedelta(minutes=1)
        )
        notification.save(update_fields=["status", "last_attempt_at"])

        notification_service.process_due_notifications()

        self.assertEqual(Notification.objects.filter(dedupe_key=dedupe_key).count(), 1)
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertEqual(notification.attempt_count, 2)

    def test_reschedule_recomputes_failed_reminder_with_attempts_remaining(self):
        appointment = self._book()
        reminder = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_REMINDER,
            resource_id=appointment.pk, recipient_user=self.patient_user,
            dedupe_key__endswith=":1",
        ).first()
        reminder.status = Notification.Status.FAILED
        reminder.attempt_count = 1
        reminder.save(update_fields=["status", "attempt_count"])
        original_scheduled_for = reminder.scheduled_for

        new_day = (dj_timezone.now() + timedelta(days=25)).date()
        availability_service.create_availability(
            actor=self.doctor_user, doctor=self.doctor, clinic=self.clinic,
            date=new_day, start_time=time(9, 0), end_time=time(13, 0),
        )
        new_start_at = availability_service.combine_local(new_day, time(9, 0), self.clinic)
        with self.captureOnCommitCallbacks(execute=True):
            appointment_service.reschedule_appointment(
                actor=self.patient_user, appointment=appointment, new_clinic=self.clinic,
                new_start_at=new_start_at, reason=RequestReason.PATIENT_REQUEST,
            )

        reminder.refresh_from_db()
        self.assertNotEqual(reminder.scheduled_for, original_scheduled_for)
        self.assertEqual(reminder.status, Notification.Status.FAILED)  # sigue elegible para reintento

    def test_transport_zero_delivered_is_treated_as_failure(self):
        appointment = self._book()
        notification = Notification.objects.filter(
            event_type=Notification.EventType.APPOINTMENT_CREATED,
            resource_id=appointment.pk, recipient_user=self.patient_user,
        ).first()
        notification.status = Notification.Status.PENDING
        notification.save(update_fields=["status"])
        with mock.patch("notifications.services.send_mail", return_value=0):
            notification_service._attempt_send(notification)
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertEqual(notification.reason_code, "TRANSPORT_ZERO_DELIVERED")

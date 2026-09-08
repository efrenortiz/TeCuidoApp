from datetime import date, timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Invitation, Person, User
from accounts.services import invitations
from doctors.models import Doctor
from patients.models import Patient


def _make_doctor(email):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user, first_name="Doc", last_name_paterno="Tor", birth_date=date(1980, 1, 1)
    )
    return Doctor.objects.create(person=person)


def _make_plain_user(email):
    return User.objects.create_user(email=email, password="s3cure-pass!")


class InvitationCreateViewTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("accounts:invitation_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_authenticated_non_doctor_is_forbidden(self):
        _make_plain_user("nodoctor@example.com")
        self.client.login(username="nodoctor@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("accounts:invitation_create"))
        self.assertEqual(response.status_code, 403)

    def test_doctor_can_create_invitation_and_email_is_sent(self):
        doctor_user = _make_doctor("doctor@example.com").person.user
        self.client.login(username="doctor@example.com", password="s3cure-pass!")

        response = self.client.post(
            reverse("accounts:invitation_create"), {"email": "prospect@example.com"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Invitation.objects.filter(email="prospect@example.com").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("prospect@example.com", mail.outbox[0].to)
        invitation = Invitation.objects.get(email="prospect@example.com")
        self.assertEqual(invitation.doctor.person.user, doctor_user)


class InvitationAcceptViewTests(TestCase):
    def setUp(self):
        self.doctor = _make_doctor("doctor2@example.com")
        self.invitation, self.raw_token = invitations.create_invitation(
            doctor=self.doctor, email="prospect3@example.com"
        )
        self.registration_payload = {
            "password": "s3cure-pass!",
            "password_confirm": "s3cure-pass!",
            "first_name": "Prospect",
            "last_name_paterno": "Three",
            "last_name_materno": "",
            "birth_date": "1998-05-20",
            "sex": Patient.Sex.FEMALE,
        }

    def test_unknown_token_returns_404(self):
        response = self.client.get(
            reverse("accounts:invitation_accept", args=["not-a-real-token"])
        )
        self.assertEqual(response.status_code, 404)

    def test_expired_token_returns_410(self):
        self.invitation.expires_at = timezone.now() - timedelta(hours=1)
        self.invitation.save(update_fields=["expires_at"])
        response = self.client.get(
            reverse("accounts:invitation_accept", args=[self.raw_token])
        )
        self.assertEqual(response.status_code, 410)

    def test_used_token_returns_410(self):
        invitations.accept_invitation(
            self.raw_token,
            password="s3cure-pass!",
            person_data=dict(
                first_name="Prospect", last_name_paterno="Three", birth_date=date(1998, 5, 20)
            ),
            patient_data=dict(sex=Patient.Sex.FEMALE),
        )
        response = self.client.get(
            reverse("accounts:invitation_accept", args=[self.raw_token])
        )
        self.assertEqual(response.status_code, 410)

    def test_valid_registration_creates_patient_and_sends_verification_email(self):
        response = self.client.post(
            reverse("accounts:invitation_accept", args=[self.raw_token]),
            self.registration_payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email="prospect3@example.com").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("prospect3@example.com", mail.outbox[0].to)

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, Invitation.Status.USED)

    def test_mismatched_passwords_are_rejected(self):
        payload = dict(self.registration_payload, password_confirm="different-pass!")
        response = self.client.post(
            reverse("accounts:invitation_accept", args=[self.raw_token]), payload
        )
        self.assertEqual(response.status_code, 200)  # re-renders the form
        self.assertFalse(User.objects.filter(email="prospect3@example.com").exists())

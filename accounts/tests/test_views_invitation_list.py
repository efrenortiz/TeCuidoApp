from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Person, User
from accounts.services import invitations
from doctors.models import Doctor


def _make_doctor(email):
    user = User.objects.create_user(email=email, password="s3cure-pass!")
    person = Person.objects.create(
        user=user, first_name="Doc", last_name_paterno="Tor", birth_date=date(1980, 1, 1)
    )
    return Doctor.objects.create(person=person)


class InvitationListViewTests(TestCase):
    def test_non_doctor_is_forbidden(self):
        User.objects.create_user(email="plain@example.com", password="s3cure-pass!")
        self.client.login(username="plain@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("accounts:invitation_list"))
        self.assertEqual(response.status_code, 403)

    def test_lists_only_this_doctors_invitations(self):
        doctor_a = _make_doctor("doc-a@example.com")
        doctor_b = _make_doctor("doc-b@example.com")
        invitations.create_invitation(doctor=doctor_a, email="prospect-a@example.com")
        invitations.create_invitation(doctor=doctor_b, email="prospect-b@example.com")

        self.client.login(username="doc-a@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("accounts:invitation_list"))

        self.assertContains(response, "prospect-a@example.com")
        self.assertNotContains(response, "prospect-b@example.com")

    def test_empty_state_when_no_invitations(self):
        _make_doctor("doc-c@example.com")
        self.client.login(username="doc-c@example.com", password="s3cure-pass!")
        response = self.client.get(reverse("accounts:invitation_list"))
        self.assertContains(response, "No hay invitaciones todavía")

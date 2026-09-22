from datetime import date

from django.test import Client, TestCase

from accounts.models import PolicyAcceptance, User
from accounts.services import consent as consent_service


class ConsentServiceTests(TestCase):
    """F6-D04 (docs/design/phase-6-consent-domain.md, phase-6-consent-service-contracts.md)."""

    def setUp(self):
        self.user = User.objects.create_user(email="consent@example.com", password="s3cure-pass!")

    def test_record_acceptance_creates_row_with_server_timestamp(self):
        acceptance = consent_service.record_acceptance(
            user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE, policy_version="1.0",
        )
        self.assertIsNotNone(acceptance.accepted_at)
        self.assertEqual(acceptance.user_id, self.user.pk)

    def test_repeated_acceptance_of_same_version_is_idempotent(self):
        first = consent_service.record_acceptance(
            user=self.user, policy_type=PolicyAcceptance.PolicyType.TERMS_AND_CONDITIONS, policy_version="1.0",
        )
        second = consent_service.record_acceptance(
            user=self.user, policy_type=PolicyAcceptance.PolicyType.TERMS_AND_CONDITIONS, policy_version="1.0",
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            PolicyAcceptance.objects.filter(
                user=self.user, policy_type=PolicyAcceptance.PolicyType.TERMS_AND_CONDITIONS,
            ).count(),
            1,
        )

    def test_unknown_version_is_rejected(self):
        with self.assertRaises(consent_service.UnknownPolicyVersion):
            consent_service.record_acceptance(
                user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE, policy_version="99.0",
            )
        self.assertFalse(PolicyAcceptance.objects.filter(user=self.user).exists())

    def test_unknown_policy_type_is_rejected(self):
        with self.assertRaises(consent_service.UnknownPolicyType):
            consent_service.record_acceptance(user=self.user, policy_type="MARKETING_CONSENT", policy_version="1.0")

    def test_has_accepted_version(self):
        self.assertFalse(
            consent_service.has_accepted_version(
                user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE, policy_version="1.0",
            )
        )
        consent_service.record_acceptance(
            user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE, policy_version="1.0",
        )
        self.assertTrue(
            consent_service.has_accepted_version(
                user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE, policy_version="1.0",
            )
        )

    def test_no_write_to_a_new_version_overwrites_previous(self):
        consent_service.CURRENT_POLICY_VERSIONS[PolicyAcceptance.PolicyType.PRIVACY_NOTICE] = "1.0"
        first = consent_service.record_acceptance(
            user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE, policy_version="1.0",
        )
        # Simula publicación de una nueva versión vigente.
        consent_service.CURRENT_POLICY_VERSIONS[PolicyAcceptance.PolicyType.PRIVACY_NOTICE] = "2.0"
        try:
            second = consent_service.record_acceptance(
                user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE, policy_version="2.0",
            )
            self.assertNotEqual(first.pk, second.pk)
            self.assertEqual(
                PolicyAcceptance.objects.filter(
                    user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE,
                ).count(),
                2,
            )
            first.refresh_from_db()
            self.assertEqual(first.policy_version, "1.0")
        finally:
            consent_service.CURRENT_POLICY_VERSIONS[PolicyAcceptance.PolicyType.PRIVACY_NOTICE] = "1.0"


class ConsentApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="consent-api@example.com", password="s3cure-pass!", email_verified=True,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_accept_endpoint_requires_authentication(self):
        anon = Client()
        response = anon.post(
            "/api/v1/consent/accept/",
            data={"policy_type": "PRIVACY_NOTICE", "policy_version": "1.0"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_accept_endpoint_ignores_client_supplied_user_and_timestamp(self):
        response = self.client.post(
            "/api/v1/consent/accept/",
            data={
                "policy_type": "PRIVACY_NOTICE", "policy_version": "1.0",
                "user": 999, "accepted_at": "2000-01-01T00:00:00Z",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        acceptance = PolicyAcceptance.objects.get(user=self.user, policy_type="PRIVACY_NOTICE")
        self.assertNotEqual(acceptance.accepted_at.date(), date(2000, 1, 1))

    def test_status_endpoint_reflects_pending_and_accepted(self):
        """PD-006: el estado incluye versión vigente, referencia canónica y
        fecha de aceptación — no solo un booleano."""
        response = self.client.get("/api/v1/consent/status/")
        self.assertEqual(response.status_code, 200)
        body = response.json()["PRIVACY_NOTICE"]
        self.assertFalse(body["accepted"])
        self.assertEqual(body["version"], "1.0")
        self.assertIsNone(body["accepted_at"])

        self.client.post(
            "/api/v1/consent/accept/",
            data={"policy_type": "PRIVACY_NOTICE", "policy_version": "1.0"},
            content_type="application/json",
        )
        response = self.client.get("/api/v1/consent/status/")
        body = response.json()["PRIVACY_NOTICE"]
        self.assertTrue(body["accepted"])
        self.assertIsNotNone(body["accepted_at"])

    def test_acceptance_trace_answers_the_five_pd006_questions(self):
        """PD-006: qué documento, qué versión, cuándo, quién, dónde publicada."""
        consent_service.record_acceptance(
            user=self.user, policy_type=PolicyAcceptance.PolicyType.TERMS_AND_CONDITIONS,
            policy_version="1.0",
        )
        trace = consent_service.acceptance_trace(
            user=self.user, policy_type=PolicyAcceptance.PolicyType.TERMS_AND_CONDITIONS,
            policy_version="1.0",
        )
        self.assertEqual(trace["policy_type"], PolicyAcceptance.PolicyType.TERMS_AND_CONDITIONS)
        self.assertEqual(trace["policy_version"], "1.0")
        self.assertEqual(trace["user_id"], self.user.pk)
        self.assertIsNotNone(trace["accepted_at"])
        self.assertIn("document_url", trace)

    def test_acceptance_trace_none_when_never_accepted(self):
        trace = consent_service.acceptance_trace(
            user=self.user, policy_type=PolicyAcceptance.PolicyType.PRIVACY_NOTICE, policy_version="1.0",
        )
        self.assertIsNone(trace)

    def test_no_cache_headers(self):
        response = self.client.get("/api/v1/consent/status/")
        self.assertEqual(response["Cache-Control"], "no-store")

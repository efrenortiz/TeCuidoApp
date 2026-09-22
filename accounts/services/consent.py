"""ConsentService (docs/design/phase-6-consent-service-contracts.md, F6-D04).

ITD-009 (docs/phases/phase-6-implementation-summary.md): Fase 6 no crea un
CMS de documentos legales (consent-domain.md §5: "no decide qué documento es
jurídicamente obligatorio ni qué texto debe contener"). "Impedir aceptar una
versión inexistente" (consent-domain.md §6) se satisface con un registro
mínimo, a nivel de código, de la versión vigente por tipo de documento — no
con un modelo de versionado de contenido completo, que no está justificado
por ninguna fuente superior."""

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone as dj_timezone

from accounts.models import PolicyAcceptance

# Única versión vigente aceptable por tipo de documento. Cambiar este valor
# es una decisión de producto/legal (nuevo texto publicado), no técnica —
# ver docs/phases/phase-6-implementation-summary.md PD sobre versiones
# futuras si se requiere un catálogo editable.
CURRENT_POLICY_VERSIONS = {
    PolicyAcceptance.PolicyType.PRIVACY_NOTICE: "1.0",
    PolicyAcceptance.PolicyType.TERMS_AND_CONDITIONS: "1.0",
}


def document_url(policy_type, policy_version):
    """PD-006: referencia estable hacia dónde estaba publicada esa versión
    (settings.LEGAL_DOCUMENT_URLS) — funciona también para una versión ya
    superada por una posterior, no solo la vigente, para que una aceptación
    histórica siga siendo trazable a su publicación original."""
    return settings.LEGAL_DOCUMENT_URLS.get(policy_type, {}).get(policy_version, "")


class ConsentError(Exception):
    pass


class UnknownPolicyType(ConsentError):
    pass


class UnknownPolicyVersion(ConsentError):
    pass


def _validate_policy(policy_type, policy_version):
    if policy_type not in CURRENT_POLICY_VERSIONS:
        raise UnknownPolicyType(policy_type)
    if policy_version != CURRENT_POLICY_VERSIONS[policy_type]:
        raise UnknownPolicyVersion(policy_version)


def record_acceptance(*, user, policy_type, policy_version):
    """docs/design/phase-6-consent-service-contracts.md §1/§4 — idempotente
    por `UNIQUE(user, policy_type, policy_version)` (get_or_create, mismo
    patrón que `medical_records.services.record.get_or_create_for_patient`)."""
    _validate_policy(policy_type, policy_version)
    try:
        with transaction.atomic():
            acceptance, _created = PolicyAcceptance.objects.get_or_create(
                user=user, policy_type=policy_type, policy_version=policy_version,
            )
    except IntegrityError:
        # Carrera concurrente perdida contra una creación idéntica.
        acceptance = PolicyAcceptance.objects.get(
            user=user, policy_type=policy_type, policy_version=policy_version
        )
    return acceptance


def get_current_acceptance(*, user, policy_type):
    """docs/design/phase-6-consent-service-contracts.md §2 — la aceptación
    de la versión vigente para este usuario, o `None`."""
    current_version = CURRENT_POLICY_VERSIONS.get(policy_type)
    if current_version is None:
        raise UnknownPolicyType(policy_type)
    return PolicyAcceptance.objects.filter(
        user=user, policy_type=policy_type, policy_version=current_version
    ).first()


def has_accepted_version(*, user, policy_type, policy_version):
    """docs/design/phase-6-consent-service-contracts.md §3."""
    return PolicyAcceptance.objects.filter(
        user=user, policy_type=policy_type, policy_version=policy_version
    ).exists()


def acceptance_status(*, user):
    """Resumen para la pantalla de aceptación (docs/design/phase-6-screens.md §1):
    qué documentos de plataforma tienen su versión vigente aceptada, con la
    versión vigente y su referencia canónica (PD-006) para que la UI pueda
    mostrarla sin una segunda consulta."""
    status = {}
    for policy_type, current_version in CURRENT_POLICY_VERSIONS.items():
        acceptance = get_current_acceptance(user=user, policy_type=policy_type)
        status[policy_type] = {
            "accepted": acceptance is not None,
            "version": current_version,
            "document_url": document_url(policy_type, current_version),
            "accepted_at": acceptance.accepted_at.isoformat() if acceptance else None,
        }
    return status


def acceptance_trace(*, user, policy_type, policy_version):
    """PD-006 — responde explícitamente las cinco preguntas exigidas:
    qué documento, qué versión, cuándo, quién y dónde estaba publicada esa
    versión. Devuelve `None` si esa combinación nunca fue aceptada."""
    acceptance = PolicyAcceptance.objects.filter(
        user=user, policy_type=policy_type, policy_version=policy_version
    ).first()
    if acceptance is None:
        return None
    return {
        "policy_type": acceptance.policy_type,
        "policy_version": acceptance.policy_version,
        "accepted_at": acceptance.accepted_at.isoformat(),
        "user_id": acceptance.user_id,
        "document_url": document_url(acceptance.policy_type, acceptance.policy_version),
    }

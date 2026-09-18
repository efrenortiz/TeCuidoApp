"""Domain error taxonomy for `CareRequest` (docs/design/care-request-error-catalog.md).
Deliberadamente pequeña: la mayoría de los fallos de esta operación son
excepciones ya existentes de Agenda (`appointments.services.exceptions`) que
se propagan sin traducirse — ver `care-request-service-contracts.md` §10."""


class CareRequestError(Exception):
    """Base para todo error de dominio de `CareRequest`."""


class CareRequestNotFound(CareRequestError):
    """La `CareRequest` no existe o no debe revelarse al actor."""


class CareRequestPermissionDenied(CareRequestError):
    """El actor no está autorizado para esta operación de `CareRequest`.
    Cubre las dos reglas de autorización propias de `_resolve_patient()`
    (`docs/design/care-request-permissions.md` §2-4): un paciente que
    envía un `patient_id` distinto de su propio registro, o un responsable
    sin una `ResponsiblePatientRelationship` `ACTIVE` con el paciente
    objetivo — esta segunda regla se valida aquí explícitamente
    (corrección 2026-09-17, `phase-5-final-report.md` §30/H3) y ya no se
    deja caer, por accidente, en el rechazo posterior de Agenda
    (`NotAuthorized`/`InvalidPatient`). Médico/consultorio válidos siguen
    siendo responsabilidad exclusiva de `HoldService`/`AppointmentService`,
    sin duplicarse aquí."""


class CareRequestConflict(CareRequestError):
    """Misma `Idempotency-Key` reutilizada para una intención distinta."""


class CareRequestRateLimitExceeded(CareRequestError):
    """El actor ya alcanzó el máximo de `CareRequest` permitidas en la
    ventana móvil de una hora (`requirements.md` §12.3)."""


class CareRequestValidationError(CareRequestError):
    """Datos de entrada inválidos que no corresponden a una regla de
    Agenda ni de `ClinicalDocument` (p. ej. campos obligatorios ausentes)."""

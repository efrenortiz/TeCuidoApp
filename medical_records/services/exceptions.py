"""Domain error taxonomy for the clinical domain
(docs/design/clinical-service-contracts.md §19). Views/API translate
these to HTTP responses — they never leak PostgreSQL/Django internals to
the client (SC-146)."""


class ClinicalError(Exception):
    """Base for every clinical domain error (SC-130)."""


class ClinicalNotFound(ClinicalError):
    """SC-131 — recurso clínico inexistente, o existente pero no
    accesible al actor (SC-068/SC-147: nunca se distingue la una de la
    otra en la respuesta, para no revelar existencia indebidamente)."""


class ClinicalNotAuthorized(ClinicalError):
    """SC-132 — el actor está identificado pero no autorizado para la
    operación (a diferencia de `ClinicalNotFound`, que cubre lectura no
    autorizada de un recurso cuya existencia no debe confirmarse)."""


class EncounterNotStartable(ClinicalError):
    """SC-133 — la `Appointment` no cumple las precondiciones de inicio
    (no está `SCHEDULED`, o está `CANCELLED`/`NO_SHOW`/`COMPLETED`)."""


class EncounterAlreadyStarted(ClinicalError):
    """SC-134 — reservada para un caso que no pueda tratarse
    idempotentemente; el segundo intento normal de inicio es idempotente
    (SC-022/SC-029) y no debe usar esta excepción."""


class EncounterNotInProgress(ClinicalError):
    """SC-135 — la operación requiere un encuentro `IN_PROGRESS`."""


class EncounterAlreadyCompleted(ClinicalError):
    """SC-136 — el encuentro ya está `COMPLETED` y la solicitud intenta
    una mutación con contenido distinto al ya persistido (ver SC-065:
    una repetición exacta sin cambios es éxito idempotente, no este
    error)."""


class IncompleteClinicalContent(ClinicalError):
    """SC-137 — uno o más de los cinco campos obligatorios está vacío o
    ausente al intentar completar. Transporta la lista completa de campos
    afectados (no solo el primero) para que la API pueda reportarlos todos
    de una vez (clinical-api-contracts.md API-103: `details.fields`)."""

    def __init__(self, fields):
        self.fields = list(fields)
        super().__init__(f"Campos obligatorios ausentes: {self.fields}")


class ClinicalContentPlaceholder(ClinicalError):
    """SC-137a — uno o más campos obligatorios contiene un valor de
    relleno reconocido (N/A, No aplica, Sin datos, etc.), distinguible de
    `IncompleteClinicalContent` para que la API mapee cada caso a su
    propio código HTTP (REQUIRED_CLINICAL_CONTENT vs
    INVALID_PLACEHOLDER_CONTENT). Transporta la lista completa de campos
    con placeholder (API-103)."""

    def __init__(self, fields):
        self.fields = list(fields)
        super().__init__(f"Campos con contenido de relleno inválido: {self.fields}")


class InvalidClinicalData(ClinicalError):
    """SC-138 — el payload viola una regla estructural (campos no
    permitidos, tipo inválido, intento de modificar identidad
    estructural)."""


class EncounterAppointmentMismatch(ClinicalError):
    """SC-139 — la cita y el encuentro presentan una identidad
    incompatible; tratado como inconsistencia de integridad, nunca como
    autorización para reasignar (clinical-encounter-rules.md §20)."""


class ClinicalRecordNotFound(ClinicalError):
    """SC-140 — no existe `MedicalRecord` cuando la operación exige uno
    ya creado (una lectura simple nunca lo crea — ver D-005)."""


class ClinicalRecordIntegrityError(ClinicalError):
    """SC-141 — la estructura del expediente no cumple sus invariantes."""


class ClinicalConcurrencyError(ClinicalError):
    """SC-142 — se detectó una carrera que no pudo resolverse de forma
    segura mediante los mecanismos normales de idempotencia."""


class ClinicalAuditError(ClinicalError):
    """SC-143 — reservada para cuando una política explícita futura
    convierta el registro exitoso de auditoría en condición de la
    operación; no se usa en Etapa 2."""

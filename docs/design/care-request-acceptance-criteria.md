# CareRequest — Acceptance Criteria

## Purpose

Define observable acceptance criteria for Fase 5. These criteria are derived from the approved design and do not add new functionality.

## Creation

- An authenticated patient can create a CareRequest for themselves.
- An authorized responsible can create a CareRequest for a valid patient relationship.
- The request requires a doctor, clinic/context, selected slot, and `motivo`.
- `padecimiento` and `descripcion` are optional free text.
- The selected slot provides `start_at` and `end_at`.

## Conversion

- A valid request creates one Hold through Agenda.
- A valid Hold is converted to one Appointment through the existing Appointment service.
- The resulting Appointment is associated through `CareRequest.appointment`.
- ClinicalDocuments created by the request are associated with the resulting Appointment.
- A successful operation finishes with `CareRequest = CONVERTIDA`.

## Atomicity

- A failure anywhere in the operation leaves no persisted CareRequest, Hold, or Appointment from that attempt.
- A `CONVERTIDA` CareRequest always has its Appointment relation.
- Database rollback is followed by synchronous filesystem compensation for files created by the failed execution.

## Idempotency

- A request with a new `Idempotency-Key` executes normally.
- A replay with the same actor and key returns the original committed result.
- Reuse of the key for a conflicting operation is rejected.
- Concurrent requests with the same actor/key result in one logical operation.
- A failed transaction does not permanently reserve the key.
- The CareRequest key is not copied literally into the Appointment namespace.

## Rate limiting

- An actor may create at most 3 CareRequests in a rolling one-hour window.
- A valid idempotent replay is resolved before the creation rate limit.
- The implementation uses PostgreSQL and no external rate-limit infrastructure.

## Attachments

- At most 5 files can be submitted.
- Only PDF, JPEG, and PNG are accepted.
- Each file is limited to 10 MB.
- Files reuse ClinicalDocument infrastructure.
- No antivirus subsystem is part of Fase 5.

## Scope

- No waiting-room/check-in workflow exists in Fase 5.
- No independent CareRequest editing exists in Fase 5.
- No automated diagnosis, triage, or recommendation is produced.

## API

- Authentication is required.
- Authorization is enforced server-side.
- Successful creation returns the approved CareRequest result DTO.
- API errors follow existing project serialization conventions.

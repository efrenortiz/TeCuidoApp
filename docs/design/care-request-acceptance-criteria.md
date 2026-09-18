# CareRequest — Acceptance Criteria

## Purpose

Define observable acceptance criteria for Fase 5. These criteria are derived from the approved design and do not add new functionality.

Each bullet carries a stable ID (`AC-<group><n>`), added 2026-09-18 so the traceability tables
in `docs/phases/phase-5-final-report.md` can cite a real, checkable identifier instead of an
identifier that existed only in the report. The IDs are labels for review/traceability; they add
no new criteria and change no existing one.

## Creation

- **AC-C1.** An authenticated patient can create a CareRequest for themselves.
- **AC-C2.** An authorized responsible can create a CareRequest for a valid patient relationship.
- **AC-C3.** The request requires a doctor, clinic/context, selected slot, and `motivo`.
- **AC-C4.** `padecimiento` and `descripcion` are optional free text.
- **AC-C5.** The selected slot provides `start_at` and `end_at`.

## Conversion

- **AC-V1.** A valid request creates one Hold through Agenda.
- **AC-V2.** A valid Hold is converted to one Appointment through the existing Appointment service.
- **AC-V3.** The resulting Appointment is associated through `CareRequest.appointment`.
- **AC-V4.** ClinicalDocuments created by the request are associated with the resulting Appointment.
- **AC-V5.** A successful operation finishes with `CareRequest = CONVERTIDA`.

## Atomicity

- **AC-A1.** A failure anywhere in the operation leaves no persisted CareRequest, Hold, or Appointment from that attempt.
- **AC-A2.** A `CONVERTIDA` CareRequest always has its Appointment relation.
- **AC-A3.** Database rollback is followed by synchronous filesystem compensation for files created by the failed execution.

## Idempotency

- **AC-I1.** A request with a new `Idempotency-Key` executes normally.
- **AC-I2.** A replay with the same actor and key returns the original committed result.
- **AC-I3.** Reuse of the key for a conflicting operation is rejected.
- **AC-I4.** Concurrent requests with the same actor/key result in one logical operation.
- **AC-I5.** A failed transaction does not permanently reserve the key.
- **AC-I6.** The CareRequest key is not copied literally into the Appointment namespace.

## Rate limiting

- **AC-R1.** An actor may create at most 3 CareRequests in a rolling one-hour window.
- **AC-R2.** A valid idempotent replay is resolved before the creation rate limit.
- **AC-R3.** The implementation uses PostgreSQL and no external rate-limit infrastructure.

## Attachments

- **AC-F1.** At most 5 files can be submitted.
- **AC-F2.** Only PDF, JPEG, and PNG are accepted.
- **AC-F3.** Each file is limited to 10 MB.
- **AC-F4.** Files reuse ClinicalDocument infrastructure.
- **AC-F5.** No antivirus subsystem is part of Fase 5.

## Scope

- **AC-S1.** No waiting-room/check-in workflow exists in Fase 5.
- **AC-S2.** No independent CareRequest editing exists in Fase 5.
- **AC-S3.** No automated diagnosis, triage, or recommendation is produced.

## API

- **AC-P1.** Authentication is required.
- **AC-P2.** Authorization is enforced server-side.
- **AC-P3.** Successful creation returns the approved CareRequest result DTO.
- **AC-P4.** API errors follow existing project serialization conventions.

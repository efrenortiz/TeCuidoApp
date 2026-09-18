# CareRequest — Audit and History Design

## 1. Purpose

Define the audit expectations for CareRequest while reusing the existing project's audit mechanisms.

This document does not create a new audit subsystem.

## 2. Audit boundary

Audit the meaningful security and lifecycle events already supported by the project, including:

- CareRequest creation attempt outcome when an auditable event is appropriate;
- successful transition `NUEVA → CONVERTIDA`;
- authorization failures when existing mechanisms record them;
- idempotency conflict;
- rate-limit rejection;
- attachment-related security/validation failures where existing audit conventions apply.

Use the project's established audit event conventions.

**Explicitly out of scope for Fase 5 (2026-09-18 scope decision):** auditing an administrator's
*read* access via `CareRequestAdmin` to `motivo`/`padecimiento`/`descripcion`. This is a real,
pre-existing project requirement (`requirements.md` §62, ADR-004 §8/§26) — not disputed — but no
reusable mechanism exists anywhere in the project to audit a `ModelAdmin` read (verified: none of
`ClinicalEncounterAdmin`/`MedicalRecordAdmin`/`PrescriptionAdmin`/`StudyOrderAdmin`/
`ClinicalDocumentAdmin` do this either), and building one ad hoc for `CareRequest` alone would be
an isolated exception, not a fix for the actual (project-wide) gap. Deferred to Fase 6
(Notificaciones y auditoría, per `CLAUDE.md`) — full reasoning, missing evidence, and accepted
risk in `care-request-security-and-privacy.md` §14.

## 3. Data minimization

Do not record in audit events:

- `motivo` raw text;
- `padecimiento` raw text;
- `descripcion` raw text;
- attachment contents;
- private storage credentials;
- private download URLs.

Prefer identifiers and event metadata already used by the project.

## 4. Failed transaction behavior

The business operation is atomic.

If the CareRequest creation/conversion transaction rolls back, the CareRequest record does not persist.

Therefore, a failed transactional attempt must not be represented later as a persisted CareRequest lifecycle state.

Any technical security/audit event that intentionally records an unsuccessful attempt must remain separate from the CareRequest domain record and must use the existing audit mechanism.

## 5. Converted history

A successful request results in:

`CareRequest = CONVERTIDA`

with:

`CareRequest.appointment = Appointment`

and ClinicalDocuments associated with the resulting Appointment.

No additional request-history entity is introduced.

## 6. No update history

Fase 5 does not implement independent CareRequest editing, so there is no edit-history workflow to document.

## 7. Reuse

Use the existing project's audit service, event naming, actor context, and retention practices.

Do not introduce a Fase 5-specific audit framework.

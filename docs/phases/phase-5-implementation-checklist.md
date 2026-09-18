# Fase 5 — Implementation Checklist

**HISTORICAL (2026-09-18):** this is the pre-implementation planning checklist; its `[ ]`
checkboxes were never updated during/after implementation and must not be read as "still
pending" — Fase 5 has since been implemented, audited, and formally closed. Every item below has
concrete, evidenced verification in `docs/phases/phase-5-final-report.md` (§2/§41.B "Auditoría
final del código", §41.C-§41.D regression/idempotency evidence, §41.H the 37-criteria DoD table)
— that report, not the checkbox state here, is the authoritative record of what was verified.
This file is kept as the original planning artifact, not maintained as a live tracker.

## Pre-implementation

- [ ] Technical Design Freeze approved.
- [ ] No unresolved functional or architectural decisions.
- [ ] Current main branch/revision identified.
- [ ] Existing F2 Agenda and F4 ClinicalDocument tests are green.
- [ ] Migration graph reviewed.
- [ ] Fase 5 documentation index reviewed.

## Data model

- [ ] CareRequest model implemented exactly as designed.
- [ ] `patient`, `created_by`, `responsible`, `doctor`, `clinic` use approved `PROTECT`.
- [ ] `appointment` is an optional OneToOne to Appointment with approved deletion behavior.
- [ ] Text fields use the approved blank/default/null semantics.
- [ ] `start_at < end_at` constraint exists.
- [ ] `(created_by, idempotency_key)` uniqueness exists for non-empty keys.
- [ ] Migration direction remains `care_requests → appointments`.

## Service

- [ ] CareRequestService owns orchestration.
- [ ] Actor lock acquired before authoritative idempotency re-check.
- [ ] Rate limit evaluated only after replay check.
- [ ] One outer transaction covers the complete business operation.
- [ ] CareRequest starts as NUEVA.
- [ ] HoldService F2 is reused.
- [ ] AppointmentService F2 is reused without CareRequest-specific knowledge.
- [ ] CareRequest.appointment is assigned by CareRequestService.
- [ ] ClinicalDocuments attach to resulting Appointment.
- [ ] CareRequest changes to CONVERTIDA only after successful completion.

## Idempotency

- [ ] Idempotency-Key is optional.
- [ ] Same actor/key produces replay.
- [ ] Conflicting same actor/key produces conflict.
- [ ] Concurrent same actor/key requests are safe.
- [ ] IntegrityError race handling is inside a savepoint/inner atomic.
- [ ] Failed transaction does not permanently reserve the key.
- [ ] Client CareRequest key is not copied into Appointment namespace.

## Rate limiting

- [ ] Maximum 3 new CareRequests per actor in rolling 1 hour.
- [ ] PostgreSQL is used.
- [ ] No Redis/Celery/external rate-limit service.

## Files

- [ ] Existing ClinicalDocument infrastructure reused.
- [ ] Maximum 5 files enforced.
- [ ] PDF/JPEG/PNG enforced.
- [ ] Maximum 10 MB per file enforced.
- [ ] Created physical files tracked for compensation.
- [ ] Compensation runs after database rollback.
- [ ] Orphan cleanup automation is not implemented.

## API/UI

- [ ] Approved API contract implemented.
- [ ] Approved DTO implemented.
- [ ] Authentication/authorization enforced server-side.
- [ ] Slot start/end preserved from Agenda.
- [ ] No waiting-room/check-in workflow.
- [ ] No independent CareRequest editing.
- [ ] Existing design-system components reused.

## Verification

- [ ] Unit/domain tests pass.
- [ ] Service tests pass.
- [ ] Transaction tests pass.
- [ ] Concurrency tests pass.
- [ ] File compensation tests pass.
- [ ] API tests pass.
- [ ] Browser/UI tests pass.
- [ ] Full existing F2 regression suite passes.
- [ ] Full existing F4 regression suite passes.
- [ ] `git diff --check` clean for implementation changes.
- [ ] Documentation updated only for verified implementation discrepancies.

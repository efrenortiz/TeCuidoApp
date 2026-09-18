# Fase 5 — Implementation Handoff

**HISTORICAL (2026-09-18):** this handoff was written before implementation started. Fase 5 has
since been implemented, audited, and formally closed — see
`docs/phases/phase-5-final-report.md` §41.K (`PHASE 5 — CLOSED`). This document is kept as the
record of the approved execution order actually followed; it does not describe the current
state of the project.

## Purpose

Provide the implementation team with the minimum execution order after Technical Design Freeze.

This document does not authorize implementation by itself; it records the approved design handoff.

## Recommended implementation order

1. Create the `care_requests` application structure.
2. Implement the approved CareRequest model and constraints.
3. Implement domain/service contracts.
4. Implement authorization and rate limiting.
5. Implement idempotency with actor locking, authoritative re-check, and savepoint-based race handling.
6. Implement Agenda integration using the existing F2 services.
7. Implement `CareRequest.appointment` assignment.
8. Implement ClinicalDocument integration and synchronous file compensation.
9. Implement the DTO and API contract.
10. Implement UI/screens according to the approved UX documents.
11. Execute the Fase 5 test strategy and regression suites.
12. Update documentation only when implementation reveals a genuine discrepancy.

## Do not implement

Do not add:

- waiting-room/check-in;
- antivirus;
- Redis/Celery;
- independent CareRequest editing;
- duplicate availability logic;
- duplicate file storage;
- a second Appointment-creation mechanism;
- a second idempotency namespace for the same client operation.

## Mandatory integration invariants

- Agenda remains the source of truth for availability and booking.
- AppointmentService remains unaware of CareRequest.
- CareRequest owns the relation to Appointment.
- ClinicalDocument remains the file-storage authority.
- Failed conversion leaves no persisted partial business operation.
- Successful conversion leaves CareRequest `CONVERTIDA` with an Appointment.

## Evidence expected before implementation closure

See `phase-5-testing-strategy.md` and `care-request-acceptance-criteria.md`.

Required evidence includes:

- service/domain tests;
- concurrency/idempotency tests;
- transaction/rollback tests;
- attachment compensation tests;
- API tests;
- browser/UI checks;
- F2/F4 regression suites.

## Change control

If implementation discovers a requirement that cannot be satisfied using the frozen design, stop at the affected boundary and document the discrepancy before changing the design.

The implementation should not silently create a new architectural decision.

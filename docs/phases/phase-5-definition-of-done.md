# Fase 5 — Definition of Done

## Purpose

Define the objective conditions required to consider the Fase 5 implementation complete.

## Functional completion

Fase 5 is complete when:

- an authenticated patient can create a CareRequest for themselves;
- an authorized responsible can create a CareRequest for a patient;
- a valid selected Agenda slot can be converted into an Appointment;
- CareRequest reaches `CONVERTIDA` only after successful completion;
- CareRequest has its `Appointment` relation;
- attachments are associated with the resulting Appointment;
- invalid/unavailable operations do not leave partial business records.

## Technical completion

The implementation must satisfy:

- approved CareRequest model and constraints;
- approved transaction boundary;
- approved Agenda integration;
- approved idempotency behavior;
- approved PostgreSQL rate limiting;
- approved file compensation;
- approved DTO/API contract;
- approved authorization;
- approved dependency direction.

## Quality completion

The following evidence must be green:

- Fase 5 unit/domain tests;
- Fase 5 service tests;
- transaction tests;
- concurrency/idempotency tests;
- filesystem compensation tests;
- API tests;
- UI/browser tests;
- Fase 2 Agenda regression tests;
- Fase 4 ClinicalDocument regression tests.

## Scope completion

The implementation must not contain:

- waiting room/check-in;
- antivirus subsystem;
- independent CareRequest editing;
- Redis/Celery for these requirements;
- duplicate Agenda availability logic;
- duplicate file storage;
- CareRequest knowledge inside AppointmentService.

## Documentation completion

The implementation is not complete until:

- implementation evidence is recorded;
- the traceability matrix is updated as appropriate;
- acceptance criteria are verified;
- any genuine implementation/design discrepancy is resolved through change control;
- the phase report records the final test/evidence results.

## Phase closure rule

Passing tests alone does not close the phase.

Fase 5 can be formally closed only when functional behavior, technical constraints, regression evidence, scope, and required documentation all satisfy this Definition of Done.

## Excluded operational responsibility

External cleanup of unexpected orphaned filesystem objects remains an administrator operational responsibility and is not a condition requiring application implementation.

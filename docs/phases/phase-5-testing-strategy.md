# Fase 5 — Testing Strategy

## 1. Purpose

Define the evidence required to implement and validate CareRequest without introducing a separate testing architecture.

The strategy reuses the project's existing Django/PostgreSQL testing conventions and browser/UI test patterns.

## 2. Test layers

### Unit/domain tests
Validate:

- allowed status values;
- required/optional fields;
- `start_at < end_at`;
- responsible/patient authorization rules;
- idempotency semantics;
- DTO construction.

### Service tests
Validate:

- CareRequestService orchestration;
- Agenda delegation;
- successful conversion;
- rollback;
- appointment relation;
- attachment handling;
- compensation behavior.

### Transaction/concurrency tests
Explicitly test:

1. two concurrent requests with the same actor and `Idempotency-Key`;
2. actor lock;
3. authoritative re-check after lock;
4. rate limit after replay check;
5. UNIQUE constraint race and savepoint handling;
6. replay of the committed result;
7. conflicting reuse of the key.

### Integration tests
Validate:

- CareRequest → HoldService;
- Hold → Appointment;
- Appointment relation;
- ClinicalDocument → Appointment;
- existing Agenda validations.

## 3. Required positive scenarios

At minimum:

- patient creates request for self;
- responsible creates request for authorized patient;
- valid slot converts successfully;
- optional fields omitted;
- valid attachments accepted;
- request without Idempotency-Key works as an independent operation.

## 4. Required negative scenarios

At minimum:

- unauthenticated request;
- unauthorized responsible/patient relationship;
- invalid doctor/clinic context;
- unavailable slot;
- conflicting slot;
- invalid attachment type;
- attachment over size limit;
- more than 5 attachments;
- rate limit exceeded;
- conflicting Idempotency-Key reuse.

## 5. Atomicity scenarios

Verify that failure at each critical stage leaves no partially committed CareRequest/Appointment/Hold state.

Examples:

- Hold creation fails;
- Appointment creation fails;
- Appointment relation write fails;
- ClinicalDocument write fails;
- CareRequest conversion write fails.

The database must roll back as one logical operation.

## 6. Filesystem compensation tests

Verify that:

- created files are tracked during the operation;
- on failure, database rollback occurs;
- compensation removes only files created by that execution;
- successful commit preserves files.

Do not introduce a persistent orphan-cleanup subsystem into application tests.

## 7. DTO tests

Verify the service result contains only the approved DTO fields:

- `care_request_id`;
- `status`;
- `appointment_id`;
- `clinical_document_ids`.

## 8. API tests

Verify:

- authentication;
- request validation;
- `Idempotency-Key` handling;
- successful DTO response;
- authorization errors;
- idempotency conflict;
- rate-limit response;
- attachment validation errors.

Reuse the project's existing API error serialization conventions.

## 9. UI/browser tests

Validate:

- doctor/date/slot selection;
- slot start/end preserved;
- successful confirmation;
- duplicate-submit protection;
- slot conflict feedback;
- attachment validation;
- rate-limit feedback;
- replay behavior;
- no waiting-room/check-in workflow.

### Evidence-type labeling (2026-09-18)

The project has no frontend test framework and no automated browser-test harness. Evidence for
§9 must always state which of the following it actually is, and must never present one as
another:

- **backend test** — Django test client (`care_requests/tests/`), runs in CI, permanent.
- **frontend test** — there is no frontend test framework in this project; when JS logic needs
  verification without a real browser, the only available substitute is a throwaway Node.js
  execution of the exact, byte-identical function bodies from the shipped `.js` file, run once
  in-session and never committed. This is explicitly **not** a browser test and **not** a proper
  JS-framework test — it exists only because no better tool is available.
- **real browser evidence** — an actual interactive session (e.g. Claude-in-Chrome) against the
  running application. This is the only evidence that can support claims about what a real user
  actually sees rendered, and it depends on external tooling connectivity that is not guaranteed
  to be available in every session; when unavailable, the impediment must be documented
  explicitly rather than substituted with either of the above.

## 10. Regression

Run the existing Agenda and ClinicalDocument test suites after implementation.

Fase 5 must not regress:

- appointment booking;
- hold concurrency;
- availability;
- clinical document behavior.

## 11. Evidence for phase closure

The implementation should produce:

- all Fase 5 tests passing;
- existing regression suites passing;
- concurrency tests passing;
- filesystem compensation tests passing;
- browser checks passing for defined Fase 5 screens;
- documentation updated only when implementation reveals a genuine discrepancy.

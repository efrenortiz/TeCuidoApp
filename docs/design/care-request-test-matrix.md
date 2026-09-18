# CareRequest — Detailed Test Matrix

## Purpose

Provide implementation-level test coverage requirements while reusing the existing project testing stack.

| ID | Scenario | Expected result | Evidence |
|---|---|---|---|
| CR-001 | Patient creates request for self | CareRequest converted and Appointment created | Service/API test |
| CR-002 | Authorized responsible creates request | Success | Authorization/service test |
| CR-003 | Unauthorized responsible | Rejected | Authorization test |
| CR-004 | Missing/empty/whitespace-only motivo | Rejected (400 at API) | Service + API test |
| CR-005 | Optional free-text omitted | Success | Domain/API test |
| CR-006 | Valid slot | Hold + Appointment created | Integration test |
| CR-007 | Slot becomes unavailable | Full rollback | Transaction test |
| CR-008 | Appointment relation assigned | CareRequest.appointment populated | Service test |
| CR-009 | ClinicalDocument associated with Appointment | Documents linked correctly | Integration test |
| CR-010 | Valid attachments | Accepted | File integration test (service + API, multipart) |
| CR-011 | >5 attachments | Rejected (400 at API) | Service + API test |
| CR-012 | Invalid file type | Rejected (400 at API) | Service + API test |
| CR-013 | >10 MB file | Rejected (400 at API) | Service + API test |
| CR-014 | Failure after physical file creation | Files compensated | Filesystem compensation test |
| CR-015 | Same actor/key replay | Existing result returned | Idempotency test |
| CR-016 | Same key with conflicting slot | Conflict | Idempotency test |
| CR-017 | Same key concurrent requests | One operation, one replay | Concurrency test |
| CR-018 | UNIQUE race (forced) | Savepoint + re-query + replay | Transaction test (mocked re-check miss, real IntegrityError) |
| CR-031 | Same key, different `motivo` | Conflict (not replay) | Idempotency test |
| CR-032 | Same key, different `padecimiento` | Conflict (not replay) | Idempotency test |
| CR-033 | Same key, different `descripcion` | Conflict (not replay) | Idempotency test |
| CR-034 | Same key, incompatible attachment count or size | Conflict (not replay) | Idempotency test |
| CR-035 | Same key, identical attachments (name + size + byte content) | Replay, no duplicate ClinicalDocument | Idempotency test |
| CR-038 | Same key, same filename + same size, **different binary content** (adversarial) | Conflict (not replay) — content is read and compared byte-for-byte only when name/size already match | Idempotency test |
| CR-039 | Same key, request itself invalid (empty `motivo` or `start_at >= end_at`) reusing a key already bound to a committed CareRequest | `400 VALIDATION_ERROR` — never replay, never `409` | Idempotency test (validation precedes idempotency evaluation) |
| CR-019 | Missing Idempotency-Key | Independent operation | Service/API test |
| CR-020 | 3 requests within one hour | Allowed up to limit | Rate-limit test |
| CR-021 | Fourth request in window | Rejected | Rate-limit test |
| CR-022 | Valid replay after rate limit reached | Replay succeeds | Combined idempotency/rate-limit test |
| CR-023 | Failed request rollback | Key not permanently reserved | Transaction/idempotency test |
| CR-024 | Patient/created_by/responsible invariant | Invalid combinations rejected | Service test |
| CR-025 | start_at >= end_at | Rejected as controlled `400`, not a raw `IntegrityError`/500 | Model test (`CheckConstraint`, defense in depth) + service test (`CareRequestValidationError`, authoritative) + API test |
| CR-026 | Appointment exists without CareRequest | Existing Agenda behavior unchanged | Regression test |
| CR-027 | Existing Agenda concurrency tests | Still pass | Regression suite |
| CR-028 | Existing ClinicalDocument tests | Still pass | Regression suite |
| CR-029 | UI slot selection | Selected start/end preserved | Browser test |
| CR-030 | Double submit | No duplicate operation | Browser + service test |
| CR-036 | `Content-Type: application/json` body | Rejected explicitly (`400`, message names the `Content-Type` problem) — not the old "missing field" 400 | API test |
| CR-037 | Unexpected/unanticipated exception in the view | Generic `500`, no traceback/internal detail/clinical text in the response body (verified with `DEBUG=False`) | API test |
| CR-040 | `Content-Type: application/x-www-form-urlencoded` body | Rejected explicitly (`400`) — Django would otherwise parse it into `request.POST` "by accident" | API test |
| CR-041 | `Cache-Control: no-store` on success (`201`) | Present | API test |
| CR-042 | `Cache-Control: no-store` on representative errors (`400`, `401`, `403`, `409`, `429`) | Present on every one, not only success | API test (one per status code) |
| CR-043 | `Cache-Control: no-store` on unanticipated exception (`500`, `DEBUG=False`) | Present | API test |
| CR-044 | Client-side `fetch()` network rejection (`apiFetchJson`/`apiFetchForm`) | Promise resolves (never rejects) with `{ok:false}` and a generic, understandable message — no raw `fetch()` error exposed | Extracted Node.js execution of the real functions (not a backend test, not a real browser) |
| CR-045 | `submitCareRequest` UI state after a network rejection | Confirm button restored (`disabled=false`); no automatic double submit (`fetch` invoked exactly once) | Extracted Node.js execution of the real functions (not a backend test, not a real browser) |
| CR-046 | `Appointment` never exposes a `.care_request` reverse accessor | `hasattr(Appointment, "care_request")` is `False`; absent from `Appointment._meta.get_fields()` | Model test |
| CR-047 | `CareRequest.appointment` still works normally (forward direction) | Create/replay flow unaffected by `related_name="+"` | Service test (full existing suite, unchanged) |
| CR-048 | `clinical_document_ids` persisted on conversion | Field on the `CareRequest` row matches the DTO's `clinical_document_ids` at the moment of conversion | Service test |
| CR-049 | `ClinicalDocument` added later to the same `Appointment` by another flow (not `CareRequestService`) | Does not appear in a later replay's identity comparison nor in its `clinical_document_ids` | Service test (adversarial — the exact scenario of hallazgo B) |
| CR-050 | Replay after CR-049's contaminating document exists | Still a valid replay (not `409`); result's `clinical_document_ids` matches the original, excludes the contaminating document's `pk` | Service test |
| CR-051 | Pre-confirmation summary shows doctor/clinic/date/start-end/motivo/padecimiento/descripcion/attachments | All fields visible before clicking confirm, no recalculated duration | Real browser test (when available) — see phase-5-final-report.md §39 for the concrete run/impediment |
| CR-052 | Client-side attachment validation: excess count, disallowed extension, oversized file | Confirm button disabled, named error shown, server limits unchanged | Extracted Node.js execution of `validateAttachments` (not a backend test, not a real browser) + backend API test (server independently re-rejects) |
| CR-053 | Attachment removal via per-file "Quitar" control | File removed from the pending `FileList`/UI list without clearing the rest of the selection | Extracted Node.js execution of `removeAttachmentAt`/`DataTransfer` usage (not a backend test, not a real browser) |
| CR-054 | UI now sends `Idempotency-Key`; two independent HTTP requests with the same key (true double submit, not just a disabled button) | Exactly one `CareRequest` and one `Appointment`, identical response bodies | API test (`test_double_submit_produces_a_single_business_operation`) |
| CR-055 | `care_request_config` attachment limits (`maxAttachments`, `maxAttachmentSizeBytes`, `allowedAttachmentExtensions`) | Match the real server constants exactly (`care_requests.api.MAX_ATTACHMENTS`, `clinical_documents.services.storage`) — never duplicated numbers | UI/view test (`test_config_exposes_attachment_limits_from_real_source_constants`) |

## Required corrections focus (2026-09-18, domain correction)

CR-046/CR-047 must be executed together — CR-046 alone (accessor absence) is meaningless without
CR-047 (forward relation still works) proving `related_name="+"` didn't silently break anything.
CR-049/CR-050 must use a document created via a direct call to `clinical_documents.services.
document.upload()` (bypassing `CareRequestService` entirely) to genuinely simulate "another
flow" — a document created through `CareRequestService` itself would not exercise the
contamination scenario.

## Required concurrency focus

At minimum, CR-017, CR-018, and CR-022 must use a concurrency-capable test strategy suitable for PostgreSQL.

## Revision (2026-09-17)

CR-016 was narrowed to slot-only conflict and split into CR-031..CR-035 to cover the full logical
identity of the operation (`care-request-service-contracts.md` §7.1): the original comparison only
considered patient/doctor/clinic/slot, which is insufficient — `motivo`/`padecimiento`/
`descripcion`/attachments are also part of the request's identity, so a same-key retry with
incompatible data in any of those fields must be a conflict, not a silent replay. CR-018 is now
tested by deliberately forcing the authoritative re-check to miss an existing row (mocked), so the
real PostgreSQL `UniqueConstraint` genuinely raises `IntegrityError` inside the savepoint and the
recovery path (re-query + replay) is exercised for real, not just reasoned about.

## Revision (2026-09-17, API/validation correction)

CR-025 previously only had model-level evidence; the service had no `start_at`/`end_at`
comparison, so an invalid interval reached the database `CheckConstraint` directly and
produced a raw `IntegrityError` propagated as an uncontrolled `500` — now covered by a
service-level check (authoritative) plus the model constraint (defense in depth) plus an API
test. CR-004/CR-011/CR-012/CR-013 gained explicit API-level (multipart, HTTP status) coverage
in addition to their existing service-level tests. CR-036/CR-037 are new: they pin down,
respectively, that the endpoint genuinely never accepts JSON (documentation previously
contradicted this) and that an unanticipated exception never leaks internals through the HTTP
response.

## Revision (2026-09-18, attachment identity correction)

CR-034/CR-035 corrected: the previous `(original_filename, size_bytes)` fingerprint allowed two
different files sharing name and size to be treated as the same attachment — a real gap, not
just a theoretical one, since size and filename are both client-controlled. CR-038 is new and
mandatory: it fixes the exact adversarial case (same filename, same byte length, different
content) that the fingerprint alone could not detect. CR-039 is new: it confirms, against the
existing `reschedule_appointment` precedent, that structural input validation (`motivo`,
interval) is evaluated before any idempotency comparison — an invalid request reusing an
existing key is `400`, never a replay or a `409` conflict.

## Revision (2026-09-18, API contract / UX-of-errors / response-security correction)

CR-036 corrected: the endpoint now rejects `application/json` explicitly (`content_type` check
before touching `request.POST`), not by accident via an empty-body-looking `400`. CR-040 is
new: `application/x-www-form-urlencoded` — previously accepted "by accident" since Django
parses it into `request.POST` the same way as multipart — is now rejected too, since multipart
is a technical requirement (the only format the real client sends), not a style preference.
CR-041/CR-042/CR-043 are new: they close a real gap where `Cache-Control: no-store` was only
applied on the success path — every `except` branch in `CareRequestJsonApiView.dispatch`
returned directly, bypassing the header assignment. CR-044/CR-045 are new and are explicitly
**not** browser tests: no browser automation was available in this environment, and the
project has no frontend test framework at all (consistent with `agenda-booking.js`, which also
has zero tests) — they are a plain Node.js execution (no new dependency, no framework) of the
exact, byte-identical functions from `static/js/care-request.js`, run once in this session to
verify the network-rejection fix works as intended, not a permanent addition to the repository.

## Revision (2026-09-18, domain correction — ORM reverse accessor and attachment-identity persistence)

Two real defects found in an audit of the current implementation, both now fixed:

**Hallazgo A:** `CareRequest.appointment`'s `related_name` (previously the implicit default,
`"care_request"`) generated a Django reverse accessor `Appointment.care_request` — no physical
FK/migration in `appointments`, but real ORM navigability in the direction ADR-005 §12/§44
explicitly prohibits. Fixed with `related_name="+"`, Django's standard mechanism to suppress a
reverse relation entirely. CR-046/CR-047 are new.

**Hallazgo B:** `_attachments_are_identical`/`_to_result` resolved "the CareRequest's
documents" by querying `ClinicalDocument.objects.filter(appointment_id=...)` — a query that
grows if another flow adds an unrelated `ClinicalDocument` to the same `Appointment` later,
retroactively changing a previously-valid replay into a `409` and leaking a foreign document ID
into the replay's `clinical_document_ids`. Fixed by persisting the exact `pk` set at conversion
time in a new field, `CareRequest.clinical_document_ids` (`ArrayField`, `care-request-data-
model.md` §3.1) — a migration on `care_requests` only, no change to `ClinicalDocument`'s model.
CR-048/CR-049/CR-050 are new.

## Revision (2026-09-18, UI correction — pre-confirmation summary, attachment validation, real double submit)

Two real defects found in a UI audit of the implementation, both now fixed, plus one
self-identified gap in the same audit:

**Hallazgo A:** the pre-confirmation summary did not visibly demonstrate doctor/clinic/date/
selected start-end alongside the entered fields and attachments, as `care-request-screens.md`
§3 requires. Fixed in `templates/care_requests/care_request_create.html` (`data-list` summary)
and `static/js/care-request.js::renderSummary()`. CR-051 is new.

**Hallazgo B:** the `accept=".pdf,.jpg,.jpeg,.png"` HTML attribute is advisory only (users can
bypass it, and it enforces neither count nor size) and was the only client-side control. Fixed
with `validateAttachments()`/`refreshAttachmentsUi()`, sourcing limits from the server's real
constants via `care_request_config` rather than duplicated numbers. CR-052/CR-053/CR-055 are
new.

**Gap found during this audit (not originally named by the prompt, but within its §7 scope):**
the UI never sent an `Idempotency-Key` header at all, so the backend's authoritative
idempotency protection was never exercised by real UI traffic — a synchronous button-disable
only prevents a same-tab double-click, not two genuinely independent HTTP requests (two tabs, a
tap registered twice). Fixed by generating a `crypto.randomUUID()` per slot-selection attempt
and sending it on every create request. CR-054 is new and tests two independent HTTP requests
with the same key, not a UI helper function.

## Required regression

The complete existing Agenda and ClinicalDocument test suites must pass after Fase 5 implementation.

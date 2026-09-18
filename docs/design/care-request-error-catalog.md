# CareRequest — Error Catalog

## Purpose

Consolidate the observable errors of Fase 5 while reusing existing project error and API serialization conventions.

## Error categories

| Condition | Meaning | Expected API behavior |
|---|---|---|
| Authentication required | No authenticated actor | Existing authentication response |
| Authorization denied | Actor cannot act for target patient | Existing authorization error mapping |
| Invalid request data | Required/malformed data | Existing validation error mapping |
| Invalid interval | `start_at >= end_at` | Existing validation error mapping — rejected by the service before persisting (`CareRequestValidationError` → 400), not by letting the database `CheckConstraint` raise a raw `IntegrityError` |
| Empty/whitespace-only `motivo` | Required free-text field with no real content after normalization | Existing validation error mapping |
| Invalid slot | Submitted interval is not a valid Agenda slot | Existing domain/API conflict mapping |
| Slot unavailable | Availability changed before Hold creation | Existing Agenda conflict mapping |
| Idempotency conflict | Same actor/key reused for incompatible operation | Conflict response |
| Valid replay | Same actor/key represents same committed operation | Return existing result |
| Rate limit exceeded | More than 3 new CareRequests in rolling hour | Rate-limit response |
| Unsupported attachment | File type outside approved set | Existing validation error mapping |
| Attachment too large | File exceeds 10 MB | Existing validation error mapping |
| Too many attachments | More than 5 files | Existing validation error mapping |
| Incompatible `Content-Type` | Body is not `multipart/form-data` (e.g. JSON, urlencoded) | `400` (`ApiError`), rejected before touching `request.POST`/`request.FILES` — see `care-request-api-contracts.md` §5 |
| Internal failure | Unexpected service/storage failure | `500`, generic and fixed message — see principle 7 (corrected) |
| Client-side network failure | `fetch()` rejects (no connection, DNS, CORS, unreachable server) | Not a server response — handled entirely in the browser client, converted to a resolved `{ok:false}` result with a generic message; see `care-request-api-contracts.md` §15 |

## Principles

1. Reuse existing domain exceptions whenever available.
2. Do not expose database exceptions directly to API consumers.
3. Do not expose storage implementation details.
4. Do not expose clinical free-text in error messages or logs.
5. A failed transactional conversion does not create a persistent pending CareRequest.
6. A valid idempotent replay is not a new creation and does not consume a creation-rate-limit slot.
7. **Corrected (2026-09-18):** unexpected/unanticipated exceptions ARE now caught by a scoped
   `except Exception` in `CareRequestJsonApiView.dispatch` — but only to guarantee `Cache-Control:
   no-store` on the resulting `500` (principle 8), and only when `DEBUG=False`. With `DEBUG=True`
   the exception is re-raised unchanged, preserving Django's development debug page exactly as
   `appointments.api.JsonApiView`/`clinical_documents.api_common.DocumentJsonApiView` behave (those
   two views were **not** modified and still have no generic catch — they never had the same
   Cache-Control gap this catch exists to close). The response message remains fixed and generic,
   with no traceback or internal detail, regardless of the real exception's content.
8. **New (2026-09-18):** every response — success and every error, including the `500` case —
   carries `Cache-Control: no-store`. Before this correction, only the success path did; each
   `except` branch returned directly, bypassing the header assignment.

**Correction (2026-09-17):** principle 2 was violated before this correction — `start_at >=
end_at` had no service-level check and reached the database `CheckConstraint`
(`care_request_start_before_end`) directly, producing a raw `IntegrityError` (whose `DETAIL`
can include other field values from the failing row, including `motivo`) instead of a
controlled `400`. Fixed by `CareRequestService._validate_interval()` — see
`care-request-service-contracts.md` §3.1.

## Idempotency conflict

A conflict occurs when an existing `(created_by, idempotency_key)` is associated with an operation whose relevant request attributes are incompatible with the new request.

The exact compatibility comparison must use the fields defined by the service contract; it must not silently replace the original operation.

## Error ownership

Agenda-originated availability/booking errors remain Agenda domain errors.

CareRequestService translates only what is necessary for its public service/API contract.

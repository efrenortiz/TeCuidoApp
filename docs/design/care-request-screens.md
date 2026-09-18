# CareRequest — Screen Design

## 1. Scope

This document defines the concrete screens/states needed for the Fase 5 CareRequest experience.

It complements the global `screens.md`, `design-system.md`, and `ui-guidelines.md`; it does not replace them.

## 2. CareRequest creation screen

### Purpose
Create a direct appointment request for an authenticated patient or authorized responsible actor.

### Main elements
- doctor selection;
- clinic/context when required;
- date selection;
- available slot list/calendar;
- motivo (required, free text);
- padecimiento (optional, free text);
- descripcion (optional, free text);
- attachment controls;
- confirmation action.

### Constraints
- only available Agenda slots are presented;
- selected slot preserves start/end;
- maximum 5 attachments;
- PDF/JPEG/PNG only;
- maximum 10 MB per file.

## 3. Selected-slot summary

Before confirmation, display:

- doctor;
- clinic;
- selected date;
- selected start/end;
- entered motivo;
- optional entered fields;
- selected attachments.

The UI must not recalculate the slot duration.

**Implemented (2026-09-18):** `templates/care_requests/care_request_create.html`'s
`details-panel` now shows a `data-list` summary (doctor, clinic, date, selected start/end) at
the top, populated by `static/js/care-request.js::renderSummary()` at slot-selection time — the
same panel already displays entered `motivo`/`padecimiento`/`descripcion` as editable fields
(the user's own typed text, visible before clicking confirm) and lists selected attachments
(`refreshAttachmentsUi()`, name + size, with a per-file remove control). No separate approval
screen or queue was added — this is the same existing panel, enriched, not a new step.

## 4. Loading/submission state

While the create operation is in progress:

- prevent duplicate submission;
- preserve the form context;
- communicate that the appointment request is being processed.

The backend idempotency mechanism remains authoritative.

**Implemented (2026-09-18):** `confirmBtn`/`cancelDetailsBtn` disable synchronously before the
request starts (prevents duplicate submission from the same tab/click sequence without waiting
for the network); the form fields are left untouched (form context preserved); `#submitting-
status` ("Enviando solicitud…") is shown while in flight. Additionally, the client now
generates an `Idempotency-Key` per slot-selection attempt (`crypto.randomUUID()`, reused across
retries of the same attempt, renewed only when a different slot is selected) and sends it on
every create request — closing a real gap where the UI previously never sent this header at
all, so a genuine double submission from two separate HTTP requests (e.g. two tabs, or a tap
registered twice before the DOM updates) had no relationship to each other from the backend's
point of view and could have created two independent business operations. The backend
idempotency mechanism remains authoritative and unmodified — this only makes the client
actually invoke it for this scenario.

## 5. Success state

Show the created appointment information.

The underlying result is based on `CareRequestResult`:

- `care_request_id`;
- `status`;
- `appointment_id`;
- `clinical_document_ids`.

## 6. Availability/conflict error state

When Agenda rejects the selected slot:

- explain that the selected time is no longer available;
- offer navigation back to slot selection;
- do not display the CareRequest as pending.

## 7. Authorization error state

When the server rejects the operation for authorization:

- display a generic authorization message appropriate to the role;
- do not disclose unrelated patient data;
- do not bypass server authorization.

## 8. Rate-limit error state

When the actor exceeds 3 CareRequests in the rolling 1-hour window:

- display a concise rate-limit message;
- do not imply that the request was queued;
- preserve no false local “pending” state.

## 9. Idempotency-conflict state

If the same `Idempotency-Key` is reused for a conflicting request:

- display a conflict message;
- do not silently replace the previous request;
- do not submit again using the same key.

## 10. Attachment validation state

For an invalid attachment:

- identify the invalid file where practical;
- explain the permitted types/size;
- prevent submission while the invalid file remains selected.

The server must still enforce all limits.

**Implemented (2026-09-18):** `static/js/care-request.js::validateAttachments()`/
`refreshAttachmentsUi()` check, on every file-input change and again right before submit: file
count (≤ `config.maxAttachments`), extension (must be in `config.allowedAttachmentExtensions`),
and size (≤ `config.maxAttachmentSizeBytes`) — all three values passed from the server's own
real constants (`care_requests.api.MAX_ATTACHMENTS`, `clinical_documents.services.storage`),
never duplicated as separate numbers in the template/JS. An invalid file is identified by name
in `#attachments-error` (`field__error`, existing design-system class), the confirm button is
disabled while any problem remains (`docs/design/care-request-screens.md` §10's exact
requirement), and each selected file has an individual "Quitar" control (built with the
`DataTransfer` Web API, no new library) so the user can remove/replace a file without clearing
the whole selection. The server continues to enforce every limit independently
(`ClinicalDocumentService`/`clinical_documents.services.storage`, unchanged) — this is UX
assistance, never a substitute.

## 11. No waiting-room screens

No CareRequest screen implements:

- check-in;
- waiting room;
- patient-in-waiting status;
- arrival workflow.

These are outside Fase 5.

## 12. Design-system requirements

Reuse existing components and patterns.

Do not introduce a separate Fase 5 design language, navigation pattern, error system, or interaction framework.

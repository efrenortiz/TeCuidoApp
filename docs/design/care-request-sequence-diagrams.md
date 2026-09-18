# CareRequest — Sequence Diagrams

## Purpose

Document the main execution sequences for Fase 5. These diagrams complement the workflow and service contracts without introducing new behavior.

## 1. Successful creation

```text
Actor
  |
  | POST CareRequest + Idempotency-Key
  v
CareRequest API
  |
  v
CareRequestService
  |
  | BEGIN transaction
  | lock actor
  | re-check idempotency
  | rate limit
  | create CareRequest(NUEVA)
  v
HoldService (F2)
  |
  | validate current Agenda state
  | create Hold
  v
AppointmentService (F2)
  |
  | create Appointment from Hold
  v
CareRequestService
  |
  | CareRequest.appointment = Appointment
  | create ClinicalDocument(s)
  | CareRequest = CONVERTIDA
  | COMMIT
  v
CareRequestResult DTO
  |
  v
API response
```

## 2. Idempotent replay

```text
Actor
  |
  | same actor + Idempotency-Key
  v
CareRequestService
  |
  | BEGIN
  | lock actor
  | re-check key
  v
Existing CareRequest
  |
  | validate replay compatibility
  v
Return existing CareRequestResult
```

No new Hold or Appointment is created during a valid replay.

## 3. Concurrent same-key requests

```text
Request A                         Request B
   |                                 |
   | BEGIN + lock actor              |
   |-------------------------------> |
   |                                 | waits
   | re-check key: absent            |
   | create CareRequest               |
   | Agenda operation                 |
   | COMMIT                           |
   |                                 | lock acquired
   |                                 | re-check key: exists
   |                                 | replay existing result
```

The UNIQUE constraint remains defensive protection against a race that reaches insertion.

## 4. Agenda rejection

```text
CareRequestService
  |
  | create CareRequest(NUEVA)
  v
HoldService
  |
  | slot invalid / unavailable / conflict
  v
Domain error
  |
  | rollback transaction
  v
CareRequestService
  |
  | synchronous file compensation
  v
API error response
```

No persisted pending CareRequest remains.

## 5. Attachment failure

```text
CareRequestService
  |
  | Appointment exists in transaction
  v
ClinicalDocumentService
  |
  | file/storage operation
  v
failure
  |
  | rollback database
  v
CareRequestService
  |
  | delete files created by this execution
  v
propagate error
```

## 6. Architectural boundary

`CareRequestService` orchestrates.

`HoldService` owns Hold and Agenda validation.

`AppointmentService` owns Appointment creation.

`ClinicalDocumentService` owns file/document handling.

No existing service is made aware of the CareRequest domain merely to support Fase 5.

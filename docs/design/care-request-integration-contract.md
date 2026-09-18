# CareRequest — Integration Contract

## Purpose

Define the boundaries between Fase 5 and existing modules without duplicating their responsibilities.

## CareRequest → Agenda

CareRequestService invokes the existing Fase 2 HoldService contract.

Inputs come from the CareRequest operation:

- authenticated actor;
- doctor;
- clinic;
- selected slot start;
- selected slot end.

Agenda remains authoritative for availability, slot validity, conflicts, duration, concurrency, DoctorClinic, and timezone rules.

## Hold → Appointment

CareRequestService uses the existing `AppointmentService.create_appointment_from_hold()` contract.

The service remains unaware of CareRequest.

## Appointment relation

After the Appointment is created successfully, CareRequestService assigns:

`CareRequest.appointment = Appointment`

This write occurs inside the same outer transaction.

## CareRequest → ClinicalDocument

Attachments are handled through the existing ClinicalDocument service.

Documents are associated with the resulting Appointment.

CareRequest does not create a second storage abstraction.

## Transaction boundary

CareRequestService owns the outer transaction. Existing nested `atomic()` blocks are treated according to Django transaction semantics and must not be interpreted as independent logical transactions.

## Error propagation

Existing domain/service errors are reused where possible. The API layer maps them using existing project conventions.

## Idempotency boundary

CareRequest owns the client-facing idempotency namespace.

Appointment keeps its own existing namespace and does not receive the CareRequest client's literal key.

## Rate-limit boundary

The CareRequest service owns the creation limit. It is evaluated after the authoritative idempotency re-check and before starting the downstream Agenda operation.

## Architectural rule

No Fase 5 component may duplicate a rule already owned by Agenda F2 or ClinicalDocument F4.

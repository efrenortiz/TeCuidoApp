# Fase 5 — Requirements Traceability Matrix

## Purpose

Provide a single traceability view from the approved Fase 5 requirements to the design artifacts and the implementation evidence expected later.

This document does not introduce new requirements.

## Traceability

| Requirement area | Authoritative design | Implementation evidence |
|---|---|---|
| Direct CareRequest creation | `requirements.md`, `phase-5-documents.md` | service/API tests |
| `NUEVA → CONVERTIDA` | `care-request-domain.md`, `care-request-workflow.md` | domain/service tests |
| Agenda as source of truth | `care-request-workflow.md`, F2 Agenda docs | integration/regression tests |
| Slot `start/end` from Agenda | `care-request-workflow.md` | API/service tests |
| Atomic conversion | `care-request-workflow.md` | transaction tests |
| Optional CareRequest → Appointment | `care-request-data-model.md` | model/service tests |
| Responsible authorization | `care-request-permissions.md` | authorization tests |
| Idempotency | `care-request-service-contracts.md` | replay/concurrency tests |
| Rate limiting | `care-request-service-contracts.md`, security document | concurrent rate-limit tests |
| Attachments | `care-request-workflow.md`, security document | file/compensation tests |
| ClinicalDocument reuse | F4 ClinicalDocument docs | integration tests |
| No waiting room | `phase-5-documents.md` | scope review |
| No antivirus | security/privacy design | scope review |
| No independent editing | domain/workflow docs | API/service contract review |
| API behavior | `care-request-api-contracts.md` | API tests |
| UX behavior | `care-request-ux.md`, `care-request-screens.md` | browser/UI tests |

## Precedence

When a requirement and a detailed design document overlap, the approved Design Freeze and detailed contracts provide the implementation detail, while requirements remain the functional source.

Any conflict discovered during implementation must be raised and documented before changing behavior.

## Completion criterion

A requirement is considered implemented only when the relevant code exists and the expected evidence defined by `phase-5-testing-strategy.md` passes.

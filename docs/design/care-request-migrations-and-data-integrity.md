# CareRequest — Migration and Data Integrity Notes

## Purpose

Document the expected database changes for implementation without writing or executing migrations during design.

## New application data

Implementation is expected to introduce the CareRequest persistence model defined in `care-request-data-model.md`.

The model includes:

- required business foreign keys protected with `PROTECT`;
- optional `responsible`;
- optional `appointment` as `OneToOneField`;
- slot `start_at` and `end_at`;
- free-text `motivo`, `padecimiento`, and `descripcion`;
- `NUEVA` / `CONVERTIDA`;
- optional `idempotency_key`;
- timestamps.

## Constraints

The implementation should enforce:

- `start_at < end_at`;
- uniqueness of `(created_by, idempotency_key)` when the key is present;
- OneToOne cardinality for `CareRequest.appointment`.

## Dependency direction

The migration dependency must remain:

`care_requests → appointments`

The `appointments` app must not acquire a model dependency on `care_requests`.

## Deletion behavior

All CareRequest business foreign keys use `PROTECT`.

The Appointment relation also uses `PROTECT`.

## No new ClinicalDocument relation

Do not add a `ClinicalDocument → CareRequest` field as part of Fase 5.

Documents are related to the resulting Appointment through the existing F4 design.

## Migration safety

Implementation must review the current migration graph before creating Fase 5 migrations.

No migration should alter existing F2/F4 data semantics without an explicit approved design change.

## Data-integrity principle

Database constraints provide defensive protection, while cross-table business rules remain in service/application logic.

# Fase 4 — Contratos de servicios

## 1. Frontera

```text
UI/API
  ↓
Service
  ↓
Authorization
  ↓
Transaction
  ↓
ORM/PostgreSQL
```

## 2. Servicios

### PrescriptionService

Operaciones:

- `issue`
- `get`
- `list_for_patient`
- `create_version`
- `void`

### StudyOrderService

Operaciones:

- `issue`
- `get`
- `list_for_patient`
- `create_version`
- `void`

### ClinicalDocumentService

Operaciones:

- `upload`
- `get`
- `list_for_patient`
- `download`
- `create_generated_document`
- `create_version`
- `void_or_inactivate` cuando el tipo lo permita.

## 3. `issue` de Prescription

Entrada conceptual:

```text
actor
patient
clinical_encounter
items[]
metadata
request_id/idempotency_key opcional según infraestructura existente
```

Salida:

```text
Prescription
ClinicalDocument(PDF)
```

Debe ser transaccional.

## 4. `issue` de StudyOrder

Mismo patrón con `items[]`, tipo e indicaciones.

## 5. Lectura

La lectura devuelve recursos ya autorizados; el servicio no delega la autorización a la vista.

## 6. Versionado

`create_version` conserva la versión anterior y crea la nueva de forma atómica.

## 7. Errores mínimos

- `NotFound`
- `PermissionDenied`
- `InvalidState`
- `ValidationError`
- `Conflict`
- `ImmutableResource`
- `ReferenceInconsistency`
- `DocumentStorageError`

**Corrección de consistencia (2026-09-11):** `ImmutableResource` cubre exactamente dos escenarios,
ambos sobre un recurso `ISSUED` o `VOIDED` que ya no admite mutación directa: (1) un intento de
`create_version` que no parte de la versión vigente (`is_current_version=False` — ver D-001,
`clinical-documents-data-model.md` §3); (2) un intento de modificar directamente el contenido de un
recurso `ISSUED`/`VOIDED` en vez de crear una nueva versión. Ver el mapeo a código HTTP en
`phase-4-api-contracts.md` §7.

## 8. Idempotencia

La repetición de la misma intención de emisión no debe crear dos recursos equivalentes.

**Corrección de consistencia (2026-09-11):** se verificó que el proyecto ya cuenta con un
mecanismo de idempotencia (Fase 2: header `Idempotency-Key` + `UniqueConstraint` parcial sobre
`(actor, idempotency_key)` — `appointments/models.py`). Fase 4 reutiliza exactamente ese mecanismo
para `issue`/`create_version`/`void` de `Prescription` y `StudyOrder`; no se diseña un mecanismo
nuevo. Ver la tabla de resolución por escenario en `phase-4-documents-workflow.md` §10.

## 9. Atomicidad PDF/documento

Cuando el contrato exige PDF como resultado de emisión, la operación no debe dejar una emisión incompleta silenciosa.

## 10. No CRUD genérico

No crear `GenericDocumentService` ni exponer escritura genérica para todas las entidades.

# Fase 4 — Contratos API

## 1. Principios

API REST pequeña, explícita y coherente con Fase 3. Las views delegan a servicios.

## 2. Endpoints de Prescription

```text
POST /api/v1/clinical/prescriptions/
GET  /api/v1/clinical/prescriptions/<id>/
POST /api/v1/clinical/prescriptions/<id>/versions/
POST /api/v1/clinical/prescriptions/<id>/void/
```

`POST` de emisión recibe Patient/Encounter e items. No acepta estado arbitrario.

## 3. Endpoints de StudyOrder

```text
POST /api/v1/clinical/study-orders/
GET  /api/v1/clinical/study-orders/<id>/
POST /api/v1/clinical/study-orders/<id>/versions/
POST /api/v1/clinical/study-orders/<id>/void/
```

## 4. Endpoints de documentos

```text
POST /api/v1/clinical/documents/
GET  /api/v1/clinical/documents/<id>/
GET  /api/v1/clinical/documents/?patient=<id>&type=<type>&from=<date>&to=<date>
GET  /api/v1/clinical/documents/<id>/download/
```

La carga usa `multipart/form-data`; los demás endpoints usan JSON salvo descarga.

## 5. Respuestas

Las respuestas devuelven sólo campos autorizados. No exponen `storage_key` físico.

## 6. Códigos mínimos

- `200` lectura/descarga exitosa;
- `201` creación/emisión;
- `400` payload inválido;
- `401` no autenticado;
- `403` no autorizado;
- `404` recurso inexistente o no visible conforme a la política del proyecto;
- `409` conflicto/idempotencia/concurrencia cuando corresponda;
- `413` archivo demasiado grande;
- `415` tipo de archivo no soportado;
- `422` validación de dominio cuando ese patrón ya exista en el proyecto;
- `500/503` sólo para fallos operativos no controlados.

## 7. Errores

Usar shape estable y sin contenido clínico innecesario.

**Corrección de consistencia (2026-09-11):** `phase-4-service-contracts.md` §7 define ocho errores
de dominio sin mapeo explícito a los códigos HTTP de §6, a diferencia del patrón ya cerrado de
Fase 3 (`clinical-api-contracts.md`, tabla explícita error↔código). Se cierra aquí con el mismo
criterio ya usado en Fase 3 (400 para payload malformado, 422 para violaciones de reglas de
dominio sobre un payload bien formado, 409 para conflictos de estado/concurrencia):

| Error de dominio | Código HTTP |
|---|---:|
| `NotFound` | `404` |
| `PermissionDenied` | `403` |
| `ValidationError` | `400` |
| `InvalidState` (p. ej. anular con datos distintos un recurso ya `VOIDED`) | `409` |
| `Conflict` (idempotencia/concurrencia — ver `phase-4-documents-workflow.md` §10) | `409` |
| `ImmutableResource` (versión superada, o intento de editar directamente un `ISSUED`) | `409` |
| `ReferenceInconsistency` (p. ej. `clinical_encounter` no pertenece al `patient` indicado) | `422` |
| `DocumentStorageError` | `500`/`503` |

## 8. Autorización

Cada endpoint llama a los servicios autorizados. Un endpoint no puede asumir que el frontend ya validó el actor.

## 9. Descarga

El endpoint no devuelve una URL pública permanente. Sirve el archivo mediante el mecanismo privado existente o emite una referencia temporal sólo si el almacenamiento actual ya lo soporta de forma segura.

## 10. Versionado

No existe `PUT` de reemplazo sobre un recurso emitido. Se utiliza `POST .../versions/`.

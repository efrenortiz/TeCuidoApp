# ADR-029 — Document Services as Application Boundary, No Generic CRUD

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Arquitectura / Servicios

## 1. Contexto

Fase 3 ya cerró (ADR-018) que la lógica clínica vive en servicios, no en vistas, y que la API es
una capa delgada sobre ellos. Fase 4 introduce tres entidades con reglas propias.

## 2. Decisión

Tres servicios, uno por entidad, todos siguiendo la misma frontera ya establecida:

```text
UI/API → Service → Authorization → Transaction → ORM/PostgreSQL
```

```text
PrescriptionService: issue, get, list_for_patient, create_version, void
StudyOrderService:   issue, get, list_for_patient, create_version, void
ClinicalDocumentService: upload, get, list_for_patient, download,
                         create_generated_document, create_version,
                         void_or_inactivate
```

No se crea un `GenericClinicalDocumentService` ni un CRUD genérico que exponga escritura uniforme
para las tres entidades — cada una conserva sus propias reglas de negocio (campos obligatorios,
transiciones de estado, idempotencia) en su propio servicio.

Errores de dominio uniformes entre los tres servicios: `NotFound`, `PermissionDenied`,
`InvalidState`, `ValidationError`, `Conflict`, `ImmutableResource`, `ReferenceInconsistency`,
`DocumentStorageError` — mapeados a HTTP en `phase-4-api-contracts.md` §7.

## 3. Reglas derivadas

- La autorización se resuelve siempre dentro del servicio, nunca delegada a la vista/API.
- La idempotencia de `issue`/`create_version`/`void` reutiliza el mecanismo de `Idempotency-Key` ya
  establecido en Fase 2 (`appointments/models.py`), sin diseñar uno nuevo.
- Ningún servicio expone una operación de escritura genérica ("update arbitrario de campos").

## 4. Alternativas consideradas

### Un solo DocumentService genérico parametrizado por tipo de entidad
**Rejected.** `Prescription` (medicamentos, dosis) y `StudyOrder` (tipo de estudio) tienen reglas
de validación estructuralmente distintas; forzarlas a un servicio genérico produciría
condicionales por tipo en vez de contratos explícitos — exactamente lo que el contrato de Fase 4
prohíbe (§16).

### Exponer un CRUD REST estándar (ModelViewSet genérico) sobre los tres modelos
**Rejected.** Permitiría mutaciones no contempladas por el dominio (p. ej. un `PATCH` arbitrario
sobre un recurso `ISSUED`), contradiciendo la inmutabilidad ya cerrada (ADR-023/024).

## 5. Consecuencias

Positivas:
- consistencia total con el patrón de servicios ya validado en Fase 3;
- cada entidad puede evolucionar sus reglas sin afectar a las otras dos.

Negativas:
- alguna duplicación estructural entre los tres servicios (patrones de idempotencia, versión,
  anulación se repiten en cada uno en vez de heredarse de una base común) — aceptada
  explícitamente para evitar una abstracción prematura.

## 6. Relación

Complementa `ADR-018` (Clinical Services as Application Boundary).

## 7. Estado

**Accepted.**

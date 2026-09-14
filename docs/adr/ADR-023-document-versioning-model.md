# ADR-023 — Document Versioning Model: New Row per Correction, Explicit Current-Version Flag

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Integridad de datos / Concurrencia

## 1. Contexto

`Prescription`, `StudyOrder` y `ClinicalDocument` son artefactos históricos: una vez emitidos, no
se sobrescriben. Una corrección debe producir una nueva versión trazable sin perder la anterior.

## 2. Problema

La documentación original de Fase 4 cerraba conceptualmente que "sólo una versión puede ser
vigente en una cadena documental" (VR-003) en tres documentos distintos, pero ninguno especificaba
cómo se persiste esa condición ni cómo se resuelve la concurrencia de dos correcciones
simultáneas — un desarrollador podría implementarlo de formas incompatibles (traversal derivado
vs. flag explícito, con o sin bloqueo transaccional).

## 3. Decisión

Cada corrección crea una **nueva fila** (nuevo `Prescription`/`StudyOrder`/`ClinicalDocument`) con
`version_number` incrementado y `previous_version_id` apuntando a la versión anterior. La versión
vigente se identifica mediante un campo explícito `is_current_version` (booleano):

- al crear la versión N+1, la misma transacción marca la versión N como `is_current_version=False`
  y la N+1 como `is_current_version=True`;
- la corrección siempre parte de la versión conocida por su propio `id` (nunca de un "id de
  cadena"); el servicio adquiere `select_for_update()` sobre esa fila antes de mutarla;
- si dos correcciones compiten sobre la misma versión, la segunda —tras el lock— encuentra
  `is_current_version=False` (la primera ya la cambió) y se rechaza con `Conflict` (409), sin
  crear una versión huérfana.

No se introduce una columna adicional de "id de cadena/raíz": no es necesaria porque cada
corrección siempre referencia la versión actual por su propio identificador, nunca por la del
primer eslabón.

## 4. Reglas derivadas

- `is_current_version` existe en `Prescription`, `StudyOrder` y en `ClinicalDocument` cuando es
  versionable.
- La invariante se protege a nivel de servicio/transacción (`select_for_update` + verificación
  post-lock), no mediante un constraint de unicidad parcial de PostgreSQL — no hay una columna de
  agrupación ("cadena") sobre la cual definir ese constraint sin agregar complejidad adicional.
- Una versión anterior permanece accesible según permisos (VR-004); nunca se oculta ni se borra.

## 5. Alternativas consideradas

### Mutar la misma fila y guardar el histórico en una tabla de auditoría/snapshot
**Rejected.** Contradice la inmutabilidad exigida (`requirements.md` §24, contrato §11) y mezclaría
historia de negocio con audit trail (ADR-017: `Clinical History ≠ Audit Trail`).

### Determinar la versión vigente por ausencia de referencias (`NOT EXISTS` sobre `previous_version_id`)
**Rejected.** Funciona en teoría pero exige una subconsulta en cada lectura y es frágil ante bugs
de aplicación (una versión intermedia sin sucesor por error quedaría indistinguible de la vigente
real). Un flag explícito es más simple y más barato de consultar (índice directo).

### Constraint de unicidad parcial de PostgreSQL para "una vigente por cadena"
**Rejected para esta fase.** Requeriría una columna adicional de agrupación que ningún documento
había cerrado; la protección transaccional ya usada en Fase 3 para invariantes de exclusividad
análogas es suficiente y más simple.

## 6. Consecuencias

Positivas:
- una única fuente de verdad simple (`is_current_version=True`) para "cuál es la versión vigente";
- reutiliza el patrón transaccional ya validado en Fase 3, sin infraestructura nueva.

Negativas:
- la exclusividad de "una vigente por cadena" depende de la disciplina del servicio (no hay un
  constraint de base de datos que la garantice de forma independiente del código de aplicación).

## 7. Relación

Complementa `ADR-016` (No Reopen or Functional Delete) y `ADR-019` (Server/DB as Source of Truth).

## 8. Estado

**Accepted.**

# ADR-024 — No Functional DELETE; VOIDED/ACTIVE for Logical Cancellation

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Integridad de datos / Historia clínica

## 1. Contexto

Fase 3 ya cerró (ADR-016) que un `ClinicalEncounter` `COMPLETED` no admite reapertura, edición ni
`DELETE` funcional. Fase 4 extiende el mismo principio a documentos clínicos, recetas y
solicitudes de estudio.

## 2. Decisión

No existe `DELETE` funcional para `Prescription`, `StudyOrder` ni `ClinicalDocument` una vez
emitidos/persistidos. La salida de vigencia se representa mediante anulación lógica:

- `Prescription`/`StudyOrder`: estados `ISSUED`/`VOIDED`.
- `ClinicalDocument` sin `Prescription`/`StudyOrder` que lo respalde: estado propio
  `ACTIVE`/`VOIDED` (ver ADR-023 y `clinical-documents-data-model.md` §3, D-002). Un
  `ClinicalDocument` respaldado por `Prescription`/`StudyOrder` no duplica ese estado: su vigencia
  sigue la de la entidad que lo respalda.

Toda anulación requiere motivo, actor y timestamp, y se audita. Una anulación repetida con el
mismo motivo sobre un recurso ya `VOIDED` es idempotente (no duplica el evento ni cambia
`voided_at`, mismo criterio que SC-065 de Fase 3); con datos distintos, se rechaza con
`InvalidState`.

## 3. Reglas derivadas

- Ningún endpoint expone una operación `DELETE` sobre estos recursos.
- El archivo físico de un documento anulado permanece almacenado y accesible según permisos —
  anular no borra el binario.
- La eliminación física de un archivo (distinta de la anulación lógica) sólo puede ocurrir para
  artefactos huérfanos no referenciados por ningún `ClinicalDocument` (ver ADR-027 §6, limpieza
  de compensación síncrona), nunca para un documento con historial clínico.

## 4. Alternativas consideradas

### Permitir DELETE físico para archivos subidos por error, antes de cualquier lectura
**Rejected.** Introduce ambigüedad sobre "cuándo es seguro borrar" y contradice el principio
uniforme de Fase 3 (`requirements.md` §11: "no eliminar información clínica histórica de forma
destructiva"). La anulación lógica (`ACTIVE`→`VOIDED`) cubre el caso sin excepciones.

## 5. Consecuencias

Positivas:
- consistencia total con el principio de historia clínica ya cerrado en Fase 3;
- ningún camino de código expone una operación destructiva sobre datos clínicos.

Negativas:
- documentos subidos por error permanecen almacenados (aunque inaccesibles funcionalmente vía
  anulación), lo que requiere una política operativa de retención fuera del alcance de Fase 4.

## 6. Relación

Complementa `ADR-016` (No Reopen or Functional Delete — Fase 3).

## 7. Estado

**Accepted.**

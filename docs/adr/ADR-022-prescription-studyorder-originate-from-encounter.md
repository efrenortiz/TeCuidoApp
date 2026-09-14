# ADR-022 — Prescription and StudyOrder Originate from ClinicalEncounter

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Dominio clínico / Integridad

## 1. Contexto

Una receta o solicitud de estudio siempre se emite en el contexto de una atención clínica. Fase 3
ya estableció que `ClinicalEncounter` se origina exclusivamente en una `Appointment` válida
(ADR-009) y que su ciclo de vida (`IN_PROGRESS`/`COMPLETED`) es cerrado.

## 2. Problema

Sin una regla explícita, `Prescription`/`StudyOrder` podrían crearse de forma independiente (sin
contexto clínico verificable), o su emisión podría alterar accidentalmente el estado del
`ClinicalEncounter` que las origina.

## 3. Decisión

`Prescription` y `StudyOrder` requieren obligatoriamente un `clinical_encounter_id`. No existen de
forma independiente. `patient` y `doctor` se derivan siempre de ese `ClinicalEncounter`
(`clinical_encounter.appointment.patient`, `clinical_encounter.doctor`) en el servicio de emisión;
nunca se aceptan como parámetros independientes del cliente.

La emisión no exige que el encounter esté `COMPLETED`: puede ocurrir durante `IN_PROGRESS`. La
emisión, corrección o anulación de un documento **nunca** cambia el estado de `ClinicalEncounter`
ni de `Appointment`.

## 4. Reglas derivadas

- `PrescriptionService.issue`/`StudyOrderService.issue` reciben `clinical_encounter`, nunca
  `patient` de forma independiente.
- Un `ClinicalEncounter` puede originar múltiples `Prescription`/`StudyOrder` (no hay cardinalidad
  1:1 — un médico puede emitir varias recetas en la misma consulta).
- La relación con `Appointment` (vía `clinical_encounter.appointment`) es contextual/derivada, no
  una FK directa adicional en `Prescription`/`StudyOrder`.

## 5. Alternativas consideradas

### Permitir Prescription sin ClinicalEncounter (p. ej. "receta administrativa")
**Rejected.** Rompe la trazabilidad clínica exigida por `requirements.md` §21/45 y no está en el
alcance funcional aprobado de Fase 4.

### Cambiar el estado de ClinicalEncounter al emitir un documento
**Rejected.** Contradice ADR-010 (estados exactos `IN_PROGRESS`/`COMPLETED`, cierre atómico ya
cerrado) — reabrir esa decisión no está justificado por una necesidad real de Fase 4.

## 6. Consecuencias

Positivas:
- trazabilidad clínica completa (todo documento remonta a una atención real);
- `ClinicalEncounter` permanece con su semántica de Fase 3 intacta.

Negativas:
- un documento no puede emitirse fuera de un `ClinicalEncounter` existente, incluso en casos
  administrativos hipotéticos futuros (requeriría una decisión explícita posterior).

## 7. Relación

Complementa `ADR-009` (Appointment as Origin of ClinicalEncounter) y `ADR-010` (ClinicalEncounter
State and Atomic Closure).

## 8. Estado

**Accepted.**

# ADR-010 — ClinicalEncounter State and Atomic Closure

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Consistencia transaccional

## 1. Contexto

El encuentro debe permitir trabajo incremental, interrupción y reanudación, pero no modificación después de su finalización.

## 2. Decisión

El estado técnico de `ClinicalEncounter` será:

```text
IN_PROGRESS → COMPLETED
```

No se introducen estados adicionales en Fase 3.

La finalización será atómica con la cita:

```text
ClinicalEncounter: IN_PROGRESS → COMPLETED
Appointment:      IN_CONSULTATION → COMPLETED
```

Ambas transiciones deben confirmarse o revertirse como una sola transacción.

## 3. Reglas técnicas

- Guardados parciales mantienen `IN_PROGRESS`.
- Una interrupción no cambia automáticamente el estado.
- No existe auto-cierre por tiempo.
- No se permite `COMPLETED → IN_PROGRESS`.
- El último contenido enviado con "Completar" debe formar parte de la transacción de cierre.
- Un doble `complete` no crea efectos duplicados; debe reconocer el estado final o rechazar de forma determinista según el contrato.

## 4. Invariantes

```text
IN_PROGRESS => Appointment = IN_CONSULTATION
COMPLETED   => Appointment = COMPLETED
```

La arquitectura debe impedir quedar de forma persistente en:

```text
Encounter COMPLETED + Appointment IN_CONSULTATION
```

## 5. Alternativas rechazadas

### Estados como `PAUSED`, `WAITING` o `AUTO_CLOSED`
**Rejected.** No resuelven un requisito F3 y agregan transiciones.

### Cerrar solo ClinicalEncounter
**Rejected.** Permitiría inconsistencias visibles entre Agenda y atención clínica.

## 6. Consecuencias

Positivas:
- máquina de estados pequeña;
- cierre fuerte y verificable;
- recuperación simple ante interrupciones.

Negativas:
- requiere transacciones y pruebas concurrentes explícitas.

## 7. Relación

Implementa las reglas de workflow y complementa `ADR-006`.

## 8. Estado

**Accepted.**

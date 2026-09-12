# ADR-009 — Appointment Originates ClinicalEncounter

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Modelo de atención

## 1. Contexto

Fase 3 define que una consulta clínica se inicia desde una cita válida. Debe existir una relación inequívoca entre la atención clínica y su evento de Agenda.

## 2. Decisión

`Appointment` es el origen obligatorio de un `ClinicalEncounter` en Fase 3.

Cardinalidad:

```text
Appointment 1 ─── 0..1 ClinicalEncounter
```

En `ClinicalEncounter`, la referencia a `Appointment` es obligatoria y única.

Un encuentro solo puede crearse durante el caso de uso de inicio de una cita elegible. No habrá endpoint ni servicio de "consulta clínica independiente" en Fase 3.

## 3. Transición arquitectónica

El inicio coordina:

```text
Appointment SCHEDULED
        ↓
Appointment IN_CONSULTATION
        +
ClinicalEncounter IN_PROGRESS
```

Ambos efectos pertenecen a una misma operación transaccional.

## 4. Razón

La decisión mantiene una sola fuente de verdad para la elegibilidad de inicio y permite rastrear el origen de cada atención sin duplicar agenda.

## 5. Consecuencias

- Una cita puede existir sin encuentro.
- Cancelación y `NO_SHOW` no generan encuentro.
- Un encuentro siempre puede remontarse a una cita concreta.
- La consulta clínica no redefine la duración ni la disponibilidad de Agenda.

## 6. Alternativa rechazada

Permitir encuentros sin cita. **Rejected** en Fase 3 porque rompería la frontera establecida entre Agenda y atención y requeriría reglas adicionales de autorización, origen y trazabilidad.

## 7. Relación

Depende de `ADR-008` y complementa `ADR-010` sobre ciclo de vida y cierre.

## 8. Estado

**Accepted.**

# ADR-014 — DoctorPatientRelationship Independence

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Relaciones de dominio

## 1. Contexto

Fase 2 establece `DoctorPatientRelationship` como relación de dominio independiente. Un médico puede atender por primera vez a un paciente mediante una cita válida sin que exista previamente esa relación.

## 2. Decisión

`DoctorPatientRelationship` no será creada, activada, modificada ni sustituida automáticamente por `Appointment` o `ClinicalEncounter`.

Las dos relaciones representan conceptos diferentes:

```text
Doctor ↔ Patient relationship

Appointment / ClinicalEncounter
        ↕
   specific care event
```

## 3. Razón

Una atención aislada no demuestra por sí sola una relación permanente o continua, y una relación preexistente tampoco constituye una cita ni un encuentro.

## 4. Consecuencias

- Crear una cita no crea la relación.
- Iniciar una consulta no crea la relación.
- Completar una consulta no crea la relación.
- La relación puede existir sin encuentros recientes.
- La autorización clínica puede utilizar la relación cuando su política lo requiera, sin convertirla en efecto secundario de atender.

## 5. Alternativa rechazada

### Auto-activación de DoctorPatientRelationship al primer encuentro
**Rejected.** Mezcla autorización/continuidad de atención con el simple hecho de haber prestado un servicio.

## 6. Relación

Complementa `ADR-004` y las reglas de `clinical-permissions.md`.

## 7. Estado

**Accepted.**

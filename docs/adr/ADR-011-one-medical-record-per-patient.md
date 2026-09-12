# ADR-011 — One MedicalRecord per Patient

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Persistencia clínica

## 1. Contexto

El expediente debe ser longitudinal y no crear copias por consulta, médico, clínica o etapa de vida.

## 2. Decisión

Cada `Patient` tendrá como máximo un `MedicalRecord`, y el modelo será único por paciente:

```text
Patient 1 ─── 1 MedicalRecord
```

**Aclaración normativa (revisión de consistencia, 2026-09-11 — misma redacción en `clinical-record-domain.md` y `clinical-data-model.md`):**

> Conceptualmente cada `Patient` tiene un único `MedicalRecord`. En persistencia, el registro puede no existir todavía porque su creación es lazy. Por eso el estado técnico previo a su creación puede representarse como `Patient 1 ─── 0..1 MedicalRecord`. Una vez creado, el `MedicalRecord` es único, no se duplica y no cambia de `Patient`. El `0..1` es exclusivamente un estado técnico transitorio anterior a la primera operación clínica — nunca una cardinalidad funcional permanente que permita a un paciente quedar sin expediente después de haber iniciado atención clínica.

La relación será estable mientras exista el paciente. El expediente no se reasigna a otro paciente.

## 3. Creación

Se permite creación lazy: el expediente puede crearse en la primera operación clínica que lo necesite, dentro de la transacción correspondiente. La creación debe ser idempotente y protegida por una restricción única de base de datos.

## 4. Propiedad

`MedicalRecord` es propiedad clínica del paciente, no del médico ni de la cita.

Crear un encuentro no crea un expediente nuevo por cada atención.

## 5. Consecuencias

- Toda la historia longitudinal del paciente puede agregarse al mismo expediente.
- Cambiar de médico no crea otro expediente.
- Cambiar de clínica no crea otro expediente.
- Pasar de menor a adulto no crea otro expediente.

## 6. Alternativas rechazadas

### Expediente por médico
**Rejected.** Fragmentaría la historia.

### Expediente por cita
**Rejected.** Duplicaría estructura e impediría una identidad longitudinal.

### Copias de expediente por clínica
**Rejected.** La clínica es un contexto operativo, no la identidad del expediente.

## 7. Relación

Se apoya en `ADR-005`, `ADR-006` y `ADR-008`.

## 8. Estado

**Accepted.**

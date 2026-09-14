# ADR-028 — Document Authorization Inherits Fase 3 Clinical Policy

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Seguridad / Autorización

## 1. Contexto

Fase 3 cerró una distinción importante en `clinical-permissions.md` (P-009/P-010/P-011/P-013):
un médico asignado a una atención puntual (un `ClinicalEncounter` concreto) puede leer/actuar sobre
ESE encuentro, pero no obtiene por eso acceso histórico permanente al paciente — eso requiere una
`DoctorPatientRelationship` vigente y autorizante. Un documento clínico (receta, solicitud, archivo)
es, por definición, un artefacto histórico consultable fuera del encuentro que lo originó.

## 2. Problema

La primera versión de `phase-4-permissions.md` colapsaba toda autorización médica bajo una única
columna "Médico autorizado", sin preservar esta distinción — un desarrollador podría implementar
esto otorgando a cualquier médico asignado a UN encuentro acceso a TODO el historial documental del
paciente, violando P-009/P-010.

## 3. Decisión

Fase 4 no crea una política de autorización nueva: reutiliza exactamente la de Fase 3, aplicada al
recurso documental concreto:

- **Emitir** una `Prescription`/`StudyOrder`: requiere ser el médico asignado al
  `ClinicalEncounter` que da contexto a la operación (igual que iniciar/completar un encuentro,
  P-011/P-012). No requiere `DoctorPatientRelationship`.
- **Leer/descargar documentos del encuentro que el médico atendió**: autorizado por la misma
  asignación.
- **Leer/descargar el historial documental completo del paciente** (documentos de otros
  encuentros): requiere `DoctorPatientRelationship` vigente y autorizante (P-009) — la sola
  asignación a una atención puntual no abre este acceso (P-010).
- **Corregir/anular**: requiere ser el autor del `ClinicalEncounter` de origen, o tener relación
  activa que lo autorice — igual criterio que emitir.
- Paciente/Responsable: acceso según su propio expediente y `ResponsiblePatientRelationship.status
  == ACTIVE`, sin cambios respecto a Fase 3.
- Administrador: acceso global conforme a Fase 1–3, sujeto a auditoría en operaciones sensibles.

La existencia de un documento nunca crea ni modifica una `DoctorPatientRelationship`.

## 4. Reglas derivadas

- `phase-4-permissions.md` §2 usa dos columnas médicas separadas ("médico asignado al encuentro
  actual" / "médico con relación activa"), nunca una sola columna ambigua.
- Ningún endpoint acepta `patient_id`/`document_id`/`prescription_id`/`study_order_id` como prueba
  suficiente de autorización (protección IDOR, igual que Fase 3).

## 5. Alternativas consideradas

### Otorgar acceso documental completo a cualquier médico asignado a una cita del paciente
**Rejected.** Contradice directamente P-009/P-010, decisión ya cerrada de Fase 3 que este ADR no
tiene motivo real para reabrir.

### Exigir DoctorPatientRelationship incluso para leer los documentos del propio encuentro atendido
**Rejected.** Sería más restrictivo que la propia Fase 3 para el caso simétrico
(`ClinicalEncounter`), sin justificación funcional — un médico ya autorizado a atender y completar
el encuentro debe poder ver la receta que él mismo emitió en ese encuentro.

## 6. Consecuencias

Positivas:
- ninguna regresión de seguridad respecto a la política ya validada de Fase 3;
- una sola fuente de verdad de autorización clínica para las cuatro fases.

Negativas:
- un médico sin relación activa que atendió una única consulta no puede ver documentos previos del
  paciente aunque estén clínicamente relacionados — limitación ya aceptada y documentada en Fase 3.

## 7. Relación

Complementa `ADR-014` (DoctorPatientRelationship Independence) y `ADR-015` (Clinical Authorization
Boundary).

## 8. Estado

**Accepted.**

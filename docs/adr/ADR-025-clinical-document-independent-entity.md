# ADR-025 — ClinicalDocument as Independent Entity with Mandatory Patient, Optional Clinical Context

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Modelo de datos / Dominio

## 1. Contexto

`ClinicalDocument` debe representar tanto archivos subidos directamente (sin receta ni solicitud
de por medio) como PDFs generados a partir de `Prescription`/`StudyOrder`. Necesita relacionarse
opcionalmente con varias entidades clínicas sin duplicar ninguna.

## 2. Decisión

`ClinicalDocument` pertenece obligatoriamente a un `Patient`. Sus demás relaciones
(`appointment_id`, `clinical_encounter_id`, `prescription_id`, `study_order_id`) son FKs nullable,
usadas sólo cuando tienen significado clínico real. No se agrega una FK a `MedicalRecord`: `Patient`
ya determina inequívocamente el expediente (mismo principio que Fase 3 aplica a `AuditEvent` y
`ClinicalEncounter`).

`document_type` distingue el tipo de artefacto (`LABORATORY`, `IMAGING`, `HISTOPATHOLOGY`,
`PHOTOGRAPH`, `PRESCRIPTION`, `INSTRUCTIONS`, `STUDY_ORDER`, `OTHER`). Un PDF `GENERATED` a partir
de una `StudyOrder` siempre usa `document_type = STUDY_ORDER` (nunca el tipo de estudio de la
propia orden); los valores `LABORATORY`/`IMAGING`/`HISTOPATHOLOGY` quedan reservados para
documentos `UPLOADED` (ver `clinical-document-domain.md` §4, CD-008).

## 3. Reglas derivadas

- Un `ClinicalDocument` nunca existe sin `Patient` (CD-001).
- `origin` distingue `UPLOADED`/`GENERATED`.
- El nombre físico de almacenamiento (`storage_key`) es independiente del nombre original
  suministrado por el cliente (ver ADR-026).

## 4. Alternativas consideradas

### FK obligatoria a MedicalRecord en vez de/además de Patient
**Rejected.** `MedicalRecord` es 1:1 con `Patient` (ADR-011); una FK adicional sería puramente
redundante y violaría el principio de no introducir relaciones equivalentes ya cerrado en Fase 3.

### Un único document_type para todo PDF generado ("GENERATED_PDF" genérico)
**Rejected.** Perdería la distinción funcional entre "esto es una receta" y "esto es una orden de
estudio", necesaria para filtros de historial documental (`phase-4-documents.md` §18).

## 5. Consecuencias

Positivas:
- un único punto de verdad para "a qué paciente pertenece este documento";
- tipificación suficientemente expresiva sin catálogo externo.

Negativas:
- cuatro FKs nullable en la misma tabla; el modelo debe documentar explícitamente cuáles
  combinaciones tienen sentido (p. ej. `study_order_id` sin `clinical_encounter_id` no debería
  ocurrir en la práctica, aunque el esquema no lo prohíba a nivel de constraint).

## 6. Relación

Complementa `ADR-011` (One MedicalRecord per Patient) y `ADR-021` (Clinical Documents Domain
Boundary).

## 7. Estado

**Accepted.**

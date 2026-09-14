# ADR-021 — Clinical Documents Domain Boundary

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Arquitectura / Límites de dominio / Django

## 1. Contexto

Fase 4 incorpora recetas, solicitudes de estudio y documentos clínicos adjuntos. Fase 3 ya
estableció `medical_records` como propietario de `ClinicalEncounter` y `MedicalRecord`; Fase 2
estableció `appointments` como propietario de `Appointment`.

## 2. Problema

Sin una frontera explícita, la nueva funcionalidad documental podría terminar dispersa dentro de
`medical_records` (acoplando un dominio ya cerrado a nuevas entidades) o duplicando `Patient`,
`Doctor`, `Clinic`, `Appointment`, `ClinicalEncounter` o `MedicalRecord`.

## 3. Decisión

El dominio documental de Fase 4 se ubica en tres apps Django especializadas:

```text
prescriptions/
    └── Prescription
        └── PrescriptionItem

study_orders/
    └── StudyOrder
        └── StudyOrderItem

clinical_documents/
    └── ClinicalDocument
```

Ninguna de las tres duplica `Patient`, `Doctor`, `Clinic`, `Appointment`, `ClinicalEncounter` ni
`MedicalRecord`. La relación lógica es:

```text
Patient
 ├── MedicalRecord
 ├── ClinicalEncounter
 ├── Prescription
 ├── StudyOrder
 └── ClinicalDocument
```

## 4. Reglas derivadas

- `medical_records` no adquiere responsabilidades documentales nuevas.
- `Prescription` y `StudyOrder` referencian `ClinicalEncounter` como contexto, sin alterar su
  ciclo de vida (ver ADR-022).
- No se crea un `GenericClinicalDocumentService` que absorba las tres apps en una sola
  abstracción (ver ADR-029).

## 5. Alternativas consideradas

### Extender `medical_records` con las nuevas entidades
**Rejected.** Mezclaría el dominio de la consulta clínica (ya cerrado en Fase 3) con el dominio
documental, aumentando el acoplamiento y el radio de cambio de una app ya estable.

### Una sola app `clinical_documents` para las tres entidades
**Rejected.** `Prescription` y `StudyOrder` tienen ciclo de vida y reglas propias (ADR-022); una
sola app las trataría como casos particulares de un documento genérico, contradiciendo el
principio de simplicidad de Fase 4 (evitar abstracciones prematuras).

## 6. Consecuencias

Positivas:
- frontera clara entre consulta clínica (Fase 3) y documentos (Fase 4);
- cada app tiene su propio ciclo de migraciones y tests;
- reutilización íntegra de las entidades canónicas existentes.

Negativas:
- tres apps nuevas en vez de una, con las importaciones cruzadas correspondientes;
- `ClinicalDocument` debe referenciar `Prescription`/`StudyOrder` mediante FK nullable en vez de
  vivir dentro de la misma app.

## 7. Relación

Complementa `ADR-005` (Django App Boundaries), `ADR-008` (Clinical Domain Boundary) y `ADR-018`
(Clinical Services as Application Boundary).

## 8. Estado

**Accepted.** Cambios que muevan ownership entre estas apps requieren un nuevo ADR o revisión
explícita de esta decisión.

# Fase 4 — Dominio StudyOrder

## 1. Propósito

Representa una solicitud clínica de estudios emitida por un médico para un paciente en el contexto de un ClinicalEncounter.

## 2. Identidad

Una StudyOrder:

- pertenece a Patient;
- tiene Doctor emisor;
- requiere ClinicalEncounter;
- contiene uno o más StudyOrderItems al emitirse.

## 3. Datos

StudyOrder:

- patient;
- doctor;
- clinical_encounter;
- status;
- issued_at;
- type/context cuando aplique;
- indications;
- observations;
- version_number;
- previous_version;
- is_current_version (mismo significado que en Prescription — D-001,
  `clinical-documents-data-model.md` §3);
- voided_at;
- void_reason.

StudyOrderItem:

- study_order;
- position;
- study_name;
- specific_instructions opcionales.

## 4. Tipos

```text
LABORATORY
IMAGING
HISTOPATHOLOGY
OTHER
```

## 5. Estados

```text
ISSUED → VOIDED
```

## 6. Corrección

Nueva versión enlazada, nunca overwrite.

## 7. Resultados

No se modelan resultados, interpretación ni seguimiento del estudio en Fase 4.

## 8. Catálogo

No existe catálogo obligatorio. El nombre del estudio se almacena explícitamente.

## 9. No dependencia con CareRequest

La StudyOrder no requiere CareRequest para ser emitida.

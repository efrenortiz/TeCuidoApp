# Fase 4 — Dominio Prescription

## 1. Propósito

Representa una receta emitida por un médico para un paciente dentro del contexto de un ClinicalEncounter.

## 2. Identidad y cardinalidad

Una Prescription:

- pertenece a un Patient;
- tiene un Doctor emisor;
- requiere un ClinicalEncounter;
- contiene uno o más PrescriptionItems para emisión.

## 3. Datos explícitos

Prescription:

- patient;
- doctor;
- clinical_encounter;
- status;
- issued_at;
- voided_at opcional;
- void_reason opcional;
- version_number;
- previous_version opcional;
- is_current_version (sólo la versión vigente de la cadena es `True` — D-001,
  `clinical-documents-data-model.md` §3);
- actor/timestamps conforme al modelo de auditoría y versión.

PrescriptionItem:

- prescription;
- position;
- medication_name;
- presentation opcional;
- dose;
- dose_unit opcional;
- route;
- frequency;
- duration opcional;
- instructions.

## 4. Estados

```text
ISSUED → VOIDED
```

No se agrega `DRAFT` persistente como estado de negocio obligatorio. Los datos sin emitir pueden vivir en la transacción/formulario hasta la emisión.

## 5. Emisión

La emisión valida autorización, integridad de items, crea la receta, genera su documento y audita la operación.

## 6. Corrección

Una corrección crea una nueva Prescription con mayor `version_number` y referencia a la anterior. La versión previa permanece inmutable.

## 7. Anulación

La anulación no elimina. Requiere motivo y actor.

## 8. Catálogo farmacológico

No existe catálogo obligatorio en Fase 4. `medication_name` es texto explícito.

## 9. Límites

No se modelan dispensación, surtido, sustitución farmacéutica ni estado de farmacia.

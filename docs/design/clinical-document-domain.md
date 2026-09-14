# Fase 4 — Dominio ClinicalDocument

## 1. Propósito

`ClinicalDocument` representa la entidad documental clínica y sus metadatos. No equivale al binario: el archivo es el artefacto asociado.

## 2. Identidad

Cada documento clínico tiene identidad propia y pertenece obligatoriamente a un Patient.

## 3. Relaciones

Relaciones contextuales opcionales:

- Appointment;
- ClinicalEncounter;
- Prescription;
- StudyOrder.

No se agrega una relación redundante a MedicalRecord cuando Patient ya identifica el expediente.

## 4. Tipos

```text
LABORATORY
IMAGING
HISTOPATHOLOGY
PHOTOGRAPH
PRESCRIPTION
INSTRUCTIONS
STUDY_ORDER
OTHER
```

El PDF `GENERATED` de una `StudyOrder` siempre usa `document_type = STUDY_ORDER` (nunca
`LABORATORY`/`IMAGING`/`HISTOPATHOLOGY`, que quedan reservados para documentos `UPLOADED` — ver
CD-008, `phase-4-documents-rules.md`).

## 5. Origen

```text
UPLOADED
GENERATED
```

## 6. Estado documental

Fase 4 evita un workflow complejo. Cuando una entidad específica tenga ciclo de vida (`Prescription`, `StudyOrder`), su estado se mantiene en esa entidad. `ClinicalDocument` no duplica estados farmacológicos o de órdenes.

**Corrección de consistencia (2026-09-11):** un `ClinicalDocument` que NO está respaldado por
`Prescription`/`StudyOrder` (p. ej. un archivo subido directamente) sí necesita su propio estado
para poder inactivarse sin `DELETE` — ver CD-007 (`phase-4-documents-rules.md`) y D-002
(`clinical-documents-data-model.md` §3), que cierran exactamente la "estrategia de inactivación"
que `phase-4-documents.md` §12 anunciaba sin definir.

## 7. Versionado

Un documento versionable mantiene número de versión, referencia a la versión anterior, actor y timestamp. Una versión emitida es inmutable.

## 8. Archivo

El documento conserva:

- referencia al almacenamiento privado;
- nombre original;
- MIME;
- tamaño;
- origen;
- timestamp;
- actor.

El nombre físico se genera de forma segura e independiente.

## 9. Inmutabilidad

La corrección del contenido crea una nueva versión. No se sobrescribe el archivo histórico.

## 10. Reglas de dominio

- patient obligatorio;
- actor obligatorio para operaciones humanas autenticadas;
- archivo requerido cuando el documento depende de un archivo;
- un documento generado debe poder reconstruirse desde la operación de emisión sin cambiar el histórico;
- un documento no puede pertenecer a dos pacientes.

## 11. Dependencias

El dominio reutiliza Authorization y Audit Trail de Fase 3 y no redefine sus políticas base.

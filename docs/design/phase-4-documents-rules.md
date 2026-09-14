# Fase 4 — Reglas y políticas de documentos clínicos

## 1. Fuente y precedencia

Este documento deriva de `phase-4-documents.md`. Las decisiones previas de Fases 1–3 conservan precedencia cuando sean referenciadas.

## 2. Identidad y propiedad

- Todo `ClinicalDocument` clínico pertenece a un Patient.
- Prescription y StudyOrder pertenecen a un Patient y se originan en un ClinicalEncounter.
- No se duplican Patient, Doctor, Clinic, Appointment, ClinicalEncounter ni MedicalRecord.

## 3. Prescription

### PR-001
Una Prescription debe identificar patient, doctor y clinical_encounter. `patient` se deriva
siempre de `clinical_encounter.appointment.patient` en el servicio de emisión; nunca se acepta
como parámetro independiente del cliente (revisión de consistencia, 2026-09-11 — ver
`clinical-documents-data-model.md` §3, D-003).

### PR-002
Una Prescription requiere al menos un PrescriptionItem para poder emitirse.

### PR-003
Los campos del medicamento son explícitos; no se requiere catálogo farmacológico.

### PR-004
`ISSUED` es el estado emitido y `VOIDED` el estado anulado.

### PR-005
Una Prescription emitida no se sobrescribe.

### PR-006
Las correcciones crean una nueva versión enlazada con la anterior.

### PR-007
La anulación requiere motivo, actor y timestamp.

### PR-008
La nueva versión debe producir un nuevo artefacto documental.

## 4. StudyOrder

### SO-001
Un StudyOrder requiere patient, doctor y clinical_encounter. `patient` se deriva siempre de
`clinical_encounter.appointment.patient`, igual que en PR-001.

### SO-002
Debe contener al menos un StudyOrderItem al emitirse.

### SO-003
El tipo de estudio pertenece a un enum pequeño: `LABORATORY`, `IMAGING`, `HISTOPATHOLOGY`, `OTHER`.

### SO-004
No existe catálogo obligatorio de estudios en Fase 4.

### SO-005
Los estados son `ISSUED` y `VOIDED`.

### SO-006
Las correcciones no sobrescriben una orden emitida.

### SO-007
La anulación requiere motivo, actor y timestamp.

## 5. ClinicalDocument

### CD-001
Patient es obligatorio.

### CD-002
Las relaciones con Appointment, ClinicalEncounter, Prescription o StudyOrder son opcionales y sólo se establecen cuando tienen significado clínico.

### CD-003
`UPLOADED` y `GENERATED` son los únicos orígenes iniciales.

### CD-004
El tipo documental pertenece al conjunto definido por el contrato de Fase 4.

### CD-005
Los binarios no se almacenan dentro del audit trail.

### CD-006
Los documentos generados son representaciones históricas de una versión concreta.

### CD-007
Un `ClinicalDocument` sin `prescription_id` ni `study_order_id` (no respaldado por una entidad con
ciclo de vida propio) tiene su propio `status` (`ACTIVE`/`VOIDED`) para representar la
"estrategia de inactivación" referida por `phase-4-documents.md` §12 — anulación lógica con
motivo, actor y timestamp, nunca DELETE funcional. Un `ClinicalDocument` respaldado por
`Prescription`/`StudyOrder` no duplica ese estado (CD-006/`clinical-document-domain.md` §6): su
vigencia sigue la de la entidad que lo respalda (revisión de consistencia, 2026-09-11 — ver
`clinical-documents-data-model.md` §3, D-002).

### CD-008
Cuando un `ClinicalDocument GENERATED` representa el PDF de una `StudyOrder`, su `document_type`
es `STUDY_ORDER` (igual que el de una `Prescription` es `PRESCRIPTION`) — nunca el tipo de estudio
de la propia orden (`LABORATORY`/`IMAGING`/`HISTOPATHOLOGY`). Esos tres valores del enum de
`document_type` quedan reservados para documentos `UPLOADED` (p. ej. un estudio externo aportado
por el paciente como referencia), evitando que el mismo PDF generado pueda documentarse con dos
valores distintos según el criterio del desarrollador (revisión de consistencia, 2026-09-11).

## 6. Archivos

### FL-001
El almacenamiento es privado.

### FL-002
El nombre enviado por el usuario nunca determina directamente el path físico.

### FL-003
Se conserva el nombre original como metadato.

### FL-004
Validar extensión, MIME y tamaño configurado.

### FL-005
El cliente no puede convertir un recurso privado en una URL pública mediante parámetros.

## 7. Versionado

### VR-001
Las versiones se numeran desde 1.

### VR-002
Una nueva versión apunta a la versión anterior.

### VR-003
Sólo una versión puede ser vigente en una cadena documental. Se persiste mediante el campo
`is_current_version` (`True` únicamente en la versión vigente); la corrección lo actualiza de
forma atómica dentro de la misma transacción que crea la nueva versión, con `select_for_update`
sobre la versión anterior (revisión de consistencia, 2026-09-11 — ver
`clinical-documents-data-model.md` §3, D-001).

### VR-004
Las versiones anteriores permanecen accesibles según permisos.

### VR-005
No se requiere hash criptográfico como criterio obligatorio inicial.

## 8. Seguridad

- Toda lectura/descarga se autoriza por objeto.
- No existe seguridad basada sólo en frontend.
- El administrador conserva acceso global conforme a políticas previas y sus acciones sensibles se auditan.
- El responsable requiere relación activa.
- Un médico debe tener autorización clínica aplicable al paciente.

## 9. Idempotencia

Las operaciones de emisión y anulación deben aceptar reintentos técnicos sin duplicados indebidos.

## 10. Eliminación

No existe DELETE funcional para documentos clínicos emitidos. La salida de vigencia se representa mediante `VOIDED` cuando aplique.

## 11. Fuera de alcance

No se introducen resultados, catálogos exhaustivos, firmas electrónicas, notificaciones ni CareRequest operativo.

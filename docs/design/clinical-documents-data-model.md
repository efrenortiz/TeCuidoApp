# Fase 4 — Modelo de datos documental

## 1. Objetivo

Definir un modelo pequeño, explícito y compatible con PostgreSQL.

## 2. Entidades

### Prescription

Campos mínimos:

| Campo | Tipo conceptual | Obligatorio | Nota |
|---|---|---:|---|
| id | PK | Sí | Identidad |
| patient_id | FK | Sí | Patient canónico — derivado siempre de `clinical_encounter` (ver §3, D-003) |
| doctor_id | FK | Sí | Emisor |
| clinical_encounter_id | FK | Sí | Contexto clínico |
| status | enum/text choices | Sí | ISSUED/VOIDED |
| issued_at | datetime | Sí | server-side |
| version_number | integer | Sí | inicia en 1 |
| previous_version_id | FK nullable | No | versión anterior |
| is_current_version | boolean | Sí | `True` sólo en la versión vigente de la cadena (ver §3, D-001) |
| voided_at | datetime nullable | No | Anulación |
| void_reason | text nullable | No | Motivo |
| idempotency_key | text | No, default `""` | Mismo patrón que Fase 2 (ver §3, D-004) |

`PrescriptionItem` requiere `prescription_id`, `position`, `medication_name`, `dose`, `route`, `frequency` e instrucciones; campos no aplicables pueden ser nullable según regla documental.

### StudyOrder

Análogo a Prescription: patient (derivado de `clinical_encounter`, nunca aceptado de forma independiente), doctor, clinical_encounter, status, issued_at, version_number, previous_version, `is_current_version`, `idempotency_key`, void metadata.

`StudyOrderItem` requiere `study_order_id`, `position`, `study_name`.

### ClinicalDocument

Campos mínimos:

| Campo | Tipo conceptual | Obligatorio |
|---|---|---:|
| id | PK | Sí |
| patient_id | FK | Sí |
| appointment_id | FK nullable | No |
| clinical_encounter_id | FK nullable | No |
| prescription_id | FK nullable | No |
| study_order_id | FK nullable | No |
| document_type | choices | Sí |
| origin | choices | Sí |
| status | enum/text choices nullable | Sólo cuando el documento no depende de `Prescription`/`StudyOrder` (ver §3, D-002) |
| original_filename | text | Sí |
| storage_key | text | Sí |
| mime_type | text | Sí |
| size_bytes | bigint | Sí |
| created_by | FK | Sí para operación humana |
| created_at | datetime | Sí |
| version_number | integer nullable | Sólo versionables |
| previous_version_id | FK nullable | No |
| is_current_version | boolean nullable | Sólo versionables — mismo significado que en Prescription/StudyOrder |

## 3. Constraints

Recomendaciones obligatorias:

- unique Patient + Prescription/StudyOrder por identidad de recurso donde corresponda;
- `position > 0`;
- unicidad de `position` dentro de cada Prescription/StudyOrder;
- `version_number >= 1`;
- una versión anterior debe pertenecer al mismo documento lógico y paciente;
- no permitir self-reference de `previous_version`;
- no permitir cambiar patient de un registro existente;
- `UniqueConstraint` parcial sobre `(created_by, idempotency_key)` en Prescription y StudyOrder, condicionada a `idempotency_key != ""` (ver D-004).

**Corrección de consistencia (revisión de Fase 4, 2026-09-11) — D-001, versión vigente:**
`phase-4-documents-rules.md` (VR-003) y `phase-4-documents.md` §11/§24 de `requirements.md`
cierran conceptualmente que "sólo una versión puede ser vigente en una cadena documental", pero
ningún documento definía cómo se persiste esa condición. Se cierra aquí: cada fila versionable
(Prescription, StudyOrder, ClinicalDocument versionable) tiene el campo `is_current_version`
(booleano); al crear una corrección, la misma transacción que inserta la nueva versión
(`is_current_version=True`) actualiza la versión anterior a `is_current_version=False` — el mismo
patrón transaccional ya usado en Fase 3 para transiciones exclusivas (`select_for_update` sobre la
versión anterior antes de mutarla, dentro de la transacción de creación de la nueva versión). No se
requiere un identificador adicional de "cadena": la corrección siempre parte de la versión actual
conocida por su propio `id`, y el `select_for_update` sobre esa fila resuelve la concurrencia de dos
correcciones simultáneas (la segunda encuentra `is_current_version=False` tras el lock y se
rechaza con `Conflict`, ver H-03/M-01 en el reporte de revisión). No se introduce un constraint de
unicidad parcial a nivel de PostgreSQL para esta invariante — se protege exclusivamente a nivel de
servicio/transacción, igual que otras invariantes de exclusividad ya cerradas en Fase 3.

**Corrección de consistencia (revisión de Fase 4, 2026-09-11) — D-004, idempotencia:** se agrega
`idempotency_key` (texto, `blank=True, default=""`) a `Prescription` y `StudyOrder`, con el mismo
patrón de constraint que Fase 2: `UniqueConstraint` parcial sobre `(created_by, idempotency_key)`
con `condition=~Q(idempotency_key="")`, análoga a `appointment_idempotency_key_unique`. Cierra la
ambigüedad de `phase-4-service-contracts.md` §8 (antes: "si la infraestructura ya cuenta con un
mecanismo... reutilizarlo", sin confirmar si existía) — se verificó que sí existe y se reutiliza
sin modificarlo.

**Corrección de consistencia (revisión de Fase 4, 2026-09-11) — D-002, estado de ClinicalDocument
standalone:** `phase-4-documents.md` §12 y `clinical-document-domain.md` §6 remiten a "la estrategia
de inactivación definida por el dominio documental" para archivos subidos erróneamente, sin que
ningún documento definiera esa estrategia. Se cierra aquí: un `ClinicalDocument` sin
`prescription_id` ni `study_order_id` (es decir, no respaldado por una entidad con su propio
ciclo de vida) tiene su propio campo `status` con los valores `ACTIVE`/`VOIDED` — misma semántica
de anulación lógica que `Prescription`/`StudyOrder` (motivo, actor, timestamp, auditoría; nunca
DELETE funcional). Un `ClinicalDocument` respaldado por `Prescription`/`StudyOrder` dejar
`status = NULL` y su vigencia se sigue leyendo exclusivamente del estado de la entidad que lo
respalda (evita la duplicación que `clinical-document-domain.md` §6 ya prohíbe).

**Corrección de consistencia (revisión de Fase 4, 2026-09-11) — D-003, origen de `patient`:**
Ningún documento especificaba explícitamente que el `patient` de `Prescription`/`StudyOrder` debe
derivarse siempre del `clinical_encounter` recibido, pese a que ambos son FKs directos e
independientes en este modelo (el `patient_id` directo existe por razones de consulta/índice —
mismo patrón ya usado por `AuditEvent` en Fase 3, que también mantiene `patient`, `appointment` y
`clinical_encounter` como FKs independientes simultáneas). Se cierra aquí: el servicio de emisión
(`PrescriptionService.issue`/`StudyOrderService.issue`) nunca acepta `patient` como parámetro
independiente del cliente; siempre lo deriva de `clinical_encounter.appointment.patient` en el
mismo punto donde valida la autorización, antes de escribir la fila. Esto elimina la posibilidad de
que `patient_id` diverja del paciente real del encuentro por un payload malformado o un bug de
integración — no se necesita un constraint de base de datos adicional porque el servicio es el
único punto de escritura (no existe CRUD genérico, `phase-4-service-contracts.md` §10).

## 4. Índices

Como mínimo:

- ClinicalDocument(patient_id, created_at desc);
- ClinicalDocument(patient_id, document_type, created_at desc);
- Prescription(patient_id, issued_at desc);
- StudyOrder(patient_id, issued_at desc);
- ClinicalDocument(appointment_id) cuando se use;
- ClinicalDocument(clinical_encounter_id) cuando se use.

## 5. Nulls y defaults

No usar campos vacíos como sustituto de estados. Las opciones no aplicables son nullable sólo cuando el dominio lo permite.

## 6. Integridad referencial

Patient, Doctor y ClinicalEncounter son canónicos y no se duplican.

Una ClinicalDocument no puede existir sin Patient.

## 7. Eliminación

No `DELETE` funcional para registros clínicos emitidos.

## 8. Archivos

El binario no se almacena en la tabla de auditoría. `storage_key` identifica el artefacto privado.

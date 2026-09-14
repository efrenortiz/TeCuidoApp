# Informe final — Fase 4: Documentos

**Fecha:** 2026-09-11

---

## 1. Resumen ejecutivo

**Objetivo:** implementar Fase 4 (recetas, solicitudes de estudio y documentos clínicos:
generación de PDF, almacenamiento privado, descarga autorizada, versionado y anulación lógica) de
forma incremental, verificable y compatible con Fases 1–3, siguiendo la documentación ya cerrada y
revisada en `docs/phases/phase-4-documentation-review-report.md` (`READY FOR PHASE 4
IMPLEMENTATION`).

**Alcance:** exactamente el definido en `phase-4-documents.md` §3.1 — `Prescription`,
`PrescriptionItem`, `StudyOrder`, `StudyOrderItem`, `ClinicalDocument`, generación de PDF,
almacenamiento privado, descarga autorizada, versionado, anulación lógica, auditoría. Sin
resultados de estudios, sin `CareRequest`, sin catálogos obligatorios, sin funcionalidad de Fase 5/6.

**Resultado general:** las 9 etapas (0–8) del plan se completaron con Gate `PASS`. Se
implementaron 3 apps Django nuevas (`prescriptions`, `study_orders`, `clinical_documents`), 157
tests nuevos (685/685 en la suite completa del proyecto), validación real de navegador (13/13), y
se encontraron y corrigieron 4 defectos reales durante la propia implementación (documentados en
cada etapa y consolidados en §9/§11). Ningún cambio sobre código de Fases 1–3 fue destructivo —
todos los cambios sobre archivos existentes son estrictamente aditivos.

**Estado final:** validado originalmente el 2026-09-11 (§15); recuperado íntegramente tras una
falla de VM y revalidado el 2026-09-14 (§16). Veredicto de cierre formal en §16.

---

## 2. Resumen de etapas

| Etapa | Nombre | Estado | Tests | Migraciones | Gaps |
|---|---|---|---:|---|---:|
| 0 | Baseline | PASS | 528/528 (previos) | Sin cambios | 0 |
| 1 | Apps y modelo de datos | PASS | 32 nuevos (32/32) | 8 migraciones nuevas | 0 |
| 2 | Dominio y servicios | PASS | 51 nuevos (83/83 acumulado) | 0 | 0 |
| 3 | Archivos y PDF | PASS | (incluidos en Stage 2) | 0 | 0 |
| 4 | API | PASS | 30 nuevos (113/113 acumulado) | 0 | 0 |
| 5 | UX y pantallas | PASS | 19 nuevos (132/132 acumulado) + navegador 13/13 | 0 | 0 |
| 6 | Auditoría y seguridad | PASS | 20 nuevos (152/152 acumulado) | 0 | 0 |
| 7 | Concurrencia e idempotencia | PASS | 5 nuevos (157/157 acumulado) | 0 | 0 |
| 8 | Regresión completa | PASS | 685/685 (528 F1–3 + 157 F4) | Sin cambios | 0 |

Documentación detallada de cada etapa en `docs/phases/phase-4-implementation/stage-0X-*.md`.

---

## 3. Cambios implementados

**Modelos** (`prescriptions`, `study_orders`, `clinical_documents` — 3 apps nuevas):
`Prescription`/`PrescriptionItem`, `StudyOrder`/`StudyOrderItem`, `ClinicalDocument`. Extensión
aditiva de `medical_records.AuditEvent` (10 `Action` nuevas, 3 `ResourceType` nuevos, 3 FKs
opcionales nuevas).

**Servicios**: `prescriptions.services.prescription` (`issue`/`get`/`list_for_patient`/
`create_version`/`void`), `study_orders.services.study_order` (análogo),
`clinical_documents.services.document` (`upload`/`get`/`list_for_patient`/`download`/
`create_generated_document`/`create_version`/`void_or_inactivate`). Taxonomía de errores `Document*`
y funciones de autorización nuevas en `medical_records.services.{exceptions,permissions}`.

**Storage**: `clinical_documents.services.storage` — almacenamiento privado
(`CLINICAL_DOCUMENTS_STORAGE_ROOT`, fuera de cualquier URL pública), validación de contenido real
(magic bytes vía `filetype`), `storage_key` generado siempre en servidor.

**PDF**: `clinical_documents.services.pdf` (`fpdf2`) — generación server-side, síncrona,
determinista, integrada atómicamente con `Prescription`/`StudyOrder` (ADR-027).

**API**: `prescriptions/study_orders/clinical_documents` `api.py` + `urls.py`, montados bajo
`api/v1/clinical/`, siguiendo exactamente `phase-4-api-contracts.md` (ningún endpoint inventado).

**UX/UI**: pantallas S1–S7 (`phase-4-screens.md`), reutilizando `layouts/app_base.html` y los
componentes visuales ya existentes; botones de acceso añadidos a `encounter_detail.html`/
`medical_record.html`.

**Seguridad**: autorización por objeto (médico asignado al encuentro vs. relación activa —
P-009/P-010 preservado), IDOR-safe (404 genérico), archivos siempre privados, validación de
contenido real de archivos subidos.

**Auditoría**: las 10 acciones mínimas de `phase-4-audit-and-history.md` §2, todas con `actor` real
verificado, sin contenido clínico ni binarios en el audit trail.

**Pruebas**: 157 tests nuevos — modelos/constraints, servicios (autorización, idempotencia,
errores), storage/PDF, API, UI (test client + navegador real), auditoría, concurrencia real con
hilos.

---

## 4. Evidencia de pruebas

| Comando | Resultado | Cantidad | Fecha/hora | Ambiente |
|---|---|---:|---|---|
| `python manage.py check` | PASS | — | 2026-09-11 | Dev, PostgreSQL local |
| `python manage.py makemigrations --check --dry-run` | PASS (`No changes detected`) | — | 2026-09-11 | ídem |
| `python manage.py migrate --plan` | PASS (sin operaciones pendientes) | — | 2026-09-11 | ídem |
| `python manage.py test` (suite completa) | PASS | 685/685 | 2026-09-11 | ídem, `test_tecuido_db` |

**Regresión F1–3:** los 528 tests preexistentes de Fases 1–3 (baseline de Stage 0, sin ningún
cambio) siguen pasando sin modificación alguna dentro de la misma corrida de 685.

---

## 5. Evidencia manual/navegador

Validación real con Chromium vía Playwright (extensión Claude-in-Chrome no conectada en este
entorno, verificado explícitamente) contra servidor de desarrollo real y PostgreSQL real (datos de
prueba sembrados y eliminados después). Evidencia completa en
`docs/phases/evidence/phase-4-browser-validation-2026-09-11/`.

| Flujo | Resultado | Evidencia |
|---|---|---|
| Crear receta | PASS | `02-prescription-form-filled.png` |
| Emitir receta | PASS | `03-prescription-detail.png` |
| Generar PDF | PASS | `results.json` (`pdf_downloaded_nonempty`, `pdf_has_valid_header`) |
| Descargar | PASS | header `%PDF-` verificado en el archivo descargado |
| Crear StudyOrder | PASS | `06-study-order-detail.png` |
| Versionar | PASS | `04-prescription-v2.png` (versión 2 con valor actualizado + enlace a versión anterior) |
| Anular | PASS | `05-prescription-voided.png` (badge "Anulada") |
| Acceso no autorizado | PASS | `08-access-denied.png` (404 genérico para médico sin relación) |

**13/13 verificaciones OK** (ver `results.json` para el detalle estructurado completo, incluyendo
también la lista de documentos del paciente).

---

## 6. Seguridad

- **Autorización**: cada operación pasa por `medical_records.services.permissions` (nuevas
  funciones `can_issue_document_for_encounter`/`can_correct_or_void_document`/
  `can_read_document_resource`), nunca delegada a la vista/UI. Preserva P-009/P-010 de Fase 3
  (médico asignado al encuentro ≠ acceso histórico permanente sin relación activa).
- **IDOR**: verificado explícitamente en tests de servicio, API y UI — "no existe" y "no
  autorizado" nunca se distinguen en la respuesta al cliente (404 genérico).
- **Almacenamiento privado**: `CLINICAL_DOCUMENTS_STORAGE_ROOT` fuera de cualquier URL pública
  (`MEDIA_URL`/`static/`); verificado por inspección completa de `urls.py` — ninguna ruta lo
  expone directamente.
- **Descargas**: siempre reautorizadas en el momento de servir el archivo (`download()` llama a
  `get()` internamente, nunca cachea una autorización previa).
- **Validación de archivos**: MIME real verificado por contenido (magic bytes), no por
  `Content-Type` del cliente ni por extensión — un ejecutable disfrazado de `.pdf` se rechaza
  (verificado con test dedicado).
- **Logs**: sin contenido clínico ni binarios (heredado del mecanismo de Fase 3, sin cambios).

---

## 7. Concurrencia

Ver detalle completo en `docs/phases/phase-4-implementation/stage-07-concurrency.md`.

- **Escenarios ejecutados**: doble emisión concurrente con `Idempotency-Key` (Prescription y
  StudyOrder), doble corrección concurrente sobre la misma versión vigente (ambos), doble
  anulación concurrente con el mismo motivo (Prescription).
- **Resultados**: los 5 escenarios pasan con hilos reales y conexiones de base de datos
  independientes.
- **Problema encontrado**: `issue()` no capturaba el `IntegrityError` real de una carrera genuina
  sobre el `UniqueConstraint` de idempotencia — el perdedor de la carrera recibía un error crudo de
  PostgreSQL en vez de un replay idempotente.
- **Problema corregido**: se agregó la captura de `IntegrityError` con re-consulta y replay,
  siguiendo exactamente el patrón ya usado por
  `appointments.services.appointment.create_appointment_from_hold` (Fase 2) para el mismo tipo de
  carrera. Verificado con los mismos tests, ahora estables.

---

## 8. Auditoría

- Las 10 acciones mínimas de `phase-4-audit-and-history.md` §2 generan un `AuditEvent` real,
  verificado con tests dedicados por cada una (`ISSUE_PRESCRIPTION`, `ISSUE_STUDY_ORDER`,
  `UPLOAD_CLINICAL_DOCUMENT`, `GENERATE_CLINICAL_DOCUMENT`, `READ_CLINICAL_DOCUMENT`,
  `DOWNLOAD_CLINICAL_DOCUMENT`, `CREATE_DOCUMENT_VERSION`, `VOID_PRESCRIPTION`,
  `VOID_STUDY_ORDER`, `VOID_CLINICAL_DOCUMENT`).
- `actor` es siempre el usuario autenticado real; verificado explícitamente que el guard
  compartido de `medical_records.services.audit` (ya endurecido durante el cierre de Fase 3 para
  el hallazgo `AuditEvent.actor_id`) también protege a todos los nuevos llamadores de Fase 4 sin
  cambio adicional — ningún evento con `actor` nulo es posible.
- Ningún evento contiene contenido clínico ni binarios — verificado por valor y estructuralmente
  (`AuditEvent` no tiene ningún campo de tipo archivo).
- `Clinical History ≠ Audit Trail` preservado sin cambios: el historial navegable
  (`Prescription`/`StudyOrder`/`ClinicalDocument` y sus versiones) nunca se reconstruye a partir
  del audit trail.

---

## 9. Gaps

| GAP | Severidad | Descripción | Estado | ¿Bloquea cierre? |
|---|---|---|---|---|
| G-01 | LOW | El formulario de items de receta/solicitud usa un número fijo de filas (5) en vez de agregar filas dinámicamente con JavaScript. | Aceptado por diseño (simplicidad, coherente con el resto de Fase 3) | No |
| G-02 | LOW | La carga de archivos lee el archivo completo en memoria (`uploaded.read()`) antes de validar tamaño; aceptable para el límite actual (10 MB). | Documentado, sin acción requerida para el volumen de Fase 4 | No |
| G-03 | LOW | No se duplicó el conjunto completo de pruebas de concurrencia con hilos reales para `ClinicalDocumentService.create_version`/`void_or_inactivate` (documentos standalone) — usa el mismo mecanismo ya verificado dos veces de forma independiente (Prescription/StudyOrder). | Riesgo residual bajo, aceptado | No |

**CRITICAL: 0 · HIGH: 0 · MEDIUM: 0 · LOW: 3 · INFO: 0**

---

## 10. Deuda técnica

- **Deuda que bloquea cierre**: ninguna.
- **Deuda aceptable**: G-01/G-02/G-03 de §9.
- **Mejoras futuras** (explícitamente fuera de alcance de Fase 4, no deuda): resultados de
  estudios, catálogo farmacológico, firma electrónica, `CareRequest` operativo — todas ya
  documentadas como fuera de alcance en ADR-030 y `phase-4-documents.md` §24; no se etiquetan como
  gap de Fase 4.

---

## 11. Desviaciones respecto de la documentación

| Desviación | Motivo | Impacto | Documento a actualizar |
|---|---|---|---|
| El PDF `GENERATED` se escribe al almacenamiento privado DENTRO de la misma transacción que crea `Prescription`/`StudyOrder` (no estrictamente antes de abrirla, como describía originalmente ADR-027/`clinical-documents-data-model.md`). | Refinamiento de implementación: da una garantía de atomicidad real de base de datos (más fuerte que la compensación aplicativa best-effort original), sin contradecir ninguna invariante cerrada ("nunca queda una receta emitida sin su documento" se sigue cumpliendo, y de forma más estricta). | Ninguno negativo — la garantía resultante es estrictamente más fuerte. | `docs/adr/ADR-027-synchronous-server-side-pdf-generation.md` — añadir una nota de implementación (no un cambio de decisión) aclarando esta secuencia exacta para el caso `GENERATED` vs. `UPLOADED`. |

No se identificó ninguna otra desviación entre diseño/ADRs e implementación.

**Actualización de cierre (2026-09-14):** la nota de implementación recomendada en la columna
"Documento a actualizar" ya está presente en
`docs/adr/ADR-027-synchronous-server-side-pdf-generation.md` §2 ("Nota de implementación",
fechada 2026-09-11) y fue verificada nuevamente contra el código real
(`prescriptions.services.prescription.issue`/`create_version`,
`study_orders.services.study_order.issue`/`create_version`,
`clinical_documents.services.document.create_generated_document`) durante la preparación del
cierre formal. No queda ninguna acción pendiente sobre ADR-027.

---

## 12. Regresión de Fases 1–3

- **Resultado**: 528/528 tests preexistentes de Fases 1–3 pasan sin ninguna modificación, dentro
  de la misma corrida completa de 685.
- **Regresiones**: ninguna.
- **Correcciones**: ninguna requerida — todos los cambios sobre código de Fases 1–3 son
  estrictamente aditivos (0 líneas eliminadas/modificadas, ver Stage 8 §"Revisión de footprint").

---

## 13. Estado de la documentación

- La documentación de Fase 4 sigue siendo consistente con la implementación, con una única
  desviación menor y no bloqueante (§11), para la cual se recomienda una nota aclaratoria en
  ADR-027 (no un cambio de decisión).
- Las 9 etapas de implementación están documentadas individualmente en
  `docs/phases/phase-4-implementation/stage-0{0..8}-*.md`.
- No se detectaron contradicciones nuevas entre documentación e implementación más allá de la ya
  descrita en §11.
- **Recomendación antes del cierre formal** (2026-09-11): actualizar ADR-027 con la nota de §11
  (menor, no bloqueante).
- **Estado de la recomendación (2026-09-14):** verificada como ya resuelta — ver nota de cierre
  en §11. Ninguna acción documental pendiente sobre ADR-027 al momento del cierre formal.

---

## 14. Criterios de cierre

| Criterio | Estado | Evidencia | Bloquea |
|---|---|---|---|
| Alcance implementado | PASS | §3; sin funcionalidad fuera de alcance (ADR-030 respetado) | No |
| Modelo | PASS | Stage 1; 32/32 tests; constraints verificados | No |
| Servicios | PASS | Stage 2; 51/51 tests; autorización/idempotencia/errores cubiertos | No |
| API | PASS | Stage 4; 30/30 tests; sin endpoints inventados | No |
| UX/UI | PASS | Stage 5; 19/19 tests + navegador real 13/13 | No |
| Seguridad | PASS | Stage 6; IDOR/almacenamiento privado/validación de archivos verificados | No |
| Auditoría | PASS | Stage 6; 10/10 acciones mínimas auditadas con actor real | No |
| Concurrencia | PASS | Stage 7; 5/5 escenarios con hilos reales; 1 bug real encontrado y corregido | No |
| Tests | PASS | 685/685 (528 F1–3 + 157 F4) | No |
| Regresión F1–3 | PASS | §12; 0 regresiones | No |
| Documentación | PASS | §13; 1 desviación menor no bloqueante | No |

---

## 15. Recomendación final

**Recomendación original (2026-09-11):** todos los criterios de cierre estaban satisfechos:
código, pruebas, migraciones, seguridad, concurrencia, auditoría, UX/UI, regresión y
documentación. No existía ningún gap CRITICAL/HIGH, y la única desviación documental
identificada era menor y no bloqueante (§11).

```text
PHASE 4 — READY TO CLOSE
```

---

## 16. Recovery Validation — 2026-09-14

Con posterioridad a la validación original de este informe (2026-09-11), el entorno de
desarrollo sufrió una falla catastrófica de VM. La implementación de Fase 4 se recuperó
íntegramente desde un respaldo previo a la falla; esta sección documenta esa recuperación y su
revalidación como un evento distinto y trazable, sin sustituir la evidencia original de §4–§8.

- **Baseline de Fase 3** utilizado como punto de partida de la recuperación: commit `7621bae`
  ("Close Fase 3: clinical domain implementation").
- **Implementación de Fase 4 recuperada:** consolidada en el commit `cf77662` ("Recover Fase 4
  implementation"), sobre la rama `recovery/fase4` (publicada como `origin/recovery/fase4`).
- **Verificaciones re-ejecutadas en el ambiente reconstruido:**

  | Verificación | Resultado |
  |---|---|
  | `python manage.py check` | PASS |
  | Consistencia de migraciones | PASS |
  | Tests de `medical_records` | 196/196 PASS |
  | Tests de `clinical_documents` | PASS |
  | Tests de `prescriptions` | PASS |
  | Tests de `study_orders` | PASS |
  | Suite completa del proyecto | PASS |

  Esta corrida reproduce el resultado esperado por la evidencia original (§4: 685/685 — 528 de
  Fases 1–3 + 157 de Fase 4). La validación de recuperación confirma que la suite completa vuelve
  a pasar en el ambiente reconstruido; no se re-documenta aquí un conteo independiente de 685
  porque el conteo exacto no forma parte de la evidencia de esta corrida — el resultado
  registrado es "PASS" sobre la suite completa y sobre cada app de Fase 4 individualmente.
- **Alcance de esta validación:** confirma la integridad de la recuperación (que la
  implementación recuperada es equivalente en comportamiento a la validada originalmente). No
  repite, ni necesita repetir, la validación manual/navegador (§5), de seguridad (§6) o de
  concurrencia (§7) — esa evidencia histórica permanece vigente sin cambios y sigue siendo la
  fuente primaria para esos aspectos.
- **ADR-027:** la aclaración documental pendiente identificada en §11/§13 fue verificada como ya
  presente y correcta en `docs/adr/ADR-027-synchronous-server-side-pdf-generation.md` §2 — sin
  cambios pendientes.

### Veredicto de cierre

Con la implementación de Fase 4 recuperada íntegramente, revalidada exitosamente en el ambiente
reconstruido, y sin ninguna desviación documental pendiente:

```text
FASE 4 — IMPLEMENTADA
PHASE 4 — CLOSED
```

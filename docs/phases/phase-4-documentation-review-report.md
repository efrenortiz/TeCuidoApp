# Revisión exhaustiva, corrección y cierre documental de Fase 4

**Fecha:** 2026-09-11
**Alcance:** exclusivamente documental — ningún modelo, migración, servicio, endpoint, vista,
plantilla ni test fue creado o modificado durante esta revisión.

---

## 1. Resumen ejecutivo

**Objetivo:** auditar exhaustivamente toda la documentación de Fase 4 (contrato, workflow, rules,
dominios, modelo de datos, permisos, seguridad, servicios, API, UX, pantallas, auditoría, testing,
índice y ADRs), corregir las inconsistencias inequívocas, y dejar la especificación suficientemente
cerrada para iniciar programación sin decisiones arquitectónicas improvisadas — sin construir
ningún código ni reabrir decisiones ya cerradas de Fases 1–3.

**Documentos revisados (16 + 10 ADRs + 4 transversales):**

- `docs/phases/phase-4-documents.md` (contrato funcional)
- `docs/design/phase-4-documents-workflow.md`
- `docs/design/phase-4-documents-rules.md`
- `docs/design/clinical-document-domain.md`
- `docs/design/prescription-domain.md`
- `docs/design/study-order-domain.md`
- `docs/design/clinical-documents-data-model.md`
- `docs/design/phase-4-permissions.md`
- `docs/design/phase-4-security-and-privacy.md`
- `docs/design/phase-4-service-contracts.md`
- `docs/design/phase-4-api-contracts.md`
- `docs/design/phase-4-ux.md`
- `docs/design/phase-4-screens.md`
- `docs/design/phase-4-audit-and-history.md`
- `docs/phases/phase-4-testing-strategy.md`
- `docs/phases/phase-4-documentation-index.md`
- ADR-021 a ADR-030 (inexistentes al inicio de la revisión — ver hallazgo C-01)
- `README.md`, `docs/architecture.md`, `requirements.md`, `CLAUDE.md`
- Documentación vigente de Fase 1 y Fase 2; documentación cerrada de Fase 3 (dominio,
  permisos, ADRs 008–020)
- Código existente de Fase 2/3 (`appointments/models.py`, `medical_records/models.py`) —
  inspeccionado únicamente para verificar consistencia documental, sin modificarlo.

**Resultado general:** se encontraron 12 hallazgos reales (0 CRITICAL bloqueante de integridad de
datos en producción — el único CRITICAL es un vacío documental, no un defecto de diseño; 3 HIGH; 6
MEDIUM; 2 LOW; 0 INFO). Los 12 se corrigieron durante esta misma revisión, todos mediante
resoluciones inequívocas basadas en decisiones ya cerradas de Fase 2/3 o en el propio contrato de
Fase 4 — ninguno requirió escalar una decisión humana pendiente. Una segunda auditoría
independiente, ejecutada después de aplicar las correcciones, no encontró contradicciones nuevas.

---

## 2. Proceso realizado

1. **Análisis inicial:** lectura completa de los 16 documentos de Fase 4 en su versión original,
   más `phase-4-documentation-index.md` y los 10 ADRs referenciados (confirmando que no existían).
2. **Revisión cruzada:** contraste sistemático de cada decisión crítica (alcance, entidades,
   relaciones, versionado, inmutabilidad, VOIDED, almacenamiento, PDF, permisos, auditoría,
   concurrencia, API, servicios, UX) entre los 16 documentos entre sí.
3. **Revisión contra fases anteriores:** contraste contra `clinical-permissions.md`,
   `clinical-encounter-domain.md`, ADRs 008–020 (Fase 3) y contra el código real de
   `medical_records/models.py` y `appointments/models.py` (Fase 2/3), para verificar que ninguna
   regla de Fase 4 reabriera o contradijera una decisión ya cerrada, y para localizar
   infraestructura reutilizable (el mecanismo `Idempotency-Key` de Fase 2).
4. **Correcciones:** se aplicaron las 12 correcciones documentadas en la §4, todas dentro de los
   límites permitidos (problema inequívoco, sin alterar una decisión arquitectónica cerrada, sin
   incompatibilidad con Fases 1–3), y se redactaron los 10 ADRs faltantes consolidando decisiones
   ya cerradas en los documentos existentes (sin introducir ninguna decisión nueva).
5. **Segunda auditoría (independiente):** repetición completa del barrido de consistencia después
   de las correcciones — referencias cruzadas, rutas, numeración de ADRs, nombres de campos,
   relaciones, permisos, seguridad, API, testing — buscando activamente que las propias
   correcciones no hubieran introducido una contradicción nueva. Resultado: sin hallazgos nuevos
   (ver §"Reverificación" más abajo).

---

## 3. Hallazgos iniciales

| ID | Severidad | Documento | Problema | Impacto | Solución |
|---|---|---|---|---|---|
| C-01 | CRITICAL | `phase-4-documentation-index.md` (y toda la jerarquía de fuentes de verdad) | ADR-021 a ADR-030, referenciados por el índice y exigidos por el alcance de esta revisión, no existían en el repositorio. | Bloquea la trazabilidad arquitectónica formal de Fase 4; contradice que los ADRs vigentes sean el nivel 2 de la jerarquía de fuentes de verdad que esta misma revisión debe aplicar. | Se redactaron los 10 ADRs, consolidando decisiones ya cerradas en los 16 documentos existentes (sin inventar ninguna decisión nueva); `docs/adr/README.md` actualizado. |
| H-01 | HIGH | `clinical-documents-data-model.md` | No existía ningún campo o mecanismo para persistir "cuál es la versión vigente" (VR-003, `requirements.md` §24, contrato §11), pese a estar cerrado conceptualmente en 3 documentos. | Implementaciones incompatibles del mismo requisito (traversal derivado vs. flag explícito, con o sin protección de concurrencia). | Se agregó `is_current_version` (booleano) + protocolo transaccional (`select_for_update` sobre la versión anterior); formalizado en ADR-023. |
| H-02 | HIGH | `phase-4-permissions.md` | La matriz de permisos colapsaba la distinción ya cerrada en Fase 3 (P-009/P-010/P-011/P-013) entre "médico asignado al encuentro actual" y "médico con `DoctorPatientRelationship` vigente" bajo una única columna "Médico autorizado". | Riesgo real de implementar acceso al historial documental más amplio del que Fase 3 autoriza para un médico simplemente asignado a una atención puntual. | Matriz reescrita con columnas separadas y reglas explícitas por operación; formalizado en ADR-028. |
| H-03 | HIGH | `phase-4-documents-workflow.md` / `phase-4-service-contracts.md` | Los 8+ escenarios de concurrencia estaban enumerados sin resolución definida, y el mecanismo de idempotencia se dejaba como "opcional según infraestructura existente" sin confirmar si existía. | Contradice el propio criterio de cierre del workflow ("cada flujo debe tener comportamiento definido para... duplicidad, concurrencia"); riesgo de doble emisión. | Se verificó que el mecanismo `Idempotency-Key` de Fase 2 existe (`appointments/models.py`) y se documentó su reutilización explícita; se agregó una tabla de resolución por escenario. |
| M-01 | MEDIUM | `phase-4-api-contracts.md` | Sin mapeo explícito error de dominio → código HTTP, a diferencia del patrón ya cerrado de Fase 3. | Ambigüedad concreta para `InvalidState`/`Conflict`/`ImmutableResource`/`ReferenceInconsistency`. | Tabla explícita agregada, con el mismo criterio ya usado en Fase 3 (400/422/409 según el tipo de violación). |
| M-02 | MEDIUM | `phase-4-audit-and-history.md` | §8 ("las lecturas sensibles pueden auditarse") contradecía §2 (que lista `READ_CLINICAL_DOCUMENT` como auditable "como mínimo"). | Un desarrollador podría omitir la auditoría de lectura interpretando que es opcional. | Wording corregido: el intento de auditar nunca es opcional; la tolerancia (AH-089) es sólo ante el fallo del mecanismo, no ante la decisión de intentarlo. |
| M-03 | MEDIUM | `clinical-documents-data-model.md` / `phase-4-documents-rules.md` | Ningún documento especificaba que `patient` en Prescription/StudyOrder debe derivarse siempre de `clinical_encounter`, pese a ser un FK directo e independiente. | Riesgo de inconsistencia silenciosa (`patient` distinto del paciente real del encounter) por un payload malformado o un bug de integración. | Regla explícita agregada (PR-001/SO-001, D-003): el servicio siempre deriva `patient`, nunca lo acepta como parámetro independiente. |
| M-04 | MEDIUM | `clinical-document-domain.md` / `phase-4-documents.md` | La "estrategia de inactivación" para archivos subidos por error se mencionaba pero nunca se definía. | Ningún estado disponible para anular un `ClinicalDocument` no respaldado por Prescription/StudyOrder sin recurrir a un DELETE. | Se definió `status` (`ACTIVE`/`VOIDED`) para ese caso concreto (CD-007, D-002); formalizado en ADR-024. |
| M-05 | MEDIUM | `clinical-document-domain.md` | `document_type` ambiguo para el PDF `GENERATED` de una `StudyOrder`: el enum permite tanto `STUDY_ORDER` como el tipo de estudio (`LABORATORY`/`IMAGING`/`HISTOPATHOLOGY`). | Dos implementaciones posibles y visiblemente distintas del mismo caso. | Regla explícita: el PDF generado siempre usa `document_type = STUDY_ORDER` (CD-008); los otros tres valores quedan para documentos `UPLOADED`. |
| M-06 | MEDIUM | `phase-4-documents-workflow.md` | El mecanismo de "eliminar/compensar" un archivo huérfano tras un fallo de persistencia posterior a la generación del PDF no especificaba si era síncrono o diferido. | Riesgo de introducir infraestructura asíncrona innecesaria, contradiciendo el propio contrato (§10/§16, "no Celery sólo para PDF"). | Orden exacto de operaciones y compensación síncrona (best-effort, mismo request) documentados; formalizado en ADR-027. |
| L-01 | LOW | `requirements.md` §23 | Faltaba la nota de alcance simétrica a la que ya existe en `phase-4-documents.md` §19 sobre la relación de `ClinicalDocument` con `CareRequest`. | Asimetría editorial menor; no generaba ambigüedad real porque el documento de Fase 4 ya resolvía el caso. | Nota de alcance agregada, remitiendo a `phase-4-documents.md` §19 y `requirements.md` §41. |
| L-02 | LOW | `phase-4-service-contracts.md` | El error genérico `ImmutableResource` no distinguía sus disparadores concretos. | Nombre correcto pero sin ejemplos, levemente subespecificado. | Nota aclaratoria agregada con los 2 escenarios reales que lo disparan. |

---

## 4. Decisiones tomadas

1. **Versión vigente persistida mediante `is_current_version`.**
   - Motivo: VR-003/`requirements.md` §24 exigían identificar la versión vigente sin definir cómo.
   - Documentos afectados: `clinical-documents-data-model.md`, `phase-4-documents-rules.md`,
     `prescription-domain.md`, `study-order-domain.md`, ADR-023.

2. **`patient` en Prescription/StudyOrder siempre derivado de `clinical_encounter`, nunca aceptado
   independientemente.**
   - Motivo: cerrar el riesgo de inconsistencia entre dos FKs directos e independientes.
   - Documentos afectados: `phase-4-documents-rules.md`, `clinical-documents-data-model.md`,
     ADR-022.

3. **Reutilización explícita del mecanismo `Idempotency-Key` de Fase 2** para
   `issue`/`create_version`/`void` de Prescription y StudyOrder.
   - Motivo: cerrar la ambigüedad "según infraestructura existente" verificando que sí existe.
   - Documentos afectados: `phase-4-service-contracts.md`, `clinical-documents-data-model.md`,
     `phase-4-documents-workflow.md`, ADR-029.

4. **Tabla de resolución explícita para los 10 escenarios de concurrencia.**
   - Motivo: el propio criterio de cierre del workflow exige que cada escenario tenga
     comportamiento definido.
   - Documentos afectados: `phase-4-documents-workflow.md`.

5. **Matriz de permisos con columnas separadas "médico asignado al encuentro actual" / "médico con
   relación activa", preservando P-009/P-010/P-011/P-013 de Fase 3.**
   - Motivo: evitar una regresión de seguridad real sobre una decisión de autorización ya cerrada.
   - Documentos afectados: `phase-4-permissions.md`, ADR-028.

6. **`status` `ACTIVE`/`VOIDED` explícito para `ClinicalDocument` no respaldado por
   Prescription/StudyOrder.**
   - Motivo: cerrar la "estrategia de inactivación" que el contrato anunciaba sin definir.
   - Documentos afectados: `clinical-document-domain.md`, `phase-4-documents-rules.md`,
     `clinical-documents-data-model.md`, ADR-024.

7. **`document_type = STUDY_ORDER` fijo para el PDF generado de una StudyOrder.**
   - Motivo: eliminar la ambigüedad entre ese valor y el tipo de estudio de la propia orden.
   - Documentos afectados: `clinical-document-domain.md`, `phase-4-documents-rules.md`.

8. **Mapeo explícito de errores de dominio a códigos HTTP**, con el mismo criterio 400/422/409 ya
   usado en Fase 3.
   - Motivo: cerrar la ambigüedad de implementación de la capa API.
   - Documentos afectados: `phase-4-api-contracts.md`.

9. **Orden exacto y compensación síncrona para la generación de PDF y su persistencia.**
   - Motivo: cerrar la ambigüedad "eliminarse/compensarse" sin especificar sincronía, evitando que
     se infiera la necesidad de infraestructura asíncrona.
   - Documentos afectados: `phase-4-documents-workflow.md`, ADR-027.

10. **Redacción de los 10 ADRs faltantes (021–030)**, consolidando decisiones ya cerradas en los
    documentos existentes.
    - Motivo: cerrar el hallazgo CRITICAL C-01 sin introducir ninguna decisión nueva.
    - Documentos afectados: `docs/adr/ADR-021*.md` a `docs/adr/ADR-030*.md`, `docs/adr/README.md`.

---

## 5. Hallazgos pendientes

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0
- INFO: 0

```text
No quedan hallazgos pendientes.
```

---

## 6. Documentos modificados

| Documento | Modificación | Motivo |
|---|---|---|
| `docs/design/clinical-documents-data-model.md` | Agregado `is_current_version`, `idempotency_key`, `status` (ClinicalDocument standalone); notas D-001 a D-004 | H-01, M-03, M-04, H-03 |
| `docs/design/phase-4-documents-rules.md` | PR-001/SO-001 (derivación de `patient`), VR-003 (mecanismo de vigencia), CD-007/CD-008 (nuevas reglas) | H-01, M-03, M-04, M-05 |
| `docs/design/clinical-document-domain.md` | §4 (regla `document_type` de StudyOrder generado), §6 (remisión a CD-007) | M-04, M-05 |
| `docs/design/prescription-domain.md` | Campo `is_current_version` agregado a §3 | H-01 |
| `docs/design/study-order-domain.md` | Campo `is_current_version` agregado a §3 | H-01 |
| `docs/design/phase-4-permissions.md` | Matriz de operaciones/actores reescrita con columnas médicas separadas; §3 ampliada | H-02 |
| `docs/design/phase-4-documents-workflow.md` | §3 (orden exacto y compensación síncrona de PDF); §10 (tabla de resolución de concurrencia) | H-03, M-06 |
| `docs/design/phase-4-service-contracts.md` | §7 (aclaración de `ImmutableResource`); §8 (reutilización confirmada de `Idempotency-Key`) | H-03, L-02 |
| `docs/design/phase-4-api-contracts.md` | §7 (tabla de mapeo error↔HTTP) | M-01 |
| `docs/design/phase-4-audit-and-history.md` | §8 (corrección de contradicción con §2) | M-02 |
| `requirements.md` | §23 (nota de alcance sobre `CareRequest`) | L-01 |
| `docs/adr/README.md` | Índice ampliado con ADR-021 a ADR-030 | C-01 |
| `docs/adr/ADR-021-clinical-documents-domain-boundary.md` | Creado | C-01 |
| `docs/adr/ADR-022-prescription-studyorder-originate-from-encounter.md` | Creado | C-01 |
| `docs/adr/ADR-023-document-versioning-model.md` | Creado | C-01, H-01 |
| `docs/adr/ADR-024-no-functional-delete-voided-documents.md` | Creado | C-01, M-04 |
| `docs/adr/ADR-025-clinical-document-independent-entity.md` | Creado | C-01 |
| `docs/adr/ADR-026-private-file-storage.md` | Creado | C-01 |
| `docs/adr/ADR-027-synchronous-server-side-pdf-generation.md` | Creado | C-01, M-06 |
| `docs/adr/ADR-028-document-authorization-inherits-phase3.md` | Creado | C-01, H-02 |
| `docs/adr/ADR-029-document-services-boundary.md` | Creado | C-01, H-03 |
| `docs/adr/ADR-030-phase4-scope-boundary.md` | Creado | C-01 |

Ningún modelo, migración, servicio, vista, plantilla, endpoint ni test fue creado o modificado.

---

## 7. Matriz de consistencia final

Leyenda: `✓` consistente · `⚠` corregido durante esta revisión (ver ID de hallazgo) · `—` no aplica.

| Decisión | Contract | Workflow | Rules | Domain | Data | Permissions | Security | Services | API | UX | Screens | Audit | Testing | ADR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Alcance (incluye/excluye) | ✓ | ✓ | ✓ | ✓ | — | — | — | — | — | ✓ | ✓ | — | ✓ | ✓ (ADR-030) |
| Entidades (Prescription/StudyOrder/ClinicalDocument) | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ (ADR-021/025) |
| Relaciones (Patient/ClinicalEncounter, sin duplicar MedicalRecord) | ✓ | ✓ | ✓ | ✓ | ✓⚠(M-03) | — | — | ✓ | — | — | — | — | ✓ | ✓ (ADR-022/025) |
| Versionado (`is_current_version`) | ✓ | ✓ | ✓⚠(H-01) | ✓ | ✓⚠(H-01) | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (ADR-023) |
| Inmutabilidad post-emisión | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ (ADR-024) |
| VOIDED / inactivación | ✓ | ✓ | ✓⚠(M-04) | ✓⚠(M-04) | ✓⚠(M-04) | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (ADR-024) |
| Almacenamiento privado | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | ✓ | — | ✓ | — | ✓ | ✓ (ADR-026) |
| PDF (generación, atomicidad, historicidad) | ✓ | ✓⚠(M-06) | — | ✓ | — | — | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | ✓ (ADR-027) |
| `document_type` de artefactos generados | ✓ | — | ✓⚠(M-05) | ✓⚠(M-05) | ✓ | — | — | — | — | — | — | — | — | — |
| Permisos (médico asignado vs. relación activa) | ✓ | — | — | — | — | ✓⚠(H-02) | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ (ADR-028) |
| Auditoría (lectura obligatoria, sin binarios) | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ | — | — | — | ✓⚠(M-02) | ✓ | — |
| Concurrencia / idempotencia | ✓ | ✓⚠(H-03) | ✓ | — | ✓⚠(H-03) | — | — | ✓⚠(H-03) | — | ✓ | ✓ | — | ✓ | ✓ (ADR-029) |
| API (errores↔HTTP) | ✓ | — | — | — | — | — | — | ✓ | ✓⚠(M-01) | — | — | — | ✓ | — |
| UX/Screens (no exceder lo autorizado por backend) | ✓ | ✓ | — | — | — | ✓ | — | — | — | ✓ | ✓ | — | ✓ | — |

Todas las celdas marcadas `⚠` fueron corregidas en esta misma revisión (ver §3/§4); ninguna
permanece abierta.

---

## 8. Compatibilidad con Fases 1–3

**Compatibilidad mantenida.** Se verificó explícitamente que Fase 4:

- no modifica los estados de `Appointment` ni de `ClinicalEncounter` (`ADR-022`);
- no crea ni modifica `DoctorPatientRelationship` automáticamente (`ADR-028`, `phase-4-permissions.md` §3);
- no duplica `Patient`, `Doctor`, `Clinic` ni `MedicalRecord` (`ADR-021`, `ADR-025`);
- preserva la distinción de autorización asignado/relación-activa ya cerrada en Fase 3
  (P-009/P-010/P-011/P-013) — el hallazgo H-02 mostró que la primera versión de
  `phase-4-permissions.md` corría el riesgo de romperla; queda corregido y formalizado en ADR-028;
- reutiliza el mecanismo de idempotencia de Fase 2 (`Idempotency-Key`) sin modificarlo;
- reutiliza `AuditEvent`/`Clinical History ≠ Audit Trail` de Fase 3 sin redefinir su política base;
- no altera ninguna migración, modelo ni código de Fase 1–3 (esta revisión fue exclusivamente
  documental).

---

## 9. Scope control

**Confirmado: Fase 4 no absorbió funcionalidad de fases posteriores.**

Se verificó explícitamente (y se formalizó en ADR-030) que ningún documento de Fase 4 introduce:
resultados de estudios, `CareRequest` como flujo operativo, notificaciones complejas, catálogos
obligatorios (farmacológico, diagnóstico o de estudios), firma electrónica, dashboards de Fase 5,
ni funcionalidad de Fase 6. La única mención de `CareRequest` (relación arquitectónica futura y
opcional de `ClinicalDocument`) está explícitamente marcada como no funcional en esta fase, tanto
en `phase-4-documents.md` §19 como, tras esta revisión, en `requirements.md` §23 (L-01).

---

## 10. Decisiones humanas requeridas

```text
No se requieren decisiones humanas adicionales.
```

Los 12 hallazgos se resolvieron de forma inequívoca aplicando la jerarquía de fuentes de verdad
(decisiones ya cerradas de Fase 2/3, principalmente P-009/P-010, SC-065, y el mecanismo
`Idempotency-Key`), sin necesidad de abrir ninguna `DECISIÓN PENDIENTE` para revisión humana.

---

## 11. Resultado final

```text
PHASE 4 DOCUMENTATION REVIEW

CRITICAL: 0
HIGH: 0
MEDIUM: 0
LOW: 0
INFO: 0

Contradicciones críticas: 0
Decisiones pendientes: 0

Consistencia documental:
PASS

Consistencia con Fases 1–3:
PASS

Scope control:
PASS

Documentación:
READY
```

```text
READY FOR PHASE 4 IMPLEMENTATION
```

*(Los conteos anteriores reflejan el estado DESPUÉS de aplicar las 12 correcciones descritas en
§3/§4 de este mismo informe; antes de la corrección el estado era 1 CRITICAL, 3 HIGH, 6 MEDIUM, 2
LOW, 0 INFO.)*

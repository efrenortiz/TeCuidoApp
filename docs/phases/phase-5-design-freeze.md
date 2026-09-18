# Fase 5 — CareRequest y operación: Design Freeze

**Fecha:** 2026-09-14
**Ámbito:** exclusivamente diseño y documentación — **en la fecha de este documento**, Fase 5 no
tenía implementación de código todavía. Este documento certificó el cierre del diseño
funcional/conceptual, no un cierre de fase (eso correspondía entonces a un informe final
posterior a la implementación, como `phase-4-final-report.md`).

**HISTORICAL (2026-09-18):** Fase 5 ya fue implementada, auditada y cerrada formalmente — ver
`docs/phases/phase-5-final-report.md` §41.K (`PHASE 5 — CLOSED`). Este documento se conserva
íntegro como registro del hito de Design Freeze (2026-09-14); no describe el estado actual del
proyecto. Para el estado actual, consultar el reporte final, no este documento.

---

## 1. Resumen ejecutivo

La definición conceptual de `CareRequest` (Fase 5) pasó por una auditoría documental final que
revisó consistencia funcional, arquitectónica, de modelo/relaciones, transaccional, de archivos,
de seguridad/autorización, de rate limiting, de alcance (sala de espera) y de UX, además de una
búsqueda cruzada de terminología heredada del modelo anterior (aprobación/revisión manual).

La auditoría encontró dos puntos sin resolver — una contradicción real entre los límites de
adjuntos documentados y lo que `ClinicalDocument` (Fase 4) soporta en código, y una ambigüedad de
concurrencia/alcance en el rate limiting de creación de `CareRequest` — y quedaron resueltos
mediante decisiones de cierre explícitas, documentadas y trazables (ver §3).

Con esos dos puntos cerrados, no queda ninguna marca `PENDIENTE DE DECISIÓN` en la documentación
de Fase 5 (verificado por búsqueda global sobre `requirements.md`, `docs/architecture.md`,
`docs/design/screens.md`, ADR-004 y ADR-005).

---

## 2. Decisiones funcionales confirmadas (D1–D14 — revisión de dominio, 2026-09-14)

| ID | Decisión | Estado | Fuente |
|---|---|---|---|
| D1 | `CareRequest` solicita directamente una cita (médico + fecha + hora), sin aprobación/revisión médica | CONFIRMADA | `requirements.md` §12 |
| D2 | Workflow único `NUEVA → CONVERTIDA`; sin `EN_REVISION`/`ATENDIDA`/`CERRADA` | CONFIRMADA | `requirements.md` §12.1 |
| D3 | Cancelación pertenece exclusivamente a `Appointment`; no existe `CareRequest = CANCELADA` | CONFIRMADA | `requirements.md` §12.1 |
| D4 | FK opcional/nullable entre `CareRequest` y `Appointment`, solo para trazabilidad — dirección exacta de la FK precisada como `CareRequest.appointment` en D24 (§6) | CONFIRMADA | `requirements.md` §13 |
| D5 | Agenda de Fase 2 = única fuente de verdad para disponibilidad/booking/concurrencia; sin lógica duplicada | CONFIRMADA | `requirements.md` §12, `docs/design/booking-and-concurrency.md` |
| D6 | Fallo de conversión → rollback total (ni `CareRequest` ni `Appointment` persisten) | CONFIRMADA | `requirements.md` §12.1 |
| D7 | Adjuntos mediante `ClinicalDocument` — **acotado exactamente a lo que Fase 4 ya soporta** (PDF/JPEG/PNG, límite único de tamaño) | CONFIRMADA | `requirements.md` §12.2 |
| D8 | Sala de espera / check-in fuera de alcance definitivo del sistema (no solo de Fase 5) | CONFIRMADA | `requirements.md` §41, `docs/design/ui-guidelines.md` §34, `docs/design/design-system.md`, ADR-004 §41 |
| D9 | Autorización según ADR-004; sin política de permisos nueva | CONFIRMADA | ADR-004 |
| D10 | `CareRequest` no diagnostica, no hace triage ni genera recomendaciones clínicas automáticas | CONFIRMADA | `requirements.md` §12.1 |
| D11 | Antivirus fuera de alcance de Fase 5 (sin ClamAV ni proveedor externo) | CONFIRMADA | `requirements.md` §12.2 |
| D12 | Máximo 3 `CareRequest` por **actor autenticado** (no por paciente destino) en ventana móvil de 1 hora | CONFIRMADA | `requirements.md` §12.3 |
| D13 | Sin Redis/Celery/microservicios/colas para resolver requisitos de Fase 5 | CONFIRMADA | `requirements.md` §12.3, `docs/architecture.md` §7.7 |
| D14 | Rate limiting implementado en PostgreSQL; concurrencia resuelta con `select_for_update()` sobre la fila del `User` actor | CONFIRMADA | `requirements.md` §12.3 |

---

## 3. Puntos cerrados durante esta revisión final

### 3.1 Adjuntos — contradicción tipos/límites vs. `ClinicalDocument`

**Problema:** una sesión de diseño previa había documentado 7 tipos de archivo (incluyendo WEBP,
DOCX, XLSX, TXT) y una tabla de límites por tipo + tope acumulado de 30 MB, bajo la premisa de
"reutilizar `ClinicalDocument`". El código real de
`clinical_documents/services/storage.py::ALLOWED_MIME_TO_EXTENSIONS` solo soporta PDF/JPEG/PNG,
con un único límite de tamaño (`CLINICAL_DOCUMENTS_MAX_UPLOAD_SIZE_BYTES`). Implementar lo
documentado habría exigido modificar una app de Fase 4 ya cerrada y auditada, sin una decisión
explícita para hacerlo.

**Resolución:** `CareRequest` se acota exactamente a los tres tipos y al límite único que
`ClinicalDocument` ya soporta, sin tocar su código. El único elemento nuevo (máximo 5 archivos
por `CareRequest`) se resuelve en la capa de `care_requests`, invocando
`ClinicalDocumentService.upload()` hasta 5 veces. Ver `requirements.md` §12.2.

### 3.2 Rate limiting — alcance del conteo y concurrencia

**Problema (alcance):** la regla "3 `CareRequest` por paciente autenticado" no contemplaba que la
solicitud puede originarla un responsable en nombre de un paciente relacionado — contado "por
paciente destino", un responsable con varios pacientes podía eludir el límite repartiendo
solicitudes entre ellos.

**Problema (concurrencia):** un `SELECT COUNT(*)` seguido de un `INSERT` sin serialización
permite que dos solicitudes casi simultáneas del mismo actor cuenten "2 previas" cada una y ambas
pasen, superando el máximo de 3.

**Resolución:** el límite se cuenta por **actor autenticado** (el `User` que crea la solicitud,
sea el propio paciente o un responsable), no por paciente destino. El conteo y la creación se
serializan con `select_for_update()` sobre la fila del `User` actor, dentro de la misma
transacción — el mismo patrón ya usado en `PrescriptionService.create_version`,
`StudyOrderService.create_version` y `ClinicalDocumentService.create_version`/
`void_or_inactivate`. Sin Redis, Celery ni infraestructura nueva. Ver `requirements.md` §12.3.

---

## 4. Matriz final de auditoría

| Área | Estado | Evidencia / documento |
|---|---|---|
| CareRequest lifecycle | ✅ | `requirements.md` §12.1 |
| CareRequest → Appointment | ✅ | `requirements.md` §12, §13 |
| Atomicidad / rollback | ✅ | `requirements.md` §12.1, `docs/architecture.md` §7.7 |
| Appointment FK | ✅ | `requirements.md` §13 |
| Agenda integration | ✅ | `requirements.md` §12, `docs/design/booking-and-concurrency.md` |
| Attachments | ✅ | `requirements.md` §12.2 (acotado a PDF/JPEG/PNG, límite único de Fase 4) |
| Authorization | ✅ | ADR-004 |
| Rate limiting | ✅ | `requirements.md` §12.3 (alcance por actor + concurrencia con `select_for_update()`) |
| Waiting room scope | ✅ | `requirements.md` §41, `ui-guidelines.md` §34, `design-system.md`, ADR-004 §41 |
| Security | ✅ | `requirements.md` §12.2 |
| UX/screens | ✅ (nivel conceptual) | `docs/design/screens.md` §9.4 |
| ADR consistency | ✅ | ADR-004, ADR-005, ADR-006 |
| Terminology | ✅ | búsqueda global sin residuos de "aprobación"/"revisión"/"bandeja"/estados legacy |
| Cross-document consistency | ✅ | `requirements.md` ↔ `docs/architecture.md` ↔ `docs/design/screens.md` |

**CRITICAL: 0 · Bloqueantes: 0 · Importantes no bloqueantes: 0 · Pendientes: 0**

---

## 5. Veredicto del diseño funcional (2026-09-14)

Un desarrollador puede implementar Fase 5 a partir de `requirements.md` §12–§13/§41,
`docs/architecture.md` §7.7, ADR-004/005/006 y `docs/design/screens.md` §9.4 sin tener que tomar
decisiones funcionales o arquitectónicas nuevas por su cuenta: el ciclo de vida, la integración
con Agenda, la atomicidad, la relación con `Appointment`, los adjuntos, la seguridad, el rate
limiting (regla y mecanismo de concurrencia) y el alcance (incluida la exclusión definitiva de
sala de espera/check-in) están completamente determinados.

```text
FASE 5 — DESIGN FREEZE (FUNCIONAL)
```

Ningún ADR fue modificado en su decisión; ADR-004/005/006 permanecen consistentes con esta
consolidación.

---

## 6. Decisiones técnicas confirmadas (D1–D24 — flujo `CareRequest → Hold → Appointment`, cerradas 2026-09-15)

**Nota de numeración:** estos D1–D24 son una serie distinta de los D1–D14 funcionales de §2 —
cubren el "cómo" a nivel de servicio y de modelo de datos, no el "qué" de dominio. Detalle
completo, con cita del código real verificado, en
`docs/design/care-request-service-contracts.md` y `docs/design/care-request-data-model.md`
(este último, nuevo en esta revisión).

| ID | Decisión | Estado | Documentos afectados |
|---|---|---|---|
| D1 | `CareRequestService` orquesta; delega disponibilidad/concurrencia/`DoctorClinic`/timezone/duración a Agenda | CONFIRMADA | `care-request-service-contracts.md` §1/§5 |
| D2 | `start_at`/`end_at` se toman de un slot de `get_available_slots(*, actor, doctor, clinic, date)` — verificado en código; `CareRequest` no calcula duración | CONFIRMADA | `care-request-service-contracts.md` §3, `docs/architecture.md` §7.7 |
| D3 | Transacción única exterior; los `atomic()` de `create_hold`/`create_appointment_from_hold` se anidan como SAVEPOINT | CONFIRMADA | `care-request-service-contracts.md` §4 |
| D4 | `CareRequest` nace `NUEVA`; transición a `CONVERTIDA` antes del `COMMIT`, sin estado intermedio de revisión | CONFIRMADA | `care-request-service-contracts.md` §4 |
| D5 | `CareRequestService` no implementa ninguna regla de Agenda — solo adapta datos al contrato existente | CONFIRMADA | `care-request-service-contracts.md` §5 |
| D6 | Reutiliza `hold.create_hold(*, actor, doctor, clinic, start_at, end_at)` tal cual; sin incompatibilidad detectada | CONFIRMADA | `care-request-service-contracts.md` §6 |
| D7 | Reutiliza `appointment.create_appointment_from_hold(...)` tal cual; sin método paralelo | CONFIRMADA | `care-request-service-contracts.md` §8 |
| D8 | Opción B: `AppointmentService` no conoce `CareRequest`; la FK (`CareRequest.appointment`, ver D24) se asigna después, en la misma transacción — `Appointment` no cambia | CONFIRMADA | `care-request-service-contracts.md` §9, ADR-005 §44, `docs/architecture.md` §7.7 |
| D9 | Rechazo de Agenda → propagación de la excepción existente → `ROLLBACK` total; sin estados `EN_REVISION`/`ATENDIDA`/`CERRADA`/`WAITING` | CONFIRMADA | `care-request-service-contracts.md` §10 |
| D10 | Idempotencia se verifica **antes** del rate limit; rate limit dentro de la transacción exterior, antes de invocar Agenda | CONFIRMADA | `care-request-service-contracts.md` §11 |
| D11 | Adjuntos vía `ClinicalDocumentService.upload()`, creados **después** de la `Appointment` y asociados a ella mediante la FK `ClinicalDocument.appointment` ya existente (sin FK nueva hacia `CareRequest`); compensación síncrona tras rollback; limpieza de huérfanos fuera de alcance de toda fase | CONFIRMADA | `care-request-service-contracts.md` §12, `docs/architecture.md` §7.7 |
| D12 | Creación de `CareRequest` dentro de un SAVEPOINT propio (no el exterior) para que un `IntegrityError` de la carrera de idempotencia no invalide la transacción — mismo patrón que `reschedule_appointment` | CONFIRMADA | `care-request-service-contracts.md` §7 |
| D13 | `idempotency_key` opcional en `CareRequest`, mismo patrón de `UniqueConstraint` parcial que `appointments` | CONFIRMADA | `care-request-service-contracts.md` §13, `care-request-data-model.md` §4 |
| D14 | Carrera con la misma clave: `UniqueConstraint` + captura de `IntegrityError` (en SAVEPOINT — D12) + re-consulta + replay — nunca un error crudo | CONFIRMADA | `care-request-service-contracts.md` §14 |
| D15 | Rollback total ⇒ ninguna fila persiste ⇒ la clave no queda "reservada" para un reintento posterior | CONFIRMADA | `care-request-service-contracts.md` §15 |
| D16 | Valor de retorno: DTO explícito `CareRequestResult` (ids + estado) — única excepción al patrón de "devolver la instancia ORM" del resto del proyecto, justificada por abarcar varias entidades | CONFIRMADA | `care-request-service-contracts.md` §16, `docs/architecture.md` §7.7 |
| D17 | **(corrige D13 de la revisión anterior)** La `Idempotency-Key` **no** se propaga a `create_appointment_from_hold` — se invoca con `idempotency_key=""`; la clave pertenece solo al namespace de `CareRequest`, para no colisionar con el namespace independiente de `Appointment` | CONFIRMADA | `care-request-service-contracts.md` §8/§13, `docs/architecture.md` §7.7 |
| D18 | No existe operación funcional de edición independiente de `CareRequest` (`update`); el ciclo es únicamente crear→`NUEVA`→`CONVERTIDA`, o crear→error→rollback→nada persiste | CONFIRMADA | `care-request-data-model.md` §2 |
| D19 | Modelo de datos completo de `CareRequest` (campos, obligatoriedad, relación `patient`/`created_by`/`responsible`, constraints `start_at < end_at` y unicidad de idempotencia) documentado en archivo dedicado | CONFIRMADA | `docs/design/care-request-data-model.md` (nuevo) |
| D20 | **(corrige D10/D12 de la revisión anterior — P1)** `select_for_update()` sobre el actor se adquiere **antes** del re-check autoritativo de idempotencia, y ese re-check ocurre **antes** del rate limit — un solo lock sirve para ambos; el `UniqueConstraint`+`IntegrityError` pasa a ser defensa en profundidad, no el mecanismo primario | CONFIRMADA | `care-request-service-contracts.md` §7/§11 |
| D21 | **(precisa el modelo — P2)** `padecimiento`/`descripcion`: única semántica `blank=True, default="", null=False` (nunca `NULL`), igual que el resto de campos de texto opcionales del proyecto; `CheckConstraint(start_at__lt=F(end_at))` con el mismo patrón exacto de `availability_start_before_end`; validación de `responsible` es de servicio (`ResponsiblePatientRelationship.Status.ACTIVE`), nunca `CheckConstraint` | CONFIRMADA | `care-request-data-model.md` §2/§4/§5/§6 |
| D22 | **(P3)** Contrato API mínimo: `POST /api/v1/care-requests/`, vistas planas sin DRF, `_ERROR_MAP` reutilizado; adjuntos con errores de validación mapeados a 400 (igual que Fase 4, no 413/415 nuevos); únicas excepciones nuevas: `CareRequestPermissionDenied` (403) y `CareRequestRateLimitExceeded` (429, sin precedente en el proyecto) | CONFIRMADA | `care-request-service-contracts.md` §17 |
| D23 | Todas las FK de `CareRequest` hacia entidades de negocio (`patient`, `created_by`, `responsible`, `doctor`, `clinic`, `appointment`) usan **`on_delete=PROTECT`**, única y explícita — sin alternativas "`PROTECT` o `RESTRICT`"/"`PROTECT` o `SET_NULL`" | CONFIRMADA | `care-request-data-model.md` §2/§6 |
| D24 | **(invierte D4/D8 anteriores)** La relación con `Appointment` es propiedad de `CareRequest`: `CareRequest.appointment` (`OneToOneField`, opcional, `on_delete=PROTECT`), cardinalidad `CareRequest 1 ─── 0..1 Appointment` — nunca `Appointment.care_request`. `Appointment` no gana ningún campo ni migración; la dependencia de apps queda exclusivamente `care_requests → appointments`, nunca al revés, también a nivel de modelo/FK. Invariante transaccional: imposible tener `CareRequest CONVERTIDA` sin `appointment` asignado | CONFIRMADA | `care-request-data-model.md` §3/§6, `care-request-service-contracts.md` §9, `docs/architecture.md` §7.7, ADR-005 §44 |

---

## 7. Flujo técnico definitivo

### Camino de éxito

```text
Actor
  ↓
CareRequest API                             [D22 — POST /api/v1/care-requests/]
  ↓
CareRequestService.create(...)
  ↓
Idempotency lookup preliminar (opcional, sin lock — solo optimización)
  ↓
Auth (ADR-004, sin política nueva)
  ↓
BEGIN atomic()                              [transacción exterior]
  ↓
select_for_update() sobre User actor         [D20 — un solo lock, sirve para lo siguiente y para rate limit]
  ↓
RE-CHECK autoritativo de Idempotency-Key     [D20 — AQUÍ, antes del rate limit]
  ├── existe, coincide → replay, FIN (sin rate limit)
  ├── existe, distinto → Conflict, FIN
  └── no existe → continuar
       ↓
     rate limit: contar CareRequest del actor en la última hora   [D10/D20]
       ↓ (< 3)
     CareRequest.objects.create(status=NUEVA, idempotency_key=...)   [SAVEPOINT defensa en profundidad — D4, D12, D13, D20]
       ↓
     get_available_slots() ya resuelto por el cliente → slot {start, end}   [D2]
       ↓
     hold_service.create_hold(start_at=slot.start, end_at=slot.end, ...)   [SAVEPOINT — D6]
       ↓
     appointment_service.create_appointment_from_hold(..., idempotency_key="")  [SAVEPOINT — D7, D17]
       ↓
     care_request.appointment = appointment; save()     [D8, D24 — opción B, FK invertida]
       ↓
     ClinicalDocumentService.upload(..., appointment=appointment) × N adjuntos   [D11 — acumula storage_key]
       ↓
     CareRequest.status = CONVERTIDA; save()      [D4]
       ↓
     COMMIT
       ↓
     return CareRequestResult(...)   [D16, D22 — DTO explícito, serializado por la API]
```

Nótese `idempotency_key=""` en la llamada a Agenda (D17) — deliberado, no un descuido: la clave
del cliente no se reutiliza ahí (§8 de la tabla).

### Camino de error

```text
Cualquier excepción de rate limit (D10/D20), de HoldService/AppointmentService (D6/D7/D9),
o de ClinicalDocumentService (D11)
  ↓
ROLLBACK de la transacción exterior
  ↓ (ninguna fila de CareRequest/Hold/Appointment/ClinicalDocument de esta ejecución persiste)
Compensación síncrona: delete_best_effort() por cada storage_key acumulado en esta ejecución
  ↓
Se propaga la excepción original al llamador → CareRequest API la traduce vía `_ERROR_MAP` (D22)
```

---

## 8. Escenarios de idempotencia

| Escenario | Resultado |
|---|---|
| Primera solicitud con `Idempotency-Key` | Se ejecuta el camino de éxito completo; la clave queda registrada **solo** en `CareRequest.idempotency_key` — no se propaga a `Appointment` (D17). |
| Replay exacto (misma clave, mismos datos) | El lookup preliminar (sin lock) puede detectarlo como atajo; si no, el **re-check autoritativo bajo lock** (D20, después de `select_for_update()`, antes del rate limit) lo detecta con certeza — no crea una segunda `CareRequest` ni `Appointment`, no consume cupo de rate limit, devuelve el resultado ya existente. |
| Misma clave con datos distintos | `Conflict` — nunca sobrescribe ni reinterpreta la intención original. |
| Dos solicitudes concurrentes con la misma clave | La segunda queda bloqueada por `select_for_update()` hasta que la primera resuelve (D20) — cuando continúa, su re-check ya ve el estado definitivo; no hay ventana en la que ambas lean "no existe". El `UniqueConstraint`+`IntegrityError` en SAVEPOINT propio (D12) queda como defensa en profundidad para el caso extraordinario en que igual llegaran ambas al `INSERT`. Nunca un error crudo. Como la clave no llega a `Appointment` (D17), no hay una segunda carrera posible en ese namespace. |
| Operación fallida con rollback | No queda ninguna fila con esa clave — un reintento posterior con la misma clave vuelve a ejecutar la operación completa desde cero, no la "encuentra reservada". |
| Solicitud sin `Idempotency-Key` | Cada solicitud es una operación independiente y válida, igual que en Agenda sin la cabecera. |

---

## 9. Matriz técnica final

| Área técnica | Estado | Evidencia |
|---|---|---|
| Orquestación vs. delegación | ✅ | `care-request-service-contracts.md` §1/§5 |
| Origen de `start_at`/`end_at` | ✅ | §3, verificado contra `get_available_slots` real |
| Límite transaccional | ✅ | §4, verificado contra `@transaction.atomic` real de `hold.py`/`appointment.py` |
| Orden lock → re-check idempotencia → rate limit | ✅ | §7/§11 (D20), justificado y sin ventana de carrera |
| SAVEPOINT en la creación de `CareRequest` (defensa en profundidad) | ✅ | §7, mismo patrón que `reschedule_appointment` (verificado en código) |
| Integración `HoldService` | ✅ | §6, sin incompatibilidad detectada contra el código real |
| Integración `AppointmentService` (opción B, FK invertida) | ✅ | §9 (D8, D24), ADR-005 §44 |
| Camino de error / rollback | ✅ | §10 |
| Adjuntos asociados a `Appointment` (FK ya existente) | ✅ | §12, verificado que `ClinicalDocument.appointment` ya existe en código |
| Valor de retorno (DTO explícito) | ✅ | §16, verificado que ningún otro servicio del proyecto usa DTO — excepción justificada y acotada a este servicio |
| Idempotencia sin propagación a Agenda | ✅ | §13/§14/§15, corregido en §8/§13 (D17) |
| Modelo de datos (`CareRequest`) — sin ambigüedad NULL/`""` | ✅ | `docs/design/care-request-data-model.md` (D21) — `blank=True, default=""` uniforme, `CheckConstraint` con precedente exacto |
| `on_delete=PROTECT` único y explícito en todas las FK | ✅ | `care-request-data-model.md` §2/§6 (D23) — sin alternativas ambiguas |
| Relación `CareRequest.appointment` (propietaria) y dependencia `care_requests → appointments` | ✅ | `care-request-data-model.md` §3/§6, `care-request-service-contracts.md` §9 (D24) — `Appointment` sin campos ni migración nuevos |
| Sin edición independiente de `CareRequest` | ✅ | `care-request-data-model.md` §2 (D18) |
| Contrato API mínimo (endpoint, entrada, DTO, errores) | ✅ | `care-request-service-contracts.md` §17 (D22) — reutiliza `_ERROR_MAP`/`JsonApiView`, sin DRF |
| No modificación de Agenda/Fase 4 | ✅ | §18 |

**Bloqueantes: 0 · Decisiones inventadas: 0 (toda reutilización verificada contra código real) · Pendientes: 0**

---

## 10. Veredicto final consolidado (revisado 2026-09-15)

> ¿El flujo técnico de `CareRequest → Hold → Appointment` está suficientemente definido para
> comenzar implementación sin tomar nuevas decisiones funcionales o arquitectónicas importantes?

**Sí.** Esta ronda cerró los tres puntos que la auditoría anterior había dejado pendientes de
precisión:

```text
P1 — Idempotencia / Rate Limit → CERRADO (D20)
P2 — Modelo CareRequest        → CERRADO (D21)
P3 — API Contract              → CERRADO (D22)
```

Cada punto de integración con Agenda (Fase 2) y con `ClinicalDocument` (Fase 4) se verificó
contra las firmas y el comportamiento reales del código existente
(`appointments/services/availability.py`, `hold.py`, `appointment.py`,
`clinical_documents/services/document.py`, `clinical_documents/api_common.py`,
`appointments/api.py`) — no se asumió ni se inventó ningún contrato. El único elemento sin
precedente exacto en el proyecto es el DTO de retorno (D16); se documentó el mínimo explícito
posible, acotado a este servicio. La idempotencia, el manejo de carreras y el uso de SAVEPOINT
propio para no invalidar la transacción exterior siguen exactamente patrones ya auditados y en
producción documental en Fase 2 (`reschedule_appointment`, `create_appointment_from_hold`) y
Fase 4 (`create_version`). El modelo de datos completo de `CareRequest` (D19) y la ausencia de
una operación de edición independiente (D18) quedaron documentados en
`docs/design/care-request-data-model.md`. La corrección sobre no propagar la `Idempotency-Key` a
Agenda (D17) se aplicó de forma consistente. El orden lock→re-check→rate-limit (D20) cierra la
ventana de carrera que la versión anterior dejaba abierta. La ambigüedad `NULL`/`""` en los
campos de texto opcionales (D21) quedó resuelta con la convención ya usada en todo el proyecto.
El contrato API (D22) reutiliza `_ERROR_MAP`/`JsonApiView` de Fases 2–4 sin excepción, incluida
la corrección de no introducir 413/415 donde Fase 4 ya usa 400.

Esta ronda adicional incorporó dos decisiones arquitectónicas de cierre: **D23** fija
`on_delete=PROTECT` como única opción para todas las FK de `CareRequest` (sin alternativas
ambiguas), y **D24** invierte la relación con `Appointment` — `CareRequest.appointment`
(`OneToOneField` opcional), nunca `Appointment.care_request`. Esta inversión es una mejora real,
no solo cosmética: con la FK del lado de `CareRequest`, `Appointment`/`appointments` no requiere
ningún campo ni migración nueva para dar cabida a Fase 5, reforzando la independencia de
`appointments` respecto de `care_requests` también a nivel de modelo, no solo de llamadas de
servicio. La dependencia de apps queda confirmada como exclusivamente
`care_requests → appointments` en toda la documentación revisada — ninguna referencia restante a
`appointments → care_requests`.

Ningún ADR fue modificado en su decisión (ADR-005 solo ganó una aclaración puntual que confirma
algo que ya era compatible, ahora actualizada para la FK invertida); ADR-004/006 y los contratos
de Agenda/Fase 4 permanecen exactamente como estaban — la reutilización fue posible sin
tocarlos.

```text
✅ FASE 5 — TECHNICAL DESIGN FREEZE
```

**Estado del proyecto tras este freeze** (no confundir con cierre de fase ni con
implementación) — **`[HISTORICAL]`, válido únicamente en la fecha de este documento
(2026-09-14); ver la nota `HISTORICAL` al inicio de este archivo y
`docs/phases/phase-5-final-report.md` §41.K para el estado actual (`PHASE 5 — CLOSED`)**:

```text
Fase 5 — Diseño técnico cerrado
Fase 5 — Implementación pendiente   [HISTORICAL — implementada y cerrada desde 2026-09-18]
```

No se implementó código, no se crearon migraciones, no se modificaron servicios ni APIs
existentes, y no se tocó infraestructura como parte de esta revisión (de nuevo: esto describe
exclusivamente el alcance de este documento de Design Freeze, no el estado actual del proyecto).

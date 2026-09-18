# Fase 5 — Contratos de servicio de `CareRequest`

**Decisiones de cierre técnico:** 2026-09-15. Consolida el flujo
`CareRequest → Hold → Appointment`. Complementa, sin sustituir,
`requirements.md` §12/§12.1/§12.2/§12.3/§13 (fuente funcional) y `docs/architecture.md` §7.7
(responsabilidad de la app).

## 1. Frontera y principio de orquestación

```text
UI/API
  ↓
CareRequestService
  ↓
BEGIN transaction.atomic()                    [transacción exterior]
  ↓
lock actor/User (select_for_update)
  ↓
RE-CHECK Idempotency-Key (autoritativo)
  │
  ├── existe → replay / conflict, FIN
  │
  └── no existe
          ↓
       rate limit
          ↓
       CareRequest = NUEVA
          ↓
       Agenda / Hold (F2)
          ↓
       Appointment (F2)
          ↓
       CareRequest.appointment = Appointment
          ↓
       ClinicalDocument (F4)
          ↓
       CareRequest = CONVERTIDA
          ↓
       COMMIT
          ↓
       DTO
```

Puede existir un lookup preliminar de idempotencia (lectura simple, sin lock) antes de `BEGIN
transaction.atomic()` como **optimización** para evitar abrir una transacción cuando el replay
es obvio — pero la comprobación **autoritativa** siempre ocurre después de adquirir el lock del
actor y antes del rate limiting (detalle completo en §7/§11).

> **CareRequest orquesta; Agenda reserva; Appointment representa la cita; ClinicalDocument
> gestiona los archivos.**

`CareRequestService` no implementa ninguna regla de disponibilidad, conflicto, concurrencia,
`DoctorClinic`, timezone ni duración — esas siguen perteneciendo exclusivamente a
`appointments.services.availability`/`hold`/`appointment` (`docs/design/
agenda-service-contracts.md` §6/§7), sin cambios en esos módulos.

## 2. Servicio y operación

```text
CareRequestService

- create(*, actor, patient, doctor, clinic, start_at, end_at, motivo, padecimiento,
         descripcion, attachments=[], idempotency_key="")
```

`start_at`/`end_at` llegan ya resueltos por el cliente a partir de un slot de Agenda (§3) — no
son calculados por `CareRequestService`. `responsible` se deriva del actor cuando aplica (no es
un parámetro independiente aceptado del cliente — mismo criterio de derivación ya usado en Fase
4, D-003 de `clinical-documents-data-model.md`). Modelo de datos completo (campos, constraints,
nulls/defaults) en `docs/design/care-request-data-model.md`.

## 3. Origen de `start_at`/`end_at` — reutilización de `get_available_slots` (P1 adicional)

Verificado en código real: `appointments/services/availability.py::get_available_slots(*,
actor, doctor, clinic, date)` ya devuelve una lista de slots con la forma
`{"start": ..., "end": ..., "status": ...}`; el frontend de Agenda ya consume `slot.start`/
`slot.end` directamente.

**Decisión definitiva:** `CareRequest` no calcula `end_at` (ni como `start + duration` ni
consultando la duración por su cuenta). El flujo es:

```text
Agenda: get_available_slots(actor, doctor, clinic, date)
      ↓
slot seleccionado por el cliente → {start, end}
      ↓
CareRequestService.create(..., start_at=slot.start, end_at=slot.end, ...)
      ↓
HoldService.create_hold(start_at=start_at, end_at=end_at, ...)
```

`create_hold` (§6) vuelve a validar el intervalo completo contra el estado actual de Agenda
(alineación de slot, disponibilidad, conflictos) — la reutilización del slot por parte de
`CareRequest` no reemplaza esa revalidación, solo evita que `CareRequest` reconstruya un
intervalo que Agenda ya calculó.

### 3.1 Validación de entrada antes de persistir (corrección — 2026-09-17)

Aunque `start_at`/`end_at` provienen de un slot ya válido de Agenda (arriba), el servicio no
puede asumir que el cliente los reenvía intactos. `create()` valida `start_at < end_at`
**antes** de abrir la transacción y antes de cualquier intento de `INSERT`
(`_validate_interval`, `CareRequestValidationError` → `400` en la API). El
`CheckConstraint(care_request_start_before_end)` del modelo permanece sin cambios como defensa
en profundidad — la validación de servicio evita que ese caso llegue a manifestarse como un
`IntegrityError` crudo propagado al consumidor (antes de esta corrección, ese era exactamente
el comportamiento: un `500` con el `DETAIL` de PostgreSQL, que además puede incluir el valor de
otros campos de la fila fallida). Orden general de la operación:

```text
request
 ↓
parse/normalize (API)
 ↓
validate service input (longitud de adjuntos, intervalo, motivo)
 ↓
transacción (lock, idempotencia, rate limit, persistencia)
 ↓
persist
```

### 3.1.1 Validación vs. idempotencia — caso "existing key + request actual inválida" (confirmado, no modificado — auditoría 2026-09-18)

Pregunta explícita auditada: si un actor reutiliza una `Idempotency-Key` ya asociada a una
`CareRequest` comprometida, pero la solicitud actual es en sí misma inválida (`motivo` vacío,
`start_at >= end_at`), ¿el resultado debe ser `400` (validación) o `409`/replay (idempotencia)?

**Confirmado contra el precedente ya existente y aprobado del proyecto** —
`appointments.services.appointment.reschedule_appointment` (`appointments/services/
appointment.py`, líneas 210-217) — llama `_require_valid_reason(reason)` **antes** de cualquier
chequeo de `idempotency_key`:

```python
def reschedule_appointment(*, actor, appointment, new_clinic, new_start_at, reason, idempotency_key=""):
    _require_valid_reason(reason)          # validación PRIMERO
    if idempotency_key:                    # idempotencia DESPUÉS
        ...
```

Este es exactamente el orden que `care_requests.services.care_request.create()` ya implementaba
(`_validate_interval`/`_clean_motivo` antes del `lock`/re-check). **No se modifica el orden** —
esta sección documenta y confirma, con evidencia concreta del contrato existente, que la
implementación actual es correcta, no una preferencia personal:

- La validez estructural de una solicitud es una propiedad de la solicitud misma, independiente
  de si su clave coincide con algo — una solicitud inválida no tiene una "identidad" coherente
  contra la cual comparar.
- Evaluar la identidad de una solicitud inválida contra un registro existente puede producir un
  `409` semánticamente engañoso (sugiere "reutilizaste una clave con datos distintos" cuando el
  problema real es que la solicitud actual está mal formada, independientemente de la clave).
- Consumir el lock del actor y hacer consultas de idempotencia/rate-limit para una solicitud que
  de todos modos será rechazada por validación estructural es trabajo innecesario.

Test que fija este comportamiento: `test_invalid_request_with_existing_key_is_400_not_replay_or_conflict`.

## 4. Transacción única (D2, sin cambios)

```text
transaction.atomic():          # exterior, de CareRequestService
    rate limit (select_for_update sobre User actor) — §9
    CareRequest.objects.create(status=NUEVA, ...)   # con savepoint propio — §7
    hold = hold_service.create_hold(...)              # @transaction.atomic anidado → SAVEPOINT
    appointment = appointment_service.create_appointment_from_hold(..., idempotency_key="")  # idem → SAVEPOINT — §13: sin propagar la clave de CareRequest
    care_request.appointment = appointment
    care_request.save(update_fields=["appointment"])
    document_service.upload(..., appointment=appointment)  # por cada adjunto — §11
    care_request.status = CONVERTIDA
    care_request.save(update_fields=["status"])
# COMMIT al salir del bloque exterior sin excepción
```

`create_hold`/`create_appointment_from_hold` ya están decorados con `@transaction.atomic` —
invocados desde dentro de la transacción exterior, Django anida esos `atomic()` como
**SAVEPOINT** sobre la misma conexión (mismo mecanismo ya documentado en ADR-027).

## 5. Validación de Agenda — delegación completa (sin cambios)

`CareRequestService` solo adapta sus datos (`doctor`, `clinic`, `start_at`, `end_at` del slot
elegido) al contrato ya existente de `create_hold`/`create_appointment_from_hold`; toda regla de
negocio de Agenda permanece en `appointments`.

## 6. Integración con `HoldService` (sin cambios)

Firma real reutilizada tal cual: `appointments.services.hold.create_hold(*, actor, doctor,
clinic, start_at, end_at)`. Ya resuelve autorización, ventana de reserva, alineación de slot,
conflictos de `Hold`/`Appointment`, y su propia condición de carrera vía `IntegrityError`
(`appointments/services/hold.py`). Sin wrapper, sin incompatibilidad detectada.

## 7. Lock del actor, re-check de idempotencia y creación de `CareRequest` (P1 — corrige el orden documentado antes)

**Decisión de cierre (2026-09-15) — secuencia autoritativa, reemplaza la versión anterior de
esta sección:**

```text
BEGIN atomic()                                   [transacción exterior — §4]
      ↓
select_for_update() sobre la fila del User actor   [un solo lock; también sirve para §11]
      ↓
RE-CHECK autoritativo: ¿existe CareRequest(created_by=actor, idempotency_key=key)?
      ├── existe, datos coinciden  → replay (return existing), FIN — sin aplicar rate limit
      ├── existe, datos distintos  → CareRequestConflict, FIN
      └── no existe                → continuar
             ↓
           rate limit (§11 — reutiliza el mismo lock, no adquiere uno nuevo)
             ↓
           CareRequest.objects.create(status=NUEVA, idempotency_key=key, ...)
```

**Razón del orden:** una solicitud concurrente que esté reintentando una operación ya creada por
otra petición con la misma clave no debe recibir `429` solo porque la ganadora de la carrera
alcanzó a crear la `CareRequest` primero — el resultado correcto es *replay*, no rate limit. Por
eso el re-check de idempotencia debe ocurrir **antes** del rate limit, no después.

**Por qué el lock debe adquirirse antes del re-check (no solo antes del rate limit):**
`select_for_update()` bloquea a cualquier otra transacción que intente lo mismo para *ese mismo
actor* hasta que la primera haga `COMMIT` o `ROLLBACK`. Si el lock se adquiriera después del
re-check, dos transacciones concurrentes podrían leer "no existe" ambas antes de que cualquiera
insertara, reabriendo la misma carrera que se buscaba cerrar. Adquiriendo el lock primero, la
segunda transacción que intente el re-check queda bloqueada hasta que la primera resuelva por
completo (persiste o revierte) — cuando por fin continúa, el re-check ve el estado ya
definitivo. Esto es un único lock que sirve para dos propósitos (serializar el re-check de
idempotencia y serializar el conteo de rate limit del §11), no dos mecanismos distintos.

**Lookup preliminar opcional, sin lock (optimización — no autoritativo):** puede existir una
lectura previa a `BEGIN atomic()` para evitar abrir una transacción cuando el replay es obvio
(p. ej. un reintento del mismo cliente segundos después). Nunca sustituye el re-check de arriba
— solo evita trabajo en el camino feliz; el re-check bajo lock sigue siendo la única fuente de
verdad.

**El `UniqueConstraint` + captura de `IntegrityError` como defensa en profundidad (ya no la
protección primaria):** se conserva `UniqueConstraint(fields=["created_by", "idempotency_key"],
condition=~Q(idempotency_key=""))` y se sigue envolviendo el `CareRequest.objects.create()` en
su propio `with transaction.atomic():` (SAVEPOINT, mismo patrón que
`appointments.services.appointment.reschedule_appointment` para no invalidar la transacción
exterior si de todos modos disparara). Bajo el lock del actor, esta rama no debería ejecutarse
en operación normal — se conserva por el mismo principio de defensa en profundidad que el
proyecto ya aplica en otros lugares (p. ej. `create_appointment_from_hold` revalida conflictos
"por si acaso" aunque el `Hold` ya esté bloqueado — `# Re-validate conflicts (step 3) — defense
in depth`, `appointments/services/appointment.py`), no porque siga siendo el mecanismo que
determina el resultado.

```text
try:
    with transaction.atomic():          # SAVEPOINT propio — defensa en profundidad
        care_request = CareRequest.objects.create(
            created_by=actor, idempotency_key=idempotency_key, status=NUEVA, ...
        )
except IntegrityError:
    existing = CareRequest.objects.filter(
        created_by=actor, idempotency_key=idempotency_key
    ).first()
    if existing is None or not _idempotent_replay_matches(existing, ...):
        raise CareRequestConflict()
    return existing
```

## 8. `Hold → Appointment` (sin cambios de firma; corregido el valor de `idempotency_key`)

Firma real reutilizada tal cual: `appointments.services.appointment.
create_appointment_from_hold(*, actor, hold, patient, doctor, clinic, idempotency_key="")`. Ya
re-valida disponibilidad/conflictos y marca el `Hold` como `CONSUMED`
(`appointments/services/appointment.py`). Sin método paralelo.

**Decisión de cierre (2026-09-15) — reemplaza la conclusión anterior sobre propagar la clave:**
`CareRequestService` invoca esto con **`idempotency_key=""`** (vacío), nunca con la clave del
cliente — ver §13.

## 9. `CareRequest.appointment` — Opción B, con la FK invertida (decisión de cierre, 2026-09-15)

**Reemplaza la versión anterior de esta sección**, que asignaba `appointment.care_request`. La
relación es propiedad de `CareRequest` (`docs/design/care-request-data-model.md` §3), no de
`Appointment`. `AppointmentService` sigue sin conocer `CareRequest` — su firma no cambia, y
ahora, además, el modelo de `appointments` tampoco necesita ningún campo nuevo (antes sí requería
agregar `Appointment.care_request`; con la FK invertida, `appointments` queda completamente
intacto, sin migración). La asignación se hace después, desde `CareRequestService`, dentro de la
misma transacción exterior:

```text
appointment = appointment_service.create_appointment_from_hold(..., idempotency_key="")
care_request.appointment = appointment
care_request.save(update_fields=["appointment"])
```

Dependencia de apps resultante — la única permitida (ADR-005 §12/§44):

```text
care_requests
      ↓
appointments
```

Nunca `appointments → care_requests` — ni a nivel de llamada de servicio (ya cerrado
anteriormente) ni, ahora explícitamente, a nivel de modelo/FK.

## 10. Rechazo de Agenda → rollback total (sin cambios)

Cualquier excepción ya existente de `appointments.services.exceptions`
(`AvailabilityNotFound`, `InvalidSlot`, `BookingWindowExpired`, `HoldAlreadyExists`,
`HoldConflict`, `SlotUnavailable`, `HoldExpired`, `HoldNotOwned`, `InvalidPatient`,
`InvalidDoctorClinic`, `AppointmentConflict`, etc.) se propaga sin traducirse a un estado de
`CareRequest`; la transacción exterior hace `ROLLBACK` completo — ni `CareRequest`, ni `Hold`,
ni `Appointment`, ni el FK, ni los `ClinicalDocument` de esa ejecución quedan persistidos. Sin
estados `EN_REVISION`/`ATENDIDA`/`CERRADA`/`WAITING`.

## 11. Rate limiting — punto exacto de evaluación (corregido: después del re-check de idempotencia, §7)

**Orden definitivo** (razón ya explicada en §7: un replay idempotente válido nunca debe
rechazarse solo por haber alcanzado el límite de creación):

```text
(dentro de la transacción exterior, después del re-check de idempotencia de §7 — mismo lock,
 no uno nuevo)
Contar CareRequest del actor creados en la última hora.
    → si ya hay 3: rechazar, ROLLBACK, FIN.
    → si no: continuar (§7 — creación de CareRequest).
```

El `select_for_update()` sobre la fila del `User` actor se adquiere **una sola vez**, al
principio de la transacción (§7), y sirve tanto para el re-check de idempotencia como para este
conteo — no se adquiere un segundo lock. Un `SELECT COUNT` sin ese lock no protegería nada bajo
concurrencia (ver la discusión de concurrencia ya cerrada en `requirements.md` §12.3). Sin
Redis, Celery ni infraestructura adicional — sigue siendo PostgreSQL puro.

## 12. Adjuntos — orden definitivo y relación con `Appointment`, no con `CareRequest` (P4 — refinado)

**Decisión definitiva:** los `ClinicalDocument` se crean **después** de que exista la
`Appointment`, y se asocian a ella usando la FK que `ClinicalDocument` **ya tiene** hoy
(`clinical_documents/services/document.py`: `upload(..., appointment=None, ...)` — el parámetro
ya existe, verificado en código). No se introduce ni se documenta una asociación obligatoria
`ClinicalDocument → CareRequest`; eso habría exigido tocar el modelo de `ClinicalDocument`
(Fase 4, cerrada) para darle una FK nueva.

```text
Appointment creada
      ↓
CareRequest.appointment = Appointment asignado (§9)
      ↓
document_service.upload(actor=actor, patient=patient, content=..., appointment=appointment, ...)
      × N adjuntos (acumulando storage_key de cada uno)
      ↓
(cada ClinicalDocument queda asociado a Appointment mediante su FK ya existente)
      ↓
CareRequest = CONVERTIDA
```

**Compensación síncrona** (sin cambios de fondo): si cualquier paso posterior falla,
`ROLLBACK` de la transacción exterior (revierte también las filas de `ClinicalDocument` ya
creadas en esta ejecución) y, para cada `storage_key` acumulado en esta ejecución,
`clinical_documents.services.storage.delete_best_effort(storage_key=...)`, luego se propaga el
error original. Se acepta la ventana entre el `ROLLBACK` de base de datos y la limpieza de
filesystem (mismo principio que ADR-027 para `UPLOADED`). No se introduce staging de archivos ni
una arquitectura de almacenamiento nueva.

**Archivos huérfanos** que sobrevivan al mejor esfuerzo: su detección y limpieza queda **fuera
del alcance de Fase 5 y de cualquier fase del proyecto** — procedimiento operativo de
mantenimiento a cargo del administrador del sistema, no un requisito funcional.

## 7.1 Identidad lógica de la solicitud — comparación de compatibilidad (corrección de cierre, 2026-09-17)

**Reemplaza la comparación anterior**, que solo consideraba `patient`/`doctor`/`clinic`/
`start_at`/`end_at`. Verificado en código real: la solicitud también contiene datos
clínicamente relevantes (`motivo`, `padecimiento`, `descripcion`) y archivos — un `(created_by,
idempotency_key)` reutilizado con una intención incompatible en cualquiera de esos campos no
puede tratarse como replay.

**Campos que forman la identidad lógica de la operación:**

```text
patient, doctor, clinic, start_at, end_at,
motivo, padecimiento, descripcion,
huella de adjuntos
```

`_idempotent_replay_matches(existing, *, patient, doctor, clinic, start_at, end_at, motivo,
padecimiento, descripcion, attachments)` compara cada campo por igualdad directa contra la
`CareRequest` existente — comparación determinista, explícita, sin snapshots de ORM completos
ni frameworks de diffing.

**Identidad de adjuntos — corrección de cierre (2026-09-18), reemplaza la huella nombre+tamaño:**

La huella `(original_filename, size_bytes)` usada hasta la ronda anterior es **insuficiente**:
dos archivos distintos pueden compartir nombre y tamaño por casualidad — o de forma
deliberadamente adversarial — sin ser el mismo archivo. La identidad correcta para esta fase es:

```text
mismo original_filename + mismo size_bytes + mismo contenido byte a byte
```

`same actor + same key + same compatible attachment identity → replay`
`same actor + same key + incompatible attachment identity → 409`

**Implementación (`_attachments_are_identical`), sin nueva infraestructura de almacenamiento:**

1. Si el número de adjuntos difiere, incompatible de inmediato (sin leer nada).
2. Para cada posición (mismo orden de envío que en la ejecución original): si `original_filename`
   o `size_bytes` ya difieren, incompatible — sin leer el contenido binario.
3. Solo cuando nombre y tamaño **ya coinciden** en esa posición, se lee el contenido original con
   `clinical_documents.services.storage.read(storage_key=...)` (Fase 4, función ya existente y
   sin modificar — la única fuente estable disponible para recuperar el contenido tal cual fue
   almacenado) y se compara byte a byte contra el contenido entrante (ya en memoria, sin I/O
   adicional para ese lado).

No se introduce hashing, tabla de hashes, campo nuevo en `ClinicalDocument`, ni ninguna
arquitectura de almacenamiento adicional — se reutiliza `storage.read()` tal cual, y solo se
invoca cuando la comparación barata (nombre + tamaño) ya no puede decidir por sí sola. Antes de
esta corrección, el caso "mismo nombre + mismo tamaño + bytes distintos" se aceptaba
incorrectamente como replay; ahora es `409 CareRequestConflict`.

**Corrección adicional (2026-09-18, hallazgo B — de qué documentos se toma "el original"):**
`_attachments_are_identical` resuelve el conjunto de documentos ORIGINALES leyendo
`existing_care_request.clinical_document_ids` (`care-request-data-model.md` §3.1) — **nunca**
consultando `ClinicalDocument.objects.filter(appointment_id=existing_care_request.appointment_id)`.
Esa consulta por `appointment_id` es incorrecta como fuente de identidad: devuelve **todos** los
documentos que existan hoy para esa `Appointment`, incluidos los que otro flujo haya agregado
después de la conversión original — un documento así de ajeno contaminaría retroactivamente la
comparación (`len(existing_documents) != len(attachments)` fallaría aunque la solicitud
reintentada sea, en los hechos, idéntica a la original) y filtraría hacia `_to_result()` un
`clinical_document_ids` que no corresponde a la operación original. `clinical_document_ids` se
fija una sola vez, en el mismo `save()` que transiciona `status` a `CONVERTIDA`, con los `pk`
recolectados durante esa ejecución — es un snapshot, no una vista recalculable.

**Ejemplo del contrato:**

```text
Request A: key=ABC, motivo="Dolor abdominal"
Request B: key=ABC, motivo="Sangrado"
→ 409 Idempotency Conflict (CareRequestConflict), no replay
```

Esta comparación se aplica en **ambos** puntos donde el código evalúa compatibilidad: el
re-check autoritativo bajo lock (§7) y la recuperación tras `IntegrityError` (§7, más abajo) —
la misma función, sin duplicar la regla.

## 13. Idempotencia — identidad y header (sin propagación a Agenda — corregido 2026-09-15)

```text
UniqueConstraint(fields=["created_by", "idempotency_key"],
                 condition=~Q(idempotency_key=""),
                 name="care_request_idempotency_key_unique")
```

— mismo patrón exacto de `appointments/models.py`
(`appointment_idempotency_key_unique`/`reschedule_idempotency_key_unique`). Clave **opcional**,
recibida vía header `Idempotency-Key`. Con clave: operación idempotente, replay ante repetición
de la misma identidad lógica completa (§7.1: paciente/médico/consultorio/intervalo/motivo/
padecimiento/descripcion/huella de adjuntos), `Conflict` ante repetición con cualquiera de esos
datos distintos. Sin clave: cada solicitud es independiente.

**Decisión de cierre (2026-09-15) — reemplaza la conclusión anterior de este documento:** la
`Idempotency-Key` del cliente pertenece exclusivamente al namespace de `CareRequest`. **No se
propaga literalmente** como `Appointment.idempotency_key` — `create_appointment_from_hold` se
invoca con `idempotency_key=""` (§8). Razón: `Appointment.idempotency_key` tiene su propio
namespace de unicidad `(created_by, idempotency_key)` para llamadas *directas e independientes*
a Agenda; compartir la misma cadena literal entre una operación de `CareRequest` y ese namespace
mezclaría dos identidades de idempotencia distintas — si ese mismo actor usara la misma clave
directamente contra Agenda para una reserva no relacionada, colisionaría sin motivo con la
`Appointment` creada aquí. `AppointmentService` mantiene su contrato y semántica actuales sin
ningún cambio.

Esto no reintroduce el riesgo de duplicados: por el momento en que se llega a invocar
`create_appointment_from_hold` ya se pasó por la protección de idempotencia de `CareRequest`
(§7/§14) — sólo la ejecución ganadora de esa carrera llega hasta aquí, así que no hay manera de
que dos ejecuciones concurrentes para el mismo `(actor, key)` de `CareRequest` intenten crear
dos `Appointment` en paralelo. La protección de Agenda contra conflictos de horario (bloqueo del
`Hold`, re-validación de disponibilidad) sigue aplicando igual, independientemente de esto.

## 14. Concurrencia con la misma `Idempotency-Key` (consistente con §7/§11/§13)

1. Lookup preliminar opcional, sin lock (§7) — replay inmediato si ya existe y coincide;
   optimización, no autoritativo.
2. Si ambas transacciones concurrentes llegan a `BEGIN atomic()`, solo una adquiere el
   `select_for_update()` sobre la fila del `User` actor primero (§7); la otra espera. Cuando la
   segunda por fin adquiere el lock, el re-check de idempotencia ya ve el resultado definitivo
   de la primera (existe, o no existe porque la primera falló) — no hay ventana en la que ambas
   vean "no existe" a la vez.
3. Solo en el caso extraordinario de que el re-check bajo lock igual fallara en detectar una
   fila ya creada por alguna vía fuera de este flujo, el `UniqueConstraint` + captura de
   `IntegrityError` (SAVEPOINT propio) actúa como defensa en profundidad — nunca un
   `IntegrityError` crudo al consumidor.
4. Como la clave no se propaga a Agenda (§8/§13), no existe una segunda carrera posible en
   `Appointment.idempotency_key` originada por esta operación.

## 15. Rollback e idempotencia (sin cambios)

Si la operación falla completamente y hace `ROLLBACK`, ninguna fila queda persistida —
`CareRequest`, `Hold`, `Appointment`, ni el registro de idempotencia (la propia fila de
`CareRequest`). La misma clave usada en un intento fallido no queda "reservada": un reintento
posterior repite la operación completa desde cero.

## 16. Valor de retorno — DTO mínimo explícito (D14 de esta revisión — reemplaza la conclusión anterior)

**Verificado de nuevo en código:** ningún servicio del proyecto usa `dataclass`, `TypedDict` ni
`NamedTuple` (`grep` sin resultados fuera de este documento) — todos devuelven la instancia ORM
directamente (`Prescription`, `StudyOrder`, `ClinicalDocument`, `Appointment`, `Hold`). No existe
un patrón de DTO que reutilizar.

**Decisión definitiva (2026-09-15):** por instrucción explícita, `CareRequestService.create`
devuelve un DTO en vez de la instancia ORM de `CareRequest`, precisamente porque el resultado de
esta operación abarca varias entidades (`CareRequest`, `Appointment`, los `ClinicalDocument`
creados) y no un solo recurso como el resto de los servicios. Se documenta el DTO más simple que
cubre lo necesario, sin arquitectura de DTOs:

```python
@dataclass(frozen=True)
class CareRequestResult:
    care_request_id: int
    status: str                     # "CONVERTIDA" en el camino de éxito
    appointment_id: int
    clinical_document_ids: list[int]
```

No replica información interna de Agenda (no incluye `Hold`, `Availability` ni detalles de
slot) — solo los identificadores que la capa de API necesita para representar el resultado. Este
DTO es específico de `CareRequestService.create`; no se propone como un patrón nuevo para el
resto de los servicios del proyecto, que siguen devolviendo instancias ORM sin cambios.

## 17. Contrato API mínimo (P3)

**Principio:** reutilizar exactamente el patrón ya usado por `appointments/api.py`,
`medical_records/api.py` y `clinical_documents/api_common.py` — vistas planas de Django
(`View`/`JsonResponse`, sin DRF, consistente con `appointments/api.py`: *"Fase 1 has no DRF
usage anywhere in the project... adding a new dependency for this would violate CLAUDE.md
§13's dependency discipline"*), autenticación por sesión (sin JWT/API-key nuevos), y un
`_ERROR_MAP = {ExcepciónDeDominio: (status, code, message)}` traducido por una clase base de
vista (`JsonApiView`/`ClinicalJsonApiView`/`DocumentJsonApiView` según la app). `CareRequest`
sigue exactamente este patrón — sin inventar uno nuevo.

### Endpoint

```text
POST /api/v1/care-requests/
```

Mismo estilo de montaje que `api/v1/clinical/` (Fase 3/4) — segmento propio (`care-requests`)
porque `CareRequest` no es una entidad clínica ni de agenda, es su propio dominio (Fase 5). El
prefijo exacto es un detalle de nomenclatura, no una decisión arquitectónica — no bloquea nada
si se ajusta durante la implementación.

### Autenticación

Sesión autenticada (mismo mecanismo que el resto del proyecto — `JsonApiView.dispatch`:
`if not request.user.is_authenticated: return _error_response(401, "NOT_AUTHENTICATED", ...)`).
Sin mecanismo nuevo.

### Header

```text
Idempotency-Key: <string opcional>
```

Leído igual que en `appointments/api.py`: `request.headers.get("Idempotency-Key", "")`.

### Cuerpo de la petición

```json
{
  "doctor_id": 12,
  "clinic_id": 3,
  "start": "2026-10-01T09:00:00-06:00",
  "end": "2026-10-01T09:30:00-06:00",
  "motivo": "Dolor abdominal",
  "padecimiento": "",
  "descripcion": "",
  "patient_id": 45
}
```

- `start`/`end`: mismos nombres de campo y mismo parseo que ya usa `HoldCreateView`
  (`appointments/api.py`: `_parse_iso_datetime(_require_field(data, "start"), "start")`) —
  formato ISO 8601, tal cual lo devuelve `get_available_slots()`. El cliente selecciona un slot
  de `/api/availability/slots/` (ya existente) y reenvía exactamente esos valores; `CareRequest`
  no recalcula nada (D2).
- `doctor_id`/`clinic_id`: mismo patrón que `HoldCreateView`.
- `patient_id`: **obligatorio solo si el actor es un responsable** (identifica para cuál de sus
  pacientes relacionados solicita); si el actor es el propio paciente, se deriva del actor y
  cualquier `patient_id` enviado que no coincida se ignora/rechaza — mismo criterio de
  no-aceptar-`patient`-independiente-del-cliente ya usado en Fase 4 (D-003,
  `clinical-documents-data-model.md` §3).
- `motivo`: obligatorio. `padecimiento`/`descripcion`: opcionales, ausentes o `""` (§4 del modelo
  de datos).
- Adjuntos: `multipart/form-data` (no JSON) si se incluyen archivos, igual que el patrón ya
  usado por la subida de `ClinicalDocument` en Fase 4 — hasta el máximo de 5 archivos
  (`requirements.md` §12.2).

### Respuesta exitosa

```text
201 Created
```

```json
{
  "care_request_id": 501,
  "status": "CONVERTIDA",
  "appointment_id": 900,
  "clinical_document_ids": [12, 13]
}
```

**Detalle de implementación HTTP (no arquitectónico) — replay idempotente:** se devuelve
`201` también en el caso de replay, sin distinguir "creación nueva" de "resultado ya existente"
en el código de estado. Precedente exacto ya existente:
`AppointmentCollectionView.post` (`appointments/api.py`) llama a
`create_appointment_from_hold(...)` y siempre responde `status=201`, sin importar si el
servicio creó una `Appointment` nueva o devolvió una ya existente por replay — la vista no
distingue ambos casos. `CareRequest` sigue exactamente esa misma convención, sin abrir una
discusión nueva sobre `200` vs. `201`.

— exactamente el DTO `CareRequestResult` de §16, serializado. No se devuelve una instancia ORM
ni un objeto que replique detalles internos de Agenda.

### Errores

| Código | Cuándo | Excepción de dominio reutilizada |
|---|---:|---|
| 400 | Cuerpo malformado, campo faltante, `start`/`end` no parseables | `ApiError`/`ValueError` — mismo patrón que `appointments/api.py` |
| 400 | Archivo con extensión/MIME no permitido, tamaño excedido, doble extensión, tipo peligroso | `DocumentValidationError` (`clinical_documents.services.exceptions`) — **reutilizada tal cual**; ver nota siguiente |
| 401 | Sin sesión autenticada | Manejado por `JsonApiView.dispatch`, ya existente |
| 403 | Responsable sin `ResponsiblePatientRelationship` `ACTIVE` con el paciente, o médico/consultorio no autorizados | Excepción de dominio nueva `CareRequestPermissionDenied`, mapeada igual que `ClinicalNotAuthorized`/`DocumentPermissionDenied` ya existentes |
| 404/422 | Slot ya no disponible, conflicto de horario, Hold expirado, etc. | **Excepciones ya existentes de Agenda** (`AvailabilityNotFound`, `SlotUnavailable`, `HoldExpired`, `AppointmentConflict`, etc. — §10), traducidas con los mismos códigos que ya usa `appointments/api.py::_ERROR_MAP` — no se inventa una nueva taxonomía para lo que Agenda ya clasifica |
| 409 | Misma `Idempotency-Key` con datos distintos | `CareRequestConflict` (§7/§14), mapeado igual que `IdempotencyKeyConflict` ya existente en `appointments/api.py` |
| 429 | Rate limit alcanzado (§11) | Excepción de dominio nueva `CareRequestRateLimitExceeded` — sin precedente en el proyecto (verificado: `grep` no encontró ningún manejo de 429 existente), mapeada con el mismo `_ERROR_MAP` dict-based pattern, no un mecanismo distinto |

**Nota de auditoría (2026-09-15) — corrige la sugerencia inicial de 413/415:** el enunciado de
esta tarea proponía distinguir `413` (archivo demasiado grande) de `415` (tipo no soportado).
Verificado en código: `clinical_documents/api_common.py` mapea **ambos** casos a la misma
excepción `DocumentValidationError` → **400** (`_ERROR_MAP`), sin distinguir tamaño de tipo. Fase
4 ya tomó esa decisión y `CareRequest` reutiliza exactamente esa excepción sin modificarla —
introducir 413/415 solo para `CareRequest` haría que la misma `DocumentValidationError` se
tradujera de forma distinta según el endpoint que la haya lanzado, para el mismo servicio
subyacente (`ClinicalDocumentService`). Por reutilización y coherencia con Fase 4, este contrato
usa 400 para ambos casos, no 413/415.

No se inventó ninguna excepción de dominio nueva salvo dos genuinamente sin precedente:
`CareRequestPermissionDenied` (autorización específica de `CareRequest`, mismo patrón que las ya
existentes) y `CareRequestRateLimitExceeded` (regla nueva de Fase 5, D9/D10). Todo lo demás
reutiliza taxonomías de error ya existentes en Fases 2 y 4.

## 18. No modificado por esta revisión

`docs/design/agenda-service-contracts.md`, `docs/design/booking-and-concurrency.md`,
`docs/design/phase-4-service-contracts.md`, y el código de `appointments`/`clinical_documents`
**no se modificaron**. `ClinicalDocument` no recibe una FK nueva hacia `CareRequest` — se
reutiliza su FK ya existente hacia `Appointment`. Con la FK invertida (§3/§9), `Appointment`
(`appointments/models.py`) tampoco requiere ningún campo, migración ni cambio para dar cabida a
Fase 5 — la única app que gana un modelo/migración nueva es `care_requests` misma. No se
introduce Django REST Framework ni ninguna otra dependencia nueva — el contrato API (§17) sigue
el mismo patrón de vistas planas ya usado en todo el proyecto.

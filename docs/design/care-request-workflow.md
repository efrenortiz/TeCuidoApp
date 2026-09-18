# Fase 5 — Workflow de `CareRequest`

**Estado:** diseño técnico cerrado
**Fecha de referencia:** 2026-09-15

## 1. Propósito

Definir la secuencia única de ejecución de una solicitud de cita y los caminos de éxito, replay, conflicto, rechazo y rollback.

## 2. Flujo normal

```text
Actor autenticado
      ↓
CareRequest API
      ↓
CareRequestService
      ↓
BEGIN transaction.atomic()
      ↓
lock actor/User con select_for_update()
      ↓
RE-CHECK Idempotency-Key
      │
      ├── existe + coincide → replay / FIN
      │
      ├── existe + datos distintos → conflict / FIN
      │
      └── no existe
              ↓
          rate limit
              ↓
          CareRequest = NUEVA
              ↓
          slot de Agenda previamente seleccionado
              ↓
          HoldService.create_hold(...)
              ↓
          AppointmentService.create_appointment_from_hold(..., idempotency_key="")
              ↓
          CareRequest.appointment = Appointment
              ↓
          ClinicalDocumentService.upload(... appointment=Appointment) × N
              ↓
          CareRequest = CONVERTIDA
              ↓
          COMMIT
              ↓
          CareRequestResult DTO
```

## 3. Slot de Agenda

La UI obtiene los slots mediante el mecanismo existente de Agenda. Cada slot contiene `start` y `end`.

CareRequestService recibe esos valores y no calcula `end_at`.

La validación definitiva ocurre de nuevo en `HoldService.create_hold()`.

## 4. Transacción exterior

La transacción exterior pertenece a `CareRequestService` y cubre lógicamente:

- CareRequest;
- Hold;
- Appointment;
- `CareRequest.appointment`;
- ClinicalDocuments creados durante la operación;
- transición `NUEVA → CONVERTIDA`.

Los `@transaction.atomic` internos existentes en Agenda se comportan como savepoints dentro de la transacción exterior en la misma conexión.

## 5. Idempotencia

### 5.0 Precondición — validación de entrada (confirmado, no modificado — 2026-09-18)

Todo lo descrito en esta sección (§5.1-§5.5) presupone una solicitud estructuralmente válida.
La validación de `motivo` y del intervalo `start_at`/`end_at` ocurre **antes** de llegar aquí
(`care-request-service-contracts.md` §3.1/§3.1.1) — una solicitud inválida nunca se compara
contra una `CareRequest` existente, sin importar si su `Idempotency-Key` ya está en uso: el
resultado es siempre `400`, nunca replay ni `409`.

### 5.1 Lookup preliminar

Puede existir una lectura preliminar sin lock como optimización para replays obvios. No es autoritativa.

### 5.2 Comprobación autoritativa

Dentro de la transacción:

```text
BEGIN
 ↓
lock actor
 ↓
re-check CareRequest(actor, key)
```

Esto evita que dos transacciones concurrentes vean simultáneamente que la clave no existe.

### 5.3 Replay

Si existe una CareRequest con la misma clave y coincide en paciente, médico, consultorio, intervalo, `motivo`, `padecimiento`, `descripcion` y el contenido exacto de los adjuntos —nombre, tamaño y bytes— (identidad lógica completa — `care-request-service-contracts.md` §7.1, corrección de adjuntos 2026-09-18), se devuelve su resultado sin aplicar rate limit y sin repetir la operación de Agenda.

### 5.4 Conflicto

Si existe la misma clave para el actor pero cualquiera de esos campos de la nueva solicitud no coincide (corrección 2026-09-17: antes solo se comparaba paciente/médico/consultorio/intervalo, sin cubrir motivo/padecimiento/descripcion/adjuntos), se genera un `CareRequestConflict`.

### 5.5 Concurrencia de la constraint

La `UniqueConstraint` parcial es defensa en profundidad. Si por alguna vía concurrente excepcional se dispara `IntegrityError`, la captura ocurre dentro de un `transaction.atomic()` interno/savepoint; después se reconsulta y se realiza replay/conflict sin invalidar la transacción exterior.

## 6. Rate limiting

El límite se evalúa solamente después del re-check de idempotencia.

```text
lock actor
 ↓
re-check idempotency
 ↓
rate limit
 ↓
crear CareRequest
```

El mismo lock del actor sirve para idempotencia y rate limit.

Regla:

> máximo 3 CareRequests creadas por actor autenticado dentro de una ventana móvil de 1 hora.

No se cuenta por paciente destino.

## 7. Creación de CareRequest

Solo cuando no existe replay y el actor no excedió el límite se crea:

```text
status = NUEVA
```

La operación continúa en la misma transacción.

## 8. Hold

Se invoca directamente el `HoldService` de Fase 2 con los valores del slot:

```text
actor
 doctor
 clinic
 start_at
 end_at
```

No se duplica disponibilidad ni lógica de conflictos.

## 9. Appointment

Se reutiliza:

```text
AppointmentService.create_appointment_from_hold(...)
```

sin modificar su firma y con:

```text
idempotency_key=""
```

La clave del cliente pertenece exclusivamente a CareRequest.

## 10. Asociación de Appointment

Una vez creada correctamente la Appointment:

```text
care_request.appointment = appointment
```

y se guarda dentro de la misma transacción.

No se agrega `care_request` al modelo de Appointment y no se modifica AppointmentService para conocer CareRequest. Tampoco se expone un accessor inverso `Appointment.care_request` a nivel de ORM (`related_name="+"`, corrección 2026-09-18 — `care-request-data-model.md` §3): "no se agrega al modelo" incluye la navegabilidad Python, no solo columnas/migraciones.

## 11. Adjuntos

Después de existir la Appointment y de haber quedado establecida la relación:

```text
Appointment
 ↓
ClinicalDocumentService.upload(... appointment=appointment)
```

Se permiten hasta 5 archivos por solicitud. Los tipos y el límite de tamaño son exactamente los soportados por Fase 4.

## 12. Transición a CONVERTIDA

Solo después de que:

1. exista Appointment;
2. exista `CareRequest.appointment`;
3. todos los adjuntos hayan sido procesados satisfactoriamente;

se ejecuta:

```text
CareRequest.status = CONVERTIDA
```

y posteriormente se realiza el commit.

## 13. Fallo de Agenda

Si `HoldService` o `AppointmentService` rechazan la operación:

```text
ERROR
 ↓
ROLLBACK
```

No queda:

- CareRequest;
- Hold;
- Appointment;
- relación CareRequest/Appointment;
- ClinicalDocument de esa ejecución.

No se transforma el fallo en un estado persistente.

## 14. Compensación de archivos

Si un archivo ya fue almacenado físicamente y después falla la operación:

```text
ROLLBACK BD
 ↓
delete_best_effort(storage_key)
```

`CareRequestService` conserva temporalmente las referencias físicas creadas durante esa ejecución.

Se acepta la ventana entre rollback de BD y limpieza del filesystem.

La limpieza de huérfanos está fuera del alcance de todas las fases y es responsabilidad operativa del administrador del sistema.

## 15. Resultado

La operación exitosa devuelve `CareRequestResult`:

```text
care_request_id
status
appointment_id
clinical_document_ids
```

El DTO no incluye Hold, Availability ni detalles internos de Agenda.

`clinical_document_ids` proviene siempre del campo persistido `CareRequest.
clinical_document_ids` (corrección 2026-09-18, `care-request-data-model.md` §3.1) — fijado una
sola vez en el momento de la conversión, nunca de una consulta fresca de `ClinicalDocument` por
`appointment_id`. Un replay reporta exactamente los mismos IDs que la ejecución original, sin
importar qué documentos existan hoy para esa `Appointment`.

## 16. Propiedades del workflow

El workflow no utiliza:

- tareas asíncronas;
- colas;
- Redis;
- Celery;
- microservicios;
- revisión humana intermedia.

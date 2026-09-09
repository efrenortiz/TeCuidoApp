# Contratos de API de Agenda — Fase 2

## 1. Propósito

Este documento define el contrato externo de la API de Agenda de TeCuidoApp.

Deriva de:

- `docs/phases/phase-2-agenda.md`
- `docs/design/appointment-domain.md`
- `docs/design/availability-rules.md`
- `docs/design/booking-and-concurrency.md`
- `docs/design/agenda-permissions.md`
- `docs/design/agenda-service-contracts.md`
- `docs/design/phase-2-agenda-ux.md`

Su objetivo es establecer una interfaz consistente entre cliente y backend para:

- disponibilidades;
- consulta de slots;
- holds;
- citas;
- cancelación;
- reprogramación;
- inicio de consulta;
- finalización;
- `NO_SHOW`.

Este documento define contratos HTTP/API. No define modelos Django ni implementación interna.

---

## 2. Principios

### 2.1 Autenticación obligatoria

Todas las operaciones de Agenda requieren un `User` autenticado.

Las operaciones anónimas no forman parte del alcance de Fase 2.

### 2.2 Autorización en backend

La API nunca debe confiar únicamente en la UI.

Cada endpoint debe validar:

- identidad;
- perfil funcional;
- relaciones de Fase 1;
- ámbito administrativo;
- propiedad del recurso;
- estado actual.

### 2.3 La API no duplica reglas de dominio

Las reglas de negocio deben implementarse en los servicios de dominio.

El endpoint sólo:

```text
recibe request
→ valida formato básico
→ llama servicio
→ traduce resultado/error
```

### 2.4 Fechas y horas

La representación externa debe utilizar ISO 8601.

Ejemplos:

```text
2026-09-15
2026-09-15T09:00:00-06:00
```

La zona horaria de negocio es la del `Clinic`.

---

# 3. Recursos API

Los recursos principales serán:

```text
/availability
/slots
/holds
/appointments
```

No existe un recurso API persistente `/slots` como entidad de dominio; los slots son una representación derivada.

---

# 4. Availability API

## 4.1 Crear disponibilidad

```http
POST /api/availability/
```

### Request

```json
{
  "doctor_id": 1,
  "clinic_id": 2,
  "date": "2026-09-15",
  "start_time": "09:00",
  "end_time": "13:00"
}
```

### Reglas

El backend debe validar:

- actor autorizado;
- relación `DoctorClinic`;
- alcance administrativo;
- fecha/hora inicial no pasada;
- máximo 6 meses calendario;
- intervalo válido;
- ausencia de solapamiento del médico;
- ausencia de solapamiento de `Doctor + Clinic`.

La duración se obtiene de la configuración vigente de `Doctor + Clinic`.

### Response

```http
201 Created
```

```json
{
  "id": 10,
  "doctor_id": 1,
  "clinic_id": 2,
  "date": "2026-09-15",
  "start_time": "09:00",
  "end_time": "13:00",
  "duration_minutes": 60,
  "is_active": true
}
```

---

## 4.2 Modificar disponibilidad

```http
PATCH /api/availability/{id}/
```

No se permite modificar una disponibilidad que tenga citas asociadas.

La modificación debe volver a validar solapamientos y reglas temporales.

### Response

```http
200 OK
```

---

## 4.3 Desactivar disponibilidad

```http
POST /api/availability/{id}/deactivate/
```

No se elimina físicamente.

No se permite desactivar una disponibilidad con citas asociadas.

### Response

```http
200 OK
```

```json
{
  "id": 10,
  "is_active": false
}
```

---

# 5. Slots API

## 5.1 Consultar slots

```http
GET /api/availability/slots/
```

### Query parameters

```text
doctor_id
clinic_id
date
```

Ejemplo:

```text
GET /api/availability/slots/?doctor_id=1&clinic_id=2&date=2026-09-15
```

### Response

```http
200 OK
```

```json
{
  "doctor_id": 1,
  "clinic_id": 2,
  "date": "2026-09-15",
  "slots": [
    {
      "start": "2026-09-15T09:00:00-06:00",
      "end": "2026-09-15T10:00:00-06:00",
      "status": "AVAILABLE"
    },
    {
      "start": "2026-09-15T10:00:00-06:00",
      "end": "2026-09-15T11:00:00-06:00",
      "status": "BOOKED"
    }
  ]
}
```

Los estados visuales son derivados:

```text
AVAILABLE
HELD
BOOKED
```

No deben persistirse como estado de `Slot`.

---

# 6. Hold API

## 6.1 Crear Hold

```http
POST /api/holds/
```

### Request

```json
{
  "doctor_id": 1,
  "clinic_id": 2,
  "start": "2026-09-15T10:00:00-06:00",
  "end": "2026-09-15T11:00:00-06:00"
}
```

### Headers

Debe soportar:

```http
Idempotency-Key: <unique-operation-key>
```

### Reglas

- actor autorizado;
- slot válido;
- dentro de disponibilidad;
- inicio no superior a 30 minutos después del comienzo del slot;
- sin cita conflictiva;
- sin hold conflictivo;
- usuario sin otro hold activo.

### Response

```http
201 Created
```

```json
{
  "id": 25,
  "doctor_id": 1,
  "clinic_id": 2,
  "start": "2026-09-15T10:00:00-06:00",
  "end": "2026-09-15T11:00:00-06:00",
  "status": "ACTIVE",
  "created_at": "2026-09-15T09:42:00-06:00",
  "expires_at": "2026-09-15T09:57:00-06:00"
}
```

---

## 6.2 Liberar Hold

```http
POST /api/holds/{id}/release/
```

Sólo puede liberarlo el usuario propietario.

### Response

```http
200 OK
```

```json
{
  "id": 25,
  "status": "RELEASED"
}
```

---

# 7. Appointment API

## 7.1 Crear cita desde Hold

```http
POST /api/appointments/
```

### Headers

```http
Idempotency-Key: <unique-operation-key>
```

### Request

```json
{
  "hold_id": 25,
  "patient_id": 5
}
```

El backend obtiene del hold:

- médico;
- consultorio;
- fecha;
- hora;
- intervalo.

No se deben aceptar desde el cliente valores que puedan contradecir el hold.

### Reglas

- hold perteneciente al actor;
- `ACTIVE`;
- no expirado;
- autorización sobre el paciente — para responsable, `ResponsiblePatientRelationship.status = ACTIVE`; para médico, `DoctorClinic` válida en la combinación de la cita, **sin exigir `DoctorPatientRelationship` previa** (decisión de cierre, 2026-09-09; esta llamada nunca la crea ni la modifica);
- disponibilidad vigente;
- sin conflicto;
- duración congelada.

### Response

```http
201 Created
```

```json
{
  "id": 100,
  "patient_id": 5,
  "doctor_id": 1,
  "clinic_id": 2,
  "start": "2026-09-15T10:00:00-06:00",
  "end": "2026-09-15T11:00:00-06:00",
  "duration_minutes": 60,
  "status": "SCHEDULED"
}
```

La creación debe consumir el hold dentro de la misma transacción.

---

## 7.2 Consultar citas

```http
GET /api/appointments/
```

Los filtros concretos pueden incluir:

```text
status
date_from
date_to
patient_id
doctor_id
clinic_id
```

El backend debe limitar resultados al ámbito autorizado.

Nunca se debe asumir que conocer un `patient_id`, `doctor_id` o `clinic_id` concede acceso.

---

## 7.3 Obtener detalle

```http
GET /api/appointments/{id}/
```

La respuesta debe incluir al menos:

```text
id
patient
doctor
clinic
start
end
duration
status
created_by
created_at
cancellation data, if applicable
NO_SHOW data, if applicable
```

---

# 8. Cancelación

## 8.1 Cancelar cita

```http
POST /api/appointments/{id}/cancel/
```

### Request

```json
{
  "reason": "PATIENT_REQUEST"
}
```

### Reglas

- actor autorizado;
- cita `SCHEDULED`;
- inicio futuro;
- motivo obligatorio.

### Response

```http
200 OK
```

```json
{
  "id": 100,
  "status": "CANCELLED",
  "cancelled_at": "2026-09-15T09:20:00-06:00",
  "cancelled_by": 7,
  "cancellation_reason": "PATIENT_REQUEST"
}
```

No debe existir:

```http
DELETE /api/appointments/{id}
```

como operación de cancelación.

---

# 9. Reprogramación

## 9.1 Reprogramar cita

```http
POST /api/appointments/{id}/reschedule/
```

### Headers

```http
Idempotency-Key: <unique-operation-key>
```

### Request

```json
{
  "clinic_id": 3,
  "start": "2026-09-18T12:00:00-06:00",
  "end": "2026-09-18T13:00:00-06:00",
  "reason": "PATIENT_REQUEST"
}
```

El médico no se envía porque no puede cambiarse.

La duración efectiva debe mantenerse congelada.

### Reglas

- actor autorizado;
- cita `SCHEDULED`;
- no iniciada;
- nuevo intervalo disponible;
- consultorio compatible con duración;
- sin conflictos;
- motivo obligatorio;
- operación atómica.

### Response

```http
200 OK
```

La misma cita devuelve:

```json
{
  "id": 100,
  "doctor_id": 1,
  "clinic_id": 3,
  "start": "2026-09-18T12:00:00-06:00",
  "end": "2026-09-18T13:00:00-06:00",
  "duration_minutes": 60,
  "status": "SCHEDULED"
}
```

El historial de reprogramación no se representa como estado `RESCHEDULED`.

---

# 10. Iniciar consulta

## 10.1 Iniciar

```http
POST /api/appointments/{id}/start/
```

No requiere datos adicionales.

### Reglas

Sólo puede hacerlo el médico asignado.

La cita debe estar:

```text
SCHEDULED
```

### Response

```http
200 OK
```

```json
{
  "id": 100,
  "status": "IN_CONSULTATION",
  "started_at": "2026-09-15T10:02:00-06:00",
  "started_by": 1
}
```

La acción representa:

> el médico confirma que el paciente está físicamente presente e inicia la atención.

---

# 11. Finalizar consulta

## 11.1 Finalizar

```http
POST /api/appointments/{id}/complete/
```

Sólo el médico asignado.

Precondición:

```text
status = IN_CONSULTATION
```

### Response

```http
200 OK
```

```json
{
  "id": 100,
  "status": "COMPLETED",
  "completed_at": "2026-09-15T10:58:00-06:00",
  "completed_by": 1
}
```

---

# 12. NO_SHOW

## 12.1 Marcar ausencia

```http
POST /api/appointments/{id}/no-show/
```

No requiere motivo.

### Reglas

- sólo médico asignado;
- cita `SCHEDULED`;
- al menos un minuto después de la hora programada;
- el médico determina que el paciente no se presentó.

### Response

```http
200 OK
```

```json
{
  "id": 100,
  "status": "NO_SHOW",
  "no_show_at": "2026-09-15T10:01:00-06:00",
  "no_show_by": 1
}
```

No existe transición automática.

---

# 13. Errores HTTP

La API debe traducir errores de dominio a respuestas HTTP consistentes.

### `400 Bad Request`

Formato o datos estructuralmente inválidos.

### `401 Unauthorized`

No existe autenticación válida.

### `403 Forbidden`

El actor está autenticado pero no está autorizado.

### `404 Not Found`

El recurso no existe o no debe revelarse al actor.

### `409 Conflict`

Conflictos de negocio o concurrencia, por ejemplo:

```text
SLOT_UNAVAILABLE
HOLD_CONFLICT
HOLD_ALREADY_EXISTS
APPOINTMENT_ALREADY_STARTED
AVAILABILITY_CONFLICT
IDEMPOTENCY_CONFLICT
```

### `422 Unprocessable Entity`

Puede utilizarse cuando el proyecto adopte este código para errores semánticos de dominio que no sean conflictos.

La elección concreta entre `400` y `422` debe mantenerse uniforme en toda la API.

---

# 14. Formato de error

Respuesta propuesta:

```json
{
  "error": {
    "code": "SLOT_UNAVAILABLE",
    "message": "El horario seleccionado ya no está disponible."
  }
}
```

El campo `code` debe ser estable y apto para consumo de frontend.

El `message` es orientativo y no debe contener detalles internos.

---

# 15. Idempotencia

Las operaciones de reserva y reprogramación deben admitir:

```http
Idempotency-Key
```

Una misma clave representa un único intento lógico.

Si la operación ya fue procesada correctamente:

```text
retry
→ mismo resultado
```

y no:

```text
retry
→ segunda cita
```

Una clave reutilizada con un payload diferente debe producir conflicto.

---

# 16. Paginación

Las listas de citas deben utilizar paginación cuando el tamaño pueda crecer.

La API debe devolver metadatos suficientes para navegar los resultados, por ejemplo:

```json
{
  "count": 125,
  "next": "...",
  "previous": "...",
  "results": []
}
```

La implementación concreta puede seguir el estándar general que adopte el proyecto.

---

# 17. Filtros de citas

Los filtros deben respetar autorización antes de aplicarse.

Ejemplo:

```text
GET /api/appointments/?date_from=2026-09-01&date_to=2026-09-30
```

El usuario no debe poder ampliar su ámbito mediante parámetros adicionales.

---

# 18. Reglas de seguridad

Nunca aceptar desde el cliente datos que contradigan el recurso o autorización ya conocida.

Ejemplo:

```text
Hold #25
```

no debe poder convertirse en una cita indicando desde el cliente:

```text
doctor_id = 99
clinic_id = 99
```

El backend debe obtener la información confiable del hold.

---

# 19. Consistencia con estados

La API sólo expone estos estados de `Appointment`:

```text
SCHEDULED
IN_CONSULTATION
COMPLETED
CANCELLED
NO_SHOW
```

No existen endpoints:

```text
/confirm
/check-in
/waiting
/release-appointment
/reschedule-state
```

La reprogramación es una operación sobre la misma cita y un evento de historial.

---

# 20. Consistencia con Hold

Estados de Hold:

```text
ACTIVE
EXPIRED
RELEASED
CONSUMED
```

Los estados de Hold no forman parte de `Appointment`.

---

# 21. Reglas de reserva de slots iniciados

La consulta de slots debe marcar como no reservable un slot cuyo inicio tenga más de 30 minutos.

La API de creación de Hold vuelve a validar esta condición.

No se confía en el estado enviado desde el frontend.

---

# 22. Zona horaria

Todos los timestamps deben ser comparables y no ambiguos.

La hora de negocio de Agenda se basa en el `Clinic`.

La API debe representar timestamps con offset o formato equivalente que preserve la zona horaria.

Las comparaciones de pasado/futuro y expiración se realizan en backend.

---

# 23. Compatibilidad futura

Los endpoints deben mantener una separación clara entre:

```text
API
↓
Services
↓
Domain / Models
```

La API no debe incorporar reglas clínicas futuras de:

- `MedicalEncounter`;
- historia clínica;
- recetas;
- CareRequest.

---

# 24. Criterios de aceptación

La API debe permitir probar:

### Disponibilidad

```text
crear → 201
solapamiento → 409
fuera de 6 meses → 400/422
inicio pasado → 400/422
```

### Hold

```text
crear → 201
segundo hold activo → 409
liberar → 200
expirado → no bloquea
```

### Reserva

```text
hold válido → appointment SCHEDULED
hold expirado → 409
doble reserva concurrente → sólo una exitosa
```

### Cancelación

```text
futura → 200
iniciada → 409
ya cancelada → 409
```

### Reprogramación

```text
válida → 200
slot ocupado → 409
cita iniciada → 409
médico diferente → rechazo
```

### Inicio

```text
médico asignado → 200
otro actor → 403
SCHEDULED → IN_CONSULTATION
```

### Finalización

```text
IN_CONSULTATION → COMPLETED
otro actor → 403
```

### NO_SHOW

```text
SCHEDULED + ≥1 min → 200
antes de tiempo → 409
ya iniciada → 409
```

---

# 25. Fuera de alcance

No define:

- implementación Django;
- serializers concretos;
- modelos;
- UI;
- documentación OpenAPI generada automáticamente;
- autenticación concreta;
- notificaciones;
- pagos;
- dominio clínico.

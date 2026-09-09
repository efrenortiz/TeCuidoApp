# Contratos de servicios de Agenda — Fase 2

## 1. Propósito

Este documento define los contratos de servicios de dominio que implementarán las políticas y reglas técnicas de Agenda de TeCuidoApp.

Deriva de:

- `docs/phases/phase-2-agenda.md`
- `docs/design/appointment-domain.md`
- `docs/design/availability-rules.md`
- `docs/design/booking-and-concurrency.md`
- `docs/design/agenda-permissions.md`

Su objetivo es establecer:

- operaciones de dominio;
- actores y autorización;
- precondiciones;
- resultados;
- errores de dominio;
- límites entre views/API y servicios;
- transacciones;
- idempotencia;
- responsabilidades de cada servicio.

No define todavía la implementación concreta de modelos Django, serializers, URLs ni componentes de UI.

---

## 2. Principios

### 2.1 Los servicios son la frontera de dominio

Las mutaciones de Agenda deben pasar por servicios de dominio.

Las views, endpoints o comandos no deben implementar directamente reglas de negocio modificando modelos.

Flujo:

```text
View / API
    ↓
Domain Service
    ↓
Authorization
    ↓
Transaction
    ↓
Models / PostgreSQL
```

### 2.2 La autorización se vuelve a validar en el servicio

Una autorización realizada previamente en la view no reemplaza la validación del servicio.

El servicio debe validar:

- identidad del actor;
- perfil funcional;
- relaciones de Fase 1;
- ámbito administrativo;
- propiedad del recurso;
- estado actual;
- reglas de negocio.

### 2.3 La base de datos es autoridad final

Los servicios deben combinar validación de dominio, transacciones y restricciones de PostgreSQL.

No se debe considerar suficiente una comprobación previa de disponibilidad realizada fuera de la transacción.

---

## 3. Servicios

Se utilizarán tres servicios principales:

```text
AvailabilityService
HoldService
AppointmentService
```

No se utilizará un `AgendaService` monolítico.

Responsabilidades:

### `AvailabilityService`

Administra disponibilidades concretas por fecha.

### `HoldService`

Administra bloqueos temporales de slots.

### `AppointmentService`

Administra el ciclo de vida de las citas y las operaciones de reserva, cancelación, reprogramación, inicio, finalización y `NO_SHOW`.

---

# 4. Convención de actores

Los servicios mutadores recibirán:

```python
actor: User
```

El servicio resolverá el perfil funcional necesario a partir del `User`.

No se confiará en perfiles proporcionados por el cliente.

Ejemplo:

```python
AppointmentService.cancel(
    appointment=appointment,
    actor=request.user,
    reason=reason,
)
```

La identidad del actor se obtiene de la autenticación.

---

# 5. `AvailabilityService`

## 5.1 `create_availability()`

### Propósito

Crear una disponibilidad concreta para un médico y consultorio.

### Entrada conceptual

```text
actor
doctor
clinic
date
start_time
end_time
```

La duración efectiva se obtiene de la configuración vigente de `Doctor + Clinic`.

### Precondiciones

- actor autorizado;
- si actor es médico, `doctor` debe ser el propio actor;
- si actor es administrador, la clínica debe pertenecer a su ámbito;
- debe existir relación válida `DoctorClinic`;
- la fecha/hora inicial no puede estar en el pasado;
- no puede superar el horizonte de 6 meses calendario;
- `start_time < end_time`;
- no debe existir otra disponibilidad activa superpuesta del mismo médico;
- no debe existir otra disponibilidad activa superpuesta para la misma combinación médico + consultorio.

### Resultado

Devuelve la disponibilidad creada con:

```text
is_active = true
duration = duración vigente de Doctor + Clinic
```

### Errores posibles

```text
NotAuthorized
DoctorClinicRequired
AvailabilityStartInPast
AvailabilityBeyondBookingHorizon
InvalidAvailabilityInterval
AvailabilityConflict
```

---

## 5.2 `update_availability()`

### Propósito

Modificar una disponibilidad existente que todavía pueda modificarse.

### Precondiciones

- actor autorizado;
- disponibilidad activa;
- sin citas asociadas que sean invalidadas por el cambio;
- no se puede modificar una disponibilidad con citas asociadas;
- el nuevo intervalo es válido;
- no se crean solapamientos;
- el inicio resultante no está en el pasado;
- se mantiene el resto de las reglas de disponibilidad.

### Regla

Una disponibilidad con citas asociadas es inmutable desde el punto de vista operativo.

Por tanto:

```text
Availability con citas
    ↓
update
    ↓
rechazado
```

### Resultado

Devuelve la disponibilidad modificada.

### Errores

```text
NotAuthorized
AvailabilityNotFound
AvailabilityHasAppointments
InvalidAvailabilityInterval
AvailabilityConflict
AvailabilityStartInPast
```

---

## 5.3 `deactivate_availability()`

### Propósito

Realizar baja lógica.

### Precondiciones

- actor autorizado;
- disponibilidad existente;
- disponibilidad sin citas asociadas.

### Resultado

```text
is_active = false
```

La disponibilidad no se elimina físicamente.

### Error principal

```text
AvailabilityHasAppointments
```

---

## 5.4 `get_available_slots()`

### Propósito

Obtener slots derivados de una disponibilidad.

### Entrada

```text
actor
doctor / clinic / date
```

### Reglas

- no crea entidades `Slot`;
- utiliza la disponibilidad activa;
- utiliza la duración efectiva congelada de la disponibilidad;
- considera ocupaciones por citas;
- considera holds activos;
- aplica la regla de reserva de slots ya iniciados;
- respeta zona horaria del consultorio.

### Resultado

Devuelve una colección calculada de intervalos:

```text
start_datetime
end_datetime
status
```

donde `status` puede expresar como mínimo:

```text
AVAILABLE
HELD
BOOKED
UNAVAILABLE
```

El detalle visual de estos estados pertenece a UI.

---

# 6. `HoldService`

## 6.1 `create_hold()`

### Propósito

Crear un hold temporal de 15 minutos sobre un slot.

### Entrada

```text
actor
doctor
clinic
start_datetime
end_datetime
```

### Precondiciones

- actor autorizado para crear la cita correspondiente;
- intervalo corresponde a disponibilidad activa;
- slot válido;
- slot no ha superado 30 minutos desde su inicio;
- intervalo está completamente contenido en la disponibilidad;
- no existe cita conflictiva;
- no existe hold activo conflictivo;
- actor no posee otro hold activo.

### Resultado

Crea:

```text
status = ACTIVE
created_at = now
expires_at = now + 15 minutes
```

### Errores

```text
NotAuthorized
AvailabilityNotFound
SlotUnavailable
BookingWindowExpired
HoldAlreadyExists
HoldConflict
InvalidSlot
```

---

## 6.2 `release_hold()`

### Propósito

Liberar voluntariamente un hold.

### Entrada

```text
actor
hold
```

### Precondiciones

- hold pertenece al actor;
- hold está `ACTIVE`.

### Resultado

```text
ACTIVE → RELEASED
```

El recurso queda inmediatamente disponible.

### Errores

```text
HoldNotFound
HoldNotOwned
HoldNotActive
```

---

## 6.3 Expiración

La expiración no requiere una llamada síncrona exacta.

El sistema considera el hold inválido para bloqueo cuando:

```text
status = ACTIVE
AND
expires_at <= now
```

Puede existir una tarea de limpieza que cambie posteriormente:

```text
ACTIVE → EXPIRED
```

pero las operaciones críticas no dependen de dicha tarea.

No existe:

```text
renew_hold()
extend_hold()
```

---

# 7. `AppointmentService`

## 7.1 `create_appointment_from_hold()`

### Propósito

Convertir un hold vigente en una cita.

Toda creación definitiva de cita utiliza el flujo de hold.

Esto aplica a:

- paciente;
- responsable;
- médico;
- administrador.

### Entrada

```text
actor
hold
patient
doctor
clinic
```

Los datos de recursos y horario deben corresponder con el hold.

### Precondiciones

- actor autorizado;
- hold pertenece al actor;
- hold `ACTIVE`;
- `expires_at > now`;
- hold corresponde al paciente/recursos de la operación;
- paciente válido;
- médico y consultorio compatibles (`DoctorClinic` válida);
- disponibilidad válida;
- intervalo sin conflicto;
- reglas de reserva cumplidas.

Cuando el actor es médico, la autorización se resuelve enteramente mediante `DoctorClinic` (§12) — **no se exige `DoctorPatientRelationship` activa previa con el paciente** (decisión de cierre, 2026-09-09). Esta operación nunca crea, activa ni modifica `DoctorPatientRelationship`; si esa relación llega a establecerse, ocurre por su propio flujo, fuera de este servicio.

### Operación transaccional

Dentro de una misma transacción:

```text
1. validar/bloquear hold
2. validar nuevamente disponibilidad
3. validar conflictos
4. crear Appointment
5. copiar duración efectiva congelada
6. establecer status = SCHEDULED
7. registrar created_by
8. cambiar Hold → CONSUMED
9. COMMIT
```

### Resultado

```text
Appointment.status = SCHEDULED
Hold.status = CONSUMED
```

### Errores

```text
NotAuthorized
HoldNotFound
HoldExpired
HoldNotOwned
SlotUnavailable
AppointmentConflict
InvalidPatient
InvalidDoctorClinic
```

---

## 7.2 `cancel_appointment()`

### Propósito

Cancelar una cita futura.

### Entrada

```text
actor
appointment
reason
```

### Precondiciones

- actor autorizado;
- cita `SCHEDULED`;
- la hora de inicio todavía no ha llegado;
- motivo obligatorio.

### Resultado

```text
status = CANCELLED
cancelled_at = now
cancelled_by = actor
cancellation_reason = reason
```

El horario queda disponible nuevamente.

La cita no se elimina.

### Errores

```text
NotAuthorized
AppointmentNotFound
AppointmentNotCancellable
AppointmentAlreadyCancelled
```

---

## 7.3 `reschedule_appointment()`

### Propósito

Cambiar fecha/hora y opcionalmente consultorio de una cita futura.

### Entrada

```text
actor
appointment
new_clinic
new_start_datetime
reason
idempotency_key
```

El médico no puede cambiarse.

### Precondiciones

- actor autorizado;
- cita `SCHEDULED`;
- la cita no ha iniciado;
- nuevo intervalo disponible;
- nueva disponibilidad válida;
- nueva combinación médico + consultorio válida;
- duración congelada de la cita compatible con el nuevo consultorio;
- nueva ubicación no genera conflicto;
- motivo obligatorio.

### Operación

Debe ser atómica:

```text
BEGIN
    validar cita
    validar autorización
    validar nuevo intervalo
    proteger nuevo intervalo
    actualizar cita
    registrar AppointmentRescheduleHistory
    liberar ocupación anterior
COMMIT
```

Ante cualquier conflicto:

```text
ROLLBACK
```

La cita original queda sin cambios.

### Resultado

La misma entidad `Appointment` permanece:

```text
status = SCHEDULED
```

con nueva fecha/hora y, si corresponde, nuevo consultorio.

La operación queda registrada en `AppointmentRescheduleHistory`.

### Errores

```text
NotAuthorized
AppointmentNotFound
AppointmentNotReschedulable
SlotUnavailable
DurationIncompatible
InvalidDoctorClinic
```

---

## 7.4 `start_appointment()`

### Propósito

Iniciar formalmente la atención.

### Actor

Exclusivamente el médico asignado.

### Entrada

```text
actor
appointment
```

### Precondiciones

- actor es el médico asignado;
- cita `SCHEDULED`;
- paciente físicamente presente según declaración operativa del médico.

### Resultado

```text
SCHEDULED → IN_CONSULTATION
started_at = now
started_by = actor
```

No existe estado `WAITING`.

No hay transición automática por el tiempo.

### Errores

```text
NotAuthorized
AppointmentNotFound
AppointmentNotStartable
```

---

## 7.5 `complete_appointment()`

### Propósito

Marcar la atención como terminada.

### Actor

Exclusivamente el médico asignado.

### Precondiciones

```text
status = IN_CONSULTATION
```

### Resultado

```text
IN_CONSULTATION → COMPLETED
completed_at = now
completed_by = actor
```

### Errores

```text
NotAuthorized
AppointmentNotFound
AppointmentNotCompletable
```

---

## 7.6 `mark_no_show()`

### Propósito

Registrar que el paciente no se presentó.

### Actor

Exclusivamente el médico asignado.

### Precondiciones

- actor es el médico asignado;
- cita `SCHEDULED`;
- el inicio programado ya ocurrió;
- ha transcurrido al menos un minuto;
- el médico determina que el paciente no se presentó.

### Resultado

```text
SCHEDULED → NO_SHOW
no_show_at = now
no_show_by = actor
```

No se requiere motivo.

No es automático.

### Errores

```text
NotAuthorized
AppointmentNotFound
NoShowNotAllowed
```

---

# 8. Idempotencia

Las operaciones que pueden ser repetidas debido a reintentos de red deben admitir idempotencia:

- creación de cita;
- reprogramación.

Se utilizará una `idempotency_key` asociada al intento lógico de operación.

La misma clave procesada nuevamente debe devolver el resultado de la operación original y no crear una segunda cita ni un segundo registro de reprogramación.

No debe existir colisión silenciosa entre operaciones distintas.

---

# 9. Errores de dominio

Los servicios deben utilizar excepciones de dominio explícitas.

Categorías mínimas:

```text
Authorization
Availability
Hold
Appointment
Concurrency
Idempotency
```

Los errores de dominio no deben exponer detalles internos de PostgreSQL.

Las views/API traducirán los errores a respuestas apropiadas.

---

# 10. Regla de transacciones

Las operaciones que afectan simultáneamente más de un recurso deben ser atómicas.

Como mínimo:

- crear cita desde hold;
- liberar hold;
- reprogramar;
- cancelar;
- operaciones que modifiquen simultáneamente ocupaciones.

El servicio debe usar `transaction.atomic()` en Django cuando corresponda.

---

# 11. Regla de locking

Las operaciones concurrentes que compiten por los mismos recursos deben proteger la sección crítica.

No se debe asumir que una consulta previa de disponibilidad garantiza el éxito posterior.

Cuando sea necesario, se utilizarán:

```text
select_for_update()
```

y restricciones de PostgreSQL apropiadas para proteger registros y/o intervalos.

La elección concreta de locking debe respetar `booking-and-concurrency.md`.

---

# 12. Relación con autorización

Los servicios deben reutilizar los mecanismos existentes de Fase 1.

Ejemplos:

```text
doctor_has_active_relationship()
responsible_has_active_relationship()
DoctorClinic
```

No se deben crear tablas o relaciones paralelas de autorización solamente para Agenda.

---

# 13. Responsabilidad de `created_by`

Toda cita debe conservar:

```text
created_by = User
```

El servicio recibe `actor=User` y registra ese actor.

Esto permite identificar uniformemente quién ejecutó la reserva, independientemente de que sea:

```text
Patient
Responsible
Doctor
Administrator
```

---

# 14. Administrador

Cuando el actor es administrador:

- su ámbito se limita a las clínicas autorizadas;
- debe existir una relación válida `DoctorClinic` para el médico y consultorio;
- puede crear, cancelar y reprogramar dentro de su ámbito;
- puede apoyar la gestión de disponibilidades;
- no puede iniciar ni completar la consulta;
- no puede marcar `NO_SHOW`.

---

# 15. Máquina de estado consumida por los servicios

Los servicios deben respetar únicamente:

```text
SCHEDULED
IN_CONSULTATION
COMPLETED
CANCELLED
NO_SHOW
```

Transiciones:

```text
SCHEDULED
 ├── cancel → CANCELLED
 ├── reschedule → SCHEDULED
 ├── start → IN_CONSULTATION
 └── no_show → NO_SHOW

IN_CONSULTATION
 └── complete → COMPLETED
```

Las operaciones `cancel`, `reschedule` y `no_show` no deben estar disponibles en estados incompatibles.

---

# 16. Fuera de alcance

No se implementan en estos contratos:

- `PENDING_CONFIRMATION`;
- `WAITING`;
- `RESCHEDULED` como estado;
- `RELEASED` como estado de Appointment;
- confirmación de citas;
- check-in del paciente;
- CareRequest;
- historia clínica;
- pagos;
- notificaciones.

---

# 17. Criterios de aceptación

Los servicios deben permitir probar, como mínimo:

### Disponibilidad

```text
crear disponibilidad válida → éxito
solapamiento del médico → rechazo
solapamiento Doctor + Clinic → rechazo
disponibilidad iniciada → sigue utilizable
disponibilidad con citas → no modificable/no desactivable
```

### Hold

```text
crear hold → ACTIVE
segundo hold del mismo usuario → rechazo
cambio de slot con hold → rechazo
liberar → RELEASED
expirar → deja de bloquear
crear cita → CONSUMED
```

### Appointment

```text
crear desde hold → SCHEDULED
cancelar futura → CANCELLED
reprogramar → SCHEDULED + historial
iniciar → IN_CONSULTATION
completar → COMPLETED
NO_SHOW → terminal
```

### Concurrencia

```text
dos usuarios / mismo intervalo
→ sólo una operación obtiene el recurso
```

### Idempotencia

```text
misma idempotency_key
→ una sola operación efectiva
```

### Autorización

```text
actor no autorizado
→ operación rechazada
```

---

# 18. Principio final

Los servicios de Agenda deben implementar las reglas del dominio, no duplicarlas en la interfaz.

El contrato general es:

```text
Autenticación
     ↓
Autorización
     ↓
Validación de dominio
     ↓
Transacción
     ↓
Protección de concurrencia
     ↓
Persistencia
     ↓
Resultado de dominio
```

La implementación concreta debe preservar este orden y las invariantes definidas en los documentos de diseño anteriores.

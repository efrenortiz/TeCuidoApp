# Fase 6 — Notification Service Contracts

**Estado:** Diseño técnico derivado — **implementado** (ver
`docs/phases/phase-6-implementation-summary.md`, PD-007).

## 1. Boundary

Los servicios de `notifications` reciben intenciones de comunicación; no contienen las reglas que determinan cuándo una cita existe o cuál es su disponibilidad.

## 2. Contratos principales

### `create_registration_invitation_notification(...)`

Crea una intención de Email para una invitación de registro ya emitida por `accounts`.

### `create_email_verification_notification(...)`

Crea la comunicación asociada al flujo existente de verificación de correo.

### `create_password_recovery_notification(...)`

Crea la comunicación del flujo de recuperación de contraseña.

### `notify_appointment_created(appointment)`

Resuelve los tres destinatarios congelados y crea intenciones idempotentes.

**Punto de enganche (cierra M-03):** debe invocarse desde el servicio de Agenda compartido de
Fase 2 (`AppointmentService`, el punto único donde una `Appointment` queda efectivamente creada),
nunca desde el punto de entrada específico de cada flujo de origen. `CareRequest` (Fase 5) crea la
`Appointment` reutilizando ese mismo servicio de Agenda
(`AppointmentService.create_appointment_from_hold`) — enganchar la notificación ahí, y no en la
vista/flujo de reserva directa, garantiza que una cita originada por reserva directa y una
originada por `CareRequest` disparen exactamente la misma notificación, sin lógica duplicada y sin
un camino de creación que quede silenciosamente sin notificar.

### `notify_appointment_modified(appointment, event_context)`

Crea notificaciones de modificación/reprogramación para los tres destinatarios.

### `notify_appointment_cancelled(appointment, event_context)`

Crea notificaciones de cancelación para los tres destinatarios.

### `schedule_appointment_reminders(appointment)`

Programa las cuatro ventanas congeladas únicamente para Patient y Responsible autorizado.

### `process_due_notifications(now)`

Obtiene notificaciones elegibles y solicita transporte.

## 3. Contrato de resultado

Los servicios deben devolver DTOs o estructuras equivalentes al patrón del proyecto, evitando exponer directamente modelos ORM cuando el consumidor necesita un contrato estable.

## 4. Error handling

Clasificar al menos:

- destinatario ausente;
- email inválido/ausente;
- notificación duplicada;
- proveedor no disponible;
- rechazo permanente del proveedor;
- configuración ausente.

Los códigos de error deben ser seguros y estables; nunca usar mensajes crudos del proveedor como regla de negocio.

**PD-007 (decisión final del propietario — implementado, `notifications/services.py`):**

- máximo de intentos: `MAX_DELIVERY_ATTEMPTS = 5` (ITD-011);
- backoff exponencial: `60s * 2^(attempt_count-1)`, tope `6h` (ITD-011);
- error transitorio vs. permanente: no se distingue por tipo de excepción — cualquier fallo de
  transporte reprograma con backoff hasta agotar el máximo de intentos, momento en el que se
  vuelve terminal (`reason_code` prefijado `MAX_ATTEMPTS_EXCEEDED:`); distinguir causas
  transitorias/permanentes específicas del proveedor no está justificado sin un proveedor SMTP
  real con esa semántica documentada;
- estado final: se reutiliza `FAILED` con `attempt_count >= MAX_DELIVERY_ATTEMPTS` — no se
  introduce un sexto estado (ver `phase-6-notification-domain.md` §6);
- recuperación de `SENDING` huérfano: `SENDING_LEASE_TIMEOUT = 10 min` (ITD-012) — una fila
  `SENDING` cuyo `last_attempt_at` excede ese lease se reclama en el siguiente
  `process_due_notifications` como si hubiera fallado (tipos reintentables) o se cierra como
  `FAILED` sin reenviar (tipos de un solo uso: invitación/verificación).

## 5. Transacciones

La persistencia de la intención de notificación puede ocurrir dentro de la transacción de negocio cuando exista una relación inequívoca con el resultado comprometido. El transporte se ejecuta fuera del límite ACID del dominio.

## 6. Duplicados y concurrencia

Dos workers concurrentes no deben producir dos efectos de envío para una misma intención. El diseño final debe apoyarse en restricciones de PostgreSQL y locking de filas, no en verificaciones “check then insert” sin protección.

## 7. Recordatorios

La fecha de referencia es la fecha/hora vigente de `Appointment.start_at`.

Un recordatorio se envía solo si, al momento de procesarlo:

- la cita sigue siendo elegible;
- el momento corresponde a la ventana configurada;
- el destinatario continúa siendo el Patient o Responsible autorizado.

## 8. Provider abstraction

El servicio opera contra una interfaz equivalente a:

```text
EmailTransport.send(message) -> TransportResult
```

El dominio no conoce SMTP host, API key o SDK concreto.

## 9. Observabilidad

Registrar métricas y logs técnicos sin incluir secretos ni contenido clínico completo.

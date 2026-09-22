# Fase 6 — Notification Domain

**Fuente normativa:** `docs/phases/phase-6-design-freeze.md` v1.1
**Estado:** Diseño técnico derivado — **implementado** (ver
`docs/phases/phase-6-implementation-summary.md`, PD-003/PD-004/PD-005).

## 1. Propósito

Definir el dominio de notificaciones de Fase 6 sin mover reglas de negocio de Agenda, cuentas, pacientes, responsables o médicos al módulo `notifications`.

## 2. Responsabilidad

`notifications` es responsable de representar y ejecutar una intención de comunicación por Email.

No es responsable de:

- crear, modificar, cancelar o reprogramar `Appointment`;
- decidir disponibilidad;
- autorizar acceso clínico;
- decidir relaciones de paciente/responsable/médico;
- cambiar estados de dominio por el resultado del correo.

## 3. Eventos funcionales

### Identidad

- invitación de registro;
- verificación de correo;
- recuperación de contraseña.

**PD-003 (decisión final del propietario):** invitación y verificación de correo pasan por el
transporte de `notifications` (`accounts/views.py` ya no llama `send_mail` directamente).
**Recuperación de contraseña se mantiene deliberadamente fuera**: sigue
`django.contrib.auth.views.PasswordResetView`/`PasswordResetForm`, el mecanismo nativo de Django,
que ya genera y envía su propio correo de forma segura. Es una excepción deliberada a la
centralización de Fase 6, no un descuido — no se modifica el mecanismo de autenticación
únicamente para conseguir uniformidad arquitectónica.
`notifications.services.create_password_recovery_notification(...)` permanece definida por
contrato pero sin invocar, igual que `ADMIN_SENSITIVE_ACCESS` en el catálogo de auditoría.

### Agenda

- cita creada;
- cita modificada/reprogramada;
- cita cancelada;
- recordatorios 15, 10, 5 y 1 días antes.

## 4. Destinatarios congelados

### 4.1 Creación, modificación y cancelación

Los tres eventos se notifican a:

```text
Patient
Responsible autorizado
Doctor asignado
```

La resolución de destinatarios debe usar las relaciones vigentes del sistema en el momento en que se genera la intención de notificación.

### 4.2 Recordatorios periódicos

Los recordatorios de 15/10/5/1 días se notifican únicamente a:

```text
Patient
Responsible autorizado
```

El Doctor asignado no recibe estos recordatorios periódicos.

Esta exclusión no afecta a creación, modificación/reprogramación o cancelación.

## 5. Opt-out

No se ofrece opt-out para las notificaciones operativas ni los recordatorios definidos por Fase 6.

El modelo no debe contener un flag de preferencia que permita al usuario desactivar estas comunicaciones congeladas.

## 6. Ciclo de vida lógico

```text
INTENT_CREATED
      ↓
QUEUED / SCHEDULED
      ↓
SENDING
   ↙      ↘
SENT     FAILED
            ↓
         RETRY / FINAL_FAILURE
```

Los nombres físicos de estados pueden ajustarse a las convenciones del proyecto siempre que mantengan la semántica.

**PD-007 (decisión final del propietario — implementado):** los cinco estados físicos son
`PENDING` (=`QUEUED/SCHEDULED`), `SENDING`, `SENT`, `FAILED`, `CANCELLED` — no se introduce un
sexto estado (`RETRY`/`FINAL_FAILURE` no son estados nuevos): `RETRY` es `FAILED` con
`scheduled_for` reprogramado hacia adelante (backoff exponencial); `FINAL_FAILURE` es `FAILED` con
`attempt_count` habiendo alcanzado el máximo (`reason_code` prefijado
`MAX_ATTEMPTS_EXCEEDED:...`), distinguible sin una columna nueva. Un `SENDING` huérfano (proceso
interrumpido a media ejecución) se reclama tras `SENDING_LEASE_TIMEOUT` (10 minutos) — ver
`notifications/services.py::process_due_notifications` y
`docs/phases/phase-6-implementation-summary.md` ITD-011/ITD-012 para los valores concretos y su
justificación técnica.

## 7. Regla de transacción

La operación de negocio y el envío de correo son límites diferentes:

```text
Business transaction → commit
                       ↓
                notification intent
                       ↓
                    transport
```

El fallo del proveedor no revierte una cita ya creada, modificada o cancelada.

## 8. Creación de una cita

La comunicación de “cita creada” significa que la reserva fue completada correctamente. No existe un estado separado de `Appointment` llamado “confirmada por correo”.

## 9. Modificación/reprogramación

Una modificación/reprogramación genera una nueva notificación de cambio.

Los recordatorios futuros deben evaluar la fecha/hora vigente de la cita; el subsistema no mantiene una copia paralela de la agenda.

## 10. Cancelación

Una cancelación genera la notificación de cancelación a los tres destinatarios definidos.

Las ejecuciones futuras de recordatorios asociadas a la cita cancelada deben quedar ineligibles para envío.

## 11. Idempotencia

Una notificación se considera duplicada cuando representa el mismo evento de negocio, para el mismo destinatario, canal y momento funcional.

Clave lógica recomendada:

```text
business_event_id + event_type + recipient_id + channel + reminder_offset
```

Para citas modificadas, la identidad del evento debe distinguir cada modificación efectiva sin crear una fuente paralela de estado de `Appointment`.

## 12. Providers

El dominio consume una abstracción de transporte. Un proveedor concreto de SMTP/API no puede aparecer en servicios de Agenda o cuentas.

## 13. Invariantes

- Email es el único canal implementado en esta fase.
- WhatsApp y SMS quedan fuera de primera versión.
- El tiempo transcurrido no cambia `Appointment`.
- El correo nunca concede permisos.
- El correo nunca contiene más información clínica que la estrictamente necesaria.
- No hay transacción ACID compartida con un proveedor externo.

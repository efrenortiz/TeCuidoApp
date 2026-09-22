# Fase 6 — Notification Data Model

**Fuente normativa:** `docs/phases/phase-6-design-freeze.md` v1.1
**Estado:** Diseño técnico derivado — **implementado** (ver
`docs/phases/phase-6-implementation-summary.md`, PD-004/PD-007).

## 1. Objetivo

Proponer una persistencia mínima para soportar intención, programación, deduplicación, resultado y diagnóstico operativo de emails sin crear un historial innecesario.

## 2. Entidades lógicas

### 2.1 Notification

Representa una intención concreta de comunicación.

Campos lógicos mínimos:

| Campo | Propósito |
|---|---|
| id | Identificador interno |
| event_type | Evento funcional (`APPOINTMENT_CREATED`, etc.) |
| channel | `EMAIL` en Fase 6 |
| recipient_user | Usuario destinatario, cuando exista vínculo de identidad |
| recipient_address | Dirección usada en el envío, congelada para trazabilidad del intento |
| resource_type/resource_id | Recurso de negocio asociado |
| scheduled_for | Momento previsto de procesamiento |
| status | Estado operacional |
| attempt_count | Conteo de intentos |
| last_attempt_at | Último intento |
| sent_at | Momento de éxito |
| provider_reference | Identificador externo cuando el proveedor lo entregue |
| reason_code | Código seguro de fallo |
| dedupe_key | Identidad operacional para evitar duplicados |
| created_at | Fecha de creación |
| updated_at | Última actualización operacional |

No se recomienda guardar el cuerpo clínico de la cita en la fila de notificación.

### 2.2 Configurabilidad de las ventanas de recordatorio (cierra H-01, `requirements.md` §27.1)

`requirements.md` §27.1 exige que las reglas de recordatorio "se diseñen de forma configurable
para poder modificarse sin cambiar código". Una constante Python (o un valor fijo en `settings`)
no satisface ese requisito, porque cambiarla exige un despliegue de código.

Mecanismo mínimo requerido: una entidad de configuración persistida en PostgreSQL, editable
administrativamente (Django Admin u operación equivalente ya usada por el proyecto), no un valor
hardcodeado en el servicio:

`ReminderWindow` (o nombre equivalente que siga la convención del proyecto):

| Campo | Propósito |
|---|---|
| id | Identificador interno |
| offset_days | Días de anticipación (p. ej. 15, 10, 5, 1) |
| is_active | Permite desactivar una ventana sin eliminar el registro histórico de configuración |
| created_at / updated_at | Trazabilidad de cambios de configuración |

Restricción: `UNIQUE(offset_days)` entre las ventanas activas — no debe existir ambigüedad sobre
qué fila gobierna una misma ventana.

Las cuatro ventanas iniciales (15/10/5/1 días) se cargan como datos semilla (migración de datos),
no como opciones fijas del código de `schedule_appointment_reminders`
(`phase-6-notification-service-contracts.md` §2). El servicio de programación debe leer las
ventanas activas desde esta tabla en cada ejecución, nunca desde una constante Python. Agregar,
desactivar o cambiar `offset_days` es una operación de datos, no un cambio de código ni una nueva
migración de esquema.

Esta entidad es distinta de `Notification`/`NotificationTemplate` (§2.1/§2.3): describe la regla
de programación, no una intención de envío concreta.

**PD-004 (decisión final del propietario):** un cambio en `ReminderWindow` tiene efecto
**hacia adelante únicamente**:

```text
nueva configuración
→ nuevas citas (schedule_appointment_reminders lee las ventanas activas en ese momento)
+
citas reprogramadas posteriormente (reschedule_appointment_reminders solo recalcula
  scheduled_for de filas ya existentes, con el offset_days ya fijado en su dedupe_key —
  nunca vuelve a leer ReminderWindow)
```

No existe reconciliación retroactiva de citas ya programadas cuyos recordatorios ya se
materializaron con la configuración vigente en su momento — y no se crea un job de reconciliación
masiva, un proceso retroactivo ni un snapshot para compensarlo: es un comportamiento ya natural
de la implementación (`ReminderWindow` solo se lee en el momento de crear la cita), no una
funcionalidad adicional solicitada.

### 2.3 NotificationTemplate

Puede ser una estructura de código/configuración si el proyecto no necesita edición desde UI.

Debe identificar:

- evento;
- idioma/locale si ya existe soporte de internacionalización;
- asunto;
- cuerpo textual/HTML;
- versión de plantilla.

No se crea un editor administrativo de plantillas en Fase 6 salvo requerimiento posterior.

## 3. Índices y restricciones

Recomendados:

- índice por `scheduled_for` + `status`;
- índice por `recipient_user` + `created_at`;
- índice por `resource_type` + `resource_id`;
- unicidad sobre `dedupe_key` cuando la semántica de eventos lo permita.

## 4. Relación con Appointment

No se crea una nueva entidad de agenda.

La notificación puede referenciar lógicamente el `Appointment` existente. Los servicios de Agenda siguen siendo la fuente de verdad de los datos de la cita.

## 5. Programación de recordatorios

La programación puede materializar cuatro intenciones futuras por cita y destinatario elegible, o calcularse bajo demanda con una tabla de tareas equivalentemente mínima. La opción final debe seguir la infraestructura realmente disponible en el repositorio.

En cualquiera de las dos opciones, las ventanas usadas para programar deben leerse de
`ReminderWindow` (§2.2), nunca de un literal `[15, 10, 5, 1]` en el código del servicio.

Requisito técnico obligatorio: una misma combinación evento/destinatario/ventana temporal no debe producir duplicados funcionales.

## 6. Cancelación y reprogramación

No se elimina información histórica de notificaciones ya procesadas.

- cancelación: las tareas futuras se marcan como `CANCELLED` o dejan de ser elegibles por estado de la cita;
- reprogramación: las tareas futuras se recalculan respecto de la fecha vigente de `Appointment` sin copiar la lógica de Agenda.

## 7. Seguridad de persistencia

No almacenar:

- contraseñas;
- tokens completos;
- cuerpos completos de requests;
- contenido clínico innecesario;
- secretos de proveedores.

## 8. Recomendación de implementación

Preferir modelos Django normales y PostgreSQL. Introducir cola externa, broker o Redis únicamente si la infraestructura existente no cubre el volumen real o las garantías requeridas.

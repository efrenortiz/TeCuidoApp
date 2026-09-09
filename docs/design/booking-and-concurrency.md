# Diseño de reservas y concurrencia — Fase 2

## 1. Propósito

Este documento define el diseño técnico para reservar horarios en TeCuidoApp y proteger la integridad de Agenda frente a concurrencia.

Deriva sus reglas funcionales de:

- `docs/phases/phase-2-agenda.md`
- `docs/design/appointment-domain.md`
- `docs/design/availability-rules.md`

Su objetivo es establecer cómo se implementan técnicamente:

- reserva directa;
- hold temporal;
- consumo del hold;
- expiración y liberación;
- prevención de doble reserva;
- concurrencia entre citas y holds;
- reprogramación concurrente;
- idempotencia;
- transacciones e integridad en PostgreSQL.

---

## 2. Principios fundamentales

### 2.1 La base de datos es la autoridad final

La interfaz puede mostrar un slot como disponible, pero esa información nunca constituye una garantía de reserva.

La disponibilidad definitiva se determina dentro de una operación transaccional contra PostgreSQL.

Por tanto:

> Ver un horario disponible y reservarlo son operaciones distintas y siempre debe existir una validación final al persistir.

### 2.2 No existe una entidad persistida `Slot`

Los slots son derivados de una `Availability`.

El mecanismo de reserva trabaja con intervalos temporales concretos y no depende de una tabla `Slot`.

### 2.3 La reserva es directa

No existe:

```text
PENDING_CONFIRMATION
```

ni una segunda etapa de confirmación.

El objetivo del hold es exclusivamente proteger temporalmente el horario durante la operación de reserva.

---

## 3. Recursos que deben protegerse

Cada cita y cada hold representan ocupación temporal de dos recursos:

```text
Doctor
+
Clinic
```

Por tanto, para cualquier intervalo:

```text
[start_datetime, end_datetime)
```

debe garantizarse:

1. un médico no tenga dos ocupaciones temporales superpuestas;
2. un consultorio no tenga dos ocupaciones temporales superpuestas.

Esto aplica tanto a:

- `Appointment`;
- `Hold`.

La protección temporal debe utilizar intervalos semiabiertos:

```text
[start, end)
```

De esta forma, dos citas consecutivas pueden coexistir:

```text
09:00–10:00
10:00–11:00
```

sin considerarse solapadas.

---

## 4. Actores autorizados

Pueden iniciar una operación de reserva:

- paciente titular;
- responsable con `ResponsiblePatientRelationship.status = ACTIVE`;
- médico con `DoctorClinic` válida en la combinación de la reserva — **sin exigir `DoctorPatientRelationship` previa con el paciente** (decisión de cierre, 2026-09-09; ver `docs/design/agenda-permissions.md` §9);
- administrador autorizado.

Las mismas reglas de autorización de Fase 1 deben seguir siendo la fuente de verdad.

Agenda no debe crear un sistema de permisos paralelo.

---

## 5. Flujo de reserva

El flujo lógico es:

```text
Usuario autorizado
      ↓
Selecciona disponibilidad/slot
      ↓
Validación inicial
      ↓
Crear Hold
      ↓
Completar datos de reserva
      ↓
Validación final dentro de transacción
      ↓
Crear Appointment = SCHEDULED
      ↓
Consumir Hold
```

El flujo real debe ser seguro frente a concurrencia aunque dos usuarios intenten reservar el mismo horario simultáneamente.

---

## 6. Creación del Hold

Un hold se crea únicamente cuando el usuario inicia una operación real de reserva.

No se crea por:

- abrir la agenda;
- consultar disponibilidad;
- desplazarse entre fechas;
- visualizar un slot.

### Datos conceptuales mínimos

El hold debe conservar:

```text
id
user
doctor
clinic
start_datetime
end_datetime
created_at
expires_at
status
```

Los timestamps se almacenan de forma consistente con la zona horaria del sistema, mientras que la interpretación de negocio de Agenda corresponde al `Clinic`.

### Un hold pertenece a un único usuario

No debe existir un hold anónimo.

---

## 7. Duración del Hold

La duración del hold es:

```text
15 minutos
```

Debe existir explícitamente un `expires_at`.

El cálculo debe producir un instante de expiración inequívoco.

La expiración no depende de una tarea que deba ejecutarse exactamente en ese momento para liberar el recurso.

Un hold se considera activo mientras:

```text
status = ACTIVE
AND
expires_at > current_time
```

En consecuencia, un hold cuyo timestamp de expiración ya pasó deja de ser válido para bloquear nuevas reservas aunque todavía no haya sido marcado físicamente como `EXPIRED`.

---

## 8. Estados del Hold

El hold tendrá los siguientes estados técnicos:

```text
ACTIVE
EXPIRED
RELEASED
CONSUMED
```

### `ACTIVE`

Hold vigente y bloqueando el intervalo.

### `EXPIRED`

El periodo de 15 minutos terminó sin convertirse en una cita.

### `RELEASED`

El usuario liberó voluntariamente el hold antes de su expiración.

### `CONSUMED`

El hold se utilizó exitosamente para crear la cita.

Estos estados pertenecen al hold y no al ciclo de vida de `Appointment`.

---

## 9. Un solo Hold activo por usuario

Un usuario no puede mantener más de un hold activo simultáneamente.

A nivel funcional:

```text
User A
  ↓
Hold 09:00 ACTIVE

intenta Hold 10:00
  ↓
rechazado
```

Para seleccionar otro horario debe:

```text
liberar Hold actual
      ↓
seleccionar nuevo horario
      ↓
crear nuevo Hold
```

No se permite transferir ni renovar un hold.

---

## 10. Cambio de horario durante un Hold

No se permite cambiar el slot mientras el usuario tenga un hold activo.

No existe una operación de “mover” un hold de un horario a otro.

El flujo obligatorio es:

```text
Hold actual
   ↓
RELEASED
   ↓
seleccionar nuevo slot
   ↓
nuevo Hold
```

Esto reduce estados intermedios y simplifica la concurrencia.

---

## 11. Liberación voluntaria

El usuario puede liberar manualmente su hold.

La operación cambia:

```text
ACTIVE → RELEASED
```

y el intervalo deja inmediatamente de estar reservado por ese hold.

La operación debe ser transaccional para evitar condiciones de carrera.

---

## 12. Expiración

La expiración no requiere un proceso síncrono exacto.

Un hold cuyo `expires_at` haya quedado en el pasado:

```text
expires_at <= now
```

ya no debe bloquear nuevas reservas.

Puede existir una operación de limpieza posterior que cambie:

```text
ACTIVE → EXPIRED
```

pero la corrección funcional nunca puede depender de que dicha limpieza ya haya ocurrido.

Esto permite que un job de mantenimiento futuro sea opcional y no forme parte del camino crítico de reserva.

---

## 13. No renovación

Un hold no puede extenderse ni renovarse.

No deben existir operaciones como:

```text
extend_hold()
renew_hold()
```

Una vez agotados los 15 minutos, el usuario debe iniciar una nueva operación.

---

## 14. Criterios para considerar un Hold activo

Un hold bloquea un intervalo sólo cuando se cumplen simultáneamente:

```text
status = ACTIVE
expires_at > now
```

No bloquean:

```text
EXPIRED
RELEASED
CONSUMED
```

Esto permite mantener historial sin mantener bloqueos obsoletos.

---

## 15. Creación de Appointment desde Hold

La creación definitiva de la cita debe ejecutarse dentro de una única transacción.

La transacción debe:

1. localizar el hold esperado;
2. verificar que pertenece al usuario que ejecuta la operación;
3. verificar que sigue siendo `ACTIVE`;
4. verificar que `expires_at > now`;
5. bloquear/validar los recursos relevantes;
6. volver a comprobar disponibilidad;
7. crear `Appointment` con estado `SCHEDULED`;
8. consumir el hold;
9. confirmar la transacción.

El resultado correcto es:

```text
Hold: ACTIVE → CONSUMED
Appointment: creado como SCHEDULED
```

No debe existir un estado intermedio visible donde la cita ya esté creada pero el hold siga bloqueando indefinidamente.

---

## 16. El Hold no garantiza por sí solo la creación de la cita

Un hold sólo garantiza una protección temporal.

La operación final debe volver a validar:

- vigencia del hold;
- estado;
- autorización;
- disponibilidad;
- ausencia de conflictos;
- reglas temporales de reserva.

Si cualquiera falla:

```text
Appointment no creado
```

y la operación debe terminar sin dejar una ocupación inconsistente.

---

## 17. Reserva de un slot ya iniciado

La política de Agenda permite reservar un slot hasta 30 minutos después de su inicio.

Ejemplo:

```text
Slot: 14:00–15:00

14:00–14:30 → reservable
14:31 → no reservable
```

Una reserva realizada dentro de esa ventana se crea normalmente como:

```text
Appointment.status = SCHEDULED
```

El hold y la creación de la cita siguen exactamente el mismo mecanismo que para un slot futuro.

La reserva tardía no cambia automáticamente el estado de la cita a `IN_CONSULTATION`.

---

## 18. Idempotencia de creación de citas

La operación de creación debe contemplar reintentos.

Si el cliente repite una petición porque no recibió la respuesta original, el sistema no debe crear dos citas para la misma operación.

La estrategia concreta puede utilizar una clave de idempotencia asociada a la operación de reserva.

La misma clave procesada exitosamente debe devolver el resultado de la operación original en lugar de crear una segunda cita.

La clave de idempotencia debe tener alcance suficiente para evitar colisiones entre operaciones distintas.

---

## 19. Concurrencia entre dos Holds

Escenario:

```text
Usuario A ─┐
           ├── Doctor D + Clinic C + 10:00–11:00
Usuario B ─┘
```

Sólo una operación puede crear un hold activo que bloquee ese intervalo.

La decisión final debe resolverse de forma transaccional.

No es suficiente comprobar primero:

```text
¿Está libre?
```

y después insertar el hold en una transacción sin protección de concurrencia, porque dos transacciones podrían observar simultáneamente el mismo estado.

---

## 20. Concurrencia entre Hold y Appointment

Un hold y una cita se consideran ocupaciones del mismo recurso temporal.

Por tanto, nunca debe poder persistirse una combinación válida donde:

```text
Hold activo
+
Appointment solapado
```

para el mismo médico o consultorio.

La creación de una cita debe coordinarse con la existencia de holds activos dentro de una transacción.

---

## 21. PostgreSQL como autoridad de integridad

Las garantías críticas no deben depender exclusivamente de lógica Python.

Cuando una restricción de negocio pueda expresarse mediante una garantía de base de datos, debe hacerse en PostgreSQL.

Para los intervalos de Agenda se debe evaluar el uso de:

```text
ExclusionConstraint
```

con rangos temporales y los identificadores de recursos correspondientes.

El objetivo es garantizar que dos ocupaciones incompatibles no puedan coexistir aunque dos requests lleguen simultáneamente.

---

## 22. Intervalos temporales

Las ocupaciones deben representarse como intervalos semiabiertos:

```text
[start_datetime, end_datetime)
```

Esto permite:

```text
09:00–10:00
10:00–11:00
```

y evita falsos conflictos entre citas consecutivas.

No deben utilizarse comparaciones ambiguas basadas únicamente en horas formateadas como texto.

---

## 23. Protección de médico y consultorio

La integridad debe evaluarse independientemente para ambos recursos.

Ejemplo:

```text
Doctor A + Clinic 1
09:00–10:00
```

impide:

```text
Doctor A + Clinic 2
09:30–10:30
```

aunque el consultorio sea diferente.

También impide:

```text
Doctor B + Clinic 1
09:30–10:30
```

aunque el médico sea diferente.

La primera regla protege al médico; la segunda protege al consultorio.

---

## 24. Concurrencia de reprogramación

Una reprogramación debe tratarse como una operación atómica.

No debe ejecutarse como:

```text
1. liberar horario anterior
2. guardar cambios
3. intentar reservar nuevo horario
```

porque una segunda operación podría ocupar el nuevo horario entre pasos.

Debe funcionar conceptualmente como:

```text
BEGIN
   validar cita original
   adquirir/proteger nuevo intervalo
   validar disponibilidad nueva
   actualizar cita
   registrar historial
   liberar ocupación anterior
COMMIT
```

Si la nueva ubicación no está disponible:

```text
ROLLBACK
```

y la cita original permanece sin cambios.

---

## 25. Idempotencia de reprogramación

La reprogramación también debe soportar reintentos seguros.

Una repetición accidental de la misma operación no debe registrar dos cambios de historial ni producir dos estados diferentes.

La estrategia concreta de idempotencia debe ser consistente con la utilizada para reservas.

---

## 26. Cancelación y liberación

Cuando una cita futura se cancela correctamente:

```text
Appointment
   ↓
CANCELLED
```

el intervalo previamente ocupado deja de bloquear nuevas reservas.

No se elimina la cita.

La liberación del recurso y el cambio de estado deben ser atómicos respecto de la operación de cancelación.

---

## 27. No borrar registros históricos

Ni `Appointment`, ni `AppointmentRescheduleHistory`, ni un Hold que sea necesario para trazabilidad deben eliminarse simplemente para liberar el recurso.

La ocupación actual se determina por estado y vigencia.

El historial se conserva separado de la disponibilidad actual.

---

## 28. Fallos transaccionales

Si falla cualquier paso de una operación de reserva:

```text
crear Hold
crear Appointment
consumir Hold
```

la transacción debe revertirse.

No deben existir situaciones permanentes como:

```text
Appointment creada
pero Hold ACTIVE infinito
```

o:

```text
Hold CONSUMED
pero Appointment inexistente
```

salvo casos de fallo catastrófico que posteriormente requieran recuperación explícita.

---

## 29. Límites de responsabilidad

Este documento define el mecanismo técnico de protección de reservas.

No redefine:

- quién puede reservar;
- quién puede cancelar;
- quién puede reprogramar;
- estados de Appointment;
- reglas de disponibilidad;
- reglas clínicas.

Esas decisiones provienen de los documentos funcionales y de dominio correspondientes.

---

## 30. Flujo de concurrencia esperado

### Dos usuarios intentan el mismo horario

```text
Usuario A ─────┐
               ├── mismo intervalo
Usuario B ─────┘

A → transacción → obtiene recurso → Hold ACTIVE
B → transacción → conflicto → rechazo
```

### Hold y creación de cita

```text
Hold ACTIVE
     ↓
validación final
     ↓
Appointment SCHEDULED
     +
Hold CONSUMED
```

### Hold expirado

```text
Hold ACTIVE
     ↓
expires_at <= now
     ↓
ya no bloquea
     ↓
nuevo usuario puede reservar
```

### Reprogramación fallida

```text
Cita 10:00
     ↓
intenta 15:00
     ↓
15:00 ocupado
     ↓
ROLLBACK
     ↓
cita permanece 10:00
```

---

## 31. Invariantes técnicas

La implementación debe garantizar:

1. Un usuario no mantiene más de un hold activo.
2. Un hold activo nunca tiene `expires_at <= now`.
3. Un hold expirado no bloquea nuevas reservas.
4. Un hold no puede renovarse.
5. Un usuario debe liberar su hold antes de seleccionar otro horario.
6. Una cita y un hold no pueden ocupar simultáneamente el mismo recurso temporal incompatible.
7. Un médico no puede tener dos ocupaciones temporales superpuestas.
8. Un consultorio no puede tener dos ocupaciones temporales superpuestas.
9. Una operación concurrente sólo puede adquirir exitosamente un mismo intervalo.
10. Crear una cita y consumir el hold deben pertenecer a una misma unidad transaccional.
11. Una reprogramación debe ser atómica.
12. Un reintento de la misma operación no debe duplicar reservas ni historial.
13. El historial no se elimina como consecuencia de liberar un recurso.
14. La base de datos debe proporcionar la garantía final de integridad frente a carreras concurrentes.

---

## 32. Criterios de aceptación técnica

Antes de implementar la funcionalidad se deben poder demostrar, mediante pruebas automatizadas, al menos estos casos:

### Reserva normal

```text
slot disponible
→ Hold ACTIVE
→ Appointment SCHEDULED
→ Hold CONSUMED
```

### Hold expirado

```text
Hold expires
→ deja de bloquear
→ otro usuario puede reservar
```

### Liberación manual

```text
Hold ACTIVE
→ RELEASED
→ otro usuario puede reservar
```

### Un solo Hold por usuario

```text
Hold A ACTIVE
→ intento Hold B
→ rechazo
```

### Cambio de slot durante Hold

```text
Hold A ACTIVE
→ intento cambiar directamente
→ rechazo
```

### Doble Hold concurrente

```text
A y B intentan mismo intervalo
→ sólo uno obtiene HOLD
```

### Doble Appointment concurrente

```text
A y B intentan mismo intervalo
→ sólo uno obtiene Appointment
```

### Reprogramación concurrente

```text
A y B intentan el mismo nuevo horario
→ sólo una operación tiene éxito
```

### Reintento idempotente

```text
misma operación repetida
→ una sola Appointment
```

---

## 33. Fuera de alcance

No se define aquí:

- interfaz de Agenda;
- diseño visual de slots;
- matriz completa de permisos;
- ciclo de vida clínico;
- notificaciones;
- pagos;
- CareRequest;
- historias clínicas;
- procesamiento de consultas médicas.

---

## 34. Principio de cierre

La arquitectura de reserva debe obedecer una regla central:

> **La disponibilidad mostrada al usuario es sólo una previsualización; la reserva real existe únicamente cuando PostgreSQL confirma, dentro de una operación segura, que el intervalo puede ser adquirido sin conflicto.**

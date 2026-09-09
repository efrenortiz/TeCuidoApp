# UX de Agenda — Fase 2

## 1. Propósito

Este documento define la experiencia de usuario de Agenda en TeCuidoApp.

Deriva de:

- `docs/phases/phase-2-agenda.md`
- `docs/design/appointment-domain.md`
- `docs/design/availability-rules.md`
- `docs/design/booking-and-concurrency.md`
- `docs/design/agenda-permissions.md`
- `docs/design/agenda-service-contracts.md`

Su función es convertir las políticas y contratos de Agenda en flujos de interfaz consistentes, sin modificar las reglas de negocio.

---

## 2. Principios UX

### 2.1 La interfaz guía, pero el backend decide

La UI debe impedir o esconder acciones que evidentemente no correspondan al actor, pero todas las reglas deben volver a validarse en backend.

Un usuario nunca debe asumir que:

```text
slot mostrado como disponible
```

significa:

```text
slot garantizado
```

### 2.2 Agenda debe ser simple

El flujo principal debe evitar pasos innecesarios:

```text
seleccionar horario
→ hold
→ datos de cita
→ crear cita
```

No existen:

- solicitudes de cita;
- confirmación posterior;
- check-in del paciente;
- sala de espera;
- estados intermedios de aprobación.

### 2.3 Las etiquetas de UI deben corresponder al dominio

Debe utilizarse:

```text
Iniciar consulta
```

y no:

```text
Check-in
```

porque la acción representa el inicio formal de la atención por parte del médico.

---

# 3. Roles y experiencias principales

## 3.1 Paciente

Puede:

- consultar disponibilidad para reservar;
- seleccionar un médico y consultorio disponibles;
- reservar para sí mismo;
- mantener un hold de 15 minutos durante una reserva;
- liberar su hold;
- cancelar sus citas futuras;
- reprogramar sus citas futuras;
- consultar sus citas.

No puede:

- crear o modificar disponibilidades;
- iniciar consultas;
- marcar `NO_SHOW`;
- acceder a citas de otros pacientes.

---

## 3.2 Responsable

Puede:

- seleccionar un paciente con relación `ACTIVE`;
- consultar disponibilidad necesaria para dicho paciente;
- reservar;
- liberar su propio hold;
- cancelar;
- reprogramar;
- consultar citas del paciente autorizado.

No puede operar sobre pacientes cuya relación ya no esté activa.

---

## 3.3 Médico

Puede:

- consultar su agenda;
- consultar su propia disponibilidad;
- crear disponibilidades;
- modificar o desactivar disponibilidades cuando las reglas lo permitan;
- crear citas para cualquier paciente al que tenga acceso legítimo (`DoctorClinic` válida), **incluida la primera cita de un paciente sin `DoctorPatientRelationship` previa** — esa operación no crea ni modifica la relación (decisión de cierre, 2026-09-09);
- consultar las citas en las que es el médico asignado;
- cancelar;
- reprogramar;
- iniciar consultas;
- finalizar consultas;
- marcar `NO_SHOW`.

No puede:

- administrar la disponibilidad de otro médico;
- consultar arbitrariamente la agenda privada de otro médico.

---

## 3.4 Administrador

Puede operar dentro de las clínicas de su ámbito autorizado.

Puede:

- consultar disponibilidad;
- crear y administrar disponibilidades de médicos de clínicas autorizadas;
- crear citas;
- consultar citas;
- cancelar;
- reprogramar;
- crear y liberar sus propios holds.

No puede:

- iniciar consultas;
- finalizar consultas;
- marcar `NO_SHOW`;
- operar fuera de su ámbito administrativo.

---

# 4. Agenda del médico

La vista principal del médico debe permitir navegar por:

```text
Fecha
  ↓
Disponibilidades
  ↓
Slots
  ↓
Citas
```

La agenda debe mostrar claramente:

- día;
- consultorio;
- disponibilidad;
- slots;
- citas;
- hora actual;
- estado de cada cita.

El médico no debe ver un selector para cambiar arbitrariamente a la agenda privada de otro médico.

---

# 5. Crear disponibilidad

La interfaz debe solicitar:

```text
Consultorio
Fecha
Hora inicio
Hora fin
```

La duración se muestra como información:

```text
Duración de citas: 60 min
```

No se captura manualmente en la disponibilidad.

### Validaciones de UI

La interfaz puede impedir:

- hora fin <= hora inicio;
- inicio en el pasado;
- fechas fuera de 6 meses.

Sin embargo, el backend siempre vuelve a validar.

### Resultado

Después de guardar:

```text
Disponibilidad creada
```

y la agenda actualiza los slots derivados.

---

# 6. Modificar disponibilidad

Para una disponibilidad sin citas, el usuario autorizado puede editar:

- fecha, cuando las reglas lo permitan;
- hora inicio;
- hora fin;
- consultorio, cuando el modelo lo permita.

Para una disponibilidad con citas:

```text
Editar
```

no debe estar disponible.

La interfaz debe explicar:

> Esta disponibilidad tiene citas asociadas y no puede modificarse. Primero deben reprogramarse las citas afectadas.

No se debe ofrecer:

```text
Eliminar disponibilidad
```

como mecanismo para evadir esta regla.

---

# 7. Desactivar disponibilidad

Cuando una disponibilidad pueda desactivarse:

```text
[Desactivar disponibilidad]
```

debe presentar confirmación.

Mensaje sugerido:

> Esta acción retirará la disponibilidad de nuevas reservas. La disponibilidad conservará su historial.

Si tiene citas asociadas, la acción debe estar bloqueada.

La UI debe usar baja lógica, no presentar eliminación destructiva.

---

# 8. Visualización de slots

Ejemplo:

```text
Disponibilidad
09:00–13:00

09:00–10:00   Disponible
10:00–11:00   Ocupado
11:00–12:00   Disponible
12:00–13:00   Reservado temporalmente
```

Los slots deben mostrarse como intervalos completos.

No deben aparecer inicios arbitrarios.

---

# 9. Slot ya iniciado

Un slot iniciado puede continuar disponible para reserva durante los primeros 30 minutos.

Ejemplo:

```text
14:00–15:00
```

Durante:

```text
14:00–14:30
```

puede mostrarse:

```text
Disponible · inicio inmediato
```

Después de:

```text
14:30
```

deja de ser seleccionable.

Si se reserva:

```text
Appointment = SCHEDULED
```

La reserva no inicia automáticamente la consulta.

---

# 10. Reserva de cita

Flujo:

```text
Seleccionar médico
        ↓
Seleccionar consultorio
        ↓
Seleccionar fecha
        ↓
Seleccionar slot
        ↓
Crear Hold
        ↓
Mostrar contador
        ↓
Capturar datos necesarios
        ↓
Crear cita
```

La cita queda:

```text
SCHEDULED
```

inmediatamente después de una creación exitosa.

No debe aparecer:

```text
Confirmar cita
```

como un paso posterior.

---

# 11. Hold durante la reserva

Al crear el hold, la UI debe mostrar:

```text
Horario reservado temporalmente
14:00–15:00

Tiempo restante:
14:32
```

El contador es informativo.

El usuario tendrá como acciones:

```text
Continuar
Liberar horario
```

No debe existir:

```text
Cambiar horario
```

mientras el hold esté activo.

---

# 12. Liberar Hold

El usuario puede seleccionar:

```text
Liberar horario
```

La UI debe pedir confirmación breve.

Después:

```text
Hold → RELEASED
```

y el usuario vuelve a la selección de horarios.

Para seleccionar otro horario deberá crear un nuevo hold.

---

# 13. Hold expirado

Cuando expire:

```text
Hold → EXPIRED
```

la pantalla debe mostrar:

> El tiempo de reserva terminó. Selecciona nuevamente un horario disponible.

No se debe intentar crear automáticamente la cita.

---

# 14. Conflicto al reservar

Si otro usuario obtiene el horario antes de completar la operación:

```text
Horario no disponible
```

La UI debe:

1. informar el conflicto;
2. refrescar la disponibilidad;
3. permitir elegir otro slot.

No debe mostrar mensajes técnicos de base de datos o concurrencia.

---

# 15. Confirmación de creación

Después de una creación exitosa:

```text
Cita programada correctamente
```

Mostrar:

```text
Paciente
Médico
Consultorio
Fecha
Hora
Duración
```

Cuando corresponda, puede mostrarse quién gestionó la cita.

---

# 16. Mis citas del paciente

Debe existir una sección:

```text
Mis citas
```

con agrupación útil, por ejemplo:

```text
Próximas
Historial
```

Cada cita debe mostrar:

- fecha;
- hora;
- médico;
- consultorio;
- duración;
- estado.

Los estados de negocio visibles son únicamente:

```text
SCHEDULED
IN_CONSULTATION
COMPLETED
CANCELLED
NO_SHOW
```

No debe mostrarse `RESCHEDULED` como estado.

---

# 17. Citas del responsable

El responsable debe comenzar por seleccionar:

```text
Paciente autorizado
```

Sólo deben aparecer pacientes con:

```text
ResponsiblePatientRelationship = ACTIVE
```

Después:

```text
Paciente
→ Citas
→ Nueva cita
```

No debe aparecer información de pacientes no autorizados.

---

# 18. Cancelación

Cuando una cita sea cancelable:

```text
[Cancelar cita]
```

El sistema solicita:

```text
Motivo de cancelación
```

Después de confirmar:

```text
SCHEDULED → CANCELLED
```

La UI debe informar:

> La cita fue cancelada y el horario quedó disponible nuevamente.

No debe ofrecer eliminar la cita.

---

# 19. Reprogramación

La acción:

```text
[Reprogramar]
```

debe permitir:

```text
Nueva fecha
Nuevo horario
Nuevo consultorio, cuando sea válido
```

No debe permitir modificar:

```text
Médico
```

El usuario debe ver claramente el horario actual antes de confirmar el cambio.

Ejemplo:

```text
Cita actual
15/09 · 10:00 · Consultorio 1

Nueva programación
18/09 · 12:00 · Consultorio 2
```

Al finalizar:

```text
Appointment permanece SCHEDULED
```

El historial queda registrado internamente.

---

# 20. Conflicto durante reprogramación

Si el nuevo horario deja de estar disponible antes de confirmar:

```text
No se pudo reprogramar
El horario seleccionado ya no está disponible.
```

La cita original debe continuar intacta.

La UI permite seleccionar otro horario.

---

# 21. Inicio de consulta

Sólo el médico asignado verá:

```text
[Iniciar consulta]
```

cuando la cita esté:

```text
SCHEDULED
```

Al ejecutarlo:

```text
SCHEDULED → IN_CONSULTATION
```

La interfaz debe registrar visualmente:

```text
Inicio de consulta
Hora
```

No debe existir un botón de check-in para paciente o responsable.

---

# 22. Finalizar consulta

Cuando una cita esté:

```text
IN_CONSULTATION
```

el médico verá:

```text
[Finalizar consulta]
```

Al ejecutarlo:

```text
IN_CONSULTATION → COMPLETED
```

La interfaz debe reflejar que la atención terminó.

---

# 23. `NO_SHOW`

Después de un minuto de la hora programada, si la cita continúa:

```text
SCHEDULED
```

el médico puede disponer de:

```text
[No se presentó]
```

No se requiere motivo.

Al confirmar:

```text
SCHEDULED → NO_SHOW
```

La acción no es automática.

Una cita `NO_SHOW` queda cerrada y no puede reactivarse.

---

# 24. Estados visuales de interfaz

Los estados visuales de la UI son independientes del estado de `Appointment`.

Estados visuales mínimos:

```text
Loading
Empty
Available
Held
Booked
Saving
Success
Conflict
Expired
Forbidden
Error
```

No deben almacenarse como estados de dominio.

---

# 25. Mensajes de errores

La interfaz debe traducir errores de dominio a lenguaje comprensible.

Ejemplos:

### Hold ocupado

> Este horario ya fue reservado temporalmente por otro usuario.

### Hold expirado

> El tiempo de reserva terminó. Selecciona nuevamente un horario.

### Sin permisos

> No tienes autorización para realizar esta acción.

### Cita ya iniciada

> La cita ya comenzó y no puede cancelarse o reprogramarse.

### Disponibilidad con citas

> Esta disponibilidad no puede modificarse porque ya tiene citas asociadas.

### Conflicto

> El horario dejó de estar disponible. Selecciona otro.

Nunca deben exponerse mensajes internos de PostgreSQL, Django o excepciones Python.

---

# 26. Estados de carga y vacío

La interfaz debe contemplar explícitamente:

### Sin disponibilidad

> No hay horarios disponibles para esta fecha.

### Sin citas

> No tienes citas programadas.

### Cargando

Mostrar un estado de carga sin permitir acciones duplicadas.

### Guardando

Deshabilitar temporalmente el botón de envío para reducir reintentos accidentales.

---

# 27. Acción duplicada

Las operaciones mutadoras deben mostrar retroalimentación inmediata:

```text
Guardando...
```

y evitar múltiples clicks mientras se espera la respuesta.

La protección real contra duplicados pertenece a idempotencia/backend.

---

# 28. Zonas horarias

La Agenda debe mostrar las horas usando la zona horaria del consultorio como referencia de negocio.

En interfaces que requieran conversión para el usuario, la conversión debe ser explícita y no cambiar la hora oficial de la cita del consultorio.

---

# 29. Accesibilidad y claridad

Los botones deben expresar la acción real:

```text
Crear disponibilidad
Reservar cita
Liberar horario
Cancelar cita
Reprogramar
Iniciar consulta
Finalizar consulta
Marcar no se presentó
```

Debe evitarse lenguaje ambiguo como:

```text
Aceptar
Procesar
Confirmar
Check-in
```

cuando una acción más específica sea posible.

Las acciones destructivas o irreversibles deben requerir confirmación.

---

# 30. Flujo completo del paciente

```text
Agenda
  ↓
Seleccionar médico
  ↓
Seleccionar consultorio
  ↓
Seleccionar fecha
  ↓
Seleccionar slot
  ↓
Hold 15 min
  ↓
Datos
  ↓
Crear cita
  ↓
SCHEDULED
```

---

# 31. Flujo completo del responsable

```text
Agenda
  ↓
Seleccionar paciente autorizado
  ↓
Seleccionar médico
  ↓
Seleccionar consultorio
  ↓
Seleccionar fecha
  ↓
Seleccionar slot
  ↓
Hold 15 min
  ↓
Crear cita
  ↓
SCHEDULED
```

---

# 32. Flujo completo del médico

```text
Agenda
  ↓
Crear disponibilidad
  ↓
Ver slots
  ↓
Ver citas
  ↓
Paciente llega físicamente
  ↓
Iniciar consulta
  ↓
IN_CONSULTATION
  ↓
Finalizar consulta
  ↓
COMPLETED
```

Alternativamente:

```text
SCHEDULED
   ↓
NO_SHOW
```

cuando corresponda.

---

# 33. Flujo completo del administrador

```text
Clínica autorizada
  ↓
Médico + Clinic válidos
  ↓
Disponibilidad / Cita
  ↓
Operación permitida
```

El administrador no inicia, finaliza ni marca `NO_SHOW`.

---

# 34. Fuera de alcance UX

No se diseñan aquí:

- historia clínica;
- CareRequest;
- pagos;
- notificaciones;
- telemedicina;
- sala de espera;
- check-in del paciente;
- aplicación clínica posterior a `COMPLETED`.

---

# 35. Principio rector UX

La experiencia de Agenda debe seguir:

```text
Descubrir disponibilidad
        ↓
Seleccionar horario
        ↓
Proteger temporalmente
        ↓
Reservar
        ↓
Gestionar cita
        ↓
Iniciar atención
        ↓
Finalizar o registrar ausencia
```

El objetivo es que cada actor vea únicamente las acciones que puede realizar, mientras que la validación definitiva y la integridad permanecen en los servicios y en PostgreSQL.

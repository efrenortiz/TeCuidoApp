# Fase 2 — Agenda

**Estado:** Especificación funcional aprobada — lista para diseño técnico y programación

**Fecha de aprobación de políticas:** 2026-09-09

**Dependencias:** Fase 1 — Fundaciones

## 1. Propósito

La Fase 2 implementa la agenda operativa de TeCuidoApp: disponibilidades por fecha, generación de horarios, reservas directas, bloqueo temporal, cancelación, reprogramación, inicio de consulta y registro de inasistencias.

La agenda debe consumir la identidad, perfiles, relaciones y autorización de Fase 1 sin reconstruir ni duplicar esos mecanismos.

## 2. Alcance

Incluye exclusivamente:

- Disponibilidad de médico + consultorio por fecha concreta.
- Configuración de duración de citas.
- Visualización de disponibilidad y slots.
- Creación directa de citas.
- Hold temporal de 15 minutos durante la reserva.
- Prevención de doble reserva y conflictos de concurrencia.
- Cancelación de citas.
- Reprogramación de citas.
- Inicio de consulta por el médico asignado.
- `NO_SHOW` por el médico asignado.
- Historial de reprogramaciones y trazabilidad de operaciones de agenda.

No incluye CareRequest, historia clínica, MedicalEncounter como dominio clínico, recetas, documentos clínicos, notificaciones, auditoría avanzada ni otras funcionalidades de fases posteriores.

## 3. Dependencias e invariantes de Fase 1

Fase 2 debe utilizar las entidades canónicas existentes:

- `User` para autenticación.
- `Person` para identidad y `birth_date`.
- `Doctor` para el perfil del médico.
- `Patient` para el paciente.
- `ResponsiblePatientRelationship` para autorizar la gestión de un paciente por un responsable.
- `DoctorPatientRelationship` para determinar la relación vigente médico-paciente cuando corresponda.
- `Clinic` para el consultorio.
- `DoctorClinic` para la relación médico-consultorio.

Reglas que Fase 2 no debe reinterpretar:

- Sólo una relación `ResponsiblePatientRelationship` con estado `ACTIVE` concede autorización operativa al responsable.
- La autorización médico-paciente depende de una relación explícita y vigente.
- `Patient.regime` no se sustituye por inferencias sobre edad cronológica.
- Un paciente adulto puede existir sin `User`; la agenda no debe obligar a crear una cuenta.
- La transición de menor a adulto de Fase 1 ya desactiva las relaciones activas del responsable.

## 4. Actores de Agenda

### Paciente

Puede gestionar citas propias cuando tenga identidad/autorización válida en el sistema.

### Responsable

Puede gestionar citas del paciente únicamente mientras exista `ResponsiblePatientRelationship.status == ACTIVE`.

### Médico

Puede gestionar su agenda, crear citas, crear/modificar disponibilidades y operar las citas que tiene asignadas.

Un médico puede crear directamente una cita para cualquier paciente al que tenga **acceso legítimo** — esto es, dentro de una combinación `Doctor + Clinic` para la que tiene una relación `DoctorClinic` válida — **aunque todavía no exista una `DoctorPatientRelationship` activa** entre ambos. No se exige relación previa como condición para la primera cita (decisión de cierre, 2026-09-09).

Crear esa cita **no crea, modifica ni activa** ninguna `DoctorPatientRelationship`, y no produce ningún otro efecto sobre el sistema de autorización de Fase 1. `crear Appointment` y `crear DoctorPatientRelationship` son operaciones distintas e independientes; la segunda, si llega a ocurrir, sigue su propio flujo de autorización/alta, ajeno a Agenda.

### Administrador

Puede crear citas, crear y modificar disponibilidades para brindar soporte operativo, y realizar las acciones administrativas de agenda autorizadas dentro de su ámbito.

Toda operación administrativa requiere que la clínica pertenezca al ámbito autorizado del administrador **y** que exista una relación `DoctorClinic` válida entre el médico y el consultorio involucrados. Ninguna de las dos condiciones sustituye a la otra.

La autorización debe validarse en servidor. La interfaz no es una barrera suficiente.

## 5. Disponibilidad

### 5.1 Modelo

La disponibilidad se define **por fecha concreta**. No existen en Fase 2 reglas semanales recurrentes ni `AvailabilityException`.

Ejemplos válidos:

```text
15/09/2026 09:00–13:00
18/09/2026 10:00–14:00
23/09/2026 16:00–20:00
```

El médico puede crear y modificar sus disponibilidades. El administrador también puede crearlas y modificarlas para brindar soporte al médico.

### 5.2 Alcance de la disponibilidad

La disponibilidad pertenece a la combinación:

```text
Doctor + Clinic + Fecha
```

No se permiten disponibilidades solapadas dentro de una misma combinación médico + consultorio + fecha.

Además, **un médico no puede tener dos disponibilidades activas que se solapen temporalmente, aunque correspondan a consultorios distintos** (decisión de cierre, 2026-09-09). El médico no puede estar disponible simultáneamente en dos lugares.

Ejemplo inválido:

```text
Consultorio 1 → 09:00–14:00
Consultorio 2 → 11:00–14:00
```

Ejemplo válido:

```text
Consultorio 1 → 09:00–14:00
Consultorio 2 → 16:00–19:00
```

### 5.3 Duración de las citas

La duración por defecto es de **60 minutos**.

La duración se configura para la combinación:

```text
Doctor + Clinic
```

Una cita ocupa simultáneamente al médico y al consultorio durante toda su duración.

### 5.4 Generación de slots

Los slots se generan desde la hora de inicio de la disponibilidad y avanzan con la duración configurada.

Ejemplo:

```text
Disponibilidad: 09:00–13:00
Duración: 60 min

09:00–10:00
10:00–11:00
11:00–12:00
12:00–13:00
```

Los inicios de slot deben estar alineados a la granularidad configurada y no se permiten inicios arbitrarios como `12:35` o `13:25`.

Una cita completa debe quedar contenida dentro de la disponibilidad efectiva.

### 5.5 Disponibilidad parcialmente ocupada

Una disponibilidad permanece vigente aunque algunos slots estén ocupados.

Ejemplo:

```text
09:00–13:00

09:00 → ocupado
10:00 → disponible
11:00 → ocupado
12:00 → disponible
```

### 5.6 Modificación de disponibilidad con citas existentes

No se permite eliminar o modificar una disponibilidad de manera que invalide citas existentes.

El sistema no cancela automáticamente esas citas. El médico debe conciliar con los pacientes y utilizar la reprogramación para resolver conflictos antes de modificar la disponibilidad de forma incompatible.

### 5.7 Citas simultáneas

No puede existir una cita simultánea que ocupe al mismo médico o al mismo consultorio.

Por lo tanto, un médico no puede atender simultáneamente en dos consultorios y un consultorio no puede albergar simultáneamente dos citas.

### 5.8 Consultorio

Toda cita requiere un consultorio.

El médico debe disponer de una relación válida con el consultorio para utilizarlo en agenda.

### 5.9 Zona horaria

La agenda utiliza la zona horaria del **`Clinic`** (decisión de cierre, 2026-09-09). La fecha/hora de negocio de una disponibilidad o de una cita pertenece al consultorio, no al usuario que consulta ni al servidor. Las comparaciones de pasado/futuro, expiración de hold y ventanas temporales de reserva se resuelven usando esa zona horaria.

La desactivación de un consultorio impide nuevas reservas en ese consultorio, pero no cancela automáticamente las citas futuras existentes.

## 6. Reserva directa de citas

### 6.1 Regla general

No existe flujo de solicitud ni confirmación posterior.

Una cita se crea directamente cuando la operación de reserva concluye correctamente.

Pueden crear una cita:

- paciente;
- responsable con relación `ACTIVE`;
- médico (con acceso legítimo al paciente — §4; no requiere `DoctorPatientRelationship` previa);
- administrador autorizado.

Todas las citas creadas directamente quedan en estado `SCHEDULED`.

**Regla de primera cita por médico (decisión de cierre, 2026-09-09):** un médico puede crear la primera cita de un paciente sin que exista todavía una `DoctorPatientRelationship` activa entre ambos. Crear la cita no crea, activa ni modifica esa relación — son operaciones independientes. Si más adelante se necesita una `DoctorPatientRelationship`, debe establecerse mediante su propio flujo de autorización/alta, nunca como efecto secundario de Agenda.

### 6.2 Restricciones para crear una cita

La fecha/hora elegida debe:

1. pertenecer a una disponibilidad válida del médico + consultorio;
2. tener una duración completamente contenida en esa disponibilidad;
3. no estar ocupada por otra cita incompatible;
4. no estar protegida por un hold activo incompatible;
5. cumplir la ventana temporal de reserva definida abajo.

### 6.3 Ventana temporal de reserva

Se permiten citas con una anticipación máxima de **6 meses** respecto del momento de reserva.

No existe una anticipación mínima para citas futuras.

También se permite reservar un slot que ya haya iniciado, siempre que haya transcurrido **como máximo 30 minutos desde el inicio del slot**.

Ejemplo:

```text
Slot: 14:00–15:00

14:00 → puede reservarse
14:20 → puede reservarse
14:30 → puede reservarse
14:31 → ya no puede reservarse ese slot
```

No se permite reservar un slot cuando hayan transcurrido más de 30 minutos desde su inicio.

La creación definitiva de la cita siempre debe validar nuevamente disponibilidad y vigencia temporal dentro de la transacción que confirma la reserva.

## 7. Hold temporal

### 7.1 Propósito

El hold es un mecanismo técnico para proteger un slot mientras el usuario completa la operación de reserva. No es un estado de aprobación de una cita.

### 7.2 Creación

El hold se crea cuando un usuario autorizado selecciona un slot disponible e inicia la reserva.

No se crean holds simplemente por visualizar la agenda.

### 7.3 Duración

Cada hold dura **15 minutos** como máximo.

No puede renovarse ni extenderse.

### 7.4 Alcance

Un hold protege simultáneamente:

```text
Doctor + Clinic + Slot
```

Mientras el hold esté activo, el slot no puede ser tomado por otro usuario, incluyendo al propio médico o administrador.

### 7.5 Un hold activo por usuario

Un usuario sólo puede mantener un hold activo simultáneamente.

### 7.6 Cambio de horario durante un hold

No se permite cambiar de horario mientras exista un hold activo.

Para seleccionar otro horario, el usuario debe:

1. liberar el hold actual;
2. seleccionar el nuevo slot;
3. crear un nuevo hold de 15 minutos.

No existe transferencia automática del hold entre slots.

### 7.7 Liberación voluntaria

El usuario puede liberar voluntariamente su hold antes de que expire.

### 7.8 Expiración

Cuando transcurren 15 minutos sin que se haya creado la cita, el hold expira y deja de bloquear el slot.

Los holds expirados se conservan como historial técnico.

### 7.9 Consumo

Cuando la cita se crea correctamente, el hold se marca como consumido y deja de bloquear el slot.

Los holds no deben permanecer activos después de una reserva exitosa.

### 7.10 Concurrencia

La reserva definitiva siempre debe volver a validar el slot dentro de una transacción.

El hold no sustituye la protección de concurrencia de la base de datos.

Si dos operaciones concurrentes intentan obtener el mismo slot, sólo una puede resultar exitosa. La otra debe recibir una respuesta de horario no disponible.

## 8. Estados de `Appointment`

Los estados finales de una cita son únicamente:

```text
SCHEDULED
IN_CONSULTATION
COMPLETED
CANCELLED
NO_SHOW
```

No se utilizarán como estados de `Appointment`:

```text
PENDING_CONFIRMATION
WAITING
RESCHEDULED
RELEASED
```

### 8.1 `SCHEDULED`

Estado inicial de toda cita creada correctamente.

Representa una cita reservada y vigente que todavía no ha iniciado la consulta.

La reprogramación no cambia este estado.

### 8.2 `IN_CONSULTATION`

Representa que el paciente está físicamente presente y el médico asignado inició la atención.

La única transición es:

```text
SCHEDULED → IN_CONSULTATION
```

Sólo puede ejecutarla el médico asignado.

### 8.3 `COMPLETED`

Representa que la atención correspondiente a la cita terminó.

Transición:

```text
IN_CONSULTATION → COMPLETED
```

Sólo puede ejecutarla el médico asignado.

El detalle clínico de la consulta pertenece a las fases clínicas correspondientes.

### 8.4 `CANCELLED`

Representa una cita cancelada antes de iniciar la consulta.

Es un estado terminal.

La cita no se elimina.

### 8.5 `NO_SHOW`

Representa una inasistencia real determinada por el médico asignado.

Es un estado terminal.

## 9. Inicio de consulta / Check-in

No existe check-in realizado por paciente, responsable o administrador.

La operación visible debe ser **“Iniciar consulta”**.

El flujo es:

```text
Paciente llega físicamente al consultorio
        ↓
Médico asignado verifica su presencia
        ↓
Médico selecciona “Iniciar consulta”
        ↓
SCHEDULED → IN_CONSULTATION
```

Sólo el médico asignado puede iniciar la consulta.

No existe un estado `WAITING` en `Appointment`.

El paso del tiempo por sí solo nunca inicia una consulta.

## 10. `NO_SHOW`

### 10.1 Definición

`NO_SHOW` significa que el paciente no se presentó físicamente a la cita y el médico asignado determinó que corresponde registrar la inasistencia.

### 10.2 Actor autorizado

Sólo el médico asignado puede marcar `NO_SHOW`.

### 10.3 Momento

Puede marcarse desde el **minuto 1 posterior a la hora programada**.

No existe una espera obligatoria de 15 minutos.

Ejemplo:

```text
Cita: 10:00

10:00 → inicia el horario
10:01 → el médico puede marcar NO_SHOW
```

### 10.4 Si el paciente llega antes de marcar `NO_SHOW`

Mientras la cita continúe en `SCHEDULED`, el médico puede iniciar la consulta normalmente, incluso después de la hora programada.

Por ejemplo:

```text
10:00 → cita
10:08 → paciente llega
10:09 → médico inicia consulta
```

Resultado:

```text
SCHEDULED → IN_CONSULTATION
```

### 10.5 Condición de estado

Sólo puede marcarse `NO_SHOW` cuando la cita esté en `SCHEDULED`.

No puede marcarse después de iniciar la consulta ni sobre una cita ya cancelada o cerrada.

### 10.6 Efecto

`NO_SHOW` es terminal.

No puede volver a:

```text
SCHEDULED
IN_CONSULTATION
COMPLETED
CANCELLED
```

Si el paciente requiere una nueva atención, debe crearse una nueva cita.

### 10.7 Persistencia

La cita no se elimina.

Debe conservar al menos:

```text
no_show_at
no_show_by
```

No se requiere motivo de `NO_SHOW` en Fase 2.

## 11. Cancelación

### 11.1 Actores

Pueden cancelar:

- paciente titular;
- responsable con relación `ACTIVE`;
- médico correspondiente;
- administrador autorizado.

### 11.2 Momento

Una cita futura puede cancelarse en cualquier momento antes de iniciar su horario programado.

Una cita ya iniciada no puede cancelarse.

### 11.3 Motivo y trazabilidad

La cancelación requiere registrar:

```text
cancelled_at
cancelled_by
cancellation_reason
```

Motivos iniciales:

```text
PATIENT_REQUEST
RESPONSIBLE_REQUEST
DOCTOR_REQUEST
CLINIC_REQUEST
OTHER
```

### 11.4 Resultado

La cancelación produce:

```text
SCHEDULED → CANCELLED
```

`CANCELLED` es terminal.

Una cita ya cancelada no puede volver a cancelarse, iniciar consulta ni reprogramarse.

El horario se libera inmediatamente después de la cancelación.

La cita permanece almacenada para historial y estadísticas.

## 12. Reprogramación

### 12.1 Actores

Pueden reprogramar:

- paciente titular;
- responsable con relación `ACTIVE`;
- médico correspondiente;
- administrador autorizado.

### 12.2 Naturaleza de la operación

La reprogramación conserva el mismo `Appointment` lógico. No crea una nueva cita por cada cambio.

La cita mantiene estado `SCHEDULED`.

La reprogramación se registra mediante historial.

### 12.3 Historial

Cada reprogramación debe conservar como mínimo:

```text
fecha/hora anterior
fecha/hora nueva
quién realizó la reprogramación
cuándo se realizó
motivo
```

### 12.4 Motivo

El motivo de reprogramación es obligatorio.

Motivos iniciales:

```text
PATIENT_REQUEST
RESPONSIBLE_REQUEST
DOCTOR_REQUEST
CLINIC_REQUEST
OTHER
```

### 12.5 Qué puede cambiar

Una reprogramación puede cambiar:

- fecha;
- hora;
- consultorio.

El médico asignado no cambia mediante una reprogramación.

La duración de la cita no cambia mediante una reprogramación.

Si se requiere otro médico, debe crearse una nueva cita conforme a las reglas normales de reserva.

### 12.6 Validación del nuevo horario

El nuevo horario debe cumplir todas las reglas aplicables a una reserva nueva:

- disponibilidad válida;
- médico disponible;
- consultorio disponible;
- cita completamente contenida en la disponibilidad;
- ausencia de otra cita incompatible;
- ausencia de hold incompatible;
- límites temporales de reserva.

### 12.7 Momento

Una cita puede reprogramarse en cualquier momento antes de iniciar su horario programado.

Una cita ya iniciada no puede reprogramarse.

Una cita `CANCELLED`, `NO_SHOW` o `COMPLETED` no puede reprogramarse.

### 12.8 Reprogramaciones múltiples

Una misma cita puede reprogramarse múltiples veces mientras continúe en `SCHEDULED` y se cumplan las reglas anteriores.

No existe límite de cantidad de reprogramaciones en Fase 2.

### 12.9 Operación atómica

La liberación del horario anterior y la asignación del nuevo horario deben tratarse como una sola operación transaccional.

Si el nuevo horario no puede reservarse, la cita original debe permanecer intacta.

## 13. Finalización de consulta

Sólo el médico asignado puede pasar:

```text
IN_CONSULTATION → COMPLETED
```

No se permite finalizar una cita desde `SCHEDULED`.

No existe finalización automática por tiempo.

La información clínica detallada pertenece al dominio de gestión clínica de fases posteriores.

## 14. Reglas temporales y ausencia de automatismos

La aplicación no debe modificar automáticamente el estado de una cita sólo porque transcurra el tiempo.

No se deben implementar por esta razón:

- tareas programadas;
- cron jobs;
- signals de cambio automático de estado;
- workers periódicos para convertir citas a `NO_SHOW`;
- transición automática a `IN_CONSULTATION`.

El tiempo sólo habilita o invalida determinadas operaciones. La transición de estado requiere la acción humana autorizada definida para cada operación.

## 15. Matriz de transiciones

| Estado actual | Acción | Estado resultante | Actor autorizado |
|---|---|---|---|
| `SCHEDULED` | Iniciar consulta | `IN_CONSULTATION` | Médico asignado |
| `SCHEDULED` | Cancelar | `CANCELLED` | Paciente / Responsable ACTIVE / Médico / Admin |
| `SCHEDULED` | Marcar inasistencia | `NO_SHOW` | Médico asignado |
| `SCHEDULED` | Reprogramar | `SCHEDULED` | Paciente / Responsable ACTIVE / Médico / Admin |
| `IN_CONSULTATION` | Finalizar consulta | `COMPLETED` | Médico asignado |
| `COMPLETED` | Operación normal de agenda | — | No permitida |
| `CANCELLED` | Operación normal de agenda | — | No permitida |
| `NO_SHOW` | Operación normal de agenda | — | No permitida |

## 16. Trazabilidad mínima

Las operaciones sensibles de Agenda deben conservar quién y cuándo las realizó.

Como mínimo deben existir datos equivalentes para:

- creación de cita;
- cancelación;
- reprogramación;
- inicio de consulta;
- finalización;
- `NO_SHOW`;
- creación, liberación, expiración y consumo de holds.

## 17. Modelo conceptual

El dominio de Fase 2 debe evolucionar hacia una estructura equivalente a:

```text
Doctor + Clinic
       │
       └── Availability (por fecha)
               │
               └── Slots derivados
                       │
                       ├── Hold temporal
                       │
                       └── Appointment
                              │
             ┌────────────────┼─────────────────┐
             │                │                 │
          SCHEDULED    IN_CONSULTATION      terminal
             │                │             /    |    \
             │                │       CANCELLED NO_SHOW COMPLETED
             │                │
             └── Reprogramación
                    │
                    └── Historial
```

## 18. Reglas de autorización

Fase 2 debe consultar las relaciones existentes en Fase 1.

### Responsable

La autorización para gestionar una cita de un paciente depende exclusivamente de:

```text
ResponsiblePatientRelationship.status == ACTIVE
```

No debe utilizarse `Patient.regime` como sustituto de esta consulta.

### Médico

Las operaciones sobre agenda propia requieren la relación médico-consultorio válida (`DoctorClinic`) cuando la operación involucra un consultorio — incluida la creación de disponibilidad y de citas.

**Crear una cita no exige `DoctorPatientRelationship` activa con el paciente** (decisión de cierre, 2026-09-09; ver §4 y §6.1). El "acceso legítimo" al paciente que exige la creación de la primera cita se resuelve enteramente mediante `DoctorClinic`: el médico debe operar dentro de una combinación `Doctor + Clinic` para la que tiene relación válida — el mismo control que ya aplica a cualquier otra operación de agenda del médico, sin ninguna condición adicional sobre el paciente. No existe una relación paralela de "acceso al paciente" distinta de `DoctorClinic`.

Las operaciones sobre una cita ya existente (cancelar, reprogramar, iniciar, finalizar, `NO_SHOW`) requieren ser el médico asignado cuando la política así lo establece.

### Administrador

Las capacidades administrativas se limitan al ámbito autorizado. La implementación no debe convertir el rol administrativo global en acceso irrestricto a todas las operaciones de dominio.

Toda operación administrativa exige, además del ámbito sobre la clínica, una relación `DoctorClinic` válida entre el médico y el consultorio involucrados (ver §4).

## 19. Experiencia de usuario mínima

La UI de Agenda debe reflejar directamente las políticas del dominio y no crear estados que no existan en el modelo.

### Médico

Debe poder:

- consultar su agenda;
- crear/modificar disponibilidades por fecha;
- crear citas;
- iniciar una consulta;
- finalizar una consulta;
- marcar `NO_SHOW`;
- cancelar y reprogramar según autorización.

### Paciente / Responsable

Debe poder:

- consultar disponibilidad válida;
- seleccionar un slot;
- crear una cita directa;
- cancelar o reprogramar las citas que legalmente gestionan.

Durante un hold activo, no debe ofrecerse cambiar directamente a otro slot. Primero debe liberarse el hold.

### Administrador

Debe poder brindar soporte operativo para crear disponibilidades y gestionar citas dentro de su ámbito autorizado.

## 20. Manejo de errores de dominio

Las operaciones deben devolver errores de negocio claros para casos como:

- slot no disponible;
- slot ocupado;
- slot bloqueado por hold;
- hold expirado;
- hold inexistente o ya consumido;
- límite de reserva excedido;
- intento de reservar un slot con más de 30 minutos desde su inicio;
- cita ya iniciada;
- cita ya cancelada;
- cita ya cerrada;
- actor no autorizado;
- médico o consultorio no disponibles;
- modificación de disponibilidad que invalidaría citas existentes;
- conflicto concurrente de reserva o reprogramación.

## 21. Integridad y concurrencia

La aplicación debe considerar PostgreSQL como autoridad final para las reglas de exclusión y concurrencia.

Las operaciones de reserva y reprogramación deben:

1. validar reglas de negocio;
2. entrar en una transacción apropiada;
3. proteger la operación contra carreras concurrentes;
4. confirmar la ocupación del recurso de forma atómica;
5. responder con un conflicto de disponibilidad si otra operación ganó la carrera.

No debe confiarse únicamente en la disponibilidad que mostró previamente la interfaz.

## 22. Fuera de alcance de Fase 2

No implementar en esta fase:

- CareRequest;
- conversión CareRequest → Appointment;
- historia clínica;
- diagnóstico;
- tratamiento;
- MedicalEncounter como dominio clínico completo;
- recetas;
- órdenes de estudios;
- documentos clínicos;
- notificaciones por email/SMS/WhatsApp;
- auditoría avanzada;
- pagos;
- facturación;
- videollamada;
- aplicación móvil nativa;
- penalizaciones por cancelaciones o inasistencias;
- bloqueo automático de pacientes por acumulación de `NO_SHOW`;
- confirmaciones manuales de citas.

## 23. Decisiones explícitamente congeladas

Estas decisiones son parte del contrato funcional de Fase 2 y no deben cambiarse silenciosamente durante la implementación:

1. Las disponibilidades son por **fecha concreta**, no recurrentes.
2. No existe `AvailabilityException` en Fase 2.
3. La duración por defecto de una cita es **60 minutos**.
4. La duración se configura por **médico + consultorio**.
5. Una cita bloquea médico y consultorio durante toda su duración.
6. Los slots parten del inicio de la disponibilidad y están alineados a la duración.
7. No existen inicios arbitrarios dentro del horario.
8. No se permiten disponibilidades solapadas para la misma combinación médico + consultorio + fecha.
9. Las citas se crean directamente; no existe confirmación posterior.
10. Paciente, responsable autorizado, médico y administrador autorizado pueden crear citas.
11. Una cita puede reservarse hasta **6 meses** hacia el futuro.
12. También puede reservarse un slot hasta **30 minutos después de su inicio**.
13. El hold dura **15 minutos**.
14. Un usuario sólo puede tener un hold activo.
15. No se puede cambiar de slot mientras exista un hold activo.
16. El hold puede liberarse voluntariamente.
17. El hold no puede renovarse.
18. El hold se conserva como historial cuando expira, se libera o se consume.
19. `RESCHEDULED` no es un estado de `Appointment`; es historial.
20. `WAITING` no es un estado de `Appointment`.
21. `RELEASED` no es un estado de `Appointment`.
22. `SCHEDULED`, `IN_CONSULTATION`, `COMPLETED`, `CANCELLED` y `NO_SHOW` son los únicos estados de `Appointment`.
23. Sólo el médico asignado inicia la consulta.
24. Sólo el médico asignado finaliza la consulta.
25. Sólo el médico asignado marca `NO_SHOW`.
26. `NO_SHOW` puede marcarse desde el minuto 1 posterior al inicio programado.
27. No existen transiciones automáticas por paso del tiempo.
28. Las cancelaciones y reprogramaciones conservan historial y no eliminan la cita.
29. La reprogramación mantiene el mismo médico y la misma duración.
30. La reprogramación puede cambiar el consultorio si el nuevo consultorio es válido y está disponible.
31. Un médico no puede tener dos disponibilidades activas que se solapen temporalmente, aunque correspondan a consultorios distintos (decisión de cierre, 2026-09-09).
32. La agenda utiliza la zona horaria del `Clinic` (decisión de cierre, 2026-09-09).
33. Toda operación administrativa requiere, además del ámbito sobre la clínica, una relación `DoctorClinic` válida entre el médico y el consultorio involucrados (decisión de cierre, 2026-09-09).
34. Un médico puede crear la primera cita de un paciente sin que exista una `DoctorPatientRelationship` activa previa, siempre que tenga acceso legítimo (`DoctorClinic` válida en la combinación de la cita). Crear la cita no crea, activa ni modifica ninguna `DoctorPatientRelationship` ni ningún otro mecanismo de autorización de Fase 1 (decisión de cierre, 2026-09-09).

## 24. Criterios de aceptación de Fase 2

La fase se considerará funcionalmente completa cuando, como mínimo, se pueda demostrar mediante pruebas:

### Disponibilidad

- creación de disponibilidad por fecha;
- modificación válida;
- rechazo de solapamientos dentro de la misma combinación médico + consultorio + fecha;
- rechazo de solapamientos del mismo médico entre consultorios distintos;
- rechazo de modificación/eliminación que invalide citas existentes;
- generación correcta de slots;
- coexistencia de slots ocupados y disponibles;
- las validaciones temporales usan la zona horaria del `Clinic`.

### Reserva

- reserva directa por paciente;
- reserva directa por responsable con relación `ACTIVE`;
- reserva directa por médico;
- reserva directa por médico para un paciente sin `DoctorPatientRelationship` previa (primera cita) — éxito, y la relación no queda creada ni modificada como efecto de la operación;
- reserva directa por administrador autorizado (con `DoctorClinic` válida para el médico y consultorio involucrados);
- rechazo de responsable sin relación `ACTIVE`;
- rechazo de médico sin `DoctorClinic` válida en la combinación de la cita;
- rechazo de administrador fuera de su ámbito o sin `DoctorClinic` válida para el médico/consultorio;
- rechazo de slot ocupado;
- rechazo de slot con hold incompatible;
- aceptación dentro de los 30 minutos posteriores al inicio del slot;
- rechazo después de los 30 minutos;
- rechazo de reservas que excedan 6 meses;
- prevención de doble reserva concurrente.

### Hold

- creación;
- expiración a los 15 minutos;
- liberación voluntaria;
- un solo hold activo por usuario;
- rechazo de cambio de horario durante hold;
- consumo al crear la cita;
- conservación de historial.

### Cancelación

- permisos correctos por actor;
- cancelación antes del inicio;
- rechazo después del inicio;
- motivo obligatorio;
- liberación inmediata del horario;
- conservación de la cita;
- imposibilidad de cancelar nuevamente una cita cancelada.

### Reprogramación

- permisos correctos;
- cambio de fecha/hora;
- cambio de consultorio cuando sea válido;
- mantenimiento del médico;
- mantenimiento de duración;
- historial completo;
- múltiples reprogramaciones;
- rechazo de cita iniciada o terminal;
- atomicidad ante conflicto.

### Inicio y `NO_SHOW`

- sólo el médico asignado puede iniciar;
- `SCHEDULED → IN_CONSULTATION`;
- sólo el médico asignado puede finalizar;
- `IN_CONSULTATION → COMPLETED`;
- `NO_SHOW` desde minuto 1;
- `NO_SHOW` sólo desde `SCHEDULED`;
- `NO_SHOW` terminal;
- ningún cambio automático de estado por tiempo.

## 25. Estrategia de implementación

La implementación debe comenzar por el dominio y las restricciones de base de datos, continuar con servicios transaccionales y autorización, y después incorporar vistas/UI.

Orden recomendado:

```text
Modelos y constraints
        ↓
Servicios de dominio
        ↓
Autorización
        ↓
Concurrencia / transacciones
        ↓
Pruebas de dominio
        ↓
Views / endpoints
        ↓
UI
        ↓
Pruebas de integración
```

No se debe empezar creando pantallas que definan implícitamente reglas de negocio que todavía no estén representadas en el dominio.

## 26. Definition of Done

Fase 2 no se considera terminada hasta que:

- todas las políticas de este documento estén implementadas;
- las restricciones críticas estén protegidas en servidor y base de datos cuando corresponda;
- existan pruebas para las reglas de negocio críticas y concurrencia;
- `python manage.py check` sea correcto;
- `python manage.py makemigrations --check` no detecte cambios pendientes;
- las migraciones sean reproducibles desde una base limpia;
- los fixtures de prueba cubran los escenarios principales de Agenda;
- no existan estados de `Appointment` contradictorios con esta especificación;
- la documentación técnica derivada sea coherente con este contrato;
- no se hayan incorporado funcionalidades de fases posteriores sin aprobación explícita.

## 27. Contrato Fase 2 → Fase 3

Fase 3 podrá consumir como entidades estables:

```text
Patient
Doctor
Clinic
Appointment
```

y utilizará el estado:

```text
IN_CONSULTATION
```

como frontera para la atención clínica.

La Agenda no debe absorber el dominio de `MedicalEncounter`, historia clínica o decisiones clínicas.

La existencia de una cita o su estado no debe interpretarse como diagnóstico, tratamiento o cualquier otra decisión médica.

## 28. Regla de mantenimiento de este documento

Este archivo es el contrato funcional rector de Fase 2.

Cualquier cambio a una política aquí establecida debe:

1. identificarse explícitamente;
2. evaluar su impacto en modelos, servicios, permisos, pruebas y UI;
3. actualizar esta especificación antes de implementar el cambio;
4. documentar mediante ADR únicamente cuando la decisión tenga impacto arquitectónico relevante.

No deben introducirse reglas de negocio nuevas silenciosamente dentro del código.

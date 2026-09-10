# Diseño de dominio — Agenda y `Appointment`

**Estado:** Diseño de dominio propuesto — previo a implementación

**Fase:** 2 — Agenda

**Fecha:** 2026-09-09

**Contrato funcional rector:** `docs/phases/phase-2-agenda.md`

## 1. Propósito

Este documento traduce las políticas funcionales aprobadas para Fase 2 a un modelo de dominio coherente, antes de implementar modelos Django, servicios o UI.

El objetivo es definir las entidades, responsabilidades, relaciones, invariantes y reglas de integridad de:

- disponibilidad;
- generación de slots;
- hold temporal;
- citas;
- historial de reprogramaciones;
- configuración de duración por `Doctor + Clinic`.

Este documento no introduce políticas nuevas. Cuando una decisión ya fue aprobada en `docs/phases/phase-2-agenda.md`, se considera obligatoria.

---

## 2. Principios de dominio

1. **La disponibilidad es una entidad de negocio concreta por fecha.** No existen reglas recurrentes ni `AvailabilityException` en Fase 2.
2. **Un slot no es una entidad persistente de negocio.** Es una representación derivada de una disponibilidad y su duración efectiva.
3. **`Appointment` es una entidad de negocio independiente.** Su existencia no depende de `CareRequest` ni representa por sí misma una consulta clínica.
4. **El médico y el consultorio son recursos simultáneamente reservables.** Una cita ocupa ambos durante toda su duración.
5. **La base de datos es la autoridad final ante concurrencia.** La UI y la capa de aplicación nunca pueden asumir que un slot sigue disponible sin validarlo dentro de la operación transaccional correspondiente.
6. **Los estados de `Appointment` representan estados reales del ciclo de atención, no acciones técnicas.**
7. **Los eventos históricos importantes no se modelan como estados cuando no representan una situación vigente.** En particular, la reprogramación se conserva mediante historial.
8. **La autorización se hereda de Fase 1.** Agenda no crea un segundo sistema de permisos para paciente, responsable, médico o administrador.
9. **No hay transiciones automáticas de `Appointment` por el paso del tiempo.**

---

## 3. Contexto del dominio

```text
User
 ├── puede actuar como Patient
 ├── puede actuar como Responsible
 ├── puede actuar como Doctor
 └── puede actuar como Administrator

Doctor ─────── DoctorClinic ─────── Clinic
                  │
                  │ duration_minutes
                  │
                  └────── Availability (por fecha)
                               │
                               └── slots derivados
                                      │
                                      ├── Hold
                                      │
                                      └── Appointment
                                               │
                                               └── RescheduleHistory
```

La autorización para cada actor se resuelve mediante las relaciones canónicas de Fase 1 (`DoctorPatientRelationship`, `ResponsiblePatientRelationship`, `DoctorClinic`) o, para el Administrador, su acceso funcional global (`user.is_superuser`, ADR-004 §8).

---

## 4. `DoctorClinic` como configuración operativa

La relación existente `DoctorClinic` es la unidad de configuración entre médico y consultorio.

### 4.1 Responsabilidad en Fase 2

Además de expresar que el médico puede trabajar en el consultorio, debe ser la asociación que determine la duración predeterminada de las citas para esa combinación.

Conceptualmente:

```text
DoctorClinic
- doctor
- clinic
- is_active
- appointment_duration_minutes
```

### 4.2 Reglas

- `appointment_duration_minutes` tiene valor inicial de **60 minutos**.
- El valor pertenece a la combinación `Doctor + Clinic`, no al paciente ni a la disponibilidad individual.
- Una cita toma una fotografía de esa duración al momento de crearse; cambiar posteriormente la configuración no altera citas existentes.
- Una disponibilidad nueva utiliza la duración vigente de su `DoctorClinic` al momento de ser creada.
- Si una cita existente se reprograma a otro consultorio del mismo médico, la nueva combinación debe ser compatible con la duración congelada de la cita. Si no lo es, la reprogramación debe rechazarse.

### 4.3 Integridad

- La relación `DoctorClinic` debe existir y estar activa para utilizarla para agenda.
- La misma pareja `Doctor + Clinic` continúa siendo única, de acuerdo con Fase 1.
- La desactivación de `DoctorClinic` impide nuevas operaciones que requieran utilizar esa combinación, sin modificar retroactivamente citas existentes.

---

## 5. Entidad `Availability`

`Availability` representa una ventana concreta en la que un médico ofrece atención en un consultorio determinado.

### 5.1 Propósito

Define una fecha, hora inicial y hora final concretas a partir de las cuales el sistema deriva los slots disponibles.

No es una regla recurrente.

### 5.2 Atributos conceptuales

| Campo | Requerido | Descripción |
|---|---|---|
| `doctor` | Sí | Médico que prestará la atención. |
| `clinic` | Sí | Consultorio donde se realizará la atención. |
| `date` | Sí | Fecha local del consultorio. |
| `start_time` | Sí | Hora local de inicio. |
| `end_time` | Sí | Hora local de fin. |
| `duration_minutes` | Sí | Duración efectiva para generar slots; se captura al crear la disponibilidad. |
| `is_active` | Sí | Baja lógica de la disponibilidad. |
| `created_at` | Sí | Registro de creación. |
| `updated_at` | Sí | Última modificación. |

### 5.3 Reglas

- La combinación `doctor + clinic + date + time range` debe ser válida.
- `start_time < end_time`.
- No se permiten disponibilidades solapadas para la misma combinación `Doctor + Clinic + Fecha`.
- **Un mismo médico no puede tener dos disponibilidades activas que se solapen temporalmente, aunque correspondan a consultorios distintos** (decisión de cierre, 2026-09-09) — el médico no puede estar disponible simultáneamente en dos lugares.
- Una disponibilidad puede permanecer activa aunque algunos slots estén ocupados.
- Una disponibilidad no necesita crear registros `Slot` persistentes.
- La duración efectiva queda congelada en la disponibilidad; un cambio posterior de la configuración `DoctorClinic` no reinterpreta disponibilidades existentes.
- La fecha y horas de la disponibilidad se interpretan en la zona horaria del `Clinic`.

### 5.4 Alta, modificación y baja lógica

- El médico puede crear y modificar sus disponibilidades.
- El administrador autorizado puede crear y modificar disponibilidades para brindar soporte operativo al médico.
- Una disponibilidad futura sin citas puede desactivarse.
- Una disponibilidad que ya tiene citas no puede modificarse ni desactivarse si el cambio pudiera invalidarlas.
- Las citas existentes no se cancelan automáticamente por una modificación de disponibilidad.
- Para modificar una ventana de forma incompatible con citas existentes, primero deben resolverse esas citas mediante reprogramación.

### 5.5 Validaciones temporales

- La disponibilidad puede representar fechas futuras que respeten la ventana máxima de reserva de 6 meses.
- No debe utilizarse una disponibilidad para crear una cita cuyo horario no cumpla las reglas temporales de reserva del contrato funcional.

---

## 6. Slots derivados

### 6.1 Naturaleza

Un slot es un intervalo derivado de una `Availability` activa y de `duration_minutes`.

No se persiste como entidad independiente.

### 6.2 Generación

Dada una disponibilidad:

```text
09:00–13:00
Duración: 60 min
```

se obtienen:

```text
09:00–10:00
10:00–11:00
11:00–12:00
12:00–13:00
```

La generación empieza exactamente en `start_time` y avanza por la duración efectiva.

No se permiten inicios arbitrarios.

### 6.3 Validez

Un slot es reservable sólo cuando:

- la disponibilidad está activa;
- el intervalo completo está dentro de la disponibilidad;
- el médico está disponible;
- el consultorio está disponible;
- no existe una cita incompatible;
- no existe un hold incompatible;
- la ventana temporal de reserva se cumple.

### 6.4 Reserva tardía dentro del slot

Un slot puede reservarse aunque ya haya comenzado, siempre que no hayan transcurrido más de 30 minutos desde su inicio.

Ejemplo:

```text
Slot 14:00–15:00

14:00 → ✅
14:20 → ✅
14:30 → ✅
14:31 → ❌
```

La cita creada en ese caso sigue siendo `SCHEDULED`; el médico debe utilizar `Iniciar consulta` para comenzar la atención.

---

## 7. Entidad `Hold`

`Hold` representa un bloqueo temporal de un slot mientras un usuario autorizado completa la operación de reserva.

### 7.1 Propósito

Es un mecanismo técnico de protección de concurrencia y no una etapa de confirmación de la cita.

### 7.2 Atributos conceptuales

| Campo | Requerido | Descripción |
|---|---|---|
| `user` | Sí | Usuario que posee el hold. |
| `doctor` | Sí | Médico del slot protegido. |
| `clinic` | Sí | Consultorio del slot protegido. |
| `availability` | Sí | Disponibilidad de origen. |
| `slot_start` | Sí | Inicio del slot protegido. |
| `slot_end` | Sí | Fin del slot protegido. |
| `status` | Sí | `ACTIVE`, `EXPIRED`, `RELEASED`, `CONSUMED`. |
| `created_at` | Sí | Inicio del hold. |
| `expires_at` | Sí | Vencimiento, 15 minutos después de la creación. |
| `released_at` | No | Momento de liberación voluntaria, si aplica. |
| `consumed_at` | No | Momento en que se convirtió en una cita, si aplica. |

### 7.3 Reglas

- Sólo un actor autorizado para crear citas puede crear un hold.
- El hold se crea al iniciar la reserva, no al visualizar la agenda.
- Su duración máxima es de 15 minutos.
- No puede renovarse ni extenderse.
- Un usuario sólo puede tener un hold `ACTIVE` simultáneamente.
- Mientras existe un hold activo, el usuario no puede cambiar de horario.
- Para elegir otro slot debe liberar el hold actual y crear uno nuevo.
- El hold bloquea simultáneamente médico + consultorio + slot.
- Un hold activo impide que cualquier otro usuario, incluido el médico o administrador, reserve ese horario.
- El usuario puede liberar voluntariamente el hold.
- Si expira, deja de bloquear el slot.
- Si la cita se crea exitosamente, el hold pasa a `CONSUMED` y deja de bloquear.
- Los holds históricos no se eliminan automáticamente.

### 7.4 Integridad y concurrencia

La existencia de un `ACTIVE Hold` no reemplaza la protección transaccional de la reserva.

La creación final de una cita debe volver a comprobar, dentro de una transacción:

1. vigencia del hold;
2. disponibilidad del slot;
3. ausencia de conflicto con otras citas;
4. ausencia de conflicto con otros holds;
5. vigencia de permisos.

---

## 8. Entidad `Appointment`

`Appointment` representa una reserva de atención médica programada.

No representa la consulta clínica completa ni reemplaza a `MedicalEncounter` de fases posteriores.

### 8.1 Atributos conceptuales

| Campo | Requerido | Descripción |
|---|---|---|
| `patient` | Sí | Paciente que recibirá la atención. |
| `doctor` | Sí | Médico asignado. No cambia mediante reprogramación. |
| `clinic` | Sí | Consultorio donde se realizará la atención. |
| `scheduled_date` | Sí | Fecha local del consultorio. |
| `scheduled_start` | Sí | Hora local del inicio. |
| `scheduled_end` | Sí | Hora local del fin. |
| `duration_minutes` | Sí | Duración congelada al crear la cita. |
| `status` | Sí | Uno de los cinco estados definidos. |
| `created_by` | Sí | `User` que ejecutó la creación. |
| `created_at` | Sí | Momento de creación. |
| `updated_at` | Sí | Última modificación. |
| `cancelled_at` | No | Momento de cancelación. |
| `cancelled_by` | No | Usuario que canceló. |
| `cancellation_reason` | No | Motivo obligatorio cuando la cita está cancelada. |
| `no_show_at` | No | Momento de marcado como `NO_SHOW`. |
| `no_show_by` | No | Usuario/médico que marcó la ausencia. |
| `started_at` | No | Momento real en que el médico inició la consulta. |
| `completed_at` | No | Momento en que el médico marcó la cita como atendida. |

Los nombres exactos de campos podrán ajustarse durante el diseño técnico sin cambiar las reglas de negocio.

### 8.2 Origen de creación

Toda cita registra `created_by = User`.

El actor que crea puede ser:

- paciente;
- responsable con relación `ACTIVE`;
- médico;
- administrador autorizado.

El sistema no necesita una FK polimórfica para representar al creador.

La relación funcional que autorizó la acción se valida en servidor y no se sustituye por `created_by`.

**Regla de primera cita por médico (decisión de cierre, 2026-09-09):** un médico puede crear la primera cita de un paciente sin que exista todavía una `DoctorPatientRelationship` activa entre ambos, siempre que tenga acceso legítimo — es decir, que opere dentro de una combinación `Doctor + Clinic` para la que tiene relación `DoctorClinic` válida (§4). No se exige ninguna condición adicional sobre el paciente para esa primera cita.

`crear Appointment` y `crear DoctorPatientRelationship` son operaciones independientes: la creación de la cita **no crea, activa ni modifica** ninguna `DoctorPatientRelationship`, ni ningún otro mecanismo de autorización de Fase 1. Si la relación médico-paciente llega a establecerse, ocurre mediante su propio flujo, ajeno a Agenda.

### 8.3 Reglas de identidad de la cita

- `patient` es obligatorio.
- `doctor` es obligatorio.
- `clinic` es obligatorio.
- La combinación médico + consultorio debe ser válida en `DoctorClinic` al momento de la reserva.
- La duración queda congelada al crear la cita.
- La zona horaria de la fecha/hora pertenece al `Clinic`.
- Una cita no se crea mediante `CareRequest` en Fase 2.

---

## 9. Estados de `Appointment`

Los únicos estados persistentes de `Appointment` son:

```text
SCHEDULED
IN_CONSULTATION
COMPLETED
CANCELLED
NO_SHOW
```

No son estados de `Appointment`:

```text
PENDING_CONFIRMATION
WAITING
RESCHEDULED
RELEASED
```

### 9.1 `SCHEDULED`

Estado inicial de toda cita creada correctamente.

Representa una cita reservada y vigente que todavía no ha iniciado la consulta.

### 9.2 `IN_CONSULTATION`

Representa que el paciente está físicamente presente y el médico asignado inició la atención.

Única transición:

```text
SCHEDULED → IN_CONSULTATION
```

Actor:

```text
médico asignado
```

### 9.3 `COMPLETED`

Representa que la atención correspondiente a la cita terminó.

Transición:

```text
IN_CONSULTATION → COMPLETED
```

Actor:

```text
médico asignado
```

### 9.4 `CANCELLED`

Representa una cita cancelada antes de iniciar la consulta.

Es terminal y la cita permanece almacenada.

### 9.5 `NO_SHOW`

Representa una inasistencia determinada por el médico asignado.

Transición:

```text
SCHEDULED → NO_SHOW
```

Puede realizarse desde el minuto 1 posterior a la hora programada.

Es terminal y no requiere motivo adicional.

No existe transición automática a `NO_SHOW`.

---

## 10. Máquina de estados

```text
                         ┌──────────────┐
                         │              │
                         ↓              │
SCHEDULED ───────────→ CANCELLED       │
    │                                    │
    ├────────────────→ NO_SHOW           │
    │                                    │
    ↓                                    │
IN_CONSULTATION                           │
    │                                    │
    ↓                                    │
COMPLETED                                │
```

La reprogramación no cambia el estado:

```text
SCHEDULED
   │
   └── reprogramar
          ↓
      SCHEDULED
```

No existen transiciones automáticas por reloj.

---

## 11. Reprogramación e historial

La reprogramación mantiene el mismo `Appointment` lógico.

No crea una segunda cita para representar el cambio.

### 11.1 Historial conceptual

Se recomienda una entidad independiente:

```text
AppointmentRescheduleHistory
```

con información como:

| Campo | Requerido | Descripción |
|---|---|---|
| `appointment` | Sí | Cita afectada. |
| `old_clinic` | Sí | Consultorio anterior. |
| `old_date` | Sí | Fecha anterior. |
| `old_start` | Sí | Inicio anterior. |
| `old_end` | Sí | Fin anterior. |
| `new_clinic` | Sí | Nuevo consultorio. |
| `new_date` | Sí | Nueva fecha. |
| `new_start` | Sí | Nuevo inicio. |
| `new_end` | Sí | Nuevo fin. |
| `rescheduled_by` | Sí | `User` que ejecutó el cambio. |
| `rescheduled_at` | Sí | Momento del cambio. |
| `reason` | Sí | Motivo de reprogramación. |

Los nombres exactos pueden ajustarse técnicamente.

### 11.2 Reglas

- Sólo se reprograman citas que aún no han iniciado y no están en estado terminal.
- El médico no puede cambiar mediante reprogramación.
- El consultorio sí puede cambiar, si la nueva combinación es válida y compatible con la duración congelada.
- La fecha/hora nueva debe cumplir las reglas de disponibilidad, ocupación, hold y ventana temporal.
- La operación es atómica.
- Si el nuevo horario no puede adquirirse, la cita conserva completamente su horario anterior.
- Puede haber múltiples reprogramaciones.
- No existe límite de cantidad de reprogramaciones en Fase 2.
- Una cita reprogramada continúa en `SCHEDULED`.

---

## 12. Cancelación

Las reglas de cancelación se aplican sobre una cita `SCHEDULED`.

### 12.1 Actor

Pueden cancelar:

- paciente titular;
- responsable con relación `ACTIVE`;
- médico correspondiente;
- administrador autorizado.

### 12.2 Persistencia histórica

La cita no se elimina.

Se conservan:

```text
cancelled_at
cancelled_by
cancellation_reason
```

El motivo es obligatorio.

### 12.3 Efectos

- La cancelación es irreversible.
- Una cita ya cancelada no puede volver a cancelarse.
- No puede cancelarse una cita cuyo horario ya inició.
- El horario queda inmediatamente disponible para una nueva reserva.

---

## 13. Inicio y finalización de consulta

### 13.1 Inicio

No existe un check-in realizado por paciente o responsable.

La operación de negocio es **Iniciar consulta**.

Condiciones:

- cita en `SCHEDULED`;
- médico ejecutor = médico asignado;
- el médico determina que el paciente está físicamente presente.

Resultado:

```text
SCHEDULED → IN_CONSULTATION
```

### 13.2 Finalización

Sólo el médico asignado puede finalizar la consulta:

```text
IN_CONSULTATION → COMPLETED
```

El dominio clínico de `MedicalEncounter` queda fuera de Fase 2.

---

## 14. `NO_SHOW`

### 14.1 Condiciones

Sólo el médico asignado puede marcar:

```text
SCHEDULED → NO_SHOW
```

A partir del minuto 1 posterior a la hora programada.

### 14.2 Sin transición automática

El paso del tiempo sólo hace que la acción pueda estar permitida. Nunca cambia el estado por sí mismo.

### 14.3 Terminalidad

Una cita `NO_SHOW` no puede:

- cancelarse;
- reprogramarse;
- iniciarse;
- volver a `SCHEDULED`.

Si el paciente necesita atención, debe crearse una nueva cita.

---

## 15. Reglas de concurrencia e integridad

Las reglas de dominio deben impedir dos citas incompatibles con el mismo recurso temporal.

### 15.1 Recursos exclusivos

Para cada intervalo de tiempo una cita ocupa:

```text
Doctor
Clinic
```

por lo que no pueden existir dos citas simultáneas que compartan cualquiera de esos recursos.

### 15.2 Reserva

El flujo de reserva debe proteger, dentro de una transacción:

```text
validar actor
    ↓
validar disponibilidad
    ↓
validar ventana temporal
    ↓
validar hold
    ↓
reservar intervalo
    ↓
crear Appointment
    ↓
consumir Hold
```

Si cualquier validación falla, no debe quedar una reserva parcial.

### 15.3 Reprogramación

La reprogramación debe ser atómica:

```text
validar cita actual
    ↓
validar nuevo horario
    ↓
proteger nuevo intervalo
    ↓
actualizar Appointment
    ↓
crear historial
```

Si el nuevo horario no está disponible, no se modifica la cita original.

---

## 16. Zona horaria

La zona horaria de agenda es la del `Clinic`.

La fecha/hora de `Availability` y `Appointment` representa el horario operativo del consultorio.

La implementación deberá evitar conversiones ambiguas alrededor de fechas y cambios de zona horaria.

La configuración concreta de la zona horaria del `Clinic` y la estrategia de almacenamiento UTC/local se formalizarán en el diseño técnico de persistencia y, si corresponde, en un ADR específico.

---

## 17. Reglas temporales de reserva

### 17.1 Anticipación máxima

Una cita puede reservarse como máximo **6 meses calendario** hacia el futuro.

### 17.2 Anticipación mínima

No existe una anticipación mínima para citas futuras.

### 17.3 Slot iniciado

Un slot puede reservarse hasta 30 minutos después de su inicio.

La cita sigue siendo `SCHEDULED` hasta que el médico la inicie.

### 17.4 Hora ya iniciada

Fuera de la ventana de 30 minutos no puede crearse una nueva cita sobre el slot.

---

## 18. Paciente, responsable y régimen

Agenda consume las reglas de autorización de Fase 1.

### Paciente

Puede crear y gestionar citas propias cuando la autorización correspondiente sea válida.

### Responsable

Sólo puede crear o gestionar citas de pacientes con:

```text
ResponsiblePatientRelationship.status == ACTIVE
```

### Médico

Puede crear una cita para cualquier paciente al que tenga acceso legítimo — esto es, dentro de una combinación `Doctor + Clinic` con `DoctorClinic` válida — **sin que se exija `DoctorPatientRelationship` activa previa** (§8.2). Esa relación no es un requisito de autorización para Agenda y crear la cita no la crea, activa ni modifica.

### Administrador

Tiene acceso funcional global (ADR-004 §8) — sin restricción territorial por clínica. Toda operación administrativa exige únicamente que exista una relación `DoctorClinic` válida entre el médico y el consultorio involucrados (§4.3).

### Régimen adulto

Agenda no infiere el régimen a partir de edad.

Un paciente adulto sin `User` puede tener citas creadas y gestionadas por un actor autorizado; Fase 2 no obliga a crear una cuenta propia.

La transición de menor a adulto de Fase 1 desactiva la relación activa del responsable y Agenda respeta ese resultado.

---

## 19. Casos límite que el dominio debe soportar

### 19.1 Reserva tardía

```text
Slot 14:00–15:00
Reserva 14:20
```

Resultado:

```text
Appointment = SCHEDULED
```

El médico decide posteriormente cuándo iniciar la consulta.

### 19.2 Dos usuarios compiten por el mismo slot

Sólo uno obtiene la reserva. El segundo recibe disponibilidad no disponible.

### 19.3 Hold expira durante el guardado

La operación definitiva vuelve a validar el hold y el slot. Si ya no está protegido/disponible, la cita no se crea.

### 19.4 Cancelación y nueva reserva

Una cancelación deja libre inmediatamente el intervalo y una nueva reserva puede ocuparlo.

### 19.5 Cambio de configuración de duración

Modificar `DoctorClinic.appointment_duration_minutes` no modifica:

- citas existentes;
- disponibilidades existentes;
- historial de reprogramaciones.

### 19.6 Reprogramación a otro consultorio incompatible

Se rechaza si la duración congelada de la cita no puede ser atendida íntegramente por la nueva combinación `Doctor + Clinic`.

---

## 20. Invariantes principales

Estas invariantes deberán quedar protegidas por modelo, constraints, servicios transaccionales y/o consultas con bloqueo donde corresponda:

1. Toda `Appointment` tiene paciente, médico y consultorio.
2. Toda `Appointment` tiene exactamente uno de los cinco estados válidos.
3. `Appointment.duration_minutes` es positivo y representa la duración congelada.
4. `scheduled_end` debe corresponder a `scheduled_start + duration_minutes`.
5. La cita debe quedar contenida en la disponibilidad que la originó.
6. El médico y el consultorio de la cita deben ser compatibles con `DoctorClinic`.
7. No pueden existir citas simultáneas incompatibles para el mismo médico.
8. No pueden existir citas simultáneas incompatibles para el mismo consultorio.
9. No puede existir más de un hold `ACTIVE` por usuario.
10. Un hold `ACTIVE` no puede tener `expires_at` en el pasado.
11. Un hold no puede renovarse.
12. Una cita `CANCELLED`, `NO_SHOW` o `COMPLETED` no puede modificarse mediante operaciones normales de agenda.
13. Sólo el médico asignado puede ejecutar `SCHEDULED → IN_CONSULTATION`.
14. Sólo el médico asignado puede ejecutar `IN_CONSULTATION → COMPLETED`.
15. Sólo el médico asignado puede ejecutar `SCHEDULED → NO_SHOW`.
16. Una cita ya iniciada no puede cancelarse ni reprogramarse.
17. Una cita cancelada no puede volver a cancelarse ni reactivarse.
18. La reprogramación no cambia el médico asignado.
19. La reprogramación no cambia la duración congelada.
20. Toda reprogramación conserva historial.
21. No existe transición automática de estado por tiempo.
22. Un médico no puede tener dos disponibilidades activas que se solapen temporalmente, aunque correspondan a consultorios distintos.
23. Toda operación administrativa exige `DoctorClinic` válida entre el médico y el consultorio involucrados; el administrador tiene acceso funcional global (ADR-004 §8), sin restricción territorial por clínica.
24. Crear un `Appointment` con un médico que no tiene `DoctorPatientRelationship` previa con el paciente es válido y no crea, activa ni modifica dicha relación.

---

## 21. Fuera del dominio de este documento

No se diseñan aquí:

- `CareRequest`;
- `MedicalEncounter`;
- historia clínica;
- recetas;
- documentos clínicos;
- notificaciones;
- auditoría avanzada;
- pagos;
- penalizaciones por cancelaciones o `NO_SHOW`;
- lista de espera;
- sala de espera;
- reglas recurrentes de disponibilidad;
- excepciones de disponibilidad.

---

## 22. Decisiones que deben preservarse durante la implementación

La implementación no debe reintroducir:

```text
PENDING_CONFIRMATION
WAITING
RESCHEDULED como estado
RELEASED como estado de Appointment
AvailabilityRule recurrente
AvailabilityException
check-in del paciente/responsable
confirmación posterior de la cita
transiciones automáticas por tiempo
```

Tampoco debe crear una entidad persistente `Slot` salvo que un diseño técnico posterior justifique formalmente el cambio y actualice este contrato.

---

## 23. Siguiente documento de diseño

Con este modelo de dominio aprobado, el siguiente diseño técnico recomendado es:

```text
docs/design/availability-rules.md
```

adaptado al modelo de disponibilidades **por fecha concreta**. Debe definir con precisión las reglas de creación, modificación, baja lógica, generación de slots y validaciones temporales antes de implementar los modelos Django.

# Diseño de disponibilidad de Agenda — Fase 2

## 1. Propósito

Este documento define el comportamiento funcional y las reglas de dominio de las disponibilidades de agenda en TeCuidoApp.

La disponibilidad representa los periodos concretos en los que un médico ofrece atención en un consultorio determinado. A partir de una disponibilidad se calculan los slots que pueden ser reservados.

Este documento deriva sus reglas de `docs/phases/phase-2-agenda.md` y debe considerarse contrato de diseño para la implementación de Agenda.

---

## 2. Principio general

La disponibilidad de Agenda es **por fecha concreta**.

No se utilizarán en Fase 2:

- reglas recurrentes semanales;
- reglas de disponibilidad indefinidas;
- `AvailabilityException`;
- excepciones sobre reglas recurrentes.

El médico define directamente las fechas y horarios en los que desea atender.

Ejemplos válidos:

```text
15/09/2026 09:00–13:00
18/09/2026 10:00–14:00
23/09/2026 16:00–20:00
```

---

## 3. Unidad de disponibilidad

Una disponibilidad pertenece a una combinación concreta:

```text
Doctor + Clinic + Date
```

y contiene como mínimo:

```text
doctor
clinic
date
start_time
end_time
duration
is_active
```

La disponibilidad debe representar un intervalo continuo.

Reglas:

- `start_time` debe ser anterior a `end_time`.
- La duración debe ser positiva.
- La fecha y horas se interpretan en la zona horaria del `Clinic`.
- La disponibilidad debe corresponder a una relación válida entre `Doctor` y `Clinic`.

---

## 4. Configuración de duración

La duración de las citas se configura en la combinación:

```text
Doctor + Clinic
```

El valor inicial es:

```text
60 minutos
```

La duración configurada se utiliza para generar los slots de nuevas disponibilidades.

### Duración congelada

Cuando se crea una disponibilidad, la duración efectiva debe quedar congelada en dicha disponibilidad.

Cambiar posteriormente la duración configurada para `Doctor + Clinic`:

- no modifica disponibilidades existentes;
- no modifica slots ya derivados de esas disponibilidades;
- no modifica la duración de citas existentes.

El cambio aplica únicamente a nuevas disponibilidades creadas después del cambio.

---

## 5. Zona horaria

La fecha y hora de una disponibilidad se interpretan en la zona horaria del consultorio (`Clinic`).

El `Clinic` es la referencia temporal del negocio para Agenda.

No se debe utilizar la zona horaria del usuario como fuente de verdad para determinar si una disponibilidad es válida o si un slot ya comenzó.

Las conversiones para presentación al usuario se realizarán sobre la hora de negocio correspondiente al consultorio.

---

## 6. Horizonte máximo

Las nuevas disponibilidades y reservas no pueden superar una anticipación de **6 meses calendario** respecto de la fecha/hora actual.

Se interpreta como seis meses calendario, no como un número fijo de días.

Ejemplo conceptual:

```text
09/09/2026 → hasta 09/03/2027
```

La validación debe utilizar la zona horaria del `Clinic` correspondiente.

---

## 7. Creación de disponibilidades

Pueden crear una disponibilidad:

- el médico propietario de la disponibilidad;
- un administrador autorizado para la clínica correspondiente.

### Médico

El médico puede crear disponibilidad únicamente para combinaciones `Doctor + Clinic` que le correspondan.

### Administrador

El administrador puede crear disponibilidad únicamente:

1. dentro de las clínicas sobre las que tiene autorización administrativa; y
2. para médicos que tengan una relación `DoctorClinic` válida con el consultorio.

No se debe permitir que un administrador cree disponibilidad para un médico que no esté asociado al consultorio mediante `DoctorClinic`.

---

## 8. Fechas de nuevas disponibilidades

Una nueva disponibilidad sólo puede comenzar en una fecha/hora cuyo inicio todavía no haya pasado.

No se permite crear retrospectivamente una disponibilidad cuyo inicio ya ocurrió.

Ejemplo:

```text
Actual: 09/09/2026 10:15

09/09/2026 11:00–13:00  → válido
09/09/2026 09:00–13:00  → inválido
```

Una disponibilidad ya existente no se elimina ni se modifica por el mero hecho de que su inicio haya ocurrido.

---

## 9. Disponibilidades ya iniciadas

Una disponibilidad puede permanecer activa aunque su intervalo ya haya comenzado.

Esto permite reservar slots que ya comenzaron, de acuerdo con la política general de Agenda.

Ejemplo:

```text
Disponibilidad: 14:00–18:00

Actual: 14:20
```

La disponibilidad sigue siendo válida y puede contener slots reservables, siempre respetando las reglas de reserva:

- sólo se puede reservar un slot cuyo inicio no tenga más de 30 minutos de haber ocurrido;
- una vez superados esos 30 minutos, el slot ya no puede reservarse.

La disponibilidad no se modifica automáticamente por el paso del tiempo.

---

## 10. No solapamiento del médico

Un mismo médico **no puede tener disponibilidades temporalmente superpuestas**, aunque correspondan a consultorios diferentes.

Ejemplo inválido:

```text
Consultorio 1
09/09/2026 09:00–14:00

Consultorio 2
09/09/2026 11:00–14:00
```

El médico estaría disponible simultáneamente en dos lugares.

Ejemplo válido:

```text
Consultorio 1
09/09/2026 09:00–14:00

Consultorio 2
09/09/2026 16:00–19:00
```

La regla aplica a cualquier disponibilidad activa del médico.

La ausencia de solapamiento debe considerarse una invariante del dominio y validarse de manera segura ante concurrencia.

---

## 11. No solapamiento dentro de Doctor + Clinic

Dentro de una misma combinación `Doctor + Clinic` tampoco pueden existir dos disponibilidades activas que se solapen temporalmente.

Ejemplo inválido:

```text
09:00–13:00
12:00–15:00
```

Ejemplo válido:

```text
09:00–13:00
14:00–18:00
```

Las disponibilidades consecutivas son válidas cuando una termina exactamente cuando comienza la siguiente.

---

## 12. Slots derivados

Los slots **no son una entidad de negocio persistida**.

Se derivan de:

```text
Availability.start_time
Availability.end_time
Availability.duration
```

No debe existir una tabla `Slot` como fuente primaria del calendario.

Ejemplo:

```text
Disponibilidad:
09:00–13:00

Duración:
60 minutos
```

Genera:

```text
09:00–10:00
10:00–11:00
11:00–12:00
12:00–13:00
```

---

## 13. Alineación de slots

Los inicios de los slots deben estar alineados al inicio de la disponibilidad y avanzar según la duración configurada.

No se permiten inicios arbitrarios.

Ejemplo con duración de 60 minutos:

```text
09:00
10:00
11:00
12:00
```

No se generan:

```text
09:15
09:30
10:35
11:25
```

La granularidad de reserva queda determinada por la disponibilidad y su duración efectiva.

---

## 14. Contención de slots

Una cita sólo puede ocupar un slot cuya duración completa quede contenida dentro de la disponibilidad.

No se permite crear una cita que sobresalga del límite de la disponibilidad.

Ejemplo:

```text
Disponibilidad: 09:00–13:00
Duración: 60 min
```

Válido:

```text
09:00–10:00
10:00–11:00
11:00–12:00
12:00–13:00
```

Inválido:

```text
12:30–13:30
```

---

## 15. Disponibilidad parcialmente ocupada

Una disponibilidad puede quedar parcialmente ocupada.

La existencia de una cita no invalida el resto de la disponibilidad.

Ejemplo:

```text
Disponibilidad: 09:00–13:00

09:00–10:00 → ocupado
10:00–11:00 → disponible
11:00–12:00 → ocupado
12:00–13:00 → disponible
```

La disponibilidad continúa activa mientras siga siendo válida.

---

## 16. Reservas en slots ya iniciados

Un slot puede reservarse después de su hora de inicio hasta un máximo de 30 minutos.

Ejemplo:

```text
Slot: 14:00–15:00

14:00–14:30 → reservable
14:31 en adelante → no reservable
```

Cuando se realiza una reserva de este tipo:

```text
Appointment.status = SCHEDULED
```

El médico debe posteriormente utilizar la acción **Iniciar consulta** para pasar la cita a `IN_CONSULTATION`.

La reserva tardía no inicia automáticamente la consulta.

---

## 17. Disponibilidad activa e inactiva

Las disponibilidades utilizan baja lógica mediante:

```text
is_active
```

Una disponibilidad inactiva:

- no genera slots reservables;
- no puede utilizarse para nuevas citas;
- permanece en el sistema para conservar historial.

No se requiere borrado físico para retirar una disponibilidad.

---

## 18. Eliminación y modificación de disponibilidades

### Disponibilidad sin citas asociadas

Una disponibilidad futura que todavía no tenga citas puede ser desactivada/eliminada de acuerdo con la operación administrativa definida por la implementación.

### Disponibilidad con citas asociadas

Una disponibilidad que tenga citas asociadas:

- **no puede eliminarse**;
- **no puede modificarse de manera que invalide las citas existentes**.

La integridad de las citas tiene prioridad sobre la modificación de la disponibilidad.

Si el médico necesita dejar de ofrecer ese horario, debe conciliar previamente con los pacientes afectados y realizar las reprogramaciones correspondientes.

No debe existir cancelación automática de las citas derivada de la modificación de una disponibilidad.

---

## 19. Regla de modificación compatible

Cuando una disponibilidad todavía puede modificarse, la nueva configuración debe seguir conteniendo todas las citas existentes asociadas a ella.

Ejemplo:

```text
Disponibilidad:
09:00–13:00

Cita existente:
10:00–11:00
```

Reducir a:

```text
09:00–12:00
```

puede ser válido si ninguna cita queda fuera.

Reducir a:

```text
09:00–10:00
```

no es válido porque invalidaría la cita existente.

En caso de cualquier conflicto, la modificación debe rechazarse.

---

## 20. Cambio de consultorio

Una disponibilidad pertenece a un único consultorio.

El médico puede tener disponibilidades en distintos consultorios siempre que sus intervalos no se solapen.

Ejemplo válido:

```text
Clinic 1
09:00–14:00

Clinic 2
16:00–19:00
```

Ejemplo inválido:

```text
Clinic 1
09:00–14:00

Clinic 2
13:00–17:00
```

---

## 21. Integridad temporal

Las validaciones de disponibilidad deben considerar conjuntamente:

- fecha;
- hora de inicio;
- hora de fin;
- zona horaria del consultorio;
- estado activo/inactivo;
- existencia de disponibilidades superpuestas;
- existencia de citas asociadas.

Las validaciones realizadas en la aplicación no sustituyen las garantías de integridad de la base de datos cuando exista riesgo de concurrencia.

---

## 22. Responsabilidad de Agenda

La entidad de disponibilidad únicamente define **cuándo y dónde el médico ofrece atención**.

No debe encargarse de:

- confirmar citas;
- controlar cancelaciones;
- controlar reprogramaciones;
- manejar el ciclo de vida de `Appointment`;
- administrar holds;
- iniciar consultas;
- marcar `NO_SHOW`.

Esas responsabilidades corresponden al dominio de citas y sus servicios relacionados.

---

## 23. Modelo conceptual

El flujo de disponibilidad queda definido como:

```text
Doctor + Clinic
       │
       │ configuración de duración
       ↓
Availability (fecha concreta)
       │
       │ generación determinista
       ↓
Slots derivados
       │
       ├──────────────→ disponible
       │
       ├──────────────→ ocupado por Appointment
       │
       └──────────────→ temporalmente bloqueado por Hold
```

La disponibilidad es la fuente de verdad para determinar qué intervalos pueden llegar a ser reservables.

---

## 24. Invariantes principales

Deben cumplirse siempre las siguientes invariantes:

1. Una disponibilidad siempre tiene fecha concreta.
2. `start_time < end_time`.
3. La disponibilidad utiliza la zona horaria del `Clinic`.
4. La duración efectiva de la disponibilidad es positiva.
5. Las disponibilidades activas de un mismo médico nunca se solapan, independientemente del consultorio.
6. Las disponibilidades activas de una misma combinación `Doctor + Clinic` nunca se solapan.
7. Los slots son derivados y no persistidos como entidad de negocio.
8. Una cita debe quedar completamente contenida en la disponibilidad correspondiente.
9. Una disponibilidad con citas no puede eliminarse.
10. Una disponibilidad con citas no puede modificarse de forma que invalide dichas citas.
11. Una disponibilidad inactiva no genera nuevas reservas.
12. Cambiar la duración configurada de `Doctor + Clinic` no modifica disponibilidades ni citas existentes.
13. Las nuevas disponibilidades no pueden comenzar en el pasado.
14. El mismo médico no puede estar disponible simultáneamente en dos consultorios.
15. La disponibilidad no cambia automáticamente de estado por el simple paso del tiempo.

---

## 25. Fuera de alcance de este documento

No se definen aquí:

- ciclo de vida de `Appointment`;
- cancelación;
- reprogramación;
- Hold temporal;
- concurrencia de reserva detallada;
- permisos detallados de citas;
- inicio/finalización de consulta;
- `NO_SHOW`;
- historia clínica;
- notificaciones;
- pagos.

Esos aspectos se especifican en sus respectivos documentos de diseño.

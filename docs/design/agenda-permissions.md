# Diseño de permisos y autorización de Agenda — Fase 2

## 1. Propósito

Este documento define la autorización funcional para las operaciones de Agenda en TeCuidoApp.

La Agenda reutiliza el modelo de identidad, perfiles y relaciones de Fase 1. No crea un sistema paralelo de permisos.

El documento deriva sus reglas de:

- `docs/phases/phase-2-agenda.md`
- `docs/design/appointment-domain.md`
- `docs/design/availability-rules.md`
- `docs/design/booking-and-concurrency.md`

---

## 2. Principios de autorización

### 2.1 Fase 1 es la fuente de verdad

Las operaciones de Agenda deben utilizar:

- `User`;
- `Person`;
- `Doctor`;
- `Patient`;
- `Responsible`;
- `DoctorPatientRelationship`;
- `ResponsiblePatientRelationship`;
- `DoctorClinic`;
- ámbito administrativo de la clínica.

Agenda no debe duplicar ni reinterpretar las relaciones de autorización ya existentes.

### 2.2 Autorización por operación

La interfaz no concede permisos.

Cada operación debe volver a verificar que el actor está autorizado para el recurso concreto sobre el que intenta actuar.

### 2.3 Denegar por defecto

Si no existe una relación o condición de autorización válida, la operación se rechaza.

---

## 3. Actores

Las operaciones de Agenda reconocen cuatro tipos principales de actores:

```text
Patient
Responsible
Doctor
Administrator
```

La identidad autenticada siempre corresponde a un `User`.

La autorización funcional se determina mediante el perfil correspondiente y sus relaciones.

---

## 4. Ámbito del médico

Un médico:

- administra únicamente su propia disponibilidad;
- consulta únicamente su propia disponibilidad;
- no administra disponibilidad de otros médicos;
- no consulta la disponibilidad de otros médicos como agenda propia.

La pertenencia del médico a un consultorio se determina mediante `DoctorClinic`.

Un médico puede trabajar con varios consultorios, pero sólo dentro de las relaciones `DoctorClinic` que le correspondan.

---

## 5. Disponibilidad — lectura

### Médico

Puede consultar sus propias disponibilidades y sus slots derivados.

No puede administrar ni consultar la disponibilidad privada de otro médico como si fuera propia.

Cuando necesita seleccionar un horario para una cita de uno de sus pacientes, sólo puede consultar la disponibilidad necesaria de los recursos en los que puede actuar.

### Paciente

Puede consultar las disponibilidades que puedan utilizarse para una reserva permitida para sí mismo.

No puede crear, modificar ni desactivar disponibilidades.

### Responsable

Puede consultar las disponibilidades necesarias para reservar una cita de un paciente respecto del cual tenga una relación:

```text
ResponsiblePatientRelationship.status = ACTIVE
```

No puede crear, modificar ni desactivar disponibilidades.

### Administrador

Puede consultar las disponibilidades dentro de las clínicas que estén dentro de su ámbito administrativo autorizado.

---

## 6. Disponibilidad — creación

### Médico

Puede crear disponibilidad únicamente para:

```text
Doctor = él mismo
+
Clinic
```

cuando exista una relación `DoctorClinic` válida.

### Administrador

Puede crear disponibilidad únicamente cuando:

1. la clínica pertenece a su ámbito administrativo;
2. el médico tiene una relación `DoctorClinic` válida con esa clínica.

### Paciente / Responsable

No pueden crear disponibilidad.

---

## 7. Disponibilidad — modificación

Una disponibilidad sin citas asociadas puede modificarse únicamente por:

- médico propietario;
- administrador autorizado para la clínica.

Una disponibilidad con citas asociadas:

- no puede modificarse;
- no puede modificarse para invalidar citas existentes.

Paciente y responsable no pueden modificar disponibilidades.

---

## 8. Disponibilidad — desactivación

Puede desactivarse una disponibilidad por:

- médico propietario;
- administrador autorizado.

La desactivación utiliza la baja lógica establecida por `is_active`.

Una disponibilidad con citas asociadas no puede eliminarse ni desactivarse de manera que afecte dichas citas.

---

## 9. Creación de citas

Puede crear una cita:

- paciente titular;
- responsable con relación `ACTIVE`;
- médico;
- administrador autorizado.

### Paciente

Sólo puede crear citas para sí mismo.

### Responsable

Sólo puede crear citas para un paciente con:

```text
ResponsiblePatientRelationship.status = ACTIVE
```

### Médico

Puede crear una cita para cualquier paciente al que tenga **acceso legítimo**, entendido exclusivamente como: operar dentro de una combinación `Doctor + Clinic` para la que tiene una relación `DoctorClinic` válida.

**No se exige `DoctorPatientRelationship` activa previa** (decisión de cierre, 2026-09-09) — un médico puede crear la primera cita de un paciente sin que esa relación exista todavía. Crear la cita no crea, activa ni modifica ninguna `DoctorPatientRelationship`; esa relación, si llega a establecerse, sigue su propio flujo de autorización/alta, ajeno a Agenda.

### Administrador

Puede crear citas dentro de las clínicas de su ámbito administrativo, y únicamente cuando existe una relación `DoctorClinic` válida entre el médico y el consultorio involucrados. Ambas condiciones son necesarias; ninguna sustituye a la otra.

---

## 10. Consulta de citas

### Paciente

Puede consultar únicamente sus propias citas.

### Responsable

Puede consultar únicamente las citas del paciente con quien mantiene una relación:

```text
ResponsiblePatientRelationship.status = ACTIVE
```

### Médico

Puede consultar las citas en las que él mismo es el médico asignado (`Appointment.doctor`), dentro de la combinación médico-consultorio correspondiente. No se exige `DoctorPatientRelationship` activa con el paciente — igual que para la creación (§9), el vínculo relevante para Agenda es ser el médico asignado a esa cita, no una relación médico-paciente independiente.

No puede utilizar Agenda para consultar arbitrariamente las citas privadas de otros médicos.

### Administrador

Puede consultar citas dentro de todas las clínicas — el rol Administrador tiene acceso
funcional global en TeCuidoApp (`docs/adr/ADR-004-role-and-object-permissions.md` §8; Fase 1
no define ni Fase 2 introduce un modelo de administradores por clínica). "Ámbito
administrativo" en este documento se refiere a ese acceso global, no a una restricción por
clínica.

---

## 11. Creación de Hold

Puede crear un hold un actor que esté autorizado para crear la cita correspondiente:

- paciente;
- responsable con relación `ACTIVE`;
- médico;
- administrador autorizado.

El hold siempre queda asociado al `User` que lo crea.

La existencia de un hold no amplía ni sustituye la autorización sobre el paciente o la cita.

---

## 12. Liberación de Hold

Un hold sólo puede ser liberado voluntariamente por el `User` que lo creó.

Ejemplo:

```text
User A
  ↓
Hold 10:00
```

Entonces:

```text
User B → liberar Hold A
             ↓
             ❌ rechazado
```

La liberación por otro actor administrativo no forma parte del flujo normal de Fase 2.

Los holds expirados o consumidos dejan de ser bloqueos activos independientemente de quién los haya creado.

---

## 13. Cancelación de citas

Puede cancelar:

### Paciente

Su propia cita futura.

### Responsable

Una cita del paciente respecto del cual tenga relación `ACTIVE`.

### Médico

Una cita cuyo médico asignado sea él mismo.

### Administrador

Una cita dentro de las clínicas de su ámbito administrativo.

En todos los casos se aplican además las reglas funcionales de cancelación:

- la cita debe seguir siendo futura;
- no puede haber iniciado;
- se registra el actor;
- se registra el motivo;
- la cita no se elimina.

---

## 14. Reprogramación de citas

Puede reprogramar:

- paciente titular;
- responsable con relación `ACTIVE`;
- médico correspondiente;
- administrador autorizado.

La operación debe respetar simultáneamente:

- autorización sobre la cita;
- disponibilidad válida;
- disponibilidad del médico;
- disponibilidad del consultorio;
- duración congelada de la cita;
- reglas de concurrencia.

La reprogramación no permite cambiar el médico.

El historial de reprogramación forma parte del registro histórico de la operación.

---

## 15. Iniciar consulta

Únicamente el:

```text
médico asignado a la cita
```

puede iniciar la consulta.

La transición es:

```text
SCHEDULED
     ↓
IN_CONSULTATION
```

No pueden realizarla:

- paciente;
- responsable;
- administrador;
- otro médico.

La autorización se determina por coincidencia entre el actor médico autenticado y `Appointment.doctor`.

---

## 16. Finalizar consulta

Únicamente el médico asignado puede completar la consulta:

```text
IN_CONSULTATION
       ↓
COMPLETED
```

No pueden realizar esta operación:

- paciente;
- responsable;
- administrador;
- otro médico.

---

## 17. Marcar `NO_SHOW`

Únicamente el médico asignado puede marcar una cita como `NO_SHOW`.

Condiciones:

- la hora programada ya comenzó;
- ha transcurrido al menos un minuto;
- la cita sigue en `SCHEDULED`;
- el médico determina que el paciente no se presentó físicamente.

La transición es:

```text
SCHEDULED
     ↓
NO_SHOW
```

No es automática.

---

## 18. Operaciones sobre citas terminales

Las citas en:

```text
COMPLETED
CANCELLED
NO_SHOW
```

son terminales para las operaciones normales de Agenda.

No pueden:

- cancelarse nuevamente;
- reprogramarse;
- iniciarse;
- reactivarse.

La conservación histórica es obligatoria.

---

## 19. Administrador — alcance de la autorización

**Corrección de consistencia (2026-09-09):** una redacción anterior de esta sección afirmaba
que el administrador "no tiene acceso global", lo cual contradecía una decisión arquitectónica
ya aceptada — `docs/adr/ADR-004-role-and-object-permissions.md` §8 define al rol Administrador
como acceso funcional global. Ni Fase 1 ni ningún documento de Fase 2 definen un modelo de
"administrador por clínica" (no existe esa entidad); cambiar esa decisión requeriría el
proceso de actualización de ADR que fija `CLAUDE.md` §7, que no se ha hecho. Se corrige aquí
para no introducir una contradicción antes de la implementación.

El administrador (`user.is_superuser`) tiene acceso funcional global a las operaciones de
Agenda, igual que al resto de la aplicación. La verificación que Agenda sí exige, y que no es
redundante, es que exista una relación `DoctorClinic` válida entre el médico y el consultorio
involucrados en la operación — no porque el administrador esté restringido a esa clínica, sino
porque la combinación médico+consultorio debe ser operativamente válida para cualquier actor.

Conceptualmente:

```text
Administrator (acceso global, ADR-004 §8)
      ↓
DoctorClinic válida (médico + consultorio de la operación)
      ↓
Agenda operation
```

Además, las operaciones sobre un médico requieren que exista una relación `DoctorClinic` válida entre el médico y el consultorio involucrado.

---

## 20. Administrador — soporte de disponibilidad

El administrador está autorizado a apoyar al médico en la creación y modificación de disponibilidad.

Esto no convierte al administrador en propietario clínico de la agenda.

La operación debe seguir identificando:

- médico al que pertenece la disponibilidad;
- consultorio;
- administrador que realizó la operación.

---

## 21. Médico y otros médicos

Un médico no puede:

- crear disponibilidad para otro médico;
- modificar disponibilidad de otro médico;
- desactivar disponibilidad de otro médico;
- consultar la agenda privada de otro médico como parte de su propia agenda.

Que dos médicos trabajen en la misma clínica no modifica esta regla.

Las operaciones de un médico sobre citas siguen limitadas a los recursos (`Doctor + Clinic`) para los cuales tiene `DoctorClinic` válida (§9, §10) — no a una relación previa con el paciente.

---

## 22. Paciente adulto y responsable

El régimen del paciente continúa siendo el definido por Fase 1.

Un responsable sólo puede operar sobre un paciente cuando la relación:

```text
ResponsiblePatientRelationship.status = ACTIVE
```

Si la relación pasa a `INACTIVE`, pierde inmediatamente la autorización para nuevas operaciones sobre las citas de ese paciente.

En particular, esto aplica después de una transición:

```text
Patient.regime
MINOR → ADULT
```

cuando las relaciones activas del responsable han sido desactivadas.

Agenda no debe crear excepciones para restaurar esa autorización.

---

## 23. Paciente adulto sin User

Un paciente puede ser objeto de una cita aunque no tenga un `User` propio.

Esto no impide que:

- un médico cree la cita;
- un responsable autorizado, cuando corresponda, la gestione antes de perder su autorización;
- un administrador autorizado la gestione dentro de su ámbito.

La existencia de `User` no sustituye las reglas de autorización sobre la persona/paciente.

---

## 24. Matriz principal de permisos

| Operación | Paciente | Responsable ACTIVE | Médico | Administrador autorizado |
|---|---:|---:|---:|---:|
| Ver disponibilidad | ✅ | ✅ | ✅ propia | ✅ ámbito |
| Crear disponibilidad | ❌ | ❌ | ✅ propia | ✅ ámbito |
| Modificar disponibilidad | ❌ | ❌ | ✅ propia* | ✅ ámbito* |
| Desactivar disponibilidad | ❌ | ❌ | ✅ propia* | ✅ ámbito* |
| Crear cita | ✅ propia | ✅ paciente autorizado | ✅ `DoctorClinic` válida† | ✅ ámbito + `DoctorClinic` válida |
| Ver cita | ✅ propia | ✅ paciente autorizado | ✅ asignado | ✅ ámbito |
| Crear Hold | ✅ | ✅ | ✅ | ✅ |
| Liberar Hold | ✅ propio | ✅ propio | ✅ propio | ✅ propio |
| Cancelar cita | ✅ propia | ✅ paciente autorizado | ✅ correspondiente | ✅ ámbito |
| Reprogramar cita | ✅ propia | ✅ paciente autorizado | ✅ correspondiente | ✅ ámbito |
| Iniciar consulta | ❌ | ❌ | ✅ asignado | ❌ |
| Finalizar consulta | ❌ | ❌ | ✅ asignado | ❌ |
| `NO_SHOW` | ❌ | ❌ | ✅ asignado | ❌ |

`*` No puede modificarse/desactivarse cuando hacerlo afectaría citas asociadas.
`†` No se exige `DoctorPatientRelationship` previa con el paciente (§9) — la creación no la crea ni la modifica.

---

## 25. Regla de separación de responsabilidades

La autorización de Agenda debe permanecer separada de:

- disponibilidad;
- generación de slots;
- concurrencia;
- ciclo de vida de Appointment.

Por ejemplo:

```text
can_manage_availability()
can_create_appointment()
can_cancel_appointment()
can_reschedule_appointment()
can_start_appointment()
can_mark_no_show()
```

pueden existir como operaciones o servicios de autorización, pero todas deben apoyarse en las entidades y relaciones de Fase 1.

---

## 26. Regla de seguridad

Una operación nunca debe confiar exclusivamente en:

- IDs enviados por el cliente;
- selección visual de la interfaz;
- rutas de navegación;
- datos cacheados de permisos.

Toda operación mutadora debe recuperar y validar el recurso real y su ámbito de autorización.

---

## 27. Principio de auditoría

En operaciones que cambian el estado de Agenda debe conservarse el actor responsable.

Como mínimo:

```text
created_by
cancelled_by
rescheduled_by
no_show_by
checked/started by = médico asignado
```

La información de actor debe corresponder al `User` autenticado y, cuando sea necesario, al perfil funcional correspondiente.

---

## 28. Fuera de alcance

Este documento no define:

- UI;
- ciclo de vida detallado de Appointment;
- reglas de disponibilidad;
- estrategia de concurrencia;
- notificaciones;
- pagos;
- CareRequest;
- historia clínica.

Esos aspectos pertenecen a sus respectivos documentos de Fase 2.

---

## 29. Principio rector

La Agenda debe aplicar el principio:

> **El usuario sólo puede operar sobre recursos para los cuales su identidad, perfil, relación y ámbito administrativo le conceden autorización; cualquier ausencia de autorización implica rechazo.**

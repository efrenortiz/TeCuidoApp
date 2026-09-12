# Fase 3 — ClinicalEncounter Workflow

**Documento rector del flujo `ClinicalEncounter`**  
**Estado:** aprobado para diseño e implementación  
**Fecha de cierre de políticas:** 2026-09-10

---

## 1. Propósito

Este documento define el flujo funcional de una consulta clínica en TeCuidoApp desde su inicio hasta su finalización.

Su objetivo es establecer de forma inequívoca:

- qué evento inicia una consulta;
- qué precondiciones deben cumplirse;
- qué estados atraviesan `Appointment` y `ClinicalEncounter`;
- qué acciones están permitidas mientras la consulta está abierta;
- qué ocurre ante interrupciones, reintentos, concurrencia o errores;
- qué condiciones permiten completar la consulta;
- cómo se realiza la transición atómica de cierre.

Este documento no define el modelo de datos detallado, la API, la UI, la matriz completa de permisos clínicos ni la estructura de `MedicalRecord`.

---

## 2. Frontera del flujo

La consulta clínica comienza en el dominio de Agenda y continúa en el dominio clínico:

```text
Appointment
    |
    | SCHEDULED
    | Médico asignado: "Iniciar consulta"
    v
Appointment = IN_CONSULTATION
    |
    +--> ClinicalEncounter = IN_PROGRESS
              |
              | Guardar
              | Guardar
              | ...
              |
              | "Completar consulta"
              v
ClinicalEncounter = COMPLETED
    |
    v
Appointment = COMPLETED
```

La transición de inicio y la transición de cierre son operaciones de negocio coordinadas entre los dominios `appointments` y `medical_records`.

---

## 3. Precondiciones para iniciar

Una consulta solo puede iniciarse cuando se cumplen simultáneamente estas condiciones:

1. Existe una `Appointment` válida.
2. La `Appointment` está en estado `SCHEDULED`.
3. El actor es el médico asignado a esa `Appointment`.
4. La `Appointment` no está `CANCELLED` ni `NO_SHOW`.
5. No existe ya un `ClinicalEncounter` para esa `Appointment`.

El flujo no crea consultas por visualizar, reservar, reprogramar o cancelar una cita.

Tampoco existe creación manual de un `ClinicalEncounter` sin una `Appointment` de origen.

---

## 4. Regla temporal de inicio

Fase 3 no introduce una ventana temporal propia para iniciar la consulta.

La posibilidad de iniciar la `Appointment` queda sujeta a las reglas vigentes del dominio de Agenda.

Una vez iniciada la consulta:

- la duración programada de la `Appointment` no determina el cierre;
- el `ClinicalEncounter` no se cierra automáticamente al transcurrir la duración prevista;
- el médico completa la consulta de forma explícita.

---

## 5. Inicio de consulta

### 5.1 Acción

El médico asignado selecciona:

```text
Iniciar consulta
```

### 5.2 Transición obligatoria

La operación debe producir de forma atómica:

```text
Appointment: SCHEDULED → IN_CONSULTATION
ClinicalEncounter: inexistente → IN_PROGRESS
```

No se considera válido un resultado parcial.

No debe persistir:

```text
Appointment = IN_CONSULTATION
ClinicalEncounter = inexistente
```

como consecuencia de un fallo de creación.

### 5.3 Datos temporales de inicio

Al crearse el `ClinicalEncounter`:

- `created_at` registra el momento en que se crea el encuentro;
- `started_at` registra el momento real en que inicia la consulta;
- ambos valores pertenecen al contexto temporal del negocio y deben ser consistentes con la zona horaria de la `Clinic`.

---

## 6. Idempotencia del inicio

La acción **Iniciar consulta** debe ser segura frente a doble clic, reintento técnico y solicitudes concurrentes.

### 6.1 Primera solicitud

```text
SCHEDULED
   ↓
IN_CONSULTATION + ClinicalEncounter IN_PROGRESS
```

### 6.2 Segunda solicitud equivalente

Si la primera operación ya terminó exitosamente, un segundo intento no crea otro encuentro ni reinicia la consulta.

El segundo intento debe reconocer el `ClinicalEncounter` existente y mantener una única consulta para la cita.

### 6.3 Concurrencia

Dos solicitudes simultáneas no pueden producir dos encuentros.

La garantía definitiva debe descansar en:

- transacción;
- bloqueo apropiado de `Appointment`;
- integridad de base de datos;
- relación única entre `Appointment` y `ClinicalEncounter`.

---

## 7. Estado `IN_PROGRESS`

`ClinicalEncounter = IN_PROGRESS` representa una consulta abierta.

Mientras el encuentro permanezca abierto:

- el médico asignado puede capturar información;
- puede guardar avances parciales;
- puede modificar la información previamente guardada;
- puede abandonar temporalmente la pantalla y posteriormente retomar la consulta;
- puede intentar completar la consulta cuando considere finalizada la atención.

El guardado parcial **no** cambia el estado a `COMPLETED`.

---

## 8. Guardado durante la consulta

### 8.1 Guardado parcial

Guardar es una operación independiente de completar.

```text
Guardar
   ↓
ClinicalEncounter permanece IN_PROGRESS
```

Los campos obligatorios para completar pueden estar incompletos mientras el encuentro está abierto.

### 8.2 `updated_at`

Cada guardado exitoso realizado por el médico actualiza:

```text
updated_at
```

El valor representa el último momento de persistencia exitosa del encuentro.

### 8.3 Fallo del guardado

Si un guardado falla:

- no se genera una actualización parcial del encuentro;
- permanece persistido el último estado exitosamente guardado;
- el encuentro continúa abierto;
- el error debe comunicarse al usuario.

Fase 3 no exige autosalvado implícito del lado del cliente.

Solo se garantiza la persistencia de información que haya sido guardada exitosamente.

---

## 9. Consulta interrumpida

Una consulta abierta puede quedar interrumpida por:

- cierre accidental de la ventana;
- pérdida de conexión;
- cierre o expiración de sesión;
- salida temporal del consultorio;
- cualquier otra interrupción operativa.

La interrupción **no equivale a completar**.

No existe cierre automático por:

- tiempo transcurrido;
- cierre del navegador;
- fin de sesión;
- fin de la duración prevista de la cita;
- cambio de fecha u hora.

El resultado funcional es:

```text
Appointment = IN_CONSULTATION
ClinicalEncounter = IN_PROGRESS
```

El médico asignado puede retomar posteriormente el encuentro.

---

## 10. Múltiples consultas abiertas por un médico

Un médico **puede tener más de un `ClinicalEncounter` en `IN_PROGRESS` simultáneamente**, siempre que cada uno corresponda a una `Appointment` distinta y válida.

No existe en Fase 3 una regla que obligue al médico a cerrar una consulta antes de iniciar o retomar otra.

Esta decisión evita que una consulta interrumpida bloquee artificialmente la atención de otros pacientes.

---

## 11. Prohibición de CANCELLED / NO_SHOW después del inicio

Una vez que una `Appointment` ha pasado a:

```text
IN_CONSULTATION
```

no puede volver a:

```text
CANCELLED
NO_SHOW
```

La razón es funcional: la atención ya fue iniciada y existe un `ClinicalEncounter` asociado.

Por tanto:

```text
SCHEDULED → CANCELLED      sí
SCHEDULED → NO_SHOW        sí
SCHEDULED → IN_CONSULTATION → CANCELLED   no
SCHEDULED → IN_CONSULTATION → NO_SHOW     no
```

`CANCELLED` y `NO_SHOW` son estados de Agenda previos al inicio clínico y no producen `ClinicalEncounter`.

---

## 12. Acciones disponibles mientras está abierto

Mientras `ClinicalEncounter = IN_PROGRESS`, el médico asignado puede:

```text
Guardar
Retomar
Guardar nuevamente
Completar consulta
```

No puede:

- cambiar el paciente;
- cambiar el médico de la consulta;
- convertir el encuentro a otra cita;
- eliminar el encuentro;
- modificar un encuentro ya completado.

Los cambios estructurales de agenda no forman parte del flujo clínico.

---

## 13. Completar consulta

La acción:

```text
Completar consulta
```

inicia el cierre definitivo del encuentro.

La operación debe:

1. trabajar sobre el `ClinicalEncounter` abierto correspondiente a la `Appointment`;
2. validar los cinco campos obligatorios;
3. validar que contienen contenido clínico real;
4. rechazar el cierre si alguna validación falla;
5. si todo es válido, completar el encuentro y la cita en una única operación atómica.

---

## 14. Validación previa al cierre

Los cinco campos obligatorios son:

```text
Motivo de consulta
Padecimiento actual
Exploración física
Evaluación / diagnóstico
Plan / indicaciones
```

La validación ocurre **solo al completar**.

No se exige que estos campos estén completos para guardar un borrador.

No son válidos como contenido clínico real valores de relleno tales como:

```text
N/A
NA
No aplica
No Aplica
Sin datos
Ninguno
-
--
.
...
No disponible
Desconocido
```

Tampoco es válido repetir la etiqueta del campo o utilizar contenido equivalente cuyo único propósito sea superar la validación.

La validación comprueba presencia de captura clínica sustancial mínima; no determina corrección médica ni formula diagnósticos.

---

## 15. Cuando la validación falla

Si cualquiera de los cinco campos no cumple:

```text
ClinicalEncounter permanece IN_PROGRESS
Appointment permanece IN_CONSULTATION
```

Además:

- el contenido previamente guardado permanece intacto;
- no se actualiza `completed_at`;
- no se produce la transición de cierre;
- el médico puede corregir o completar la información y volver a intentar.

---

## 16. Cierre atómico

Cuando la validación es exitosa, el cierre debe ser atómico:

```text
BEGIN

ClinicalEncounter
    IN_PROGRESS → COMPLETED

Appointment
    IN_CONSULTATION → COMPLETED

completed_at = ahora

COMMIT
```

No debe quedar como estado final:

```text
ClinicalEncounter = COMPLETED
Appointment = IN_CONSULTATION
```

ni:

```text
ClinicalEncounter = IN_PROGRESS
Appointment = COMPLETED
```

Si una parte de la operación falla, la transacción completa debe revertirse.

---

## 17. `completed_at`

`completed_at` registra el momento en que la consulta fue completada exitosamente.

No debe establecerse durante:

- creación;
- guardado parcial;
- interrupción;
- intento de completar que falle validación.

Solo se establece durante una transición exitosa a `COMPLETED`.

---

## 18. Estado `COMPLETED`

Una vez completado:

```text
ClinicalEncounter = COMPLETED
Appointment = COMPLETED
```

el flujo clínico finaliza.

El encuentro queda bloqueado de forma permanente en Fase 3.

No puede:

- editarse;
- guardarse nuevamente;
- cambiarse a `IN_PROGRESS`;
- eliminarse funcionalmente;
- modificarse para corregir silenciosamente información.

No existe en Fase 3 un flujo de reapertura ni de enmienda.

---

## 19. Corrección de información después del cierre

Una vez `COMPLETED`, cualquier necesidad de corregir información queda fuera de este workflow.

No se permite resolverla mediante:

```text
COMPLETED → IN_PROGRESS
```

a modo de reapertura.

Un eventual mecanismo de versionado o enmienda será objeto de una especificación futura.

---

## 20. Concurrencia durante el cierre

El sistema debe proteger el cierre ante solicitudes concurrentes.

Escenarios mínimos:

### 20.1 Dos clics en "Completar consulta"

Solo una solicitud puede realizar exitosamente:

```text
IN_PROGRESS → COMPLETED
```

La otra debe encontrar el encuentro ya completado y no debe volver a ejecutar el cierre.

### 20.2 Guardar vs. completar

Si un guardado y un cierre concurren sobre el mismo encuentro, la persistencia final debe ser consistente y no permitir que se modifiquen datos después de que el encuentro haya quedado `COMPLETED`.

La implementación deberá resolver el orden mediante transacción y bloqueo apropiados.

### 20.3 Solicitud contra un encuentro ya completado

Cualquier actualización que llegue después de que el encuentro haya quedado `COMPLETED` debe rechazarse.

---

## 21. Estado inconsistente: Appointment sin ClinicalEncounter

Por diseño, el sistema debe impedir que persista como resultado normal de la operación:

```text
Appointment = IN_CONSULTATION
ClinicalEncounter = inexistente
```

Si una implementación detecta ese estado, debe tratarlo como inconsistencia del dominio y no como un nuevo flujo clínico válido.

No se crearán múltiples encuentros como mecanismo de recuperación automática.

---

## 22. Estado inconsistente: ClinicalEncounter sin Appointment

Un `ClinicalEncounter` sin `Appointment` de origen no forma parte del flujo de Fase 3.

La integridad del dominio debe impedir su creación funcional.

Por tanto:

```text
ClinicalEncounter.appointment
```

es una referencia obligatoria a la cita que originó la consulta.

---

## 23. Relación con DoctorPatientRelationship

El workflow clínico no crea ni modifica relaciones permanentes médico-paciente.

Crear, retomar, guardar o completar un `ClinicalEncounter`:

- no crea `DoctorPatientRelationship`;
- no activa una relación existente;
- no desactiva una relación existente;
- no sustituye una relación existente.

La relación médico-paciente y el encuentro clínico permanecen conceptualmente independientes.

---

## 24. Relación con la duración de la cita

La duración programada de `Appointment` pertenece a Agenda.

Una vez iniciada la consulta:

```text
Appointment duration ≠ ClinicalEncounter duration
```

El encuentro puede durar menos, igual o más que la duración prevista de la cita.

Fase 3 no implementa autocierre por duración.

---

## 25. Flujo completo nominal

```text
Appointment = SCHEDULED
        |
        | Médico asignado: Iniciar consulta
        v
Appointment = IN_CONSULTATION
ClinicalEncounter = IN_PROGRESS
        |
        +-------------------+
        |                   |
        | Guardar           | Interrupción
        v                   v
IN_PROGRESS           IN_PROGRESS
        |                   |
        +--------+----------+
                 |
                 | Retomar / Guardar
                 v
            IN_PROGRESS
                 |
                 | Completar consulta
                 v
        Validar 5 campos mínimos
                 |
          +------+------+
          |             |
       Falla           Éxito
          |             |
          v             v
  Permanece abierto   BEGIN
                      ClinicalEncounter → COMPLETED
                      Appointment → COMPLETED
                      completed_at = ahora
                      COMMIT
```

---

## 26. Flujos alternativos

### 26.1 Intento de iniciar por actor incorrecto

```text
Iniciar consulta
       ↓
actor no es médico asignado
       ↓
rechazar
```

No cambia `Appointment` y no crea `ClinicalEncounter`.

### 26.2 Intento de iniciar una cita CANCELLED

```text
CANCELLED
   ↓
rechazar
```

No crea encuentro.

### 26.3 Intento de iniciar una cita NO_SHOW

```text
NO_SHOW
   ↓
rechazar
```

No crea encuentro.

### 26.4 Doble clic en iniciar

```text
Request 1 → crea encuentro
Request 2 → reconoce encuentro existente
```

Resultado final: un solo encuentro.

### 26.5 Completar sin contenido suficiente

```text
Completar
   ↓
validación falla
   ↓
permanece IN_PROGRESS
```

### 26.6 Cerrar navegador durante la consulta

```text
cierre de navegador
   ↓
IN_PROGRESS permanece
   ↓
retomar posteriormente
```

---

## 27. Acciones que el workflow no contempla

No forman parte de este flujo:

- creación de consultas independientes de una cita;
- consultas iniciadas por pacientes o responsables;
- consultas iniciadas por administrador;
- reasignación del médico dentro del encuentro;
- cancelación de una consulta ya iniciada;
- `NO_SHOW` después del inicio clínico;
- eliminación funcional de encuentros;
- reapertura de encuentros completados;
- enmiendas o versionado posterior al cierre;
- acceso de lectura de otros médicos;
- generación automática de diagnósticos o recomendaciones.

---

## 28. Criterios de consistencia del workflow

La implementación debe garantizar como mínimo:

1. una `Appointment` genera como máximo un `ClinicalEncounter`;
2. un encuentro solo puede originarse desde una `Appointment` válida;
3. iniciar consulta cambia `SCHEDULED → IN_CONSULTATION` y crea `IN_PROGRESS` de manera atómica;
4. un retry o doble clic no genera duplicados;
5. el guardado parcial nunca completa automáticamente;
6. una interrupción nunca completa automáticamente;
7. una consulta abierta puede retomarse por el médico asignado;
8. un médico puede mantener más de una consulta abierta sobre citas distintas;
9. `IN_CONSULTATION` no puede convertirse en `CANCELLED` o `NO_SHOW`;
10. completar valida los cinco campos obligatorios;
11. los valores de relleno no permiten completar;
12. un cierre fallido conserva el encuentro abierto y sus datos guardados;
13. completar actualiza `ClinicalEncounter` y `Appointment` de manera atómica;
14. `completed_at` solo existe para cierres exitosos;
15. un encuentro `COMPLETED` no puede modificarse ni eliminarse funcionalmente;
16. `DoctorPatientRelationship` no se crea ni modifica por este flujo.

---

## 29. Dependencias y documentos relacionados

Este workflow depende conceptualmente de:

```text
phase-2-agenda.md
phase-3-clinical-encounter.md
```

Y alimentará directamente los documentos posteriores:

```text
clinical-encounter-rules.md
clinical-encounter-domain.md
clinical-record-domain.md
clinical-data-model.md
clinical-service-contracts.md
clinical-api-contracts.md
phase-3-clinical-ux.md
clinical-screens.md
clinical-audit-and-history.md
phase-3-testing-strategy.md
```

La matriz completa de acceso de lectura clínica se define separadamente en:

```text
clinical-permissions.md
```

---

## 30. Decisiones cerradas para el workflow

| Decisión | Estado |
|---|---|
| Inicio solo por médico asignado | Cerrada |
| Sin ventana temporal adicional en Fase 3 | Cerrada |
| `SCHEDULED → IN_CONSULTATION` al iniciar | Cerrada |
| Creación atómica de `ClinicalEncounter` al iniciar | Cerrada |
| Máximo un encuentro por `Appointment` | Cerrada |
| Segundo inicio idempotente | Cerrada |
| Estado técnico `IN_PROGRESS` | Cerrada |
| Guardado parcial | Cerrada |
| `updated_at` en cada guardado exitoso | Cerrada |
| Sin autosalvado implícito obligatorio | Cerrada |
| Consulta interrumpida permanece abierta | Cerrada |
| Retomar consulta posteriormente | Cerrada |
| Un médico puede tener varias consultas abiertas | Cerrada |
| `IN_CONSULTATION` no puede pasar a `CANCELLED` | Cerrada |
| `IN_CONSULTATION` no puede pasar a `NO_SHOW` | Cerrada |
| Completar exige cinco campos clínicos mínimos | Cerrada |
| Validación de contenido clínico real al completar | Cerrada |
| Cierre atómico `ClinicalEncounter + Appointment` | Cerrada |
| `ClinicalEncounter COMPLETED → Appointment COMPLETED` | Cerrada |
| `completed_at` solo al completar exitosamente | Cerrada |
| Sin reapertura en Fase 3 | Cerrada |
| Sin edición después de `COMPLETED` | Cerrada |
| Sin DELETE funcional | Cerrada |
| Lectura por otros médicos | Fuera de este documento; `clinical-permissions.md` |

---

## 31. Próximo documento

Con el workflow cerrado, el siguiente documento de diseño funcional es:

```text
clinical-encounter-rules.md
```

Ese documento deberá transformar el flujo en reglas de negocio más atómicas, expresadas como invariantes, precondiciones, postcondiciones y errores de dominio, sin volver a abrir decisiones ya cerradas aquí.

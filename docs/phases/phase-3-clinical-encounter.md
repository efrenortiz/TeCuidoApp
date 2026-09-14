# Fase 3 — ClinicalEncounter

**Documento rector del dominio `ClinicalEncounter`**  
**Estado:** aprobado para implementación funcional  
**Fecha de cierre de políticas:** 2026-09-10

---

## 1. Propósito

Este documento define las reglas funcionales y los invariantes del primer componente del dominio clínico de TeCuidoApp: `ClinicalEncounter`.

El objetivo es establecer un contrato único antes de implementar modelos, servicios, API y UI, siguiendo el mismo principio utilizado en Fase 2: las reglas de negocio deben quedar decididas y documentadas antes de programarse.

`ClinicalEncounter` representa el registro clínico de una consulta que fue iniciada a partir de una cita existente.

Este documento define exclusivamente el encuentro clínico genérico. No incorpora todavía módulos especializados de ginecología, obstetricia, colposcopia, menopausia, osteoporosis u otras áreas clínicas.

---

## 2. Relación con Fase 2

La frontera entre Agenda y atención clínica queda definida así:

```text
Appointment
    |
    | SCHEDULED
    |      |
    |      |  Médico asignado: "Iniciar consulta"
    |      v
    +--> IN_CONSULTATION
              |
              v
       ClinicalEncounter
```

`Appointment` continúa siendo responsabilidad del dominio `appointments`.

`ClinicalEncounter` pertenece al dominio clínico de la futura app `medical_records`.

La existencia de una `Appointment` no implica por sí misma la existencia de un encuentro clínico ni ninguna decisión médica.

---

## 3. Regla fundamental

**Un `ClinicalEncounter` corresponde a la consulta iniciada mediante una cita.**

La cita es el evento de agenda que habilita el inicio de la atención. El encuentro es el registro clínico que contiene lo sucedido durante esa atención.

No se creará un `ClinicalEncounter` por:

- visualizar una cita;
- reservar una cita;
- reprogramar una cita;
- cancelar una cita;
- marcar una cita como `NO_SHOW`;
- crear manualmente un registro clínico sin una cita que lo origine.

En Fase 3, el flujo normal y válido es siempre:

```text
Appointment válida
        ↓
Médico asignado selecciona "Iniciar consulta"
        ↓
Appointment: SCHEDULED → IN_CONSULTATION
        ↓
Se crea ClinicalEncounter
```

---

## 4. Creación del ClinicalEncounter

### 4.1 Disparador

El `ClinicalEncounter` se crea **al pulsar "Iniciar consulta"** por parte del médico asignado.

La operación de Agenda que cambia:

```text
SCHEDULED → IN_CONSULTATION
```

y la creación del encuentro clínico deben tratarse como una única operación de negocio consistente.

### 4.2 Médico que puede iniciarlo

Solo el **médico asignado a la cita** puede iniciar la consulta.

El administrador no puede iniciar una consulta en nombre del médico.

El paciente y el responsable tampoco pueden iniciar una consulta.

### 4.3 Idempotencia

La operación de inicio debe ser segura frente a reintentos técnicos o doble clic.

No debe ser posible terminar con dos `ClinicalEncounter` correspondientes a la misma `Appointment` como consecuencia de concurrencia o reintentos.

La regla de negocio es:

> **Una cita puede generar como máximo un `ClinicalEncounter`.**

La protección definitiva deberá apoyarse en la integridad de base de datos y en la transacción que ya gobierna el cambio de estado de `Appointment`.

---

## 5. Relación con Appointment

El encuentro debe conservar una referencia a la `Appointment` que originó la consulta.

Como mínimo, el encuentro debe identificar:

- paciente;
- médico asignado;
- cita de origen;
- fecha/hora de inicio;
- estado propio del encuentro, si el diseño técnico requiere distinguir una consulta abierta de una completada.

La relación entre cita y encuentro no debe reinterpretarse como una relación médico-paciente permanente.

---

## 6. DoctorPatientRelationship permanece independiente

`DoctorPatientRelationship` y `ClinicalEncounter` son conceptos distintos y no deben mezclarse.

Crear un `ClinicalEncounter`:

- no crea una `DoctorPatientRelationship`;
- no activa una `DoctorPatientRelationship`;
- no modifica una `DoctorPatientRelationship`;
- no sustituye una `DoctorPatientRelationship`.

Una relación médico-paciente podrá existir o no existir independientemente del encuentro clínico.

Esto mantiene la decisión adoptada en Fase 2: la primera cita de un paciente puede ser creada por un médico sin relación previa y esa operación no crea automáticamente la relación.

---

## 7. Estados y ciclo de vida

En términos funcionales, el encuentro debe soportar como mínimo dos situaciones:

```text
OPEN / IN_PROGRESS
        ↓
    COMPLETED
```

Los nombres técnicos definitivos podrán ajustarse durante el diseño de implementación, pero la semántica es normativa.

### 7.1 Consulta abierta

Mientras la consulta está en curso, el médico puede capturar información y guardar avances parciales.

### 7.2 Consulta completada

Cuando el médico completa el encuentro, este pasa a estado `COMPLETED`.

A partir de ese momento:

- el encuentro queda bloqueado;
- no puede editarse;
- no se permite modificar sus campos clínicos;
- no se debe convertir el encuentro en un registro mutable de "último estado".

El historial clínico debe conservar el contenido tal como fue completado.

---

## 8. Consulta interrumpida

Una consulta puede quedar interrumpida antes de ser completada.

Ejemplos:

- cierre accidental de la ventana;
- pérdida de conexión;
- salida temporal del consultorio;
- interrupción operativa del usuario.

**No existe cierre automático.**

El encuentro permanece abierto junto con la cita en `IN_CONSULTATION` y posteriormente puede ser retomado por el médico asignado.

El sistema no debe inferir que la consulta terminó solo porque:

- transcurrió cierto tiempo;
- cerró el navegador;
- terminó la sesión;
- terminó la hora prevista de la cita.

---

## 9. Guardado parcial

El guardado parcial está permitido durante una consulta abierta.

El médico puede almacenar información incompleta mientras trabaja en el encuentro.

Por tanto, los campos obligatorios de completado no necesariamente deben estar completos para poder guardar un borrador.

La validación de contenido clínico obligatorio se aplica al momento de **completar** el encuentro.

---

## 10. Mínimo obligatorio para completar

Para cambiar un encuentro a `COMPLETED`, deben existir contenidos clínicos reales en los siguientes cinco campos:

1. **Motivo de consulta**
2. **Padecimiento actual**
3. **Exploración física**
4. **Evaluación / diagnóstico**
5. **Plan / indicaciones**

Estos cinco componentes constituyen el mínimo clínico obligatorio de Fase 3.

El encuentro no puede completarse mientras cualquiera de ellos carezca de contenido clínico válido.

---

## 11. Contenido clínico real

Los campos obligatorios deben contener **contenido clínico real**, no solamente una cadena técnicamente no vacía.

No son válidos como contenido:

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

Tampoco debe considerarse válido repetir automáticamente el nombre del campo, copiar una etiqueta o utilizar contenido equivalente cuyo único propósito sea evitar la validación.

La validación debe impedir que el usuario complete el encuentro mediante valores de relleno evidentes.

### 11.1 Alcance de la validación

La validación de contenido real no pretende determinar si una nota clínica es médicamente correcta ni si el diagnóstico del médico es correcto.

TeCuidoApp únicamente valida que exista una captura clínica sustancial mínima. El contenido clínico sigue siendo responsabilidad del profesional.

TeCuidoApp **no diagnostica, no interpreta clínicamente y no genera recomendaciones médicas autónomas**.

---

## 12. Campos opcionales

Además del mínimo obligatorio, el encuentro puede contener información clínica adicional relevante.

Entre otros:

- signos vitales;
- peso;
- talla;
- antecedentes relevantes para la consulta;
- estudios y paraclínicos;
- resultados relevantes;
- observaciones;
- evolución;
- pronóstico;
- otros datos clínicos pertinentes.

La lista exacta puede ampliarse durante la evolución de Fase 3, siempre que no rompa el carácter genérico del encuentro.

Los campos opcionales no son requisito para completar un encuentro salvo que una política posterior específica de un módulo clínico establezca lo contrario.

---

## 13. Diagnóstico

En Fase 3, el diagnóstico se captura **exclusivamente como texto libre**.

No se implementa en esta fase:

- CIE-10;
- catálogo estructurado de diagnósticos;
- códigos propios de diagnóstico;
- catálogo obligatorio de enfermedades.

La etiqueta funcional puede mostrarse como:

```text
Evaluación / diagnóstico
```

La arquitectura debe mantener la posibilidad de incorporar posteriormente catálogos o codificación estructurada sin asumirlos ahora.

---

## 14. Modificación y edición

### 14.1 Mientras el encuentro está abierto

El **médico asignado** puede modificar y guardar el encuentro mientras permanezca abierto.

### 14.2 Después de COMPLETED

Un encuentro `COMPLETED` queda bloqueado.

No existe edición posterior por parte de:

- médico asignado;
- otros médicos;
- administrador;
- paciente;
- responsable.

La necesidad futura de correcciones posteriores debe resolverse mediante una política específica de versionado/enmiendas y no mediante mutación silenciosa de un encuentro completado.

### 14.3 Autoridad

La UI no es la barrera de seguridad. El servicio de dominio y la persistencia deben impedir la modificación no autorizada aunque el endpoint sea invocado directamente.

---

## 15. CANCELLED y NO_SHOW

Una cita en estado:

```text
CANCELLED
NO_SHOW
```

**no genera `ClinicalEncounter`.**

No debe existir un encuentro clínico creado únicamente porque la cita haya existido o porque se haya intentado abrir la atención cuando finalmente quedó cancelada o marcada como no presentado.

La operación de `NO_SHOW` sigue siendo responsabilidad de la Agenda y del médico asignado, de acuerdo con las reglas de Fase 2.

---

## 16. Terminología funcional

La interfaz debe utilizar términos de negocio comprensibles para el usuario.

El usuario no debe ver necesariamente nombres internos como:

```text
ClinicalEncounter
DoctorPatientRelationship
Appointment
```

como etiquetas técnicas.

Para la UI se preferirán expresiones como:

```text
Consulta
Iniciar consulta
Completar consulta
Motivo de consulta
Padecimiento actual
Exploración física
Evaluación / diagnóstico
Plan / indicaciones
```

---

## 17. Alcance genérico de Fase 3

El `ClinicalEncounter` de esta fase debe ser deliberadamente genérico.

No se crearán todavía estructuras específicas para:

- ginecología;
- obstetricia;
- control prenatal;
- colposcopia;
- menopausia;
- osteoporosis;
- endocrinología;
- cirugía;
- otras subespecialidades.

Los módulos especializados se incorporarán posteriormente y deberán extender el dominio clínico sin contaminar la definición genérica del encuentro.

---

## 18. Relación con MedicalRecord

`ClinicalEncounter` forma parte del expediente clínico, pero no reemplaza a `MedicalRecord`.

Conceptualmente:

```text
MedicalRecord
    ├── información longitudinal del paciente
    ├── historia clínica
    ├── ClinicalEncounter 1
    ├── ClinicalEncounter 2
    ├── ClinicalEncounter 3
    └── ...
```

La historia clínica y los encuentros históricos deben conservarse.

Un nuevo encuentro no debe sobrescribir los encuentros previos.

El diseño de `MedicalRecord` como tal se documentará en su propio contrato.

---

## 19. Acceso y permisos

**Cerrado (revisión de consistencia, 2026-09-11):** una redacción anterior de esta sección dejaba pendiente la política completa de lectura del expediente por otros médicos, remitiéndola a `clinical-permissions.md`. Ese documento ya fue cerrado y ratificado, y contiene la política definitiva: médico asignado, otros médicos con `DoctorPatientRelationship` activa, paciente, responsable, administrador, reglas de lectura histórica, restricciones de escritura y auditoría. Esta sección deja de describir una decisión pendiente.

La política normativa de acceso vive en:

```text
clinical-permissions.md
```

que define, entre otras cosas:

- qué médico puede leer un `ClinicalEncounter` que no le pertenece;
- en qué circunstancias existe ese acceso;
- alcance por paciente, consulta, clínica o relación;
- acceso histórico;
- comportamiento del administrador;
- auditoría de accesos clínicos sensibles.

Este documento (`phase-3-clinical-encounter.md`) no reabre esa política ni la duplica; la cita como fuente normativa.

Lo anterior no altera la regla ya cerrada en este documento:

> **La modificación de un `ClinicalEncounter` abierto corresponde exclusivamente al médico asignado, y un encuentro `COMPLETED` queda bloqueado.**

---

## 20. Integridad y concurrencia

El dominio debe asumir los mismos riesgos establecidos por la arquitectura general de TeCuidoApp:

```text
Requests can fail.
Requests can retry.
Requests can run concurrently.
Users can submit unexpected input.
```

Por ello, el diseño técnico deberá impedir al menos:

- dos encuentros para una misma cita por doble clic o retry;
- que dos solicitudes completen simultáneamente el mismo encuentro;
- que una solicitud modifique un encuentro que otro proceso acaba de completar;
- que un usuario no autorizado modifique el encuentro mediante acceso directo al endpoint;
- que un `ClinicalEncounter` sea creado para una cita `CANCELLED` o `NO_SHOW`;
- que una `Appointment` pase a `COMPLETED` sin que su `ClinicalEncounter` correspondiente también haya quedado `COMPLETED` en la misma operación transaccional.

**Cerrado (revisión de consistencia, 2026-09-11):** una redacción anterior de este último punto lo describía como una regla pendiente de formalizar en un futuro "contrato de transición de Agenda/Fase 3". Esa formalización ya ocurrió y es una de las invariantes centrales de Fase 3, no trabajo futuro:

> **`Appointment.COMPLETED` no puede resultar de la operación clínica de cierre sin que el `ClinicalEncounter` correspondiente también haya quedado `COMPLETED` en la misma transacción — y viceversa.**

Esta invariante está cerrada y desarrollada en `clinical-encounter-workflow.md` (§16, "Cierre atómico"), `clinical-encounter-rules.md` (R-064 a R-070) y en las capas de implementación: `clinical-service-contracts.md` (§8, contrato `complete_encounter`) y `clinical-api-contracts.md` (§12, endpoint de completar).

Las condiciones que requieran garantía fuerte deben resolverse con transacción y restricciones de base de datos, no únicamente con validaciones de interfaz.

---

## 21. Transacción de "Iniciar consulta"

La operación funcional de inicio debe ser atómica desde el punto de vista del negocio.

Conceptualmente:

```text
BEGIN
  bloquear Appointment
  verificar que está SCHEDULED
  verificar que el actor es el médico asignado
  cambiar Appointment → IN_CONSULTATION
  crear ClinicalEncounter
COMMIT
```

Ante cualquier error, la operación completa debe revertirse.

No debe quedar una cita en `IN_CONSULTATION` sin su encuentro correspondiente como resultado de una creación parcialmente fallida.

El mecanismo técnico concreto podrá apoyarse en los patrones transaccionales ya definidos para Agenda, sin duplicar lógica de autorización en la UI.

---

## 22. Finalización de la consulta

La acción funcional de **"Completar consulta"** debe validar los cinco campos obligatorios definidos en §10 y §11.

Conceptualmente:

```text
Consulta abierta
     ↓
validar contenido clínico mínimo
     ↓
ClinicalEncounter → COMPLETED
```

Si la validación falla:

- el encuentro permanece abierto;
- no se pierde el contenido parcial guardado;
- el usuario recibe información clara sobre qué requisito falta.

Completar el encuentro no debe sobrescribir ni eliminar el contenido previamente guardado.

---

## 23. Relación con la duración de la cita

La duración de `Appointment` es una regla de Agenda y no determina automáticamente la duración real del encuentro clínico.

El sistema no debe cerrar el `ClinicalEncounter` automáticamente porque haya transcurrido la duración de la cita.

La consulta permanece abierta hasta que el médico la complete.

---

## 24. Datos temporales

El encuentro debe conservar al menos:

- fecha/hora de inicio;
- fecha/hora de finalización, cuando se complete;
- referencias a la cita, paciente y médico que correspondan.

La fecha/hora de negocio debe ser consistente con las reglas de Agenda y la zona horaria del `Clinic`.

No se debe utilizar la zona horaria local del dispositivo del usuario como autoridad clínica de la consulta.

---

## 25. Reglas que esta especificación sobrescribe de documentos anteriores

Este documento consolida decisiones tomadas después de las primeras definiciones generales de Fase 3.

Por tanto, para `ClinicalEncounter`, quedan supersedidas como criterio de obligatoriedad de completado las listas anteriores que trataban como mínimos campos como:

- paraclínicos;
- manejo/tratamiento;
- pronóstico;
- evolución;
- observaciones clínicas.

Esos elementos **siguen siendo parte del dominio y pueden existir en el encuentro**, pero dejan de ser requisitos universales para cambiar a `COMPLETED`.

El mínimo normativo de completado es ahora exclusivamente:

```text
Motivo de consulta
Padecimiento actual
Exploración física
Evaluación / diagnóstico
Plan / indicaciones
```

Asimismo, la regla de diagnóstico se cierra para Fase 3 como **texto libre**, sin CIE-10 ni catálogo.

---

## 26. Decisiones cerradas

Quedan aprobadas para implementación las siguientes decisiones:

| Decisión | Estado |
|---|---|
| Un encuentro corresponde a una consulta iniciada mediante una cita | Cerrada |
| Creación al pulsar "Iniciar consulta" | Cerrada |
| Un encuentro como máximo por cita | Cerrada |
| Inicio solo por médico asignado | Cerrada |
| Mínimo obligatorio de 5 campos para completar | Cerrada |
| Validación de contenido clínico real | Cerrada |
| Guardado parcial | Cerrada |
| Consulta interrumpida sin autocierre | Cerrada |
| Retomar consulta abierta | Cerrada |
| Bloqueo después de `COMPLETED` | Cerrada |
| Modificación solo por médico asignado | Cerrada |
| Diagnóstico únicamente texto libre | Cerrada |
| Independencia de `DoctorPatientRelationship` | Cerrada |
| `CANCELLED` / `NO_SHOW` no generan encuentro | Cerrada |
| Núcleo de encuentro genérico | Cerrada |
| Acceso de otros médicos al expediente | Cerrada — ver `clinical-permissions.md` (fuente normativa) |
| Atomicidad `ClinicalEncounter COMPLETED` ↔ `Appointment COMPLETED` | Cerrada — ver §21 y `clinical-encounter-workflow.md`/`clinical-service-contracts.md`/`clinical-api-contracts.md` |

---

## 27. Fuera de alcance de este documento

No se define aquí:

- matriz completa de permisos de lectura clínica;
- `MedicalRecord` completo;
- historia clínica detallada como contrato independiente;
- `ClinicalAlert`;
- recetas;
- órdenes de estudios;
- documentos clínicos;
- archivos adjuntos;
- versionado/enmiendas posteriores a un encuentro `COMPLETED`;
- auditoría avanzada de acceso clínico;
- módulos de ginecología/obstetricia/colposcopia/menopausia;
- CIE-10 o catálogos diagnósticos.

Cada elemento que quede fuera deberá tener su propio contrato o formar parte de la siguiente especificación funcional correspondiente.

---

## 28. Preparación para implementación

La implementación de este contrato deberá respetar la separación arquitectónica existente:

```text
appointments
    ↓
Appointment / transición a IN_CONSULTATION
    ↓
medical_records
    ↓
ClinicalEncounter
```

No se debe mover lógica clínica a `appointments`.

La futura app `medical_records` utilizará las entidades canónicas existentes de Fase 1 y Fase 2, especialmente:

```text
Patient
Doctor
Clinic
Appointment
```

sin duplicarlas.

La implementación debe seguir el patrón de servicios de dominio ya adoptado en TeCuidoApp:

```text
UI / API
   ↓
Domain Service
   ↓
Authorization
   ↓
Transaction
   ↓
ORM / PostgreSQL
```

---

## 29. Criterio de aceptación funcional

La primera implementación de `ClinicalEncounter` se considerará funcionalmente completa cuando pueda demostrarse, como mínimo, que:

1. una `Appointment` `SCHEDULED` puede ser iniciada únicamente por su médico asignado;
2. iniciar la cita crea exactamente un `ClinicalEncounter`;
3. un retry o doble clic no crea duplicados;
4. la consulta puede guardarse parcialmente;
5. una consulta interrumpida puede retomarse;
6. una consulta no puede completarse con campos obligatorios vacíos o con valores de relleno equivalentes a `N/A`;
7. una consulta sí puede completarse con contenido clínico real en los cinco campos obligatorios;
8. al completar, el encuentro queda bloqueado;
9. ningún otro actor puede modificarlo;
10. `CANCELLED` y `NO_SHOW` no generan encuentros;
11. la creación de un encuentro no modifica `DoctorPatientRelationship`;
12. el diagnóstico se almacena como texto libre;
13. el comportamiento de acceso de otros médicos está cerrado en `clinical-permissions.md`, sin haberse inventado una regla propia en esta etapa del diseño.

---

## 30. Documento normativo de permisos

**Actualizado (revisión de consistencia, 2026-09-11):** `clinical-permissions.md` ya fue cerrado y ratificado; contiene la política definitiva de lectura del expediente clínico por otros médicos, paciente, responsable y administrador, junto con sus reglas de autorización y auditoría. Este documento no vuelve a apuntar a él como trabajo pendiente — lo cita como fuente normativa vigente para cualquier pregunta de acceso/lectura clínica.

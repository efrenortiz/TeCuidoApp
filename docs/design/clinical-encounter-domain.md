# Fase 3 — ClinicalEncounter Domain

**Documento rector del dominio `ClinicalEncounter`**  
**Estado:** aprobado para diseño e implementación  
**Fecha de cierre de políticas:** 2026-09-11  
**Dominio:** atención clínica genérica  
**Aplicación prevista:** `medical_records`

---

## 1. Propósito

Este documento define el modelo conceptual y las reglas estructurales del dominio `ClinicalEncounter` de TeCuidoApp.

Su objetivo es traducir las decisiones ya cerradas para Fase 3 a un dominio implementable, manteniendo una separación estricta entre:

- la **Agenda**, representada por `Appointment`;
- el **encuentro clínico**, representado por `ClinicalEncounter`;
- el **expediente médico**, representado por `MedicalRecord` en la evolución del dominio clínico.

Este documento define qué es un `ClinicalEncounter`, qué identidad tiene, con qué entidades se relaciona, qué atributos constituyen su estado, cuáles son sus invariantes y qué operaciones de dominio son válidas.

No define todavía:

- la estructura de la API HTTP;
- las pantallas definitivas;
- la matriz completa de permisos de lectura clínica entre médicos;
- el diseño de archivos/documentos clínicos;
- módulos especializados de ginecología, obstetricia, colposcopia, menopausia, osteoporosis u otras especialidades;
- códigos CIE-10;
- catálogos diagnósticos;
- versionado clínico posterior a `COMPLETED`.

---

## 2. Fuentes normativas y jerarquía

El dominio debe leerse junto con los documentos que ya cerraron las decisiones funcionales de Fase 3.

### 2.1 Fuentes inmediatas

```text
phase-3-clinical-encounter.md
clinical-encounter-workflow.md
clinical-encounter-rules.md
```

### 2.2 Fuentes arquitectónicas y de fases anteriores

```text
requirements.md
docs/architecture.md
docs/design/appointment-domain.md
docs/design/agenda-service-contracts.md
docs/adr/ADR-005-django-app-boundaries.md
docs/adr/ADR-006-database-integrity-and-transactions.md
```

Cuando una definición histórica resulte más amplia que la decisión cerrada para Fase 3, prevalece la decisión específica y posterior de Fase 3 únicamente en aquello que sea propio del `ClinicalEncounter`.

No se deben reinterpretar las reglas de Fase 2 de Agenda desde el dominio clínico.

---

## 3. Definición del dominio

### 3.1 Qué es ClinicalEncounter

Un `ClinicalEncounter` es el registro clínico de una consulta que fue iniciada a partir de una `Appointment` válida.

Representa una atención clínica concreta, identificable y trazable en el tiempo, desde el momento en que el médico asignado inicia la consulta hasta que la consulta es completada.

La definición central es:

> **Una `Appointment` puede originar cero o un `ClinicalEncounter`; una vez iniciado el encuentro, este registra la atención clínica asociada a esa cita.**

### 3.2 Qué no es

`ClinicalEncounter` no es:

- una cita;
- una agenda;
- una relación permanente médico-paciente;
- una nota médica global e ilimitada;
- un diagnóstico estructurado;
- un expediente médico completo;
- una autorización para atender al paciente;
- un mecanismo de check-in;
- un estado de espera;
- un reemplazo de `DoctorPatientRelationship`.

### 3.3 Frontera del dominio

La frontera funcional queda expresada así:

```text
+--------------------+          +------------------------+
| appointments       |          | medical_records        |
|                    |          |                        |
| Appointment        |  ---->  | ClinicalEncounter     |
| Agenda state       |          | Clinical clinical data|
+--------------------+          +------------------------+
            |                               |
            |                               v
            |                         MedicalRecord
            |                         (evolución futura)
            |
            +---- Doctor / Patient / Clinic
```

La Agenda decide si una cita puede entrar al flujo de atención. El dominio clínico registra lo ocurrido durante la atención.

---

## 4. Posición dentro de la arquitectura

Se conserva el patrón arquitectónico adoptado en las fases anteriores:

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

Para `ClinicalEncounter` se añade una separación conceptual importante:

```text
Appointment (Agenda)
        ↓
operación de inicio coordinada
        ↓
ClinicalEncounter (Atención clínica)
        ↓
MedicalRecord / otros componentes clínicos
```

La UI no es autoridad para:

- decidir si un encuentro puede iniciarse;
- crear directamente registros clínicos;
- completar sin validación del dominio;
- impedir por sí sola la edición posterior a `COMPLETED`;
- garantizar unicidad.

La base de datos tampoco sustituye las reglas clínicas de aplicación, pero sí debe reforzar las invariantes estructurales que pueda expresar.

---

## 5. Identidad y cardinalidad

### 5.1 Identidad propia

`ClinicalEncounter` es una entidad de dominio con identidad propia.

Su identidad no debe depender de la posición física de sus datos clínicos ni de que el contenido de sus campos coincida con otro encuentro.

La implementación podrá utilizar el mecanismo de identidad estándar de Django/PostgreSQL para la entidad.

### 5.2 Relación con Appointment

La cardinalidad normativa es:

```text
Appointment 1 ─── 0..1 ClinicalEncounter
```

Esto significa:

- una `Appointment` puede no haber iniciado todavía un encuentro;
- una `Appointment` puede tener un único encuentro;
- un `ClinicalEncounter` debe tener exactamente una `Appointment` de origen.

### 5.3 Unicidad

La referencia a `Appointment` debe ser única en `ClinicalEncounter`.

En términos conceptuales:

```text
UNIQUE(clinical_encounter.appointment_id)
```

La unicidad no debe depender de la lógica de interfaz ni de una consulta previa sin protección concurrente.

---

## 6. Agregado y raíz de agregado

### 6.1 Aggregate Root

La raíz del agregado clínico de esta fase es `ClinicalEncounter`.

Las operaciones que modifican su información clínica deben pasar por las reglas del agregado y no por actualizaciones arbitrarias desde cualquier capa.

### 6.2 Límites del agregado

El agregado `ClinicalEncounter` contiene, conceptualmente, el estado de una consulta individual:

```text
ClinicalEncounter
├── identity
├── appointment reference
├── doctor identity
├── patient identity
├── clinic context
├── lifecycle state
├── timestamps
├── required clinical content
├── optional clinical content
└── audit/history hooks
```

No contiene como subentidades en Fase 3:

- `Appointment` completa;
- `Patient` completo;
- `Doctor` completo;
- `Clinic` completa;
- `DoctorPatientRelationship`;
- el expediente médico completo;
- documentos binarios externos.

El encuentro referencia estas entidades o contextos canónicos; no los duplica como agregados independientes.

---

## 7. Entidades canónicas relacionadas

### 7.1 Patient

`Patient` identifica a la persona que recibe la atención.

El encuentro debe corresponder al paciente de la `Appointment` de origen.

La implementación no debe permitir cambiar manualmente el paciente de un encuentro.

### 7.2 Doctor

`Doctor` identifica al profesional asignado a la `Appointment` que inició la consulta.

El médico que queda asociado al `ClinicalEncounter` es el médico asignado en el momento de inicio.

Solo ese médico puede modificar el encuentro mientras está abierto, conforme a las decisiones de permisos de Fase 3.

### 7.3 Clinic

`Clinic` representa el contexto físico/operativo donde ocurre la atención.

El encuentro conserva el contexto de clínica asociado a la cita de origen y no debe ser transferido manualmente a otra clínica.

### 7.4 Appointment

`Appointment` es la entidad de Agenda que da origen al encuentro.

La relación debe permitir recuperar la trazabilidad completa:

```text
ClinicalEncounter → Appointment → Patient / Doctor / Clinic / agenda data
```

---

## 8. DoctorPatientRelationship

`DoctorPatientRelationship` permanece completamente fuera de la identidad del encuentro.

### 8.1 No forma parte del agregado

No debe modelarse como una dependencia obligatoria del `ClinicalEncounter`.

### 8.2 No se crea automáticamente

Crear un encuentro no crea una relación médico-paciente.

### 8.3 No se modifica automáticamente

Ni iniciar, guardar, retomar ni completar un encuentro debe modificar el estado de `DoctorPatientRelationship`.

### 8.4 Razón de dominio

Una consulta es un episodio de atención.

La relación médico-paciente es un concepto independiente que puede existir antes, después o no existir en absoluto.

---

## 9. Ciclo de vida

El encuentro tiene dos estados funcionales definitivos en Fase 3:

```text
IN_PROGRESS
     |
     | completar
     v
COMPLETED
```

No existen en el dominio de Fase 3 estados funcionales adicionales para:

- cancelación del encuentro;
- `NO_SHOW` del encuentro;
- espera;
- check-in;
- suspensión temporal como estado persistente separado;
- reapertura;
- edición de un encuentro completado.

### 9.1 Estado IN_PROGRESS

Representa una consulta abierta.

Mientras está en `IN_PROGRESS`:

- puede guardar cambios parciales;
- el médico asignado puede modificar los datos clínicos;
- la consulta puede ser interrumpida;
- la consulta puede ser retomada;
- el encuentro puede ser completado cuando se cumplan las reglas de cierre.

### 9.2 Estado COMPLETED

Representa una consulta finalizada.

Una vez que el encuentro pasa a `COMPLETED`:

- queda bloqueado;
- no admite modificaciones clínicas;
- no puede reabrirse;
- no puede regresar a `IN_PROGRESS`;
- no puede eliminarse funcionalmente.

---

## 10. Estados de Appointment y relación con ClinicalEncounter

El dominio clínico no sustituye los estados de `Appointment`.

La combinación normativa de estados es:

| Momento | Appointment | ClinicalEncounter |
|---|---|---|
| Cita creada y pendiente | `SCHEDULED` | inexistente |
| Consulta iniciada | `IN_CONSULTATION` | `IN_PROGRESS` |
| Consulta completada | `COMPLETED` | `COMPLETED` |
| Cita cancelada antes de iniciar | `CANCELLED` | inexistente |
| Paciente no se presenta | `NO_SHOW` | inexistente |

La existencia de `ClinicalEncounter` está condicionada al inicio clínico real.

---

## 11. Creación del encuentro

### 11.1 Comando conceptual

La operación de creación no se expone como un CRUD genérico.

El comando de dominio es conceptualmente:

```text
StartClinicalEncounter(appointment, actor)
```

### 11.2 Resultado

Cuando es válida, la operación produce:

```text
Appointment:        SCHEDULED → IN_CONSULTATION
ClinicalEncounter:  inexistente → IN_PROGRESS
```

### 11.3 Atomicidad

Ambas transiciones forman una sola operación de negocio consistente.

No debe quedar persistido un estado en el que:

```text
Appointment = IN_CONSULTATION
ClinicalEncounter = inexistente
```

### 11.4 Actor

El actor autorizado funcionalmente es el médico asignado a la cita.

No se delega la autoridad a:

- paciente;
- responsable;
- administrador;
- otro médico no asignado.

Las reglas detalladas de autorización se documentarán en `clinical-permissions.md`.

---

## 12. Idempotencia

### 12.1 Principio

Iniciar una consulta es una operación que debe tolerar reintentos técnicos.

### 12.2 Doble clic

Dos activaciones de "Iniciar consulta" no deben crear dos encuentros.

### 12.3 Solicitudes concurrentes

Dos solicitudes concurrentes para la misma `Appointment` deben converger en un único encuentro.

### 12.4 Mecanismos de protección

La garantía debe apoyarse en varias capas:

```text
Service rule
    +
transaction
    +
concurrency control
    +
unique appointment reference
```

Ninguna capa por sí sola debe considerarse suficiente.

---

## 13. Identidad clínica del encuentro

La identidad clínica mínima de un encuentro está constituida por:

```text
Encounter ID
Appointment ID
Patient
Doctor
Clinic context
```

La `Appointment` es la fuente estructural de los vínculos con paciente, médico y clínica.

Se debe evitar almacenar una segunda fuente editable de verdad que pueda entrar en contradicción con la cita.

Si por razones de implementación se materializan referencias directas a `Patient`, `Doctor` o `Clinic`, estas deben tratarse como datos estructurales derivados y protegidos contra edición independiente.

---

## 14. Campos clínicos del agregado

Fase 3 utiliza campos simples y explícitos.

No se utilizará un único `JSONField` genérico para representar toda la consulta.

### 14.1 Campos obligatorios al completar

El agregado debe contener exactamente estos cinco conceptos como mínimo funcional:

| Campo conceptual | Obligatorio al guardar | Obligatorio al completar |
|---|---:|---:|
| Motivo de consulta | No | Sí |
| Padecimiento actual | No | Sí |
| Exploración física | No | Sí |
| Evaluación / diagnóstico | No | Sí |
| Plan / indicaciones | No | Sí |

"No" en la columna de guardado significa que el encuentro puede guardarse incompleto mientras esté `IN_PROGRESS`.

### 14.2 Campos opcionales

Podrán existir campos adicionales en el núcleo genérico, siempre que no introduzcan una interpretación especializada prematura.

Entre ellos se encuentran, de forma orientativa:

- signos vitales;
- peso;
- talla;
- antecedentes relevantes;
- estudios;
- observaciones;
- otros datos clínicos generales que hayan sido aprobados para Fase 3.

Estos campos son opcionales y no deben inventarse como requisitos de cierre.

### 14.3 Especialidades posteriores

La existencia de campos genéricos no debe bloquear una futura extensión para:

- ginecología;
- obstetricia;
- colposcopia;
- menopausia;
- osteoporosis;
- medicina preventiva;
- otras áreas.

Los módulos especializados deberán extender el dominio sin contaminar el núcleo genérico con campos que solo una especialidad requiere.

---

## 15. Semántica de los cinco campos obligatorios

### 15.1 Motivo de consulta

Expresa por qué el paciente acude a atención en términos clínicos registrados por el médico.

No existe catálogo obligatorio en Fase 3.

### 15.2 Padecimiento actual

Describe la historia o evolución del problema actual que motiva la consulta, en la medida en que el médico decida registrarla.

### 15.3 Exploración física

Registra los hallazgos de la exploración realizada.

No se exige una estructura anatómica universal en esta fase.

### 15.4 Evaluación / diagnóstico

Es el juicio clínico expresado por el médico en texto libre.

No se utiliza CIE-10 ni catálogo diagnóstico en Fase 3.

### 15.5 Plan / indicaciones

Registra el plan o las indicaciones médicas correspondientes a la atención.

No deben generarse automáticamente por el sistema.

---

## 16. Diagnóstico en texto libre

### 16.1 Regla de Fase 3

El campo de evaluación/diagnóstico es de texto libre.

### 16.2 Fuera de alcance

No forma parte de Fase 3:

- CIE-10;
- catálogos de diagnósticos;
- clasificación automática;
- sugerencias automáticas de diagnóstico;
- inferencia diagnóstica mediante IA;
- validación médica automática del diagnóstico.

### 16.3 Responsabilidad

El sistema almacena el contenido ingresado por el médico, pero no determina su corrección clínica.

---

## 17. Validación de contenido clínico real

La obligación de un campo no se satisface simplemente porque la columna tenga un valor no nulo.

### 17.1 Principio

Al completar, los cinco campos obligatorios deben contener contenido clínico real introducido por el médico.

### 17.2 Normalización mínima

La validación debe:

1. eliminar espacios al inicio y al final para efectos de evaluación;
2. considerar vacío el contenido formado solo por espacios;
3. comparar equivalentes de placeholders sin sensibilidad a mayúsculas/minúsculas;
4. impedir variantes obvias usadas para eludir la validación;
5. no exigir una longitud arbitraria en caracteres.

### 17.3 Placeholders inválidos

**Corrección de consistencia (revisión de cierre, 2026-09-11):** la lista definitiva y cerrada de valores de relleno es la de `clinical-encounter-rules.md` R-053 (comparación insensible a mayúsculas/minúsculas y a espacios externos):

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

Una redacción anterior de esta sección enumeraba un subconjunto distinto (le faltaban "Ninguno" y "Desconocido", e incluía "Sin información", que no forma parte de la lista cerrada). Se corrige para referenciar directamente R-053 en vez de mantener una segunda enumeración que pueda divergir.

### 17.4 No se evalúa la calidad clínica

El dominio no intenta determinar si el contenido:

- es médicamente correcto;
- es suficientemente detallado;
- corresponde a una enfermedad concreta;
- sigue una guía clínica específica;
- constituye una buena nota médica.

La validación es de **presencia de contenido real**, no de calidad médica.

---

## 18. Guardado parcial

### 18.1 Operación

El encuentro abierto admite un comando conceptual:

```text
SaveClinicalEncounter(...)
```

### 18.2 Condición

Solo es válido sobre un encuentro `IN_PROGRESS` y para el actor autorizado.

### 18.3 Resultado

Después de un guardado correcto:

```text
status = IN_PROGRESS
updated_at = now()
```

No se completa automáticamente.

### 18.4 Persistencia

Fase 3 garantiza únicamente la información que haya sido guardada exitosamente.

No existe requisito de autosave.

### 18.5 Fallo

Un fallo debe conservar el último estado exitosamente persistido y no producir una transición clínica parcial.

---

## 19. Timestamps y semántica temporal

El encuentro utiliza cuatro marcas temporales principales:

| Campo | Significado |
|---|---|
| `created_at` | momento en que se crea el `ClinicalEncounter` |
| `started_at` | momento real en que inicia la consulta |
| `updated_at` | último momento de guardado exitoso |
| `completed_at` | momento en que se completa exitosamente |

### 19.1 created_at

Se establece una sola vez al crear el encuentro.

No debe representar la hora programada de la cita.

### 19.2 started_at

Representa el inicio real de la consulta, no la hora nominal de la `Appointment`.

### 19.3 updated_at

Se actualiza en cada guardado exitoso que modifique/persista el encuentro según la semántica de la operación de servicio.

### 19.4 completed_at

Solo se establece al pasar exitosamente a `COMPLETED`.

### 19.5 Orden temporal

Debe cumplirse:

```text
created_at ≤ started_at ≤ completed_at
```

Cuando el encuentro sigue abierto, `completed_at` es nulo.

### 19.6 Zona horaria

Los timestamps deben seguir la estrategia temporal definida por la aplicación y el contexto de la clínica. La hora programada de la cita no se reutiliza como sustituto del inicio real.

---

## 20. Regla sobre duración

El encuentro clínico no hereda una duración obligatoria de la cita para su cierre.

Conceptualmente existen dos tiempos distintos:

```text
Appointment.duration

ClinicalEncounter:
    started_at
    completed_at
```

La diferencia entre `started_at` y `completed_at` constituye la duración efectiva del encuentro cuando este ya fue completado.

No existe cierre automático porque haya transcurrido:

- la duración programada;
- la hora de finalización de la cita;
- un periodo fijo posterior al inicio.

---

## 21. Interrupción y reanudación

### 21.1 Interrupción

Un encuentro `IN_PROGRESS` puede quedar temporalmente sin actividad.

Ejemplos:

- cierre de navegador;
- pérdida de conexión;
- expiración de sesión;
- salida temporal de la pantalla.

### 21.2 Estado resultante

El encuentro permanece:

```text
IN_PROGRESS
```

y la cita permanece:

```text
IN_CONSULTATION
```

### 21.3 No auto-close

No existe proceso automático que cambie el encuentro a `COMPLETED` debido a inactividad.

### 21.4 Reanudación

El médico asignado puede recuperar el encuentro abierto y continuar trabajando.

### 21.5 No es una transición adicional

"Interrumpido" no se modela como estado de dominio persistente independiente en Fase 3.

---

## 22. Múltiples encuentros abiertos del mismo médico

Fase 3 permite que un mismo médico tenga más de un `ClinicalEncounter` en `IN_PROGRESS` al mismo tiempo, siempre que correspondan a distintas `Appointment` válidas.

Ejemplo conceptual:

```text
Doctor A
├── Appointment 101 → ClinicalEncounter 501 → IN_PROGRESS
└── Appointment 102 → ClinicalEncounter 502 → IN_PROGRESS
```

La restricción de unicidad es **por `Appointment`**, no global por médico.

Por tanto, no debe implementarse una regla como:

```text
un doctor solo puede tener un encuentro abierto
```

salvo que una fase futura la establezca expresamente.

---

## 23. Regla de cancelación y NO_SHOW

`CANCELLED` y `NO_SHOW` son estados de `Appointment`, no estados de `ClinicalEncounter`.

### 23.1 Antes de iniciar

Una cita puede terminar en `CANCELLED` o `NO_SHOW` sin crear encuentro.

### 23.2 Después de iniciar

Una `Appointment` en `IN_CONSULTATION` no puede pasar a:

```text
CANCELLED
NO_SHOW
```

Por consecuencia, un `ClinicalEncounter` ya iniciado no queda asociado a una cancelación o no presentación posterior.

---

## 24. Completar el encuentro

### 24.1 Comando conceptual

```text
CompleteClinicalEncounter(encounter, actor, submitted_values)
```

### 24.2 Precondiciones

El encuentro debe:

- existir;
- estar en `IN_PROGRESS`;
- pertenecer al médico autorizado;
- mantener una referencia válida a su `Appointment`;
- tener completos y válidos los cinco campos obligatorios.

### 24.3 Persistencia de los últimos cambios

La acción "Completar consulta" debe incluir los últimos valores clínicos enviados por el usuario en esa operación.

No se requiere que el médico pulse previamente "Guardar" para poder completar.

### 24.4 Resultado

La finalización debe producir atómicamente:

```text
ClinicalEncounter: IN_PROGRESS → COMPLETED
Appointment:       IN_CONSULTATION → COMPLETED
```

### 24.5 completed_at

La marca `completed_at` se establece como parte de la operación exitosa de cierre.

---

## 25. Atomicidad del cierre

El cierre es una operación de negocio coordinada entre los dos dominios.

El sistema no debe dejar persistido normalmente ninguno de estos estados parciales:

```text
ClinicalEncounter = COMPLETED
Appointment = IN_CONSULTATION
```

o:

```text
ClinicalEncounter = IN_PROGRESS
Appointment = COMPLETED
```

La transición de cierre debe utilizar una transacción que coordine ambos cambios.

Si alguna parte falla, toda la operación debe revertirse.

---

## 26. Inmutabilidad después de COMPLETED

### 26.1 Regla principal

`COMPLETED` es un cierre definitivo en Fase 3.

### 26.2 Operaciones rechazadas

Después de `COMPLETED` deben rechazarse:

- cambios de campos clínicos;
- cambios de paciente;
- cambios de médico;
- cambios de clínica;
- cambios de cita de origen;
- regreso a `IN_PROGRESS`;
- reapertura;
- eliminación funcional.

### 26.3 No versionado en Fase 3

No existe todavía un modelo de:

- enmienda;
- addendum;
- nueva versión clínica;
- reapertura controlada.

Si una fase futura lo necesita, deberá definirse como una decisión arquitectónica explícita y no mediante una excepción ad hoc.

---

## 27. Eliminación

### 27.1 Sin DELETE funcional

El dominio no ofrece una operación funcional para eliminar un `ClinicalEncounter`.

### 27.2 Razón

El contenido clínico es histórico y debe preservarse para trazabilidad.

### 27.3 Consecuencia técnica

La implementación debe evitar exponer un CRUD genérico que permita a un usuario borrar el encuentro.

Los mecanismos administrativos o de mantenimiento de infraestructura quedan fuera del comportamiento funcional de Fase 3.

---

## 28. Invariantes estructurales

El agregado debe mantener como mínimo las siguientes invariantes.

### I-001 — Appointment obligatoria

Todo `ClinicalEncounter` tiene una `Appointment` de origen.

### I-002 — Appointment única

Una `Appointment` tiene como máximo un `ClinicalEncounter`.

### I-003 — Estado válido

El estado del encuentro pertenece al conjunto:

```text
IN_PROGRESS | COMPLETED
```

### I-004 — Appointment coherente

Mientras el encuentro está `IN_PROGRESS`, la cita asociada está `IN_CONSULTATION`.

Mientras el encuentro está `COMPLETED`, la cita asociada termina en `COMPLETED` como parte del cierre atómico.

### I-005 — Identidad del paciente

El paciente del encuentro coincide con el paciente de la cita de origen.

### I-006 — Identidad del médico

El médico del encuentro coincide con el médico asignado a la cita de origen.

### I-007 — Contexto de clínica

El contexto clínico de clínica corresponde al de la cita de origen.

### I-008 — Temporalidad

Se cumple:

```text
created_at ≤ started_at
```

y, cuando existe:

```text
started_at ≤ completed_at
```

### I-009 — completed_at según estado

Si `status = IN_PROGRESS`, `completed_at` debe ser nulo.

Si `status = COMPLETED`, `completed_at` debe estar presente.

### I-010 — Inmutabilidad del cierre

Un encuentro `COMPLETED` no vuelve a ser modificable por las operaciones clínicas normales.

### I-011 — Sin DoctorPatientRelationship implícita

Ninguna operación del encuentro crea o modifica automáticamente una relación médico-paciente.

### I-012 — Sin creación por CANCELLED/NO_SHOW

Una cita cancelada o marcada `NO_SHOW` no genera `ClinicalEncounter`.

---

## 29. Invariantes de contenido

### I-013 — Obligatorios para completar

Los cinco campos requeridos deben contener contenido clínico válido al completar.

### I-014 — Placeholders no son contenido

Un placeholder conocido no satisface un campo obligatorio.

### I-015 — Sin longitud mínima arbitraria

No se impone un número mínimo genérico de caracteres.

### I-016 — No evaluación semántica

El agregado no valida la corrección ni suficiencia médica del texto.

### I-017 — Guardado parcial permitido

Un encuentro `IN_PROGRESS` puede persistirse con campos requeridos aún incompletos.

---

## 30. Invariantes de autorización relevantes al dominio

El dominio debe asumir que las operaciones clínicas pasan por una autorización explícita.

### I-018 — Solo médico asignado modifica

Mientras el encuentro esté abierto, únicamente el médico asignado puede modificarlo según la política funcional cerrada.

### I-019 — Completar requiere actor autorizado

No se puede completar un encuentro por el mero hecho de que los campos estén completos; también debe cumplirse la autorización.

### I-020 — Cambio de identidad no permitido

Un actor autorizado para editar no obtiene por ello capacidad para cambiar la identidad estructural del encuentro.

La matriz detallada de lectura y otras capacidades se define fuera de este documento.

---

## 31. Múltiples consultas del mismo paciente

Un paciente puede tener múltiples `ClinicalEncounter` a lo largo del tiempo.

Ejemplo:

```text
Patient P1
├── Appointment A1 → Encounter E1 → COMPLETED
├── Appointment A2 → Encounter E2 → COMPLETED
└── Appointment A3 → Encounter E3 → IN_PROGRESS
```

El historial clínico se entiende como el conjunto histórico de encuentros y otros elementos clínicos relacionados, no como una única fila mutable que se sobreescribe en cada consulta.

---

## 32. Relación conceptual con MedicalRecord

Fase 3 reconoce la necesidad de `MedicalRecord`, pero no debe convertirlo en duplicado de `ClinicalEncounter`.

### 32.1 Distinción

```text
MedicalRecord
    │
    └── historial clínico del paciente
          │
          ├── ClinicalEncounter
          ├── Prescription
          ├── StudyOrder
          ├── ClinicalAlert
          └── otros componentes futuros
```

### 32.2 ClinicalEncounter como episodio

`ClinicalEncounter` representa un episodio específico de atención.

### 32.3 MedicalRecord como contenedor conceptual del historial

`MedicalRecord` representa la identidad y continuidad del expediente clínico del paciente.

No debe copiar en masa todos los campos del encuentro para crear una segunda fuente de verdad.

---

## 33. Proyección histórica

El dominio está diseñado para que la consulta sea histórica.

Un encuentro `COMPLETED` debe poder responder al menos:

- qué paciente fue atendido;
- qué médico realizó la consulta;
- en qué cita se originó;
- en qué clínica ocurrió;
- cuándo inició;
- cuándo se completó;
- qué contenido clínico fue registrado;
- qué contenido fue modificado antes del cierre, de acuerdo con el modelo de auditoría futuro.

Esto no significa que el encuentro tenga que contener toda la información del episodio médico para siempre; significa que su propio contenido cerrado debe conservarse.

---

## 34. Reglas de modificación por estado

| Operación | IN_PROGRESS | COMPLETED |
|---|---:|---:|
| Leer encuentro | sujeto a autorización | sujeto a autorización |
| Editar campos clínicos | Sí, médico asignado | No |
| Guardar parcial | Sí | No |
| Completar | Sí, si cumple reglas | No |
| Retomar | Sí | No |
| Reabrir | No aplica | No |
| Cambiar Appointment | No | No |
| Cambiar Patient | No | No |
| Cambiar Doctor | No | No |
| Cambiar Clinic | No | No |
| DELETE funcional | No | No |

---

## 35. Comandos de dominio previstos

Los nombres concretos de clases y métodos se decidirán durante `clinical-service-contracts.md`, pero conceptualmente se requieren operaciones equivalentes a las siguientes.

### 35.1 Iniciar

```text
StartClinicalEncounter
```

Responsabilidad:

- validar precondiciones;
- verificar actor;
- cambiar `Appointment` a `IN_CONSULTATION`;
- crear `ClinicalEncounter` en `IN_PROGRESS`;
- hacerlo atómicamente;
- ser idempotente frente a reintentos.

### 35.2 Guardar

```text
SaveClinicalEncounter
```

Responsabilidad:

- localizar el encuentro;
- verificar estado abierto;
- autorizar al médico asignado;
- persistir el contenido enviado;
- actualizar `updated_at`;
- conservar `IN_PROGRESS`.

### 35.3 Completar

```text
CompleteClinicalEncounter
```

Responsabilidad:

- verificar autorización;
- validar los cinco campos obligatorios;
- persistir los últimos cambios enviados;
- establecer `completed_at`;
- pasar el encuentro a `COMPLETED`;
- pasar la cita a `COMPLETED`;
- realizar todo en una sola transacción.

### 35.4 Leer

La lectura no debe expresarse como un `GET` sin autorización. Debe existir una operación o servicio de consulta que respete las políticas de privacidad y acceso clínico.

---

## 36. Errores de dominio previstos

Los nombres exactos se cerrarán en `clinical-service-contracts.md`, pero el dominio debe distinguir al menos:

```text
AppointmentNotFound
AppointmentNotInitiable
AppointmentAlreadyCompleted
AppointmentCancelled
AppointmentNoShow
ActorNotAssignedDoctor
EncounterAlreadyExists
EncounterNotFound
EncounterNotInProgress
EncounterAlreadyCompleted
EncounterImmutable
ClinicalContentIncomplete
ClinicalContentPlaceholder
AppointmentEncounterMismatch
ConcurrentClinicalTransition
UnauthorizedClinicalModification
```

Los errores deben reflejar reglas de negocio, no detalles internos de SQL.

**Resolución final (auditoría de cierre, 2026-09-11):** `clinical-service-contracts.md` §19 cerró esta lista consolidando varios candidatos en categorías más genéricas. En particular: `EncounterAlreadyExists` se descarta por completo (un segundo inicio es éxito idempotente, no un error — §12); `ActorNotAssignedDoctor` se consolida en `ClinicalNotAuthorized` (SC-132); `ClinicalContentIncomplete`/`ClinicalContentPlaceholder` se mantienen como dos excepciones distinguibles (`IncompleteClinicalContent`/`ClinicalContentPlaceholder`, SC-137/SC-137a) para que la API pueda distinguir "campo vacío" de "campo con placeholder". El resto de nombres exactos vive en `clinical-service-contracts.md` §19, que es la fuente autoritativa final.

---

## 37. Concurrencia

La concurrencia es parte del diseño del dominio, no un detalle posterior.

### 37.1 Inicio concurrente

Dos operaciones simultáneas no deben crear dos encuentros.

### 37.2 Guardado concurrente

La implementación deberá definir en `clinical-service-contracts.md` y `clinical-api-contracts.md` la estrategia concreta de concurrencia para modificaciones concurrentes. En Fase 3, la garantía mínima es que el estado final sea consistente y no permita modificar un encuentro ya cerrado.

### 37.3 Completar concurrentemente

Dos solicitudes de completar no deben producir dos cierres independientes.

La primera operación válida que cierre el encuentro debe impedir una segunda modificación posterior.

### 37.4 Guardar frente a completar

Una solicitud que intente guardar después de que el cierre se haya confirmado debe ser rechazada.

La autoridad es el estado persistido, no el estado visual del navegador.

---

## 38. Consistencia cruzada con Appointment

Dado que el agregado clínico depende de la Agenda para iniciar y completar, existen invariantes cruzados.

### 38.1 Antes del inicio

```text
Appointment = SCHEDULED
Encounter = inexistente
```

### 38.2 Durante la consulta

```text
Appointment = IN_CONSULTATION
Encounter = IN_PROGRESS
```

### 38.3 Después del cierre

```text
Appointment = COMPLETED
Encounter = COMPLETED
```

### 38.4 Estados inválidos

Los siguientes estados son inconsistentes como resultado de operaciones normales:

```text
Appointment = IN_CONSULTATION
Encounter = inexistente
```

```text
Appointment = COMPLETED
Encounter = IN_PROGRESS
```

```text
Appointment = CANCELLED
Encounter = IN_PROGRESS
```

```text
Appointment = NO_SHOW
Encounter = IN_PROGRESS
```

Estos estados deben ser prevenidos por las transacciones de dominio.

---

## 39. Integridad de base de datos

La implementación deberá traducir a PostgreSQL, donde sea posible, las invariantes estructurales.

### 39.1 Restricciones esperadas

Como mínimo conceptual:

```text
appointment_id NOT NULL
UNIQUE(appointment_id)
status ∈ {IN_PROGRESS, COMPLETED}
```

Y restricciones equivalentes para la semántica de timestamps cuando sean expresables sin crear conflictos con la lógica transaccional.

### 39.2 Responsabilidad dividida

La base de datos debe proteger:

- unicidad;
- nulabilidad estructural;
- estados permitidos;
- consistencia básica.

La capa de dominio debe proteger:

- autorización;
- contenido clínico real;
- transiciones válidas;
- coordinación con `Appointment`;
- semántica de negocio.

---

## 40. Separación de responsabilidades

### 40.1 Appointment

Es responsable de:

- agenda;
- disponibilidad;
- programación;
- estado de cita;
- reglas de cancelación y `NO_SHOW`;
- asignación de médico según el dominio de Agenda.

### 40.2 ClinicalEncounter

Es responsable de:

- registro de la atención iniciada;
- contenido clínico del encuentro;
- estado `IN_PROGRESS`/`COMPLETED`;
- guardado parcial;
- validación de cierre;
- inmutabilidad posterior al cierre.

### 40.3 MedicalRecord

Será responsable del expediente/historial clínico más amplio.

Su contrato detallado se definirá después de cerrar el núcleo del encuentro.

### 40.4 DoctorPatientRelationship

Es responsable de la relación longitudinal médico-paciente.

No debe utilizarse como sustituto de la cita ni del encuentro.

---

## 41. Protección contra duplicación de conceptos

Antes de agregar un nuevo campo o entidad al dominio debe preguntarse:

1. ¿Ya existe en `Patient`, `Doctor`, `Clinic` o `Appointment`?
2. ¿Es realmente propio del episodio clínico?
3. ¿Debe formar parte del núcleo genérico o de una especialidad?
4. ¿Es histórico o solo una proyección?
5. ¿Debe pertenecer realmente a `MedicalRecord`?

El objetivo es evitar dos fuentes contradictorias de verdad.

---

## 42. No CRUD genérico

El dominio no debe diseñarse como:

```text
POST /clinical-encounters/
GET /clinical-encounters/
PUT /clinical-encounters/{id}
DELETE /clinical-encounters/{id}
```

sin reglas de negocio.

Los endpoints y servicios deben expresar operaciones clínicas específicas y respetar el ciclo de vida.

Un CRUD genérico permitiría potencialmente:

- crear encuentros sin cita;
- cambiar de médico;
- reubicar un encuentro entre pacientes;
- reabrir una consulta;
- borrar historia clínica;
- modificar encuentros completados.

Todo ello está prohibido por el dominio de Fase 3.

---

## 43. Extensibilidad sin contaminar el núcleo

El dominio genérico debe poder evolucionar sin convertir `ClinicalEncounter` en una colección de campos específicos de una sola especialidad.

### 43.1 Núcleo estable

Los cinco campos mínimos y el ciclo de vida forman el núcleo estable de Fase 3.

### 43.2 Extensiones futuras

Las necesidades específicas podrán incorporarse mediante:

- entidades clínicas especializadas;
- módulos por especialidad;
- formularios específicos;
- relaciones con estudios;
- prescripciones;
- alertas;
- documentos;
- estructuras clínicas aprobadas posteriormente.

### 43.3 Criterio

Una extensión no debe modificar silenciosamente el significado de `IN_PROGRESS` o `COMPLETED`.

---

## 44. Relación con ClinicalAlert, Prescription y StudyOrder

La arquitectura general de TeCuidoApp contempla conceptos como:

```text
ClinicalAlert
Prescription
StudyOrder
```

En Fase 3, estos conceptos no forman parte automática del mínimo de `ClinicalEncounter`.

Un encuentro puede relacionarse con ellos en fases posteriores, pero su existencia no debe convertirse en requisito para completar la consulta genérica.

Ejemplo conceptual futuro:

```text
ClinicalEncounter
    ├── Prescription 0..N
    ├── StudyOrder 0..N
    └── ClinicalAlert 0..N
```

La cardinalidad y el comportamiento exactos deberán definirse en los documentos correspondientes.

---

## 45. Auditoría e historial

El dominio debe ser compatible con una capa de auditoría clínica, pero no debe mezclar el log de auditoría con los campos clínicos del encuentro.

La auditoría deberá poder establecer, como mínimo en la fase correspondiente:

- quién inició;
- quién guardó;
- quién completó;
- cuándo ocurrieron las operaciones;
- qué operación se intentó;
- qué resultado tuvo.

La decisión detallada sobre qué valores históricos se conservan, cómo se consultan y qué operaciones generan eventos se documentará en `clinical-audit-and-history.md`.

---

## 46. Privacidad y acceso

El encuentro contiene información clínica y, por tanto, su acceso debe pasar por políticas de privacidad y autorización.

Este documento no cierra quién puede leer el contenido clínico completo entre distintos médicos; esa decisión pertenece a:

```text
clinical-permissions.md
clinical-security-and-privacy.md
```

Lo que sí queda cerrado aquí es que:

- leer y modificar son capacidades distintas;
- tener acceso funcional a la Agenda no equivale automáticamente a tener acceso a todo el contenido clínico;
- el médico asignado tiene la capacidad de modificación mientras el encuentro está abierto, sujeto a la matriz de permisos.

---

## 47. Reglas de no inferencia

El dominio debe ser deliberadamente pasivo respecto de decisiones médicas.

No debe inferir automáticamente:

- un diagnóstico a partir del texto;
- una indicación médica;
- una contraindicación;
- una urgencia clínica;
- una receta;
- un estudio indicado;
- una recomendación terapéutica.

El sistema registra y estructura lo que el profesional decide.

Las alertas clínicas automáticas, si se introducen en una fase futura, necesitarán reglas explícitas y separadas.

---

## 48. Contrato conceptual de la entidad

**Corrección de consistencia (auditoría de cierre, 2026-09-11):** una redacción anterior de esta sección usaba nombres distintos a los ya fijados por `docs/adr/ADR-012-explicit-clinical-fields.md` (Accepted) para los cinco campos obligatorios — `current_illness`, `physical_examination`, `assessment_diagnosis`, `plan_instructions` — lo que permitió que documentos posteriores (`clinical-data-model.md`, `clinical-service-contracts.md`) inventaran cada uno su propia variante adicional. Se corrige: los nombres de columna de los cinco campos obligatorios son los de ADR-012, sin variación, y dejan de considerarse "conceptuales" para ese punto específico.

La entidad puede expresarse conceptualmente como:

```text
ClinicalEncounter {
    id
    appointment
    patient
    doctor
    clinic

    status

    reason_for_visit
    present_illness
    physical_exam
    assessment
    plan

    vital_signs              [optional]
    weight                   [optional]
    height                   [optional]
    relevant_history         [optional]
    studies                  [optional]
    observations             [optional]

    created_at
    started_at
    updated_at
    completed_at             [nullable until COMPLETED]
}
```

Los nombres de los cinco campos obligatorios (`reason_for_visit`, `present_illness`, `physical_exam`, `assessment`, `plan`) son definitivos y provienen de ADR-012 — no deben renombrarse en documentos posteriores sin reabrir ese ADR.

La lista anterior sigue siendo conceptual únicamente respecto de lo que no pretende cerrar todavía:

- tipos Django;
- tamaño de campos;
- índices secundarios;
- `choices` concretos;
- constraints definitivos;
- serializers;
- nombres definitivos de los campos opcionales (`vital_signs`, `weight`, `height`, `relevant_history`, `studies`, `observations`), que sí pueden ajustarse en el diseño técnico posterior.

Estos elementos pertenecen al diseño técnico posterior.

---

## 49. Reglas de asignación de valores estructurales

### 49.1 Al crear

Al iniciar:

```text
appointment = Appointment seleccionada
patient = appointment.patient
    doctor = appointment.doctor
clinic = appointment.clinic
status = IN_PROGRESS
created_at = now
started_at = now
completed_at = null
```

La separación entre `created_at` y `started_at` se mantiene aunque inicialmente puedan resultar iguales en una implementación, porque representan conceptos distintos.

### 49.2 Durante guardado

```text
updated_at = now
status = IN_PROGRESS
```

No se debe modificar la identidad estructural.

### 49.3 Al completar

```text
status = COMPLETED
completed_at = now
updated_at = now
```

La operación debe sincronizar el estado de `Appointment` dentro de la misma transacción.

---

## 50. Regla sobre created_at y started_at

Aunque el encuentro se crea como parte de la acción de iniciar consulta, los campos tienen semántica distinta.

- `created_at` = cuándo se creó la entidad.
- `started_at` = cuándo inició realmente la atención.

En la implementación normal de Fase 3 ambos podrán generarse dentro de la misma operación transaccional y por tanto pueden quedar iguales o prácticamente iguales.

No deben fusionarse conceptualmente porque futuras necesidades de auditoría podrían requerir distinguirlos.

---

## 51. Regla sobre updated_at

`updated_at` es una marca de persistencia, no una marca del inicio ni del fin de la consulta.

Debe actualizarse en cada guardado exitoso.

No debe actualizarse por:

- una mera lectura;
- apertura de la pantalla sin modificación;
- intento fallido de guardado;
- intento rechazado de modificar un encuentro completado.

La implementación definitiva deberá precisar el comportamiento exacto ante operaciones que no cambien valores pero sí procesen un comando de guardado.

---

## 52. Regla de cierre definitivo

Una vez que:

```text
ClinicalEncounter.status == COMPLETED
```

el estado pasa a considerarse un hecho histórico.

No existe una transición de salida en Fase 3.

Por tanto, el grafo de estados es:

```text
                 +------------------+
                 |                  |
Appointment      |  create/start    v
SCHEDULED ---------------------- IN_PROGRESS
                                      |
                                      | complete
                                      v
                                  COMPLETED
                                      |
                                      | no outbound transition
                                      X
```

---

## 53. Casos nominales del dominio

### Caso A — Consulta normal

```text
1. Appointment = SCHEDULED
2. Médico asignado inicia
3. Appointment = IN_CONSULTATION
4. ClinicalEncounter = IN_PROGRESS
5. Médico guarda contenido
6. Médico completa
7. Validación de cinco campos pasa
8. ClinicalEncounter = COMPLETED
9. Appointment = COMPLETED
```

### Caso B — Consulta con varios guardados

```text
Start
  ↓
Save
  ↓
Save
  ↓
Save
  ↓
Complete
```

Todos los guardados dejan el encuentro `IN_PROGRESS` hasta el cierre.

### Caso C — Consulta interrumpida

```text
Start
  ↓
Save
  ↓
Interrupción
  ↓
Resume
  ↓
Save
  ↓
Complete
```

No se crea un segundo encuentro.

### Caso D — Doble clic de inicio

```text
Request 1 ─┐
           ├─→ único ClinicalEncounter
Request 2 ─┘
```

### Caso E — Intento de completar con campos inválidos

```text
Complete
   ↓
validation fails
   ↓
encounter remains IN_PROGRESS
```

La consulta no se cierra parcialmente.

---

## 54. Casos inválidos del dominio

Los siguientes comportamientos no forman parte del dominio:

### 54.1 Crear encuentro sin cita

```text
ClinicalEncounter created without Appointment
```

Inválido.

### 54.2 Dos encuentros para una cita

Inválido.

### 54.3 Crear por NO_SHOW

Inválido.

### 54.4 Completar con placeholders

Inválido.

### 54.5 Cambiar médico durante consulta

Inválido como modificación clínica del encuentro.

### 54.6 Reabrir completado

Inválido en Fase 3.

### 54.7 Eliminar encuentro

Inválido funcionalmente.

### 54.8 Cerrar por timeout

Inválido.

### 54.9 Cerrar porque terminó la hora programada

Inválido.

### 54.10 Crear automáticamente DoctorPatientRelationship

Inválido.

---

## 55. Decisiones técnicas deliberadamente abiertas

Las siguientes cuestiones pertenecen a documentos posteriores y no deben resolverse por accidente en el modelo:

- nombres exactos de métodos de servicio;
- nombres exactos de endpoints;
- formato de errores HTTP;
- serializers;
- permisos detallados de lectura;
- roles con acceso clínico de solo lectura;
- detalles de auditoría;
- índices de búsqueda clínica;
- paginación del historial;
- campos especializados;
- attachments/documentos;
- catálogo CIE-10;
- interoperabilidad futura.

Mantenerlas abiertas evita congelar decisiones antes de tiempo.

---

## 56. Criterios de aceptación del dominio

El dominio `ClinicalEncounter` se considera correctamente definido para implementación cuando se cumple todo lo siguiente:

- [x] Existe una definición única del concepto `ClinicalEncounter`.
- [x] La cardinalidad es `Appointment 1 ─── 0..1 ClinicalEncounter`.
- [x] La `Appointment` es obligatoria.
- [x] El encuentro no se crea sin una cita.
- [x] Solo el médico asignado inicia la consulta.
- [x] El inicio produce `Appointment → IN_CONSULTATION` y `ClinicalEncounter → IN_PROGRESS` de forma atómica.
- [x] El inicio es idempotente.
- [x] Se permite más de un encuentro abierto para un mismo médico cuando corresponden a citas distintas.
- [x] Se permite guardado parcial.
- [x] `updated_at` representa el último guardado exitoso.
- [x] Una interrupción no cierra automáticamente la consulta.
- [x] `CANCELLED` y `NO_SHOW` no crean encuentro.
- [x] Una cita en `IN_CONSULTATION` no puede pasar a `CANCELLED` o `NO_SHOW`.
- [x] El diagnóstico es texto libre.
- [x] No se exige CIE-10.
- [x] Los cinco campos mínimos se validan al completar.
- [x] Placeholders no satisfacen los campos obligatorios.
- [x] No existe longitud mínima arbitraria.
- [x] No se evalúa la corrección médica del contenido.
- [x] Completar persiste los últimos cambios enviados.
- [x] El cierre `ClinicalEncounter COMPLETED + Appointment COMPLETED` es atómico.
- [x] `COMPLETED` es inmutable.
- [x] No existe DELETE funcional.
- [x] `DoctorPatientRelationship` permanece independiente.

---

## 57. Matriz resumen del dominio

| Tema | Decisión Fase 3 |
|---|---|
| Origen | `Appointment` |
| Cardinalidad | `1 : 0..1` |
| Creación | al iniciar consulta |
| Actor de inicio | médico asignado |
| Estado abierto | `IN_PROGRESS` |
| Estado cerrado | `COMPLETED` |
| Guardado parcial | permitido |
| Autosave | no requerido |
| Interrupción | permanece abierto |
| Reanudación | permitida |
| Múltiples abiertos por médico | sí, para citas distintas |
| Cancelación del encuentro | no existe |
| NO_SHOW del encuentro | no existe |
| Diagnóstico | texto libre |
| CIE-10 | fuera de alcance |
| Mínimo de cierre | 5 campos clínicos |
| Placeholders | inválidos |
| Longitud mínima arbitraria | no |
| Evaluación médica automática | no |
| Cierre automático | no |
| Reapertura | no |
| DELETE funcional | no |
| DoctorPatientRelationship | independiente |
| Cierre cruzado | atómico con Appointment |
| Duración | derivada de `started_at`/`completed_at` |

---

## 58. Próximos documentos

Con este documento queda definido el dominio conceptual de `ClinicalEncounter`.

La siguiente secuencia de diseño de Fase 3 continúa con:

```text
clinical-record-domain.md
clinical-data-model.md
clinical-permissions.md
clinical-security-and-privacy.md
clinical-service-contracts.md
clinical-api-contracts.md
phase-3-clinical-ux.md
clinical-screens.md
clinical-audit-and-history.md
phase-3-testing-strategy.md
ADRs de Fase 3
```

El siguiente documento inmediato de acuerdo con el orden aprobado es:

**`clinical-record-domain.md`**

---

## 59. Estado de cierre

**Dominio `ClinicalEncounter`: cerrado para pasar a diseño de `MedicalRecord` y modelo de datos.**

Las decisiones aquí descritas deben considerarse normativas para la implementación de Fase 3, salvo modificación explícita y documentada posterior.

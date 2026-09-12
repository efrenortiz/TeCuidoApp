# Fase 3 — Clinical Data Model

**Documento de modelo de datos clínicos**  
**Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11 — ver §37/§41 y las correcciones de nombres de campo aplicadas en esta misma revisión)  
**Fecha:** 2026-09-11  
**Aplicación prevista:** `medical_records`  
**Dominio:** expediente clínico longitudinal y encuentro clínico genérico

---

## 1. Propósito

Este documento traduce las decisiones funcionales y de dominio de Fase 3 a un modelo de datos concreto para TeCuidoApp.

No pretende implementar todavía los modelos Django ni las migraciones. Su objetivo es cerrar las decisiones estructurales que deben preceder a la implementación:

- qué entidades existen;
- cuál es la identidad de cada una;
- qué relaciones son obligatorias;
- qué datos son fuente de verdad;
- qué campos son opcionales;
- qué valores deben tener constraints de base de datos;
- qué información no debe duplicarse;
- qué índices y garantías de integridad son necesarios;
- qué partes pertenecen a futuras entidades clínicas y no al núcleo F3.

El criterio rector es el mismo utilizado en `clinical-encounter-domain.md` y `clinical-record-domain.md`: **modelo explícito, pequeño, relacional, trazable y sin JSON clínico genérico como sustituto de un diseño de dominio.**

---

## 2. Fuentes normativas

Este documento se debe leer junto con:

```text
phase-3-clinical-encounter.md
clinical-encounter-workflow.md
clinical-encounter-rules.md
clinical-encounter-domain.md
clinical-record-domain.md
requirements.md
docs/architecture.md
docs/adr/ADR-005-django-app-boundaries.md
docs/adr/ADR-006-database-integrity-and-transactions.md
```

### 2.1 Jerarquía

En caso de contradicción:

1. decisión funcional explícita más reciente de Fase 3;
2. `phase-3-clinical-encounter.md` y documentos de políticas F3;
3. dominio de `ClinicalEncounter` y `MedicalRecord`;
4. requisitos generales del proyecto;
5. documentación arquitectónica previa.

Una decisión específica de Fase 3 sustituye una regla anterior únicamente en aquello que realmente contradice.

---

# 3. Políticas pendientes y propuesta de cierre

Las siguientes políticas constituyen la propuesta de cierre del modelo físico-lógico.

La etiqueta **PROPUESTA** indica que se recomienda convertirla en decisión normativa al cerrar este documento.

---

## DM-001 — Aplicación propietaria del modelo clínico

**PROPUESTA:** el núcleo clínico de Fase 3 se implementará dentro de una aplicación Django `medical_records`.

La aplicación podrá contener inicialmente:

- `MedicalRecord`;
- `ClinicalEncounter`;
- servicios y validadores propios del dominio.

Entidades futuras como `Prescription`, `StudyOrder`, `ClinicalAlert` y `ClinicalDocument` podrán incorporarse en la misma aplicación o separarse posteriormente según sus límites, sin cambiar la identidad conceptual del expediente.

---

## DM-002 — No duplicar entidades canónicas existentes

El modelo clínico no creará versiones clínicas paralelas de:

- `Patient`;
- `Doctor`;
- `Clinic`;
- `Appointment`.

Las relaciones deberán utilizar claves foráneas a las entidades canónicas existentes.

**Razón:** una segunda tabla de pacientes, médicos o citas produciría dos fuentes de verdad y haría ambiguos permisos, auditoría e historial.

---

## DM-003 — Identidad técnica

Las entidades clínicas tendrán una identidad primaria propia administrada por Django/PostgreSQL.

No se utilizarán CURP, correo electrónico, nombre, número de cita ni combinación de campos funcionales como primary key.

---

## DM-004 — UUID versus entero

**PROPUESTA:** para Fase 3 se recomienda conservar la estrategia de primary key ya establecida por el proyecto, sin introducir UUID solamente para las entidades clínicas.

Si las entidades canónicas existentes utilizan enteros, `MedicalRecord` y `ClinicalEncounter` deberán utilizar el mismo criterio salvo que exista una razón arquitectónica documentada para cambiarlo.

**Razón:** uniformidad y simplicidad pesan más que introducir un mecanismo de identificación diferente sin requerimiento funcional.

---

# 4. Entidad `MedicalRecord`

## DM-005 — Una instancia por paciente

Modelo conceptual:

```text
Patient 1 ─── 1 MedicalRecord
```

Estado técnico transitorio antes de la creación lazy:

```text
Patient 1 ─── 0..1 MedicalRecord
```

La relación física será:

```text
MedicalRecord.patient_id → Patient.id
```

con `patient_id` obligatorio y `UNIQUE`.

**Redacción normativa (idéntica a `ADR-011` y `clinical-record-domain.md` CR-001, revisión de consistencia 2026-09-11):**

> Conceptualmente cada `Patient` tiene un único `MedicalRecord`. En persistencia, el registro puede no existir todavía porque su creación es lazy. Por eso el estado técnico previo a su creación puede representarse como `Patient 1 ─── 0..1 MedicalRecord`. Una vez creado, el `MedicalRecord` es único, no se duplica y no cambia de `Patient`. El `0..1` es exclusivamente un estado técnico transitorio anterior a la primera operación clínica — nunca una cardinalidad funcional permanente que permita a un paciente quedar sin expediente después de haber iniciado atención clínica.

---

## DM-006 — Creación lazy

La aplicación no necesita crear un expediente vacío durante el alta administrativa de cada paciente.

La primera operación clínica que requiera expediente podrá crearlo.

En F3, la primera operación prevista es el inicio de un `ClinicalEncounter`.

---

## DM-007 — Creación idempotente

Si dos solicitudes concurrentes intentan crear el expediente para el mismo paciente, sólo una fila debe sobrevivir.

La garantía principal debe ser la restricción única de `patient_id`, no una comprobación de aplicación aislada.

---

## DM-008 — Creación atómica con primer encuentro

Cuando un primer encuentro clínico crea el expediente, la operación debe ejecutarse dentro de la misma transacción que:

1. obtiene o crea `MedicalRecord`;
2. cambia la cita a `IN_CONSULTATION`;
3. crea `ClinicalEncounter` como `IN_PROGRESS`.

Un fallo intermedio debe provocar rollback completo.

---

## DM-009 — No existe estado de `MedicalRecord` en F3

No se almacenará un campo `status` para `MedicalRecord`.

No se introducen en F3 estados como `OPEN`, `CLOSED`, `ARCHIVED` o `CANCELLED`.

La continuidad del expediente no depende del estado administrativo del paciente.

---

## DM-010 — No borrado funcional

`MedicalRecord` no tendrá una operación funcional de `DELETE`.

A nivel de base de datos se recomienda `on_delete=PROTECT` en la relación hacia `Patient`, para impedir que una eliminación accidental del paciente arrastre el expediente.

---

## DM-011 — No reasignación

Un `MedicalRecord` no puede cambiar de paciente una vez creado.

El vínculo `patient_id` es inmutable desde la perspectiva del dominio.

---

## DM-012 — `created_at` del expediente

`created_at` significa el momento en que la fila del expediente fue persistida por primera vez.

No representa:

- fecha de nacimiento del paciente;
- primera cita agendada;
- fecha de primera atención histórica fuera de TeCuidoApp;
- fecha de ingreso administrativo del paciente.

---

## DM-013 — `updated_at` del expediente

`updated_at` representa la última modificación exitosa de **datos propios del `MedicalRecord`**.

La modificación de un `ClinicalEncounter` hijo no debe actualizar automáticamente `MedicalRecord.updated_at`.

**Razón:** evita que el campo sea ambiguo y permite distinguir cambios del expediente de actividad clínica de sus hijos.

---

# 5. Campos de `MedicalRecord`

## DM-014 — Modelo explícito

Los datos longitudinales de Fase 3 se representarán mediante campos explícitos.

No se utilizará:

```text
metadata = JSON
clinical_history = JSON
extra_fields = JSON
```

como mecanismo genérico para almacenar la historia clínica.

---

## DM-015 — Campos longitudinales iniciales

**PROPUESTA:** el primer modelo genérico de `MedicalRecord` puede incluir únicamente estas secciones abiertas y explícitas:

| Campo | Tipo lógico | Obligatorio | Semántica |
|---|---|---:|---|
| `family_history` | texto largo | No | Antecedentes heredofamiliares |
| `personal_pathological_history` | texto largo | No | Antecedentes personales patológicos |
| `personal_non_pathological_history` | texto largo | No | Antecedentes personales no patológicos |
| `housing_history` | texto largo | No | Tipo y condiciones de vivienda relevantes |
| `other_relevant_history` | texto largo | No | Otros antecedentes clínicos relevantes |

Estos campos pueden permanecer vacíos hasta que exista información clínica.

---

## DM-016 — Antecedentes gineco-obstétricos

Los requisitos generales contemplan antecedentes gineco-obstétricos, pero el núcleo F3 debe permanecer genérico.

**PROPUESTA:** no convertir Fase 3 core en un modelo gineco-obstétrico especializado mediante una docena de columnas específicas.

Se recomienda inicialmente:

- conservar un campo explícito `gynecologic_obstetric_history` si ya fue aceptado como parte del contrato de `MedicalRecord`;
- pero tratarlo como **sección especializada del expediente**, no como un conjunto obligatorio para todos los pacientes;
- reservar una futura descomposición estructurada de embarazos, partos, abortos, gestaciones actuales, etc. para una fase de especialidad.

Esto permite cumplir el requerimiento vigente sin contaminar el núcleo con reglas de obstetricia.

---

## DM-017 — Datos personales del paciente

No se copiarán dentro de `MedicalRecord`:

- nombre;
- fecha de nacimiento;
- sexo;
- nacionalidad;
- CURP;
- datos de contacto administrativos.

La fuente de verdad seguirá siendo `Patient` → `Person`.

---

## DM-018 — Tipo sanguíneo

`Patient.blood_type` ya existe en el modelo actual.

**PROPUESTA:** Fase 3 lo utilizará como dato canónico del paciente en lugar de crear `MedicalRecord.blood_type`.

Si posteriormente se necesita registrar determinaciones históricas o confirmar el tipo sanguíneo mediante estudios, eso deberá resolverse con una entidad clínica específica, no duplicando el campo.

---

## DM-019 — Alergias

`Patient.allergies` ya existe como texto.

**PROPUESTA:** durante la primera implementación F3 se mantiene como fuente administrativa/actual existente y el modelo no crea una segunda columna duplicada en `MedicalRecord`.

La futura `ClinicalAlert` podrá representar una alergia clínica activa como alerta estructurada.

La eventual migración de `Patient.allergies` hacia una entidad `Allergy` estructurada queda fuera del alcance de este modelo y deberá realizarse con una política explícita de migración.

---

## DM-020 — Enfermedades crónicas

`Patient.chronic_conditions` ya existe.

No se duplicará automáticamente como `MedicalRecord.chronic_conditions`.

En F3 la información longitudinal nueva podrá documentarse en antecedentes o encuentros, mientras la migración de este campo administrativo hacia un componente clínico estructurado se reserva para una evolución posterior.

---

## DM-021 — Medicamentos actuales

`Patient.current_medications` ya existe.

No se creará una segunda columna `MedicalRecord.current_medications` sólo para satisfacer el resumen clínico.

El resumen deberá mostrar este dato mientras siga siendo la fuente vigente.

Cuando exista `Prescription`, los medicamentos emitidos deberán conservarse en su propia entidad histórica. “Medicamentos actuales” será entonces una vista derivada, no un texto sobrescrito manualmente por cada consulta.

---

## DM-022 — Antecedentes quirúrgicos y hospitalizaciones

`Patient.surgical_history` y `Patient.relevant_hospitalizations` existen.

Fase 3 no duplicará estas columnas dentro del expediente.

La propuesta es mantenerlas como datos existentes hasta que una fase posterior requiera un modelo estructurado de procedimientos/hospitalizaciones.

---

## DM-023 — Resumen clínico no es una tabla base

No se creará una tabla `ClinicalSummary` en F3.

El resumen será una proyección de:

```text
Patient
MedicalRecord
ClinicalEncounter
ClinicalAlert
Prescription
StudyOrder
ClinicalDocument
```

según corresponda.

---

## DM-024 — No persistir datos derivados innecesariamente

No se almacenarán como copia permanente dentro del expediente datos que puedan calcularse de una fuente canónica, por ejemplo:

- edad;
- IMC;
- número de consultas;
- última consulta;
- último diagnóstico;
- “diagnóstico actual” inferido;
- cantidad de estudios.

Cuando sea necesario para rendimiento, un dato derivado sólo podrá persistirse mediante una decisión específica posterior y con reglas de invalidez/actualización explícitas.

---

# 6. Entidad `ClinicalEncounter`

## DM-025 — Identidad

`ClinicalEncounter` tiene identidad propia.

Un encuentro no es un campo dentro de `Appointment` ni una fila reutilizable de agenda.

---

## DM-026 — Relación con `Appointment`

Modelo:

```text
Appointment 1 ─── 0..1 ClinicalEncounter
```

Físicamente:

```text
ClinicalEncounter.appointment_id → Appointment.id
```

`appointment_id` es obligatorio y `UNIQUE`.

---

## DM-027 — Razón de unicidad

La unicidad de `appointment_id` garantiza:

```text
una cita iniciada → como máximo un encuentro clínico
```

Esto protege el idempotency requirement del inicio incluso bajo concurrencia.

---

## DM-028 — Relación con `Patient`

**Cerrado:** `ClinicalEncounter` no tiene `patient_id` duplicado (ya implementado como propiedad derivada — ver R-008).

El paciente se obtiene de:

```text
ClinicalEncounter → Appointment → Patient
```

La combinación de claves y transacción debe garantizar que el encuentro sólo pueda existir para el paciente de la cita.

---

## DM-029 — Relación con `Clinic`

**Cerrado:** `ClinicalEncounter` no tiene `clinic_id` redundante en F3 core (ya implementado como propiedad derivada).

El contexto de consultorio se obtiene de:

```text
ClinicalEncounter → Appointment → Clinic
```

Si en una fase futura se necesita conservar una fotografía de contexto independiente de cambios posteriores de una cita, deberá aprobarse explícitamente como snapshot histórico.

---

## DM-030 — Médico responsable

`ClinicalEncounter.doctor_id` será obligatorio.

El valor se establece a partir del médico asignado a la cita durante la creación del encuentro.

No habrá una relación separada `created_by`/`completed_by` en el encuentro para F3, de acuerdo con la decisión de dominio.

---

## DM-031 — Coherencia doctor-cita

Debe existir un invariante equivalente a:

```text
ClinicalEncounter.doctor_id == Appointment.doctor_id
```

La aplicación debe tratar esta igualdad como parte de la integridad del agregado.

No se permite crear un encuentro para la cita de un médico distinto al asignado.

---

## DM-032 — Estado del encuentro

Sólo se utilizarán:

```text
IN_PROGRESS
COMPLETED
```

No se almacenarán estados F3 como:

```text
DRAFT
PAUSED
CANCELLED
ABANDONED
NO_SHOW
```

La cancelación y el no-show pertenecen a `Appointment` y no generan encuentro.

---

## DM-033 — Campo `status`

`ClinicalEncounter.status` debe tener:

- choices de Django;
- constraint de base de datos que limite los valores válidos;
- sin `default` que oculte un error de creación.

La creación debe indicar explícitamente `IN_PROGRESS`.

---

## DM-034 — Cinco campos clínicos obligatorios al completar

**Corrección de consistencia (auditoría de cierre, 2026-09-11):** los nombres siguientes son ahora exactamente los de `docs/adr/ADR-012-explicit-clinical-fields.md` (Accepted) y de `clinical-encounter-domain.md` §48 corregido — no una variante propia de este documento.

El modelo deberá permitir registrar explícitamente:

1. `reason_for_visit` — motivo de consulta;
2. `present_illness` — padecimiento actual;
3. `physical_exam` — exploración física;
4. `assessment` — evaluación / diagnóstico;
5. `plan` — plan / indicaciones.

Todos son campos de texto largo.

En F3 no existe catálogo CIE-10 obligatorio.

---

## DM-035 — Campos clínicos opcionales

Se recomienda incluir inicialmente, sin convertirlos en requisitos de cierre:

| Campo | Tipo lógico |
|---|---|
| `vital_signs` | texto largo |
| `weight_kg` | decimal opcional |
| `height_cm` | decimal opcional |
| `relevant_history` | texto largo |
| `studies` | texto largo |
| `observations` | texto largo |

Estos campos no sustituyen los cinco mínimos.

---

## DM-036 — No JSON para campos de consulta

No se utilizará un único campo `clinical_data = JSON` para los datos de consulta.

La razón es mantener:

- nombres semánticos claros;
- validaciones simples;
- migraciones predecibles;
- consultas ORM normales;
- trazabilidad de cambios estructurales.

---

## DM-037 — Texto libre del diagnóstico

`assessment` es texto libre.

No se crea en F3 una tabla de diagnósticos ni una FK obligatoria a un catálogo diagnóstico.

Un catálogo futuro debe ser una decisión independiente y compatible con registros históricos.

---

# 7. Timestamps de `ClinicalEncounter`

## DM-038 — `created_at`

Momento en que el encuentro fue creado.

Debe quedar aproximadamente en el mismo flujo transaccional que el paso de la cita a `IN_CONSULTATION`.

---

## DM-039 — `started_at`

Momento real de inicio clínico.

No es una copia del `Appointment.start_at`.

Puede existir diferencia entre horario programado y momento real de inicio.

---

## DM-040 — `updated_at`

Momento de la última modificación exitosa persistida del encuentro mientras está abierto.

Debe cambiar tanto en un guardado parcial exitoso como en la última persistencia incluida en el cierre.

---

## DM-041 — `completed_at`

Momento en que la operación de cierre fue confirmada exitosamente.

Sólo debe existir cuando `status = COMPLETED`.

---

## DM-042 — Orden temporal

**Corrección de consistencia (auditoría de cierre, 2026-09-11):** a diferencia de las restricciones de solapamiento de Fase 2 (que no pueden expresarse como `CHECK` por depender de `now()`, no IMMUTABLE), esta es una comparación pura entre columnas ya persistidas — sí es expresable como `CHECK` constraint de PostgreSQL sin conflicto con la lógica transaccional. Se cierra como constraint obligatorio, no solo como meta de aplicación:

```text
CHECK (started_at >= created_at)
CHECK (completed_at IS NULL OR completed_at >= started_at)
```

Ambas deben implementarse como `CheckConstraint` de Django, siguiendo el mismo patrón ya usado en `appointments` (Fase 2) para invariantes estructurales expresables como comparación directa de columnas.

Se debe poder garantizar al menos:

```text
created_at <= started_at <= completed_at
```

cuando los tres valores existan.

`updated_at` puede ser posterior a `completed_at` solamente si existiera modificación posterior, pero tal modificación está prohibida por el dominio. Por ello, en condiciones normales un encuentro completado debe satisfacer también:

```text
updated_at >= completed_at
```

sin utilizar esa relación como constraint primaria de negocio.

---

## DM-043 — Zona horaria

Los timestamps persistidos deberán utilizar `DateTimeField` consciente de zona horaria, siguiendo la configuración temporal existente del proyecto.

El modelo clínico no debe guardar fechas clínicas críticas como texto.

---

# 8. Datos clínicos del encuentro

## DM-044 — No sobrescritura de historial

Cada `ClinicalEncounter` es una pieza histórica.

Cuando pasa a `COMPLETED`, sus campos no se deben modificar.

No se almacena una sola nota “actual” que vaya reemplazándose con la siguiente consulta.

---

## DM-045 — Guardado parcial

Mientras `status = IN_PROGRESS`, los campos clínicos pueden permanecer incompletos.

Por ello, los cinco campos obligatorios funcionales de cierre **no deben ser `NOT NULL` como requisito de creación**.

Se recomienda almacenarlos como strings permitiendo vacío durante el estado abierto.

La obligatoriedad se aplica en la operación de completar mediante validación de dominio.

---

## DM-046 — Contenido real

Los campos requeridos al completar deben pasar la normalización mínima definida en `clinical-encounter-rules.md`:

- trim de espacios iniciales y finales;
- vacío o sólo espacios = inválido;
- detección de placeholders obvios;
- comparación de placeholders sin depender de mayúsculas/minúsculas;
- variantes evidentes no deben eludir la validación.

No se almacena un resultado booleano adicional como `is_clinically_valid`.

---

## DM-047 — No evaluar calidad clínica

La base de datos no intentará determinar si un diagnóstico o plan es médicamente correcto.

No crear constraints de contenido que requieran lenguaje clínico, longitud mínima arbitraria o listas cerradas de términos.

---

# 9. Relaciones entre expediente y encuentros

## DM-048 — Relación lógica del expediente

Conceptualmente:

```text
MedicalRecord 1 ─── 0..N ClinicalEncounter
```

La existencia del vínculo no requiere una FK `medical_record_id` dentro de `ClinicalEncounter`.

Se mantiene por la cadena canónica:

```text
ClinicalEncounter → Appointment → Patient → MedicalRecord
```

---

## DM-049 — Motivo para evitar `medical_record_id` redundante

Duplicar:

```text
ClinicalEncounter.patient_id
ClinicalEncounter.appointment_id
ClinicalEncounter.medical_record_id
```

crearía tres caminos para determinar el paciente.

Eso abriría la posibilidad de inconsistencia:

```text
appointment.patient_id != medical_record.patient_id
```

La simplicidad recomendada es una única cadena de identidad.

---

## DM-050 — Historial ordenable

El historial clínico debe poder ordenarse por `started_at` y, como respaldo, por `created_at`/`id`.

Se recomienda un índice que facilite:

```text
Appointment.patient -> ClinicalEncounter
```

a través de consultas ORM con join, sin agregar redundancia sólo por conveniencia de lectura.

---

# 10. Constraints de base de datos

## DM-051 — `MedicalRecord.patient_id UNIQUE`

Constraint obligatorio:

```text
UNIQUE(patient_id)
```

---

## DM-052 — `ClinicalEncounter.appointment_id UNIQUE`

Constraint obligatorio:

```text
UNIQUE(appointment_id)
```

---

## DM-053 — FKs protegidas

**Cerrado:** se utiliza `PROTECT` en las relaciones clínicas con entidades cuya eliminación rompería la historia, especialmente:

- `MedicalRecord.patient`;
- `ClinicalEncounter.appointment`;
- `ClinicalEncounter.doctor`.

La elección final de `on_delete` debe evitar cascadas destructivas sobre historia clínica.

---

## DM-054 — Constraint de estado de encuentro

La base debe impedir valores ajenos a:

```text
IN_PROGRESS
COMPLETED
```

---

## DM-055 — Constraint de `completed_at`

**Cerrado:** se impone consistencia estructural mediante `CheckConstraint` de PostgreSQL:

```text
status = COMPLETED  => completed_at IS NOT NULL
status != COMPLETED => completed_at IS NULL
```

Esto evita estados físicamente contradictorios.

---

## DM-056 — Constraint de `started_at`

Como el encuentro se crea al iniciar la consulta:

```text
started_at IS NOT NULL
```

debe ser verdadero para todo `ClinicalEncounter` válido.

Por tanto, `started_at` puede modelarse como obligatorio en la fila, aunque el servicio sea responsable de asignarlo al crear el registro.

---

## DM-057 — Constraint de actor

`doctor_id` debe ser obligatorio.

No se permite un `ClinicalEncounter` sin médico asignado.

---

## DM-058 — Cinco campos no deben tener `NOT NULL`

No utilizar `NOT NULL` como mecanismo para los cinco campos obligatorios de cierre, porque contradice el guardado parcial.

El modelo debe distinguir:

```text
integridad estructural de fila
```

de:

```text
condiciones funcionales para completar
```

---

# 11. Coherencia con `Appointment`

## DM-059 — No duplicar estado de Appointment

`ClinicalEncounter` no almacena:

- `appointment_status`;
- `appointment_start`;
- `appointment_end`;
- `appointment_duration`.

Se leen desde `Appointment` cuando sean necesarias.

---

## DM-060 — No copiar duración de la cita

La duración programada pertenece a Agenda.

El encuentro clínico no requiere `duration_minutes` en F3.

La diferencia entre hora programada y duración real no gobierna el cierre.

---

## DM-061 — `IN_CONSULTATION` es frontera de dominio

La aplicación clínica sólo debe crear el encuentro como parte de la transición válida:

```text
Appointment.SCHEDULED
        ↓
Appointment.IN_CONSULTATION
        +
ClinicalEncounter.IN_PROGRESS
```

---

## DM-062 — No encuentro para estados terminales previos al inicio

Una cita `CANCELLED` o `NO_SHOW` no puede tener `ClinicalEncounter`.

El constraint principal reside en el servicio/transacción de creación y la unicidad de la relación protege el modelo físico contra duplicados.

---

## DM-063 — No cancelar/no-show después del inicio

La existencia de `ClinicalEncounter` implica que la cita ya está en frontera clínica.

No se permite que posteriormente la cita pase a `CANCELLED` o `NO_SHOW`.

La protección de esta regla pertenece al dominio de `Appointment`, pero el modelo clínico debe asumirla como invariante.

---

# 12. Atomicidad y concurrencia

## DM-064 — Inicio atómico

La creación del primer encuentro debe ser una operación transaccional única junto con el cambio de estado de la cita.

---

## DM-065 — Doble inicio concurrente

Dos solicitudes simultáneas de inicio deben producir como máximo un `ClinicalEncounter`.

La combinación recomendada es:

- `transaction.atomic()`;
- bloqueo de la fila de `Appointment` (`select_for_update()`);
- constraint `UNIQUE(appointment_id)`.

La protección de base de datos sigue siendo la última barrera.

---

## DM-066 — Segundo inicio idempotente

Una segunda solicitud equivalente sobre una cita ya iniciada no crea otra fila.

Debe localizar el encuentro existente y devolver su estado actual.

---

## DM-067 — Guardado versus completar

Las operaciones `save` y `complete` deben protegerse contra carreras.

La recomendación es bloquear el `ClinicalEncounter` mientras se comprueba su estado y se persiste el resultado.

---

## DM-068 — Completar dos veces

Si dos solicitudes intentan completar el mismo encuentro:

- sólo una puede realizar la transición a `COMPLETED`;
- la segunda no debe reescribir el encuentro ni crear un cierre alternativo.

---

## DM-069 — Petición después de completar

Un guardado posterior a `COMPLETED` debe ser rechazado por regla de dominio, aunque la petición se haya iniciado con una representación vieja del encuentro.

---

# 13. Actualizaciones y borrado

## DM-070 — `MedicalRecord` actualizable

Los campos propios del expediente longitudinal pueden modificarse mientras la política de permisos lo permita.

El contenido de un encuentro completado no puede utilizarse como mecanismo de actualización del expediente.

---

## DM-071 — `ClinicalEncounter` abierto actualizable

Sólo un `ClinicalEncounter` `IN_PROGRESS` puede recibir cambios clínicos.

---

## DM-072 — No funcional DELETE de ClinicalEncounter

No existirá eliminación funcional de encuentros.

El historial clínico debe preservarse.

---

## DM-073 — No soft-delete como sustituto del historial

No se añadirá un simple `is_deleted` para fingir trazabilidad.

Si en el futuro existe una política extraordinaria de rectificación o anonimización, será un diseño específico con auditoría y salvaguardas apropiadas.

---

# 14. Transición menor → adulto

## DM-074 — Mismo `MedicalRecord`

Cuando `Patient.regime` cambia de `MINOR` a `ADULT`, el paciente conserva:

```text
Patient.id
MedicalRecord.id
ClinicalEncounter históricos
```

No se crea un expediente nuevo.

---

## DM-075 — No migración física del expediente

La transición de régimen no requiere UPDATE de todas las filas clínicas ni copia de historial.

Se modifica únicamente la entidad `Patient` y las relaciones de autorización que correspondan.

---

## DM-076 — El expediente no determina permisos

La persistencia de `MedicalRecord` y `ClinicalEncounter` no decide por sí sola si un usuario puede leerlos.

La autorización pertenece a `clinical-permissions.md`.

---

# 15. Relación con DoctorPatientRelationship

## DM-077 — No FK obligatoria

`ClinicalEncounter` no tendrá una FK obligatoria a `DoctorPatientRelationship`.

---

## DM-078 — Primera consulta válida sin relación previa

La primera consulta del médico puede existir cuando Agenda permitió una cita válida, aun sin relación médico-paciente previa.

El modelo clínico no debe crear automáticamente una relación `DoctorPatientRelationship`.

---

## DM-079 — Relación independiente

Modificar, crear o desactivar `DoctorPatientRelationship` no modifica retrospectivamente los encuentros existentes.

---

# 16. Entidades clínicas futuras

## DM-080 — `ClinicalAlert`

`ClinicalAlert` será una entidad independiente del encuentro.

Puede estar asociada al paciente y, cuando sea necesario, conservar referencia al evento que la originó.

No se implementa todavía en este modelo salvo como extensión reservada.

---

## DM-081 — `Prescription`

`Prescription` será una entidad propia e histórica.

Puede relacionarse con el paciente, médico y encuentro que la originó, pero no debe almacenarse como texto sobrescribible dentro de `MedicalRecord`.

---

## DM-082 — `StudyOrder`

`StudyOrder` será una entidad propia para solicitudes de laboratorio, gabinete y otros estudios.

No debe convertirse en una columna de `ClinicalEncounter.studies` cuando evolucione a flujo formal.

El campo `studies` del encuentro F3 se considera contexto clínico libre/temporal, no sustituto permanente de una solicitud estructurada.

---

## DM-083 — `ClinicalDocument`

Los documentos clínicos deberán tener entidad y almacenamiento privado propios.

No se incluirán archivos binarios dentro de `MedicalRecord` ni dentro de `ClinicalEncounter` mediante campos improvisados.

---

# 17. Auditoría y modelo de datos

## DM-084 — Auditoría separada

No se introducirá una tabla de auditoría dentro de `MedicalRecord` para simular historial.

La auditoría será un mecanismo transversal independiente.

---

## DM-085 — Auditoría no sustituye timestamps

`created_at`, `updated_at`, `started_at` y `completed_at` expresan estado temporal del dominio.

La auditoría registrará quién hizo una operación, qué ocurrió y desde qué contexto, pero no reemplazará dichos campos.

---

## DM-086 — Auditoría no sustituye versionado

Fase 3 no implementa versionado funcional de `ClinicalEncounter`.

Una futura auditoría de cambios no autoriza automáticamente a reabrir una consulta completada.

---

# 18. Índices

## DM-087 — Índice por paciente en MedicalRecord

`UNIQUE(patient_id)` también proporciona la ruta eficiente para localizar el expediente del paciente.

---

## DM-088 — Índice por appointment en ClinicalEncounter

`UNIQUE(appointment_id)` cubre la localización del encuentro a partir de la cita.

---

## DM-089 — Índice por médico y estado

**PROPUESTA:** índice compuesto:

```text
(doctor_id, status)
```

para recuperar consultas abiertas del médico y verificar rápidamente actividad clínica.

---

## DM-090 — Índice temporal

**PROPUESTA:** índice sobre:

```text
(started_at)
```

o una combinación apropiada con médico/paciente según las consultas reales de la aplicación.

No se debe llenar el modelo de índices hipotéticos antes de conocer los patrones de acceso.

---

## DM-091 — Índices derivados de FK

Las FKs consultadas frecuentemente deben disponer de índices, aprovechando los índices implícitos/creados por Django o agregando índices compuestos cuando realmente aporten una consulta frecuente.

---

# 19. Reglas de null, blank y defaults

## DM-092 — FKs obligatorias

Relaciones estructurales que son invariantes del dominio deben utilizar `null=False`:

- `MedicalRecord.patient`;
- `ClinicalEncounter.appointment`;
- `ClinicalEncounter.doctor`;
- `ClinicalEncounter.started_at`.

---

## DM-093 — Texto clínico abierto

Campos clínicos abiertos que soportan guardado parcial deben permitir vacío durante `IN_PROGRESS`.

Recomendación Django:

```python
blank=True
null=False
```

para campos de texto, evitando distinguir innecesariamente entre `NULL` y `""`.

---

## DM-094 — Defaults clínicos

No establecer como default textos clínicos engañosos tales como:

```text
"N/A"
"No aplica"
"Sin datos"
```

Los campos pueden iniciar vacíos y permanecer incompletos hasta que el médico capture información.

---

## DM-095 — Defaults de status

No usar un default silencioso para `ClinicalEncounter.status`.

La creación del encuentro debe declarar explícitamente `IN_PROGRESS`.

---

# 20. Campo semántico versus presentación UI

## DM-096 — Nombres de dominio, no etiquetas de pantalla

El nombre físico de un campo debe expresar su concepto estable y no depender de la etiqueta actual de UI.

Por ejemplo:

```text
assessment
```

es preferible a:

```text
diagnostico_final_del_medico
```

porque F3 define el concepto como evaluación/diagnóstico libre.

---

## DM-097 — No persistir formato de presentación

El modelo no debe guardar HTML, markdown ni bloques específicos de componentes UI como contenido clínico canónico.

El texto debe permanecer neutral a la interfaz.

---

# 21. Datos derivados y contexto clínico

## DM-098 — Edad

La edad se deriva de `Person.birth_date` al momento de consulta.

No se copia a `MedicalRecord` ni a `ClinicalEncounter` salvo que una necesidad histórica futura lo justifique como snapshot explícito.

---

## DM-099 — IMC

Si peso y talla suficientes están disponibles, el IMC puede calcularse como dato derivado.

No es necesario crear `bmi` persistente en F3 core.

---

## DM-100 — Último diagnóstico

No existe un campo `current_diagnosis` dentro de `MedicalRecord`.

El resumen puede mostrar la evaluación del último encuentro completado, sin convertirla en diagnóstico actual oficial.

---

## DM-101 — Última consulta

No existe un `last_encounter_id` obligatorio dentro de `MedicalRecord`.

La última consulta se obtiene mediante consulta ordenada sobre el historial.

Sólo una decisión posterior de rendimiento podría justificar materializarlo, y en ese caso deberá documentar cómo se mantiene consistente.

---

# 22. Importación y migración

## DM-102 — No copiar historia al crear el expediente

Crear `MedicalRecord` no implica copiar automáticamente texto desde todos los campos de `Patient` hacia nuevos campos del expediente.

Las duplicaciones de datos sólo deben hacerse mediante una política de migración explícita.

---

## DM-103 — Datos legados de Patient

Los campos clínicamente relevantes ya presentes en `Patient` deben considerarse legado funcional válido mientras no exista una migración aprobada.

No se deben vaciar ni reinterpretar silenciosamente durante la creación del nuevo modelo.

---

## DM-104 — Migración futura de datos

Una migración futura debe definir, por separado:

- origen;
- destino;
- transformación;
- duplicados;
- validación;
- reversibilidad;
- auditoría;
- convivencia temporal.

No se incorpora esta lógica en F3 core.

---

## DM-105 — Importación de expediente externo

La importación de historia desde otro sistema queda fuera de F3.

No diseñar columnas `source_system`, `external_record_id` o snapshots externos sólo como prevención hipotética.

---

# 23. Consistencia referencial

## DM-106 — Encounter debe tener Appointment válido

No existe `ClinicalEncounter` huérfano.

La FK debe ser obligatoria y protegida.

---

## DM-107 — Encounter debe corresponder al mismo paciente de Appointment

La identidad clínica del paciente se deriva de la cita.

La capa de servicio debe rechazar cualquier intento de asociar manualmente un paciente distinto.

---

## DM-108 — Encounter debe corresponder al mismo doctor de Appointment

Debe rechazarse cualquier discrepancia:

```text
encounter.doctor_id != appointment.doctor_id
```

---

## DM-109 — MedicalRecord debe corresponder al paciente real

La creación/obtención de expediente debe utilizar `Appointment.patient` y no un `patient_id` recibido independientemente del cliente como fuente de verdad.

---

# 24. Modelo lógico consolidado

La estructura recomendada es:

```text
┌───────────────┐
│    Patient    │
└───────┬───────┘
        │ 1
        │
        │ 0..1
┌────────────────────────────────────┐
│           MedicalRecord            │
│-------------------------------------│
│ id                                  │
│ patient_id UNIQUE                   │
│ family_history*                     │
│ personal_pathological_history*      │
│ personal_non_pathological_history*  │
│ housing_history*                    │
│ gynecologic_obstetric_history*      │
│ other_relevant_history*             │
│ created_at                          │
│ updated_at                          │
└───────┬─────────────────────────────┘
        │
        │ logical 1:N through Patient
        │
        │
┌───────▼──────────────┐
│  ClinicalEncounter   │
│----------------------│
│ id                   │
│ appointment_id UNIQUE│
│ doctor_id            │
│ status               │
│ reason_for_visit     │
│ present_illness      │
│ physical_exam        │
│ assessment           │
│ plan                 │
│ vital_signs*         │
│ weight_kg*           │
│ height_cm*           │
│ relevant_history*    │
│ studies*             │
│ observations*        │
│ created_at           │
│ started_at           │
│ updated_at           │
│ completed_at*        │
└──────────┬───────────┘
           │
           │ N:1
           ▼
┌─────────────────────┐
│     Appointment     │
│ patient_id          │
│ doctor_id           │
│ clinic_id           │
│ status               │
└─────────────────────┘
```

`*` = opcional.

**Corrección de consistencia (auditoría de cierre, 2026-09-11):** una versión anterior de este diagrama marcaba con `*` únicamente `gynecologic_obstetric_history`, dando a entender que los demás campos longitudinales de `MedicalRecord` (`family_history`, `personal_pathological_history`, `personal_non_pathological_history`, `housing_history`, `other_relevant_history`) eran obligatorios — lo cual contradecía a DM-015, que explícitamente los marca todos como "Obligatorio: No". Se corrige el diagrama: los seis campos longitudinales son opcionales, consistente con DM-015 y DM-016.

La relación física importante es:

```text
MedicalRecord.patient_id → Patient.id
ClinicalEncounter.appointment_id → Appointment.id
ClinicalEncounter.doctor_id → Doctor.id
```

---

# 25. Modelo físico recomendado para primera migración

La siguiente tabla resume la propuesta mínima.

## 25.1 `medical_records_medicalrecord`

| Campo | Tipo Django recomendado | Null | Blank | Restricción / comentario |
|---|---|---:|---:|---|
| `id` | PK existente del proyecto | No | No | identidad técnica |
| `patient_id` | `OneToOneField(Patient)` | No | No | UNIQUE, PROTECT |
| `family_history` | `TextField` | No | Sí | texto longitudinal |
| `personal_pathological_history` | `TextField` | No | Sí | texto longitudinal |
| `personal_non_pathological_history` | `TextField` | No | Sí | texto longitudinal |
| `housing_history` | `TextField` | No | Sí | texto longitudinal |
| `gynecologic_obstetric_history` | `TextField` | No | Sí | especialidad, abierta |
| `other_relevant_history` | `TextField` | No | Sí | texto longitudinal |
| `created_at` | `DateTimeField(auto_now_add=True)` | No | No | persistencia inicial |
| `updated_at` | `DateTimeField(auto_now=True)` | No | No | cambios del expediente |

La inclusión de `gynecologic_obstetric_history` se mantiene como decisión de compatibilidad con los requisitos actuales; su futura estructuración queda fuera de F3 core.

---

## 25.2 `medical_records_clinicalencounter`

| Campo | Tipo Django recomendado | Null | Blank | Restricción / comentario |
|---|---|---:|---:|---|
| `id` | PK existente del proyecto | No | No | identidad técnica |
| `appointment_id` | `OneToOneField(Appointment)` | No | No | UNIQUE, PROTECT |
| `doctor_id` | `ForeignKey(Doctor)` | No | No | PROTECT |
| `status` | `CharField` | No | No | `IN_PROGRESS/COMPLETED` |
| `reason_for_visit` | `TextField` | No | Sí | obligatorio al completar |
| `present_illness` | `TextField` | No | Sí | obligatorio al completar |
| `physical_exam` | `TextField` | No | Sí | obligatorio al completar |
| `assessment` | `TextField` | No | Sí | obligatorio al completar |
| `plan` | `TextField` | No | Sí | obligatorio al completar |
| `vital_signs` | `TextField` | No | Sí | opcional |
| `weight_kg` | `DecimalField` | Sí | Sí | opcional |
| `height_cm` | `DecimalField` | Sí | Sí | opcional |
| `relevant_history` | `TextField` | No | Sí | opcional |
| `studies` | `TextField` | No | Sí | opcional/contextual |
| `observations` | `TextField` | No | Sí | opcional |
| `created_at` | `DateTimeField(auto_now_add=True)` | No | No | creación |
| `started_at` | `DateTimeField` | No | No | inicio real |
| `updated_at` | `DateTimeField(auto_now=True)` | No | No | último save exitoso |
| `completed_at` | `DateTimeField` | Sí | Sí | sólo COMPLETED |

---

# 26. Decisiones sobre `DecimalField`

## DM-110 — Peso

Si se implementa `weight_kg`, se recomienda un decimal con precisión suficiente para medición clínica ordinaria, evitando `FloatField` por su semántica binaria.

La precisión y rango exactos deben validarse en función de las necesidades del proyecto y no utilizarse como mecanismo para juzgar la plausibilidad médica de la captura.

---

## DM-111 — Talla

Si se implementa `height_cm`, se recomienda `DecimalField` por la misma razón.

La base debe impedir valores negativos o cero mediante constraint o validación estructural sencilla.

No se intenta validar rangos clínicos complejos.

---

# 27. Integridad de campos opcionales numéricos

## DM-112 — Peso positivo

Si `weight_kg` no es `NULL`, debe ser mayor que cero.

---

## DM-113 — Talla positiva

Si `height_cm` no es `NULL`, debe ser mayor que cero.

---

## DM-114 — Sin BMI persistido

No almacenar `bmi` como columna F3 core.

El valor puede calcularse cuando existan peso y talla válidos.

---

# 28. Reglas sobre documentos, estudios y recetas

## DM-115 — No almacenar archivos en TextField

No guardar rutas públicas, base64 ni contenido binario en campos de texto clínico.

---

## DM-116 — No duplicar solicitudes estructuradas

Cuando exista `StudyOrder`, el campo `studies` del encuentro no se convertirá automáticamente en una segunda fuente de verdad del pedido.

---

## DM-117 — No duplicar recetas

Cuando exista `Prescription`, el plan del encuentro puede referenciar conceptualmente el tratamiento, pero la receta formal será la entidad histórica específica.

---

# 29. Corrección y versionado

## DM-118 — No reabrir encuentro completado

No se agregan campos `reopened_at`, `reopened_by`, `version`, `revision_number` ni equivalentes en F3 core.

---

## DM-119 — Rectificación extraordinaria futura

Una necesidad de corregir un dato clínico cerrado no debe resolverse editando directamente el registro desde la UI.

Requiere una política futura específica de rectificación, auditoría y preservación del valor original.

---

# 30. Consultas y rendimiento

## DM-120 — Leer expediente sin duplicar datos

El servicio de consulta del expediente puede usar `select_related`/`prefetch_related` para reunir datos de:

```text
Patient
MedicalRecord
Appointment
ClinicalEncounter
```

sin agregar campos duplicados únicamente para evitar joins.

---

## DM-121 — Paginación del historial

El historial de encuentros debe poder paginarse.

No cargar indefinidamente todos los encuentros de un paciente como requisito del modelo.

---

## DM-122 — Orden determinista

Cuando dos encuentros tengan el mismo `started_at`, la API debe usar un segundo criterio determinista, por ejemplo `id`, para evitar saltos de orden entre páginas.

---

# 31. Servicios responsables del modelo

## DM-123 — No usar `save()` como autoridad de negocio

El modelo Django no debe asumir por sí solo la lógica completa de inicio/cierre.

La transición clínica pertenece a servicios de dominio.

---

## DM-124 — No usar signals para crear encuentros

No utilizar signals Django como autoridad para transformar automáticamente:

```text
Appointment.IN_CONSULTATION → ClinicalEncounter
```

La operación debe ser explícita, transaccional y auditable.

---

## DM-125 — Servicio de inicio

Se recomienda un servicio conceptual:

```text
ClinicalEncounterService.start(appointment, doctor)
```

que gestione:

- autorización;
- precondiciones de Agenda;
- creación/obtención de `MedicalRecord`;
- transición de `Appointment`;
- creación idempotente del encuentro;
- transacción;
- resultado estable.

---

## DM-126 — Servicio de guardado

Se recomienda un servicio conceptual para persistir cambios del encuentro abierto y actualizar `updated_at`.

---

## DM-127 — Servicio de completion

El cierre debe ser responsabilidad de una operación de dominio que persista los últimos cambios y ejecute atómicamente:

```text
ClinicalEncounter → COMPLETED
Appointment → COMPLETED
```

---

# 32. Matriz de decisiones

| Tema | Propuesta F3 |
|---|---|
| Expediente por paciente | 1 lógico |
| Creación | Lazy |
| Expediente sin status | Sí |
| Borrado | No funcional |
| Reasignación | Prohibida |
| JSON clínico genérico | No |
| Datos de Patient duplicados | No |
| Encounter por Appointment | 0..1 |
| `appointment_id` en Encounter | UNIQUE + obligatorio |
| `medical_record_id` en Encounter | No |
| `patient_id` en Encounter | No redundante |
| `clinic_id` en Encounter | No redundante |
| `doctor_id` en Encounter | Sí |
| Status Encounter | IN_PROGRESS / COMPLETED |
| Guardado parcial | Sí |
| Obligatorios de creación | Ninguno de los 5 clínicos |
| Obligatorios de cierre | 5 campos |
| Diagnóstico | Texto libre |
| CIE-10 | Fuera de F3 |
| Edición después de COMPLETED | Prohibida |
| Reapertura | Prohibida |
| Versionado | Fuera de F3 |
| Auditoría | Módulo separado |
| Resumen | Proyección |
| Menor → adulto | Mismo expediente |
| DoctorPatientRelationship | Independiente |
| Recetas | Entidad futura |
| Estudios | Entidad futura |
| Alertas | Entidad futura |
| Documentos | Entidad futura |

---

# 33. Invariantes físicos y lógicos

## I-001

Todo `MedicalRecord` pertenece a exactamente un `Patient`.

## I-002

Un `Patient` no puede tener más de un `MedicalRecord` lógico.

## I-003

Todo `ClinicalEncounter` pertenece exactamente a una `Appointment`.

## I-004

Una `Appointment` puede tener como máximo un `ClinicalEncounter`.

## I-005

Todo `ClinicalEncounter` tiene `doctor_id`.

## I-006

`ClinicalEncounter.doctor_id = Appointment.doctor_id`.

## I-007

Los encuentros sólo existen para citas que cruzaron a `IN_CONSULTATION` mediante la operación autorizada.

## I-008

Una cita `CANCELLED` o `NO_SHOW` no genera encuentro.

## I-009

Un encuentro `COMPLETED` es inmutable desde la UI y servicios ordinarios.

## I-010

Un encuentro `IN_PROGRESS` puede estar incompleto.

## I-011

El expediente conserva continuidad cuando cambia el régimen del paciente.

## I-012

La historia clínica no se destruye mediante las operaciones administrativas ordinarias.

---

# 34. Casos que el modelo debe soportar

## Caso A — Paciente nuevo, primera consulta

```text
Patient existe
MedicalRecord no existe
Appointment = SCHEDULED
↓
start()
↓
MedicalRecord creado
Appointment = IN_CONSULTATION
ClinicalEncounter = IN_PROGRESS
```

## Caso B — Paciente con expediente existente

```text
Patient
  ↓
MedicalRecord existente
  ↓
Appointment SCHEDULED
  ↓
ClinicalEncounter IN_PROGRESS
```

No se crea un segundo expediente.

## Caso C — Doble clic

```text
request 1 → crea encounter
request 2 → encuentra encounter existente
```

No hay duplicado.

## Caso D — Consulta incompleta

```text
ClinicalEncounter IN_PROGRESS
campos parcialmente capturados
```

Es válido.

## Caso E — Completar

```text
validar 5 campos
persistir últimos cambios
ClinicalEncounter → COMPLETED
Appointment → COMPLETED
```

En una única transacción.

## Caso F — No show

```text
Appointment → NO_SHOW
ClinicalEncounter → no existe
```

## Caso G — Transición a adulto

```text
Patient.regime MINOR → ADULT
MedicalRecord.id permanece igual
ClinicalEncounter históricos permanecen iguales
```

---

# 35. Casos que el modelo debe rechazar

1. Dos expedientes para el mismo paciente.
2. Dos encuentros para una misma cita.
3. Encounter sin Appointment.
4. Encounter sin Doctor.
5. Encounter asociado a médico diferente del de la cita.
6. Encounter creado directamente sin la frontera de Agenda.
7. Encounter con estado desconocido.
8. `COMPLETED` sin `completed_at`.
9. Encounter posterior a `CANCELLED`/`NO_SHOW`.
10. Modificación de un encuentro `COMPLETED`.
11. Eliminación funcional del historial.
12. Duplicación del paciente dentro del modelo clínico.

---

# 36. Fuera de alcance

Este documento no implementa todavía:

- CIE-10;
- catálogo de diagnósticos;
- receta estructurada completa;
- catálogo de medicamentos;
- resultados de laboratorio estructurados;
- resultados de gabinete estructurados;
- alertas clínicas completas;
- almacenamiento de documentos;
- versionado de encuentros cerrados;
- firma electrónica;
- especialización obstétrica estructurada;
- gineco-obstetricia por embarazo;
- integración con expediente externo;
- interoperabilidad clínica;
- importación de datos externos;
- reglas legales de retención específicas por jurisdicción.

La exclusión es deliberada: el modelo F3 core debe permanecer pequeño.

---

# 37. Compatibilidad con los documentos anteriores

Este modelo implementa conceptualmente las decisiones cerradas de `ClinicalEncounter`:

```text
Appointment 1 ─── 0..1 ClinicalEncounter
ClinicalEncounter.status = IN_PROGRESS | COMPLETED
five required fields only at completion
partial save
no edit after completion
no cancel/no-show after start
atomic completion
```

Y las decisiones propuestas de `MedicalRecord`:

```text
Patient 1 ─── 0..1 MedicalRecord
one logical record per patient
no delete
no reassignment
longitudinal continuity
summary as projection
independent DoctorPatientRelationship
```

No se introduce una segunda arquitectura clínica.

---

# 38. Recomendación final de esquema F3

La recomendación más simple y consistente es implementar inicialmente sólo dos tablas propias del núcleo clínico:

```text
medicalrecord
clinicalencounter
```

relacionadas con las entidades existentes:

```text
Patient
Doctor
Appointment
Clinic
```

sin copiar paciente, cita o consultorio dentro del modelo clínico.

La columna más importante para garantizar identidad longitudinal es:

```text
MedicalRecord.patient_id UNIQUE
```

La columna más importante para garantizar idempotencia clínica es:

```text
ClinicalEncounter.appointment_id UNIQUE
```

Y la cadena de identidad recomendada es:

```text
ClinicalEncounter
      ↓
Appointment
      ↓
Patient
      ↓
MedicalRecord
```

Esto reduce el número de fuentes de verdad y deja la especialización clínica para entidades posteriores.

---

# 39. Orden de implementación recomendado

1. Crear aplicación `medical_records`.
2. Crear `MedicalRecord` con `patient_id UNIQUE`.
3. Crear `ClinicalEncounter` con `appointment_id UNIQUE` y `doctor_id`.
4. Añadir constraints de estado y timestamps.
5. Añadir campos clínicos explícitos.
6. Añadir índices justificados.
7. Implementar servicios transaccionales.
8. Implementar pruebas de constraints y concurrencia.
9. Implementar permisos.
10. Implementar API y UX.

No invertir el orden empezando por pantallas y dejando identidad/concurrencia para después.

---

# 40. Pruebas mínimas derivadas del modelo

El futuro `phase-3-testing-strategy.md` deberá cubrir al menos:

### Identidad

- un `MedicalRecord` por paciente;
- un `ClinicalEncounter` por cita.

### Integridad

- FKs protegidas;
- estados inválidos rechazados;
- timestamps inconsistentes rechazados;
- encounter sin doctor rechazado.

### Concurrencia

- dos inicios simultáneos;
- dos creaciones de expediente simultáneas;
- dos completes simultáneos;
- save concurrente con complete.

### Historial

- encuentro completado no modificable;
- no delete funcional;
- transición menor → adulto conserva historial.

### Contenido

- guardado parcial aceptado;
- placeholders rechazados al completar;
- cinco campos requeridos realmente exigidos;
- diagnóstico libre permitido.

---

# 41. Criterio de salida para aprobar el modelo

**Ratificado en la auditoría de cierre de Fase 3 (2026-09-11).** Todas las decisiones siguientes quedan aprobadas, incorporando las correcciones de nombres de campo (ADR-012) y de constraints temporales aplicadas en esta misma revisión:

- [x] `MedicalRecord` uno por paciente.
- [x] `patient_id` único.
- [x] creación lazy.
- [x] creación idempotente y transaccional.
- [x] no delete/no reasignación.
- [x] no duplicación de `Patient`.
- [x] campos longitudinales explícitos.
- [x] `ClinicalEncounter.appointment_id` obligatorio y único.
- [x] `doctor_id` obligatorio y coherente con la cita.
- [x] no `medical_record_id` redundante.
- [x] sólo `IN_PROGRESS` / `COMPLETED`.
- [x] cinco campos obligatorios únicamente al completar (nombres definitivos: `reason_for_visit`, `present_illness`, `physical_exam`, `assessment`, `plan`, per ADR-012).
- [x] guardado parcial.
- [x] no edición después de completar.
- [x] constraints de timestamps y estado, incluyendo el orden temporal como `CheckConstraint` (DM-042).
- [x] protección de FKs.
- [x] índices mínimos.
- [x] entidades futuras separadas para recetas, estudios, alertas y documentos.

Las decisiones de acceso por actor siguen perteneciendo a `clinical-permissions.md`.

---

# 42. Siguiente documento

Una vez aprobado este modelo, el siguiente paso lógico es:

```text
clinical-permissions.md
```

Ese documento deberá convertir la existencia física de las entidades en una matriz normativa de autorización, especialmente para:

- paciente titular;
- responsable;
- médico tratante/relacionado;
- otro médico;
- administrador;
- acceso contextual desde una cita;
- acceso longitudinal al expediente;
- lectura y descarga de documentos.

El modelo de datos no debe inferir esas reglas por sí solo.

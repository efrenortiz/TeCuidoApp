# Fase 3 — Clinical Record Domain

**Documento del dominio `MedicalRecord`**  
**Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11 — las 90 decisiones CR-001 a CR-090 quedan aprobadas; ver §21 y la resolución de CR-034 más abajo)  
**Fecha:** 2026-09-11  
**Dominio:** expediente clínico longitudinal genérico  
**Aplicación prevista:** `medical_records`

---

## 1. Propósito

Este documento define las políticas que faltaban cerrar alrededor del expediente clínico (`MedicalRecord`) y propone una solución consistente con los documentos ya aprobados de Fase 3.

Su objetivo no es rediseñar `ClinicalEncounter`, sino establecer qué significa el expediente, qué información pertenece realmente a él, cómo se relaciona con el paciente y con los encuentros, cómo se conserva el historial y cuáles son los límites del dominio.

La propuesta busca cuatro propiedades:

1. **Simplicidad:** evitar entidades o versiones innecesarias.
2. **Consistencia:** no duplicar `Patient`, `Appointment` ni el contenido cerrado de `ClinicalEncounter`.
3. **Historicidad:** no sobrescribir la información clínica histórica.
4. **Extensibilidad:** permitir incorporar recetas, estudios, alertas y documentos sin convertir `MedicalRecord` en un contenedor de campos arbitrarios.

Este documento debe leerse junto con:

```text
phase-3-clinical-encounter.md
clinical-encounter-workflow.md
clinical-encounter-rules.md
clinical-encounter-domain.md
requirements.md
docs/architecture.md
docs/adr/ADR-005-django-app-boundaries.md
docs/adr/ADR-006-database-integrity-and-transactions.md
```

---

## 2. Principio rector

La propuesta fundamental es:

> **El expediente médico es la continuidad clínica de un paciente; no es una nota clínica mutable que se sobrescribe en cada consulta.**

Conceptualmente:

```text
Patient
   │
   │ 1
   ▼
MedicalRecord
   │
   ├── historial de ClinicalEncounter
   ├── ClinicalAlert
   ├── Prescription
   ├── StudyOrder
   ├── ClinicalDocument
   └── otras entidades clínicas futuras
```

`MedicalRecord` representa la continuidad del expediente.

`ClinicalEncounter` representa cada episodio de atención.

Los componentes clínicos emitidos o registrados durante una atención conservan su propia identidad e historial.

---

# 3. Políticas pendientes y propuesta de cierre

Esta sección identifica las decisiones que no quedaron completamente cerradas en los documentos anteriores y propone una política para cada una.

La etiqueta **PROPUESTA** significa que la decisión se recomienda para cerrar el dominio, pero deberá considerarse aprobada de forma definitiva cuando el conjunto de políticas de Fase 3 sea cerrado.

---

## CR-001 — Cardinalidad `Patient` ↔ `MedicalRecord`

**Cerrado — `ADR-011-one-medical-record-per-patient.md` (Accepted).**

Conceptualmente:

```text
Patient 1 ─── 1 MedicalRecord
```

En persistencia durante la creación lazy:

```text
Patient 1 ─── 0..1 MedicalRecord
```

**Redacción normativa (idéntica a `ADR-011` y `clinical-data-model.md`, revisión de consistencia 2026-09-11):**

> Conceptualmente cada `Patient` tiene un único `MedicalRecord`. En persistencia, el registro puede no existir todavía porque su creación es lazy. Por eso el estado técnico previo a su creación puede representarse como `Patient 1 ─── 0..1 MedicalRecord`. Una vez creado, el `MedicalRecord` es único, no se duplica y no cambia de `Patient`. El `0..1` es exclusivamente un estado técnico transitorio anterior a la primera operación clínica — nunca una cardinalidad funcional permanente que permita a un paciente quedar sin expediente después de haber iniciado atención clínica.

Reglas:

- Un paciente tiene como máximo un expediente médico lógico.
- Un `MedicalRecord` pertenece exactamente a un `Patient`.
- No existen dos expedientes activos para el mismo paciente.
- La identidad del expediente se basa en el paciente, no en una consulta.

**Razón:** un único expediente evita duplicación y simplifica la lectura longitudinal.

**Decisión técnica sugerida:** `patient_id` obligatorio y `UNIQUE`.


## CR-002 — Creación del `MedicalRecord`

**Situación pendiente:** no se estableció cuándo nace técnicamente el expediente.

**PROPUESTA DE CIERRE:**

El expediente puede ser creado de forma **perezosa (lazy)** cuando ocurre la primera operación clínica que realmente lo requiere, inicialmente el inicio de un `ClinicalEncounter`.

Reglas:

- Registrar un paciente no obliga a crear inmediatamente un expediente clínico vacío.
- La primera operación clínica válida crea el expediente si todavía no existe.
- La creación debe ser idempotente.
- La creación del expediente no debe crear por sí misma una consulta.
- Si el expediente ya existe, se reutiliza.

**Razón:** evita crear miles de expedientes vacíos para pacientes que nunca han tenido atención clínica y evita acoplar innecesariamente el alta administrativa con el dominio clínico.

**Importante:** desde el punto de vista funcional, el expediente puede considerarse existente conceptualmente para cualquier paciente; la decisión lazy es una decisión técnica de persistencia.

---

## CR-003 — Creación del expediente y atomicidad con el primer encuentro

**Situación pendiente:** debe definirse si crear el expediente y crear el primer encuentro son operaciones separadas.

**PROPUESTA DE CIERRE:**

Cuando el primer `ClinicalEncounter` requiere crear el `MedicalRecord`, ambos deben quedar protegidos por la misma transacción de inicio clínico.

Resultado esperado:

```text
BEGIN
  obtener/crear MedicalRecord del Patient
  cambiar Appointment → IN_CONSULTATION
  crear ClinicalEncounter → IN_PROGRESS
COMMIT
```

Si una parte falla, ninguna parte debe quedar registrada como si la consulta hubiera iniciado correctamente.

**Razón:** mantiene la frontera transaccional ya establecida en `ClinicalEncounter`.

---

## CR-004 — Identidad del expediente

**Situación pendiente:** no se necesita un número de expediente visible adicional para Fase 3.

**PROPUESTA DE CIERRE:**

La identidad técnica del `MedicalRecord` será la proporcionada por PostgreSQL/Django, y la unicidad funcional la determina `patient_id`.

No crear en Fase 3:

- número de expediente manual;
- folio clínico editable;
- identificadores duplicados derivados del paciente;
- código especial por clínica.

**Razón:** evita agregar una segunda identidad que no tiene utilidad funcional definida.

Si en una fase posterior existe una necesidad legal u operativa de un número visible de expediente, se diseñará por separado.

---

## CR-005 — Estado del expediente

**Situación pendiente:** no se definió un ciclo de vida propio para `MedicalRecord`.

**PROPUESTA DE CIERRE:**

Fase 3 **no tendrá estados funcionales propios** para `MedicalRecord`.

No se agregará un enum como:

```text
OPEN
CLOSED
ARCHIVED
CANCELLED
```

El expediente permanece como la continuidad clínica del paciente durante toda su vida funcional en la plataforma.

La activación o desactivación administrativa del paciente no equivale a cerrar o borrar el expediente.

**Razón:** los estados pertenecerían a procesos que todavía no existen y añadirían complejidad innecesaria.

---

## CR-006 — Eliminación del expediente

**Situación pendiente:** `requirements.md` exige conservar historia clínica y evitar eliminación física rutinaria.

**PROPUESTA DE CIERRE:**

No existirá `DELETE` funcional del `MedicalRecord` en Fase 3.

Reglas:

- El expediente no se elimina por la desactivación del paciente.
- No se permite borrar el expediente desde la UI.
- No se permite reasignar el expediente a otro paciente.
- Una eventual eliminación administrativa extraordinaria deberá ser una política independiente, con garantías legales y de auditoría.

**Razón:** protege la continuidad e integridad histórica.

---

## CR-007 — Reasignación del expediente a otro paciente

**PROPUESTA DE CIERRE:** **prohibida.**

Una vez creado:

```text
MedicalRecord → Patient P1
```

no puede cambiar a `Patient P2`.

**Razón:** cambiar el paciente destruiría la identidad histórica del expediente y sería análogo a cambiar el paciente de un `ClinicalEncounter`.

---

## CR-008 — Duplicación de datos de `Patient`

**Situación pendiente:** `requirements.md` contiene datos del paciente que pueden aparecer en el resumen clínico.

**PROPUESTA DE CIERRE:**

`MedicalRecord` no duplicará como campos propios los datos administrativos canónicos de `Patient`.

Ejemplos que deben seguir siendo responsabilidad de `Patient`:

- nombre;
- fecha de nacimiento;
- teléfono;
- correo;
- domicilio;
- régimen `MINOR/ADULT`;
- información de identidad.

El resumen clínico obtiene esos datos mediante la relación con `Patient`.

**Razón:** una sola fuente de verdad evita inconsistencias.

---

## CR-009 — Datos médicos ya existentes en `Patient`

**Situación pendiente:** `Patient` ya contempla información médica relevante.

**PROPUESTA DE CIERRE:**

Mientras una información clínica tenga una definición canónica en `Patient`, `MedicalRecord` no debe crear una segunda copia simplemente para mostrarla en el expediente.

Cuando una información evolutiva requiera historial clínico, deberá migrar a una entidad clínica apropiada, no convertirse en un campo duplicado de `MedicalRecord`.

**Razón:** evita que "dato actual" e "historia" compitan como fuentes de verdad.

---

## CR-010 — Contenido propio del `MedicalRecord`

**PROPUESTA DE CIERRE:**

En Fase 3 el núcleo del `MedicalRecord` será deliberadamente pequeño.

Debe contener como mínimo:

```text
id
patient
created_at
updated_at
```

No se agregarán inicialmente campos como:

```text
current_diagnosis
current_treatment
latest_consultation_text
summary_json
medical_notes
```

**Razón:** esos campos convertirían al expediente en una segunda nota clínica mutable y crearían duplicación con encuentros y otros componentes clínicos.

---

## CR-011 — Qué significa `updated_at` del expediente

**Situación pendiente:** no debe confundirse con `ClinicalEncounter.updated_at`.

**PROPUESTA DE CIERRE:**

`MedicalRecord.updated_at` representa el último cambio persistente realizado sobre datos **propios del expediente**, no cualquier cambio ocurrido en una entidad relacionada.

Por tanto:

- guardar un `ClinicalEncounter` actualiza el `ClinicalEncounter.updated_at`;
- no necesariamente actualiza `MedicalRecord.updated_at`;
- cambiar una sección mutable propia del expediente sí actualiza `MedicalRecord.updated_at`.

Para saber cuál fue la última actividad clínica se deben consultar los componentes relacionados, no interpretar `MedicalRecord.updated_at` como "última consulta".

---

## CR-012 — Fecha de creación del expediente

**PROPUESTA DE CIERRE:**

`MedicalRecord.created_at` registra el momento en que el registro persistente fue creado.

No representa:

- la fecha de nacimiento del paciente;
- la primera consulta médica de toda su vida;
- la fecha de alta administrativa.

**Razón:** mantener semántica técnica precisa.

---

## CR-013 — Relación `MedicalRecord` ↔ `ClinicalEncounter`

**Situación pendiente:** el encuentro pertenece al paciente por medio de `Appointment`.

**PROPUESTA DE CIERRE:**

La relación conceptual es:

```text
MedicalRecord 1 ─── N ClinicalEncounter
```

pero `ClinicalEncounter` **no necesita un `medical_record_id` redundante** en Fase 3.

La identidad del paciente del encuentro se obtiene de:

```text
ClinicalEncounter
    → Appointment
        → Patient
            → MedicalRecord
```

**Razón:** evita duplicar la identidad del paciente en dos relaciones simultáneas y reduce el riesgo de inconsistencias del tipo:

```text
Appointment.patient = P1
Encounter.medical_record.patient = P2
```

La consulta de historial puede usar relaciones ORM a través de `appointment__patient`.

---

## CR-014 — Un encuentro pertenece a un solo expediente

**PROPUESTA DE CIERRE:**

Dado que cada `ClinicalEncounter` pertenece a un único `Appointment`, y cada `Appointment` identifica a un único `Patient`, cada encuentro pertenece lógicamente a un único `MedicalRecord`.

Nunca debe ser posible que un encuentro aparezca simultáneamente en dos expedientes.

---

## CR-015 — Historial ordenado

**PROPUESTA DE CIERRE:**

El historial del paciente se presenta en orden cronológico mediante las fechas clínicas de las entidades relacionadas.

Para `ClinicalEncounter`:

- mientras está abierto, el orden de actividad puede considerar `started_at`;
- una vez completado, `completed_at` es la referencia principal de cierre;
- no se debe ordenar por `created_at` del `MedicalRecord`.

Las entidades futuras deberán definir su propia fecha clínica de referencia.

---

## CR-016 — `MedicalRecord` no es una fotografía del expediente

**PROPUESTA DE CIERRE:** **prohibido diseñarlo como snapshot mutable.**

No se almacenará un gran JSON como:

```text
MedicalRecord.data = { ...todo el expediente... }
```

ni se copiarán cada vez los campos de todas las consultas.

**Razón:** un snapshot global dificulta trazabilidad, concurrencia, validación, consultas históricas y evolución del dominio.

---

## CR-017 — Resumen clínico del paciente

**Situación pendiente:** `requirements.md` exige un resumen clínico al abrir el expediente.

**PROPUESTA DE CIERRE:**

El resumen será una **proyección de lectura** construida a partir de fuentes canónicas, no una tabla duplicada.

Conceptualmente:

```text
Patient
 + MedicalRecord
 + ClinicalEncounters
 + ClinicalAlerts
 + Prescriptions
 + StudyOrders
 + ClinicalDocuments
      ↓
Clinical Summary
```

No se almacenará inicialmente un `summary_json` permanente.

**Razón:** el resumen puede cambiar con la incorporación de nuevas entidades y siempre debe reflejar la información persistida más reciente.

---

## CR-018 — Campos del resumen clínico

**PROPUESTA DE CIERRE:**

El resumen clínico debe agrupar, cuando exista información:

### Datos generales

- edad;
- fecha de nacimiento;
- peso y talla recientes;
- IMC calculable;
- alergias;
- tipo sanguíneo si existe.

### Antecedentes

- enfermedades crónicas relevantes;
- cirugías;
- hospitalizaciones;
- medicamentos actuales;
- antecedentes familiares relevantes.

### Gineco-obstétricos

- antecedentes relevantes;
- embarazos previos;
- complicaciones obstétricas;
- embarazo actual, cuando aplique.

### Actividad clínica reciente

- últimas consultas;
- últimos diagnósticos registrados en encuentros;
- tratamientos/indicaciones recientes;
- recetas;
- solicitudes y resultados de estudios cuando existan;
- documentos clínicos relevantes;
- alertas activas.

La presentación visual concreta se definirá en UX y pantallas.

---

## CR-019 — Qué información puede ser "actual" y qué información es histórica

**PROPUESTA DE CIERRE:**

Debe distinguirse explícitamente:

```text
Información actual / contexto
        ↓
fuentes clínicas activas o vigentes

Información histórica
        ↓
ClinicalEncounter COMPLETED
Prescription histórica
StudyOrder histórico
ClinicalDocument histórico
etc.
```

El expediente no convierte automáticamente un dato histórico en dato actual.

Por ejemplo, un diagnóstico registrado hace dos años sigue siendo un diagnóstico histórico de esa consulta, no necesariamente una enfermedad activa hoy.

**Razón:** evita inferencias clínicas automáticas.

---

## CR-020 — No inferencia de "diagnóstico actual"

**PROPUESTA DE CIERRE:**

TeCuidoApp no deberá convertir automáticamente:

```text
último diagnóstico registrado
```

en:

```text
diagnóstico actual del paciente
```

La aplicación puede mostrar "diagnósticos registrados recientemente" o una formulación equivalente y neutral.

**Razón:** la plataforma no debe tomar decisiones médicas autónomas.

---

## CR-021 — Antecedentes médicos longitudinales

**Situación pendiente:** `requirements.md` exige antecedentes heredofamiliares, personales patológicos, no patológicos, vivienda, gineco-obstétricos y otros antecedentes.

**PROPUESTA DE CIERRE:**

El expediente tendrá conceptualmente una sección de **historia clínica longitudinal actualizable**, separada de los encuentros.

Para Fase 3 puede implementarse como un conjunto explícito de campos de texto guiados, por ejemplo:

```text
family_history
personal_pathological_history
personal_non_pathological_history
housing_history
gynecologic_obstetric_history
other_relevant_history
```

Estos campos representan **contexto clínico longitudinal actual**, no sustituyen las notas históricas de los encuentros.

**Razón:** satisface el requisito existente sin convertir cada antecedente en una entidad especializada prematuramente.

---

## CR-022 — Edición de antecedentes longitudinales

**Situación pendiente:** si los antecedentes se pueden actualizar, debe aclararse qué ocurre con su versión anterior.

**PROPUESTA DE CIERRE:**

En Fase 3:

- los antecedentes longitudinales pueden actualizarse por el actor autorizado;
- el valor actual sustituye al anterior en el perfil longitudinal;
- la operación queda registrada en auditoría;
- el historial de consultas cerradas no cambia.

No implementar aún un sistema de versionado completo del perfil de antecedentes.

**Razón:** mantiene trazabilidad sin introducir un segundo sistema de versiones clínicas.

En una fase posterior, si el requisito clínico/legal lo exige, podrá incorporarse versionado explícito del perfil.

---

## CR-023 — Antecedentes no equivalen a alertas

**PROPUESTA DE CIERRE:**

Los antecedentes longitudinales y las `ClinicalAlert` son conceptos diferentes.

Ejemplo:

```text
Antecedente:
"Madre con diabetes mellitus tipo 2"

Alerta activa:
"Alergia a penicilina"
```

Una alerta representa una consideración clínica que debe destacar operativamente.

Un antecedente es información contextual del expediente.

---

## CR-024 — Alergias

**Situación pendiente:** `requirements.md` las exige en el resumen, pero no define una entidad propia.

**PROPUESTA DE CIERRE:**

No duplicar inicialmente alergias en `MedicalRecord` si la fuente canónica futura será `ClinicalAlert` u otro componente clínico.

Para Fase 3, el resumen puede mostrar las alergias desde la fuente que sea aprobada para ese dato.

Mientras `ClinicalAlert` no esté implementado, no inventar una segunda estructura provisional dentro de `MedicalRecord` salvo que la implementación lo requiera explícitamente.

---

## CR-025 — Relación con `ClinicalAlert`

**PROPUESTA DE CIERRE:**

```text
MedicalRecord 1 ─── N ClinicalAlert
```

Las alertas pertenecen al contexto longitudinal del paciente.

El encuentro puede originar una alerta, pero no se crea una alerta automáticamente por el simple hecho de existir un encuentro.

Las reglas detalladas de `ClinicalAlert` quedan para su propio contrato/dominio.

---

## CR-026 — Relación con `Prescription`

**PROPUESTA DE CIERRE:**

```text
MedicalRecord 1 ─── N Prescription
ClinicalEncounter 1 ─── N Prescription
```

Una receta pertenece al historial clínico del paciente y está asociada a la consulta que la originó.

No se copiarán los medicamentos de la receta en `MedicalRecord`.

El estado "medicamentos actuales" del resumen se construirá mediante reglas explícitas posteriores y nunca se inferirá solo por existir una receta histórica.

---

## CR-027 — Relación con `StudyOrder`

**PROPUESTA DE CIERRE:**

```text
MedicalRecord 1 ─── N StudyOrder
ClinicalEncounter 1 ─── N StudyOrder
```

Las solicitudes de estudios pertenecen al historial del paciente y conservan su relación con la consulta originadora.

Los resultados de estudios, cuando se implementen, deberán conservar su propia identidad y no sobrescribir la solicitud original.

---

## CR-028 — Relación con `ClinicalDocument`

**PROPUESTA DE CIERRE:**

Los documentos clínicos se consideran componentes del expediente, pero no deben almacenarse como grandes blobs dentro de `MedicalRecord`.

El expediente debe poder localizar documentos autorizados mediante su relación con la entidad documental correspondiente.

El almacenamiento físico seguirá siendo privado.

Las reglas de almacenamiento y descarga pertenecen al dominio de documentos y a seguridad/privacidad.

---

## CR-029 — No incrustar documentos dentro del expediente

**PROPUESTA DE CIERRE:**

No crear campos como:

```text
MedicalRecord.pdf_file
MedicalRecord.all_documents
MedicalRecord.attachments_json
```

Los documentos tendrán identidad propia.

**Razón:** facilita permisos, auditoría, versionado documental y almacenamiento privado.

---

## CR-030 — Relación con `Appointment`

**PROPUESTA DE CIERRE:**

`MedicalRecord` no tendrá una relación directa de negocio obligatoria hacia `Appointment`.

La ruta es:

```text
MedicalRecord
   ↓ Patient
Appointment
```

Cada encuentro clínico que nace de una cita queda vinculado a la cita por `ClinicalEncounter`.

**Razón:** `Appointment` pertenece a Agenda y no al expediente como fuente primaria.

---

## CR-031 — Separación entre expediente y agenda

**PROPUESTA DE CIERRE:**

La existencia del expediente no modifica reglas de disponibilidad, reserva, cancelación o `NO_SHOW`.

La existencia de citas tampoco crea por sí misma contenido clínico.

Solo el inicio válido de una consulta cruza la frontera hacia `ClinicalEncounter`.

---

## CR-032 — Relación con `DoctorPatientRelationship`

**PROPUESTA DE CIERRE:**

`MedicalRecord` no crea, activa, desactiva ni modifica automáticamente `DoctorPatientRelationship`.

La relación longitudinal médico-paciente seguirá siendo independiente.

Un encuentro tampoco convierte automáticamente al médico en propietario del expediente.

---

## CR-033 — Propiedad del expediente

**Situación pendiente:** debe evitarse hablar de "propietario" como si el expediente perteneciera a un médico.

**PROPUESTA DE CIERRE:**

El expediente está **asociado al paciente** y la aplicación controla quién puede acceder a él.

No existe un concepto funcional de:

```text
owner_doctor
```

en `MedicalRecord`.

**Razón:** un paciente puede ser atendido por múltiples médicos a lo largo del tiempo.

---

## CR-034 — Lectura por el paciente

**CERRADO (auditoría de cierre, 2026-09-11) — Decisión D-004:**

Una redacción anterior de esta sección delegaba indefinidamente a `clinical-permissions.md` la lista exacta de campos visibles, y `clinical-permissions.md` y `clinical-security-and-privacy.md` a su vez delegaban de vuelta sin que ningún documento fijara la respuesta — un ciclo de referencias sin resolución real.

Se cierra: **el paciente adulto puede consultar los cinco campos clínicos obligatorios completos** (`reason_for_visit`, `present_illness`, `physical_exam`, `assessment`, `plan`) **de cada `ClinicalEncounter` propio en estado `COMPLETED`**, junto con los metadatos del encuentro (fecha, médico, consultorio, duración) y los campos opcionales que existan. Un encuentro `IN_PROGRESS` no se expone al paciente (el contenido aún no está confirmado ni es históricamente estable).

Razón: transparencia total sobre el propio historial es consistente con el principio ya aplicado en Fase 1 al perfil del paciente (sin campos internos ocultos por defecto), y evita inventar una regla de filtrado por campo sin justificación clínica o legal concreta. Si en el futuro existe una razón clínica/legal específica para ocultar algún campo, deberá cerrarse como una decisión explícita y documentada, no como un valor por defecto.

La matriz normativa de esta regla vive en `clinical-permissions.md` (que debe citarla textualmente, no reabrirla).

---

## CR-035 — Lectura por responsable

**CERRADO (auditoría de cierre, 2026-09-11) — consistente con CR-034/D-004:**

El responsable solo puede consultar el expediente de pacientes para los que mantiene una relación `ResponsiblePatientRelationship.ACTIVE` y siempre respetando el régimen de autorización del paciente.

El acceso no se deriva simplemente de haber creado una cita.

Cuando el acceso está autorizado, el responsable ve exactamente lo mismo que vería el paciente sobre sí mismo (CR-034): los cinco campos obligatorios completos de cada encuentro `COMPLETED`, metadatos y campos opcionales. No existe una regla de filtrado adicional específica para el responsable más allá de la propia autorización de acceso a ese paciente.

La matriz normativa vive en `clinical-permissions.md`.

---

## CR-036 — Lectura por médico

**Cerrado en `clinical-permissions.md`** (revisión de consistencia, 2026-09-11 — una redacción anterior describía esto como "situación pendiente crítica"; ese documento ya fue cerrado y ratificado, y contiene la matriz definitiva).

La política separa dos conceptos:

### Acceso contextual

El médico asignado puede consultar el contexto clínico que necesita para la atención de una cita válida.

### Acceso longitudinal

La consulta amplia del expediente histórico se concede según una regla explícita de relación/autorización clínica.

La recomendación para mantener el sistema simple es:

> **El acceso longitudinal de un médico se fundamenta en una relación médico-paciente activa; la asignación a una cita proporciona el acceso contextual necesario para esa atención, pero no crea ni activa la relación.**

Esta regla fue cerrada formalmente en `clinical-permissions.md` (P-011 a P-014).

---

## CR-037 — Lectura por administrador

**PROPUESTA DE CIERRE:**

El administrador con autoridad funcional puede acceder globalmente según las reglas de administración, pero todo acceso a información clínica sensible debe auditarse.

No se usará la condición de administrador como sustituto de las reglas de seguridad.

---

## CR-038 — Cambio de régimen menor → adulto

**Situación pendiente:** debe aclararse qué pasa con el expediente al cumplir 18 años y al ejecutar la transición explícita de régimen.

**PROPUESTA DE CIERRE:**

La transición de `MINOR` a `ADULT` **no crea un nuevo `MedicalRecord`**.

Se conserva exactamente el mismo expediente.

La transición modifica el régimen de acceso y autorizaciones, pero no altera:

- la identidad del paciente;
- la identidad del expediente;
- las consultas históricas;
- las recetas históricas;
- los estudios históricos;
- las alertas históricas.

El acceso del responsable se ajusta según la política ya definida para la transición a adulto.

**Razón:** el expediente pertenece a la continuidad clínica del paciente, no a su régimen de autorización.

---

## CR-039 — Cambio de responsable

**PROPUESTA DE CIERRE:**

Un cambio, alta o baja de `ResponsiblePatientRelationship` no modifica el expediente ni su historial.

Solo cambia quién tiene acceso según permisos.

---

## CR-040 — Cambio de médico

**PROPUESTA DE CIERRE:**

Un cambio de relación médico-paciente no mueve ni duplica el expediente.

El historial permanece asociado al mismo paciente.

Las consultas anteriores conservan el médico que las realizó.

---

## CR-041 — Un paciente con múltiples médicos

**PROPUESTA DE CIERRE:**

Un `MedicalRecord` puede contener información clínica generada por múltiples médicos a lo largo del tiempo.

No se crea un expediente independiente por médico.

Conceptualmente:

```text
Patient P1
   │
   └── MedicalRecord MR1
          ├── Encounter E1 by Doctor A
          ├── Encounter E2 by Doctor B
          └── Encounter E3 by Doctor A
```

---

## CR-042 — Múltiples clínicas

**PROPUESTA DE CIERRE:**

El expediente pertenece al paciente, no a una clínica.

Un paciente puede ser atendido en distintas `Clinic` sin crear múltiples expedientes.

Cada `ClinicalEncounter` conserva el contexto de clínica a través de la `Appointment` que lo originó.

---

## CR-043 — Contexto de clínica del expediente

**PROPUESTA DE CIERRE:**

No agregar `clinic_id` al `MedicalRecord`.

La clínica es un atributo contextual de la atención, no de la identidad longitudinal del expediente.

---

## CR-044 — Historial cuando un paciente deja de estar activo

**PROPUESTA DE CIERRE:**

Desactivar un paciente no elimina ni archiva funcionalmente su expediente clínico.

El historial permanece conservado conforme a las políticas del sistema y a las obligaciones aplicables.

El acceso posterior dependerá del estado del paciente y de los permisos definidos.

---

## CR-045 — Historial cuando el médico deja de estar activo

**PROPUESTA DE CIERRE:**

Desactivar un médico no modifica los `ClinicalEncounter` históricos ni elimina su autoría.

Los encuentros conservan el médico que los registró.

La inactividad del médico afecta su capacidad futura de operar, no la autoría histórica.

---

## CR-046 — Inmutabilidad del contenido clínico histórico

**PROPUESTA DE CIERRE:**

El contenido de un `ClinicalEncounter` `COMPLETED` sigue siendo inmutable conforme a `clinical-encounter-rules.md`.

`MedicalRecord` no tendrá mecanismos para sobrescribir encuentros históricos.

---

## CR-047 — Corrección de errores históricos

**Situación pendiente:** el dominio general necesita alguna salida para errores reales, pero Fase 3 ya cerró "sin reapertura, sin enmiendas/versionado" para `ClinicalEncounter`.

**PROPUESTA DE CIERRE PARA FASE 3:**

No implementar corrección funcional de encuentros completados dentro de `MedicalRecord`.

No permitir:

- editar directamente un encuentro cerrado desde el expediente;
- copiar un encuentro y reemplazar el anterior;
- cambiar su médico;
- cambiar su paciente;
- borrar el encuentro para ocultar el error.

Si posteriormente se requiere un mecanismo de corrección legal o clínica, será una evolución explícita con nuevo modelo de enmienda/versionado y auditoría.

---

## CR-048 — El expediente no altera la historia

**PROPUESTA DE CIERRE:**

Una vista del expediente es una proyección de lectura.

Ninguna operación de "abrir expediente" debe modificar datos clínicos.

La única excepción posible será el registro de auditoría de acceso, que pertenece al sistema de auditoría.

---

## CR-049 — Lectura no implica modificación

**PROPUESTA DE CIERRE:**

Consultar un expediente, un encuentro o un documento no modifica el contenido clínico.

Debe evitarse cualquier patrón que actualice `updated_at` de entidades clínicas solo por lectura.

---

## CR-050 — Auditoría del expediente

**PROPUESTA DE CIERRE:**

Las operaciones sensibles sobre `MedicalRecord` deben ser auditables.

Como mínimo conceptual:

- consulta del expediente;
- acceso a contexto clínico sensible;
- creación/modificación de antecedentes longitudinales;
- acceso administrativo;
- exportaciones o documentos, cuando existan.

La implementación concreta pertenece a `clinical-audit-and-history.md` y al módulo de auditoría.

---

## CR-051 — Auditoría no sustituye historial clínico

**PROPUESTA DE CIERRE:**

`AuditLog` registra el evento de acceso o modificación.

No debe convertirse en el almacenamiento principal del contenido clínico.

Por ejemplo:

```text
AuditLog: "Dr. X consultó expediente MR1"
```

no sustituye a:

```text
ClinicalEncounter E1
```

---

## CR-052 — Integridad del expediente

**PROPUESTA DE CIERRE:**

Las invariantes mínimas son:

```text
MedicalRecord.patient IS NOT NULL
UNIQUE(MedicalRecord.patient)
```

El expediente no puede existir sin paciente.

---

## CR-053 — Paciente válido

**PROPUESTA DE CIERRE:**

No crear un `MedicalRecord` para:

- `Responsible` sin ser `Patient`;
- `Invitation`;
- `User` sin identidad de paciente;
- prospectos no convertidos en pacientes.

El sujeto del expediente siempre es `Patient`.

---

## CR-054 — Una fuente de verdad para la identidad

**PROPUESTA DE CIERRE:**

La identidad del paciente dentro del expediente se obtiene de la relación `MedicalRecord.patient`.

No almacenar dentro de `MedicalRecord`:

```text
patient_name
patient_birth_date
patient_phone
patient_email
```

como copias persistentes.

---

## CR-055 — Datos derivados

**PROPUESTA DE CIERRE:**

Datos como:

- edad;
- IMC;
- última consulta;
- cantidad de consultas;
- fecha de última receta;
- número de estudios;

son datos derivados y no deben persistirse en `MedicalRecord` en Fase 3 salvo que una optimización posterior lo justifique y preserve una única fuente de verdad.

---

## CR-056 — No crear un "current encounter"

**PROPUESTA DE CIERRE:**

No agregar al expediente un campo:

```text
current_encounter
```

como fuente de verdad persistente.

El encuentro actual se determina por sus estados y relaciones válidas.

---

## CR-057 — Encuentros abiertos en el expediente

**PROPUESTA DE CIERRE:**

El expediente puede tener cero o más encuentros históricos `COMPLETED` y, de acuerdo con las reglas ya cerradas, puede tener uno o más `IN_PROGRESS` de diferentes citas.

El expediente no impone una regla adicional de exclusividad sobre consultas abiertas.

La regla de múltiples encuentros abiertos pertenece al dominio de `ClinicalEncounter`.

---

## CR-058 — Un mismo paciente y consultas abiertas simultáneas

**PROPUESTA DE CIERRE:**

`MedicalRecord` no bloqueará técnicamente múltiples encuentros abiertos del mismo paciente.

Las restricciones aplicables serán las definidas por Agenda y `ClinicalEncounter`.

**Razón:** evitar que el expediente introduzca una regla transversal no aprobada.

---

## CR-059 — Diagnósticos históricos

**PROPUESTA DE CIERRE:**

Los diagnósticos de Fase 3 permanecen como texto libre dentro de `ClinicalEncounter`.

`MedicalRecord` puede presentarlos como historial, pero no los normaliza a un catálogo ni crea automáticamente un diagnóstico activo.

No CIE-10 en Fase 3.

---

## CR-060 — Tratamientos históricos

**PROPUESTA DE CIERRE:**

El expediente conserva la referencia histórica a tratamientos e indicaciones registradas en encuentros y documentos correspondientes.

No se debe inferir que un tratamiento histórico sigue vigente a menos que una entidad futura indique explícitamente su vigencia.

---

## CR-061 — Prescripciones históricas vs. medicamentos actuales

**PROPUESTA DE CIERRE:**

Una receta histórica no equivale automáticamente a medicamento actual.

La vista "medicamentos actuales" solo podrá mostrarse cuando exista una fuente y regla explícita de vigencia.

Fase 3 no inferirá vigencia únicamente por fecha.

---

## CR-062 — Estudios históricos vs. resultados

**PROPUESTA DE CIERRE:**

Una `StudyOrder` y su eventual resultado son entidades relacionadas pero conceptualmente distintas.

La existencia de una solicitud no implica que el estudio se haya realizado ni que el resultado sea normal, anormal o interpretado.

---

## CR-063 — No diagnóstico automático desde resultados

**PROPUESTA DE CIERRE:**

El expediente puede presentar resultados disponibles, pero no genera diagnóstico, alerta o recomendación clínica automáticamente sin una regla explícitamente aprobada en una fase posterior.

---

## CR-064 — Historia gineco-obstétrica en Fase 3

**PROPUESTA DE CIERRE:**

La estructura genérica del expediente puede contener una sección explícita de antecedentes gineco-obstétricos en texto guiado.

No se crearán todavía modelos especializados para:

- embarazos;
- partos;
- cesáreas;
- abortos;
- menopausia;
- colposcopia;
- osteoporosis;
- fertilidad;

salvo que una fase funcional específica los requiera.

Esto mantiene el núcleo de Fase 3 genérico.

---

## CR-065 — No contaminar el núcleo con especialidades

**PROPUESTA DE CIERRE:**

`MedicalRecord` no debe tener campos especializados como:

```text
pregnancy_week
menopause_status
pap_result
bone_density
```

en el núcleo genérico de Fase 3.

Esos conceptos pertenecerán a módulos clínicos especializados o entidades específicas cuando se definan.

---

## CR-066 — Lectura de historial por contexto de cita

**PROPUESTA DE CIERRE:**

Cuando un médico esté atendiendo una cita y tenga autorización clínica válida para ese contexto, la interfaz puede mostrar el contexto necesario del expediente antes y durante la consulta.

Esto no modifica el historial y no crea una nueva relación médico-paciente.

---

## CR-067 — Privacidad por defecto

**PROPUESTA DE CIERRE:**

El expediente se considera información clínica sensible por defecto.

No existe un modo "público" de expediente.

Toda lectura debe pasar por autorización a nivel de objeto y por las reglas clínicas de acceso.

---

## CR-068 — No confiar en URLs ocultas

**PROPUESTA DE CIERRE:**

Una URL de expediente, encuentro o documento no constituye autorización.

El backend debe volver a validar el permiso en cada operación sensible.

---

## CR-069 — Exportación del expediente

**Situación pendiente:** `requirements.md` contempla generación de PDFs, pero no define todavía un "PDF de expediente completo".

**PROPUESTA DE CIERRE:**

No implementar en el núcleo de Fase 3 un PDF indiscriminado de todo el expediente.

Los documentos PDF se generan por tipos de documento clínico definidos.

Una exportación integral del expediente, si se requiere, será una capacidad separada con sus propias reglas de privacidad, autorización y auditoría.

---

## CR-070 — Importación de expedientes externos

**PROPUESTA DE CIERRE:**

Fuera de alcance de Fase 3.

No crear mecanismos genéricos para importar un expediente externo como texto/JSON/PDF y convertirlo automáticamente en historia clínica estructurada.

---

## CR-071 — Migración de historia clínica previa

**Situación pendiente:** el proyecto actualmente no tiene una historia clínica previa real que requiera migración.

**PROPUESTA DE CIERRE:**

No crear un flujo de migración genérico en Fase 3.

Si en una fase posterior existen datos clínicos legados, la migración deberá conservar su carácter histórico y registrar su origen.

---

## CR-072 — Paciente con expediente sin encuentros

**PROPUESTA DE CIERRE:**

Técnicamente puede existir un `MedicalRecord` sin encuentros cuando fue creado por una operación clínica preparatoria o cuando una migración posterior lo requiera.

Funcionalmente, un expediente vacío no se interpreta como consulta médica realizada.

---

## CR-073 — Encuentro sin expediente persistido

**PROPUESTA DE CIERRE:**

Una vez que se implementa el expediente como requisito del dominio clínico, un `ClinicalEncounter` no debe quedar persistido sin un `MedicalRecord` correspondiente al paciente.

Esto debe ser una propiedad del flujo de inicio cuando el expediente sea creado de forma lazy.

---

## CR-074 — Consistencia entre `Patient`, `Appointment`, `Encounter` y `MedicalRecord`

**PROPUESTA DE CIERRE:**

La cadena canónica es:

```text
MedicalRecord.patient
        ↑
        │
Appointment.patient
        ↑
        │
ClinicalEncounter.appointment
```

Debe cumplirse:

```text
Appointment.patient == MedicalRecord.patient
```

para todo `ClinicalEncounter` relacionado con ese expediente.

---

## CR-075 — Fallo de consistencia

**PROPUESTA DE CIERRE:**

Si una operación detecta una inconsistencia entre paciente, cita, encuentro y expediente, debe rechazarse como error de integridad y registrarse técnicamente.

No intentar "arreglar" automáticamente cambiando referencias para que coincidan.

---

## CR-076 — Concurrencia al crear expediente

**PROPUESTA DE CIERRE:**

Dos inicios clínicos concurrentes del mismo paciente no deben crear dos `MedicalRecord`.

La base de datos debe proteger la unicidad por paciente y la transacción debe manejar el posible conflicto de creación.

---

## CR-077 — Concurrencia de actualización del perfil longitudinal

**Situación pendiente:** dos actores pueden guardar cambios sobre los antecedentes al mismo tiempo.

**PROPUESTA DE CIERRE PARA FASE 3:**

El control mínimo será transaccional y deberá impedir que una escritura opere sobre un registro cerrado/inexistente o deje referencias inconsistentes.

No se implementará inicialmente un sistema sofisticado de edición colaborativa.

Cuando dos usuarios modifiquen simultáneamente un perfil mutable, la estrategia concreta de control de concurrencia se definirá en servicios/API.

---

## CR-078 — Pérdida silenciosa de cambios

**PROPUESTA DE CIERRE:**

La aplicación no debe afirmar al usuario que un cambio fue guardado si la transacción falló.

Los cambios no confirmados no forman parte del historial clínico.

---

## CR-079 — Autosave del expediente

**PROPUESTA DE CIERRE:**

No existe requisito de autosave para el perfil longitudinal en Fase 3.

Solo información que haya sido persistida exitosamente forma parte del expediente.

---

## CR-080 — Fechas de entidades relacionadas

**PROPUESTA DE CIERRE:**

`MedicalRecord` no reemplaza los timestamps propios de sus componentes.

Cada entidad clínica mantiene sus propias fechas semánticas.

Ejemplo:

```text
MedicalRecord.created_at
ClinicalEncounter.created_at
ClinicalEncounter.started_at
ClinicalEncounter.completed_at
Prescription.issued_at
StudyOrder.issued_at
ClinicalAlert.created_at
```

---

## CR-081 — Zona horaria

**PROPUESTA DE CIERRE:**

Los timestamps persistentes deberán representar instantes inequívocos de tiempo, siguiendo la configuración temporal global del sistema.

La zona horaria del consultorio sigue siendo relevante para la Agenda, pero `MedicalRecord` no adopta una zona horaria propia.

---

## CR-082 — Borrado en cascada

**PROPUESTA DE CIERRE:**

El borrado físico en cascada desde `Patient` hacia `MedicalRecord` y datos clínicos no debe utilizarse como mecanismo normal de operación.

La estrategia de relaciones debe diseñarse para preservar historia clínica y evitar eliminación accidental.

---

## CR-083 — Restauración

**PROPUESTA DE CIERRE:**

No habrá una operación funcional de "restaurar expediente eliminado", porque el expediente no se elimina funcionalmente en Fase 3.

---

## CR-084 — Copias y duplicados

**PROPUESTA DE CIERRE:**

No permitir:

- duplicar expediente;
- clonar expediente para otro paciente;
- copiar un expediente como nuevo expediente de la misma persona.

Toda continuidad clínica utiliza el mismo `MedicalRecord` del paciente.

---

## CR-085 — Separación de `MedicalRecord` y `ClinicalEncounter`

**PROPUESTA DE CIERRE:**

La separación es obligatoria:

```text
MedicalRecord = continuidad del paciente
ClinicalEncounter = episodio puntual de atención
```

Ninguno sustituye al otro.

---

## CR-086 — El expediente no determina el estado de la consulta

**PROPUESTA DE CIERRE:**

`MedicalRecord` nunca decide si una consulta está:

```text
IN_PROGRESS
COMPLETED
```

El estado pertenece a `ClinicalEncounter`.

---

## CR-087 — El expediente no determina el estado de la cita

**PROPUESTA DE CIERRE:**

`MedicalRecord` no cambia:

```text
SCHEDULED
IN_CONSULTATION
COMPLETED
CANCELLED
NO_SHOW
```

La coordinación necesaria se hace desde servicios clínicos que respetan las reglas de Agenda.

---

## CR-088 — Prohibición de CRUD genérico del expediente

**PROPUESTA DE CIERRE:**

No modelar `MedicalRecord` como un CRUD genérico sin reglas.

Las operaciones deben expresar acciones clínicas concretas:

```text
GetClinicalRecord
GetClinicalSummary
UpdateLongitudinalHistory
ListClinicalHistory
```

Los nombres exactos quedarán para `clinical-service-contracts.md`.

---

## CR-089 — No API genérica de reemplazo total

**PROPUESTA DE CIERRE:**

No exponer una operación equivalente a:

```text
PUT /medical-record/{id}
```

que permita reemplazar de una sola vez todos los datos del expediente.

Los cambios deben respetar la estructura y permisos de cada sección.

---

## CR-090 — Lectura histórica consistente

**PROPUESTA DE CIERRE:**

Una consulta de historial debe obtener los datos desde las entidades fuente, respetando su estado e invariantes.

No deberá mezclar datos de una entidad con otra como si fueran una sola versión mutable.

---

# 4. Modelo conceptual propuesto

La propuesta mínima para el núcleo del expediente es:

```text
Patient 1 ─── 1 MedicalRecord

MedicalRecord
├── longitudinal clinical history
├── ClinicalEncounter (indirectly through Patient/Appointment)
├── ClinicalAlert[]
├── Prescription[]
├── StudyOrder[]
└── ClinicalDocument[]
```

El modelo evita duplicar el paciente y evita un `medical_record_id` redundante dentro de `ClinicalEncounter`.

---

## 4.1 `MedicalRecord` como Aggregate Root

**PROPUESTA:** `MedicalRecord` puede tratarse como raíz de agregado del expediente longitudinal para las operaciones propias del expediente, pero no debe absorber las reglas internas de otros agregados clínicos.

Ejemplo:

```text
MedicalRecord Aggregate
├── longitudinal history/profile
└── references to clinical components
```

`ClinicalEncounter`, `Prescription`, `StudyOrder` y documentos conservan sus propias reglas y ciclos de vida.

Esto evita un mega-agregado con transacciones gigantes.

---

## 4.2 Qué pertenece directamente al agregado

En Fase 3, directamente en `MedicalRecord`:

```text
id
patient
created_at
updated_at
longitudinal history fields
```

No incluir directamente:

```text
appointment_id
current_doctor_id
current_clinic_id
current_diagnosis
current_prescription_id
all_documents_json
all_encounters_json
```

---

# 5. Historia longitudinal propuesta

## 5.1 Secciones

Para la primera versión, las secciones propuestas son:

```text
family_history
personal_pathological_history
personal_non_pathological_history
housing_history
gynecologic_obstetric_history
other_relevant_history
```

Son campos explícitos de texto, no JSON genérico.

---

## 5.2 Motivo de esta estructura

El requisito histórico solicita una primera versión con campos abiertos guiados.

La opción más sencilla compatible con lo ya decidido es usar campos explícitos y permitir evolución posterior.

No introducir todavía:

- constructor dinámico de formularios;
- campos definidos por usuario;
- formularios por especialidad dentro del núcleo;
- esquema clínico JSON arbitrario.

---

## 5.3 Semántica de los antecedentes

Los antecedentes representan información longitudinal conocida en el expediente.

No son una copia de cada consulta.

Ejemplo:

```text
ClinicalEncounter E1
  Padecimiento actual: "..."

MedicalRecord history
  Antecedentes personales patológicos: "Diabetes mellitus..."
```

La consulta conserva lo que se documentó en ese momento; el perfil longitudinal conserva el contexto actual del expediente.

---

## 5.4 Texto clínico real

Los campos longitudinales deben seguir una regla de contenido similar a la ya cerrada para `ClinicalEncounter`:

- trim de espacios iniciales/finales;
- cadenas solo con espacios equivalen a vacío;
- placeholders obvios no deben aceptarse como contenido real;
- no imponer una longitud mínima arbitraria;
- no evaluar automáticamente la corrección médica.

---

# 6. Relación con `ClinicalEncounter`

La relación conceptual es:

```text
Patient
   │
   ├── MedicalRecord
   │
   └── Appointment
          │
          └── ClinicalEncounter
```

La historia clínica se construye uniendo ambas perspectivas:

```text
MedicalRecord
    │
    └── Patient
          ├── Appointments
          │      └── ClinicalEncounters
          ├── ClinicalAlerts
          ├── Prescriptions
          ├── StudyOrders
          └── Documents
```

---

# 7. Invariantes propuestas del `MedicalRecord`

## MR-I-001 — Un paciente, un expediente

```text
COUNT(MedicalRecord WHERE patient = P) ≤ 1
```

## MR-I-002 — Todo expediente tiene paciente

```text
MedicalRecord.patient IS NOT NULL
```

## MR-I-003 — No reasignación

El paciente de un expediente no cambia.

## MR-I-004 — Sin borrado funcional

El expediente no se elimina mediante una operación clínica normal.

## MR-I-005 — Encuentro clínico asociado al mismo paciente

Todo encuentro que aparezca en el historial de un expediente debe corresponder al mismo paciente del expediente.

## MR-I-006 — No duplicación del paciente

Los datos administrativos del paciente no se duplican como fuente persistente dentro del expediente.

## MR-I-007 — Historia separada de contexto actual

Un dato histórico no debe presentarse automáticamente como un estado actual.

## MR-I-008 — Sin diagnóstico autónomo

El expediente no genera diagnósticos.

## MR-I-009 — Sin sobrescritura histórica

Los encuentros completados conservan su contenido.

## MR-I-010 — Sin relación médico-paciente implícita

Crear o leer el expediente no modifica `DoctorPatientRelationship`.

## MR-I-011 — Régimen menor/adulto no crea un expediente nuevo

La transición conserva el mismo expediente.

## MR-I-012 — Clínica no define la identidad del expediente

Un paciente tiene el mismo expediente aunque sea atendido en distintas clínicas.

---

# 8. Invariantes de historial

## MR-H-001 — Los encuentros históricos son unidades independientes

Cada consulta conserva su propia identidad, fechas, médico y cita.

## MR-H-002 — No combinar consultas

El expediente no debe fusionar dos consultas históricas en una sola nota.

## MR-H-003 — No sobrescribir por "último valor"

El último diagnóstico o tratamiento no reemplaza los valores históricos.

## MR-H-004 — Orden temporal explícito

Las consultas se ordenan por sus fechas clínicas, no por el orden en que el usuario abrió las pantallas.

## MR-H-005 — No inferencia clínica

Mostrar historia no equivale a emitir una nueva interpretación clínica.

---

# 9. Ciclo de vida conceptual

A diferencia de `ClinicalEncounter`, `MedicalRecord` no necesita un ciclo de vida de estados.

Conceptualmente:

```text
NO RECORD
   │
   │ primera operación clínica
   ▼
RECORD EXISTS
   │
   ├── consultas en progreso
   ├── consultas completadas
   ├── alertas
   ├── recetas
   ├── estudios
   └── documentos
        │
        ▼
continuidad histórica
```

No existe una transición funcional de cierre del expediente en Fase 3.

---

# 10. Operaciones de dominio previstas

Los nombres exactos se definirán en `clinical-service-contracts.md`.

## 10.1 Obtener expediente

```text
GetMedicalRecord
```

Responsabilidad:

- localizar el expediente del paciente;
- verificar autorización;
- devolver la estructura longitudinal correspondiente.

---

## 10.2 Obtener resumen clínico

```text
GetClinicalSummary
```

Responsabilidad:

- reunir datos canónicos;
- ordenar historial reciente;
- incluir alertas y componentes disponibles;
- no inferir diagnósticos ni estados clínicos no registrados.

---

## 10.3 Actualizar historia longitudinal

```text
UpdateLongitudinalHistory
```

Responsabilidad:

- verificar autorización;
- validar contenido;
- persistir los campos explícitos;
- actualizar `MedicalRecord.updated_at`;
- generar auditoría cuando corresponda.

---

## 10.4 Listar historial clínico

```text
ListClinicalHistory
```

Responsabilidad:

- devolver encuentros y otros elementos ordenados;
- respetar autorización por objeto;
- no alterar datos.

---

# 11. Errores de dominio propuestos

Los nombres definitivos quedarán en `clinical-service-contracts.md`.

Como mínimo:

```text
MedicalRecordNotFound
MedicalRecordAlreadyExists
PatientAlreadyHasMedicalRecord
MedicalRecordPatientMismatch
MedicalRecordImmutableIdentity
UnauthorizedMedicalRecordAccess
UnauthorizedMedicalRecordModification
ClinicalHistoryInvalidContent
ClinicalHistoryPlaceholder
ClinicalRecordIntegrityError
ConcurrentMedicalRecordUpdate
```

No exponer errores de SQL como contrato funcional.

---

# 12. Concurrencia e integridad

## 12.1 Creación concurrente

La combinación:

```text
UNIQUE(patient_id)
+
transaction
+
tratamiento del conflicto
```

protege la creación única del expediente.

---

## 12.2 Actualización concurrente

Para el perfil longitudinal mutable, la estrategia concreta puede utilizar una transacción y mecanismos de control de actualización apropiados.

Fase 3 no requiere edición colaborativa sofisticada.

---

## 12.3 Encuentro vs. expediente

Cerrar un `ClinicalEncounter` no requiere modificar simultáneamente el contenido del perfil longitudinal salvo que exista una operación clínica explícita que cambie ambos dominios y sea aprobada posteriormente.

Esto evita convertir el cierre de consulta en una operación gigantesca que actualice todo el expediente.

---

# 13. Integridad de base de datos propuesta

Como mínimo:

```text
MedicalRecord.patient_id NOT NULL
UNIQUE(MedicalRecord.patient_id)
```

Los campos longitudinales explícitos deben tener la nulabilidad que corresponda a su naturaleza opcional.

No almacenar un JSON clínico único como fuente de verdad.

---

# 14. Separación de responsabilidades

## 14.1 `Patient`

Responsable de:

- identidad;
- datos administrativos;
- régimen del paciente;
- información base definida en su propio dominio.

## 14.2 `MedicalRecord`

Responsable de:

- continuidad del expediente;
- contexto clínico longitudinal;
- acceso estructurado al historial.

## 14.3 `ClinicalEncounter`

Responsable de:

- episodios de atención;
- contenido de cada consulta;
- estados `IN_PROGRESS/COMPLETED`;
- inmutabilidad del encuentro completado.

## 14.4 `DoctorPatientRelationship`

Responsable de:

- relación longitudinal de autorización/relación médico-paciente;
- no de la identidad del expediente.

## 14.5 `ClinicalAlert`

Responsable de:

- alertas clínicas activas e históricas.

## 14.6 `Prescription`

Responsable de:

- recetas emitidas y su trazabilidad.

## 14.7 `StudyOrder`

Responsable de:

- solicitudes de estudios y su trazabilidad.

## 14.8 `ClinicalDocument`

Responsable de:

- documentos clínicos y almacenamiento privado.

## 14.9 `AuditLog`

Responsable de:

- trazabilidad de accesos y operaciones relevantes.

---

# 15. Matriz propuesta de decisiones

| Tema | Propuesta | Estado recomendado |
|---|---|---|
| Patient ↔ MedicalRecord | 1:1 | Cerrar |
| Creación | Lazy en primera operación clínica | Cerrar |
| Creación + primer encuentro | Misma transacción | Cerrar |
| Estado propio | Ninguno | Cerrar |
| DELETE | No funcional | Cerrar |
| Reasignación | Prohibida | Cerrar |
| Número de expediente | No en F3 | Cerrar |
| Datos administrativos duplicados | No | Cerrar |
| Núcleo de MedicalRecord | Mínimo | Cerrar |
| Antecedentes | Campos explícitos guiados | Cerrar |
| Historial de antecedentes | Mutable + auditoría; sin versionado completo F3 | Cerrar |
| ClinicalEncounter | Relación indirecta por Patient/Appointment | Cerrar |
| Alertas | Entidad separada | Cerrar |
| Recetas | Entidad separada | Cerrar |
| Estudios | Entidad separada | Cerrar |
| Documentos | Entidad separada | Cerrar |
| Resumen clínico | Proyección, no snapshot | Cerrar |
| Diagnóstico actual automático | Prohibido | Cerrar |
| Especialidades | Fuera del núcleo | Cerrar |
| Menor → adulto | Mismo expediente | Cerrar |
| Cambio de responsable | No modifica expediente | Cerrar |
| Cambio de médico | No modifica expediente | Cerrar |
| Cambio de clínica | No modifica expediente | Cerrar |
| Auditoría | Obligatoria para operaciones sensibles | Cerrar |
| Permisos de médico | Contextual + longitudinal según relación | Cerrado en `clinical-permissions.md` |
| Permisos de paciente | Sujeto a política de privacidad | Cerrado en `clinical-permissions.md` |
| Permisos de responsable | Relación activa + régimen | Cerrado en `clinical-permissions.md` |
| Exportación integral | Fuera del núcleo F3 | Cerrar |
| Importación | Fuera de alcance | Cerrar |

---

# 16. Relación con documentos futuros

El cierre de este documento habilita directamente:

```text
clinical-permissions.md
clinical-security-and-privacy.md
clinical-service-contracts.md
clinical-api-contracts.md
phase-3-clinical-ux.md
clinical-screens.md
clinical-audit-and-history.md
phase-3-testing-strategy.md
```

Especialmente importante:

### `clinical-permissions.md`

Debe transformar las propuestas CR-034 a CR-037 en una matriz normativa de lectura por actor y contexto.

### `clinical-security-and-privacy.md`

Debe concretar protección de información clínica, documentos privados, acceso a nivel de objeto y controles de seguridad.

### `clinical-service-contracts.md`

Debe convertir las operaciones conceptuales de este documento en servicios con entradas, salidas, errores y transacciones.

---

# 17. Decisiones que este documento no debe cerrar por sí solo

Este documento deliberadamente no fija de forma definitiva:

1. La matriz completa de permisos para leer todo el historial clínico.
2. Qué campos exactos puede ver el paciente desde su portal.
3. Qué campos puede ver un responsable.
4. Qué médicos pueden consultar historia completa frente a contexto limitado.
5. Diseño físico final de `ClinicalAlert`.
6. Diseño físico final de `Prescription`.
7. Diseño físico final de `StudyOrder`.
8. Diseño físico final de `ClinicalDocument`.
9. Versionado futuro de antecedentes longitudinales.
10. Mecanismos extraordinarios de corrección de registros clínicos cerrados.

Estas decisiones deben aparecer en sus documentos correspondientes y no deben resolverse implícitamente desde la UI.

---

# 18. Criterio de consistencia del dominio

La implementación será consistente con este documento cuando pueda cumplirse, como mínimo:

```text
Patient P1
    ↓
MedicalRecord MR1
    ↓
Clinical history of P1
```

sin duplicar la identidad del paciente ni crear múltiples expedientes.

Y para una consulta:

```text
Appointment A1
   ↓
ClinicalEncounter E1
   ↓
Patient P1
   ↓
MedicalRecord MR1
```

con:

```text
A1.patient == P1
MR1.patient == P1
```

Además:

```text
E1.COMPLETED
    ⇒ E1 remains historical and immutable
```

La vista del expediente podrá mostrar ese encuentro, pero no podrá modificarlo.

---

# 19. Principios de implementación

1. **Una fuente de verdad por concepto.**
2. **No duplicar `Patient`.**
3. **No duplicar `ClinicalEncounter`.**
4. **No usar JSON clínico genérico como atajo.**
5. **No crear estados de expediente sin necesidad funcional.**
6. **No introducir especialidades en el núcleo genérico.**
7. **No convertir auditoría en historia clínica.**
8. **No convertir el resumen clínico en fuente de verdad.**
9. **No inferir estados clínicos actuales desde datos históricos.**
10. **Proteger toda lectura clínica con autorización.**
11. **Mantener la historia después de cambios administrativos.**
12. **Usar transacciones y restricciones de PostgreSQL para invariantes estructurales.**

---

# 20. Recomendación final

La propuesta recomendada para TeCuidoApp es mantener `MedicalRecord` como un **contenedor longitudinal ligero y estable**, con un único expediente por paciente, mientras que la riqueza histórica reside en las entidades clínicas especializadas que lo componen.

En términos simples:

```text
Patient
   │
   └── MedicalRecord  ← identidad longitudinal
          │
          ├── ClinicalEncounter  ← cada consulta
          ├── ClinicalAlert      ← alertas
          ├── Prescription       ← recetas
          ├── StudyOrder         ← estudios
          └── ClinicalDocument   ← documentos
```

Esto conserva la decisión fundamental del proyecto:

> **El expediente no se sobrescribe; el expediente acumula historia clínica estructurada y trazable.**

La matriz exacta de **quién puede leer qué parte del expediente en cada contexto** vive normativamente en `clinical-permissions.md`; la resolución de base (paciente/responsable ven los cinco campos completos de cada encuentro `COMPLETED` propio/autorizado) queda cerrada en CR-034/CR-035 de este documento y no debe reabrirse ahí.

---

# 21. Criterio de salida

**Ratificado en la auditoría de cierre de Fase 3 (2026-09-11).** Las 90 decisiones CR-001 a CR-090 de este documento quedan aprobadas, incluyendo:

- cardinalidad uno a uno `Patient ↔ MedicalRecord`;
- creación lazy y atómica con la primera consulta;
- no borrado y no reasignación;
- no duplicación de datos del paciente;
- historial por componentes clínicos;
- antecedentes longitudinales explícitos;
- resumen como proyección;
- continuidad del expediente en transición menor → adulto;
- separación total de Agenda y `DoctorPatientRelationship`;
- estructura sin JSON clínico genérico;
- auditoría de operaciones sensibles;
- permisos de lectura por paciente/responsable (CR-034/CR-035, resueltos en esta misma revisión — D-004);
- permisos de lectura por médico y administrador cerrados en `clinical-permissions.md`.

**Siguiente documento:** `clinical-permissions.md`.

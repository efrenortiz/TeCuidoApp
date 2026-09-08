# ADR-007 — Responsible-Initiated Minor Patient Registration

**Estado:** Accepted
**Fecha:** 2026-09-08
**Decisores:** Equipo de desarrollo
**Área:** Identidad / Registro de pacientes / Relaciones de dominio

---

## 1. Contexto

`requirements.md` §3.1 ya establecía que un Responsable puede "registrar pacientes menores de
edad o personas que requieran responsable", pero sin detallar el mecanismo. Todo el diseño de
registro implementado hasta ahora (ADR-002, ADR-003) asume un único flujo:

```text
Doctor
   ↓
Invitation
   ↓
Prospect (adulto)
   ↓
User / Person / Patient
```

Ese flujo asume que **quien se registra es quien queda registrado**: el prospecto adulto crea
su propia cuenta, acepta su propia invitación y verifica su propio correo. Ese supuesto no es
válido cuando un responsable incorpora a un paciente menor: ahí, quien inicia el flujo
(el responsable, ya autenticado) no es la persona que queda registrada como paciente (el
menor). Superponer ambos casos en el mismo formulario/modelo mezclaría dos conceptos de
negocio distintos y debilitaría garantías de seguridad ya documentadas en ADR-003.

Esta ADR registra la decisión de tratarlos como dos flujos explícitamente separados y define
las implicaciones arquitectónicas del segundo.

Además del registro inicial, esta ADR cubre el ciclo de vida completo del régimen de menor de
edad: también fija (§3.8) el mecanismo por el cual un paciente registrado como menor pasa a
régimen adulto, quedando fuera del alcance de sus responsables.

---

## 2. Problema

Reutilizar `accounts.Invitation` tal cual para este nuevo flujo requeriría:

- hacer `Invitation.doctor` opcional (hoy es `ForeignKey(... on_delete=PROTECT)`, obligatorio
  — ADR-003 §9 lo trata explícitamente como el ancla de confianza de la invitación: "el
  médico asociado a una invitación debe obtenerse desde la entidad `Invitation`");
- cambiar el destinatario conceptual del token: en el flujo actual, quien acepta la
  invitación es quien queda registrado; en el nuevo flujo, quien confirma (el responsable) no
  es quien queda registrado (el menor);
- decidir si "aceptar" produce un `Patient` nuevo (como hoy) o simplemente confirma uno que
  **ya fue creado antes** de generar el enlace (el orden de creación es distinto: en el flujo
  actual, el `Patient` se crea *al aceptar*; en el propuesto, el `Patient` se crea *al
  capturar los datos del menor*, antes de generar cualquier enlace).

Superponer estos dos casos en un mismo modelo obligaría a introducir condicionales sobre "qué
significa este campo según el caso", exactamente el tipo de ambigüedad que ADR-005 busca
evitar entre entidades de dominio.

---

## 3. Decisión

### 3.1 Dos flujos, no una variante

Se modelan como dos flujos separados, ambos documentados en `requirements.md` §7 (§7.1 el
existente, §7.2 el nuevo). No se reutiliza `accounts.Invitation` para el caso de menores.

### 3.2 El `Patient` se crea directamente, no al confirmar

En el flujo de menor, el responsable ya está autenticado y autorizado (tiene un
`Responsible` existente). El sistema crea `Person` + `Patient` en el momento en que el
responsable captura los datos del menor — no existe un "prospecto" intermedio que deba
aceptar nada para que el paciente exista.

Inmediatamente después se crea `ResponsiblePatientRelationship(responsible=<autenticado>,
patient=<nuevo>, relationship_type=<elegido>)`. Esta relación es la única fuente de
autorización del responsable sobre ese paciente — nunca "ambos registros los creó el mismo
usuario" (consistente con ADR-004 §17 y con `patients/services/permissions.py`).

### 3.3 `Person.user` permanece `NULL` por defecto

Esto **no requiere ningún cambio de esquema**: ADR-002 ya diseñó `Person.user` como
`OneToOneField` nullable exactamente para este caso ("un Patient puede existir sin User
propio"). Este ADR confirma que el flujo de menor es el caso de uso real que justifica esa
decisión, ya tomada.

Se formaliza la distinción conceptual:

- **Paciente clínico** (`Patient`/`Person` sin `User`): existe en TeCuido, puede recibir
  atención y quedar en el expediente, sin poder iniciar sesión.
- **Usuario paciente** (`Patient`/`Person` con `User` asociado): además tiene credenciales
  propias.

El registro inicial de un menor por su responsable **crea solo el paciente clínico**. No se
exige `User` en este paso.

### 3.4 Mecanismo de confirmación — sin token/enlace por correo; aprobación en la app

**Addendum (resuelto en implementación, 2026-09-08):** esta sección originalmente exigía "un
mecanismo de confirmación de un solo uso con token seguro y expiración, cuyo destinatario es
el responsable". Al implementar, se resolvió que ese mecanismo **no necesita ser un token/
enlace por correo**:

- **Alta de un menor nuevo (sin coincidencia):** no se genera ningún token. El responsable ya
  está autenticado durante todo el flujo (su propio login ya pasó por la verificación de
  `email_verified` de ADR §36 regla 3) — pedirle que además confirme por correo algo que
  acaba de hacer con sesión activa es fricción sin beneficio real de seguridad. Esto es
  distinto del flujo médico → prospecto (ADR-003), donde el destinatario del token *no* está
  autenticado — ahí el token sí es la única prueba de acceso al correo.
- **Coincidencia por CURP (§3.7), relación creada en estado `PENDING`:** la "confirmación" es
  la aprobación hecha en la app (`docs/design/screens.md` §6.7,
  `patients.services.minors.approve_relationship_request`) por un responsable *ya
  autenticado* que gestiona ese paciente — no un enlace por correo. La autorización se
  verifica con `patients.services.permissions.responsible_has_active_relationship`, reusando
  el mismo mecanismo de autorización de objeto que el resto de Fase 1 (ADR-004), no uno nuevo.

No se creó ninguna entidad de token para este flujo. El texto original de esta sección se
conserva abajo como registro de la decisión que se reemplazó, no como el estado actual:

> ~~Se requiere un mecanismo de confirmación de un solo uso con token seguro y expiración,
> cuyo destinatario es el responsable (para confirmar identidad/términos), no el menor. Se
> modela como una entidad propia... Debe seguir los mismos principios de seguridad ya
> establecidos en ADR-003 (§7-8, §11-12, §24-25): token generado con `secrets`, solo se
> persiste su hash, expiración configurable, uso único, sin datos sensibles legibles en el
> token, sin registrar el token completo en logs.~~

### 3.5 Ninguna `DoctorPatientRelationship` automática

Registrar a un menor no crea ni modifica ninguna `DoctorPatientRelationship`. Esa relación se
establece por un camino separado (igual que hoy: vía invitación de médico, o el mecanismo que
se decida para asociar un médico a un paciente ya existente). Se mantienen deliberadamente
separadas:

```text
Responsible ──── ResponsiblePatientRelationship ──── Patient ──── DoctorPatientRelationship ──── Doctor
```

"Quién tiene autorización sobre el menor" y "qué médico puede acceder a su expediente" son
relaciones independientes (consistente con ADR-002 §8 y ADR-005 §9).

### 3.6 Edad derivada del servidor, no del cliente

La condición de "menor" se deriva siempre de `Person.birth_date` en el servidor. No existe ni
debe existir un campo tipo `is_minor` capturado por el usuario.

### 3.7 Detección de "menor ya existente" nunca otorga acceso automático

Antes de crear un `Patient`, el sistema busca coincidencias en dos niveles (detalle completo
en `requirements.md` §7.2.7):

1. **CURP** (normalizado) — alta confianza, es un identificador único de persona.
2. **Nombre completo + fecha de nacimiento** (coincidencia exacta, no difusa) — solo si no hay
   CURP capturado. Confianza baja: es una señal, no una confirmación de identidad.

La decisión central es que **ninguna coincidencia, ni siquiera por CURP, otorga acceso por sí
sola**:

- Coincidencia por CURP contra un paciente **sin `User` propio**: no se duplica el registro,
  pero la nueva `ResponsiblePatientRelationship` nace **sin vigencia** — requiere aprobación de
  un responsable ya autorizado sobre ese paciente. Esto es deliberado: que alguien conozca el
  CURP de un menor no debe bastar para obtener acceso a su expediente.
- Coincidencia solo por nombre+fecha de nacimiento (sin CURP): no se crea ni se vincula nada
  automáticamente. Se escala a un proceso manual (contactar al consultorio/médico) — no es un
  flujo de autoservicio, precisamente porque la señal no es confiable.
- Coincidencia contra un paciente que **ya tiene `User` propio** (gestiona su propia cuenta):
  vincular un responsable requiere el consentimiento de esa persona. Ese consentimiento no se
  diseña en esta ADR — mientras no exista, el sistema no debe crear la relación bajo ninguna
  circunstancia, aunque el CURP coincida.
- En ningún caso el sistema revela al responsable datos del registro existente (nombre de
  otro responsable, información del paciente) — mismo principio anti-enumeración que ADR-003
  §18, aplicado aquí a un contexto distinto (vinculación, no invitación).

**Implementado como:** `ResponsiblePatientRelationship.status` (`CharField` con `choices`
`PENDING`/`ACTIVE`/`INACTIVE`, reemplazando el `is_active` booleano original) — nunca-aprobada
/ vigente / desactivada como tres estados distintos, no colapsados en un solo booleano.

**Sin `default` a nivel de campo, deliberadamente.** Ni `ACTIVE` ni `PENDING` son un default
seguro de forma genérica: cada operación de negocio sabe si está creando una relación ya
aprobada (alta de menor nuevo, §3.2) o una que requiere aprobación (coincidencia por CURP,
más arriba) — dejar que un `default` decida por omisión es exactamente el tipo de activación
implícita que "deny by default" (ADR-004) prohíbe. Como Django no rechaza un `CharField` sin
`default` ni valor explícito (inserta `""` silenciosamente), la garantía real es un
`CheckConstraint` en `Meta.constraints` que solo permite los tres valores del enum — omitir
`status` falla con `IntegrityError`, no con una activación accidental.

### 3.8 Transición a régimen adulto — mecanismo concreto (addendum 2026-09-08)

**Addendum:** esta sección originalmente solo fijaba que cumplir 18 años no dispara ningún
cambio automático, y dejaba el mecanismo real como pendiente ("no se diseña un mecanismo de
consentimiento nuevo... queda sujeto a §5"). Al aterrizar el diseño con el usuario, se decidió
el mecanismo concreto. El texto original se conserva tachado al final de esta sección; lo que
sigue es la decisión vigente.

**Modelo de datos.** La autorización del paciente sobre su propio expediente es un concepto
distinto de su edad cronológica — se separan en dos campos independientes:

```text
Person.is_minor   → computado desde birth_date (sin cambios, ADR-007 §3.6)
Patient.regime    → MINOR | ADULT — almacenado, cambia solo por transición explícita
```

- `Patient.regime`: `CharField` con `choices` (`MINOR`/`ADULT`), **sin `default` de campo**
  (mismo motivo que `ResponsiblePatientRelationship.status`, §3.7: cada creación de `Patient`
  debe declararlo explícitamente — `register_minor_patient` siempre pasa `MINOR`;
  `accept_invitation`, al ser un adulto autorregistrándose, siempre pasa `ADULT`). Un
  `CheckConstraint` restringe la columna a esos dos valores, para que un `Patient` creado sin
  especificar `regime` falle con `IntegrityError` en vez de insertar `""`.
- `Patient.regime_changed_at`: `DateTimeField` nulo — se llena únicamente al ejecutar la
  transición.
- `Patient.regime_changed_by`: `ForeignKey` a `doctors.Doctor`, nulo, `on_delete=PROTECT` —
  igual criterio de trazabilidad que el resto del sistema (nunca perder quién hizo qué).

`ResponsiblePatientRelationship` gana dos campos para poder decir "quién tuvo autorización
sobre este paciente, desde cuándo y hasta cuándo, y por qué terminó":

- `deactivated_at`: `DateTimeField` nulo mientras la relación siga `PENDING`/`ACTIVE`.
- `deactivation_reason`: `CharField` con `choices` (`ADULT_TRANSITION`, `REQUEST_REJECTED`,
  `OTHER`), **sin `default` de campo** — cada servicio que desactive una relación declara su
  motivo explícitamente. Un `CheckConstraint` exige que, cuando `status = INACTIVE`,
  `deactivated_at` y `deactivation_reason` no sean nulos — mismo patrón ya usado en
  `Invitation.used_at` (requiere `status = USED`). `reject_relationship_request` (ya
  implementado, ADR-007 §3.7) queda pendiente de actualizarse para pasar
  `deactivation_reason=REQUEST_REJECTED` — no se hace en este addendum, queda registrado como
  trabajo de implementación pendiente.

**Quién puede ejecutar la transición y cuándo.** Cualquier médico con `DoctorPatientRelationship`
**activa** hacia el paciente — sin restringir por `relationship_type` (tratante, sustituto u
otro sirven igual). El disparador de negocio es que el paciente manifieste, en consulta, por
teléfono o de viva voz, su voluntad de ser tratado como adulto; el sistema no exige ni valida
un artefacto de consentimiento independiente — la acción del médico en el sistema **es** la
constancia de esa manifestación, bajo su responsabilidad profesional. Mientras ningún médico
la ejecute, el paciente se sigue tratando como menor sin importar su edad cronológica.

**Candado legal.** La transición se rechaza (en servidor, no solo en UI) si `Person.is_minor`
sigue siendo `True` en el momento de ejecutarla.

**Operación, atómica en un solo paso** (`patients/services/minors.py`,
`transition_patient_to_adult(*, patient, performed_by_doctor)`):

1. Rechaza si `patient.regime` ya es `ADULT` (operación no repetible — es irreversible).
2. Rechaza si `patient.person.is_minor` es `True` (candado legal).
3. Rechaza si `performed_by_doctor` no tiene `DoctorPatientRelationship` activa con `patient`.
4. `patient.regime = ADULT`, `regime_changed_at = ahora`, `regime_changed_by = performed_by_doctor`.
5. **Todas** las `ResponsiblePatientRelationship` `ACTIVE` de ese paciente → `INACTIVE`,
   `deactivated_at = ahora`, `deactivation_reason = ADULT_TRANSITION` — en la misma
   transacción, no una por una.
6. No crea, exige ni modifica ningún `User`. Deliberadamente desacoplado: un paciente puede
   quedar en `regime = ADULT` sin cuenta propia todavía. Quién autoriza que la obtenga más
   adelante sigue siendo una decisión pendiente e independiente (§5) — no bloquea ni condiciona
   esta transición.

**Irreversible.** Una vez `ADULT`, no existe operación para volver a `MINOR` dentro de este
flujo.

**No se introduce ninguna entidad de auditoría nueva.** La traza completa vive en los campos
ya descritos (`Patient.regime_changed_at`/`regime_changed_by` + `deactivated_at`/
`deactivation_reason` en cada relación) — no se necesita un modelo `PatientAdultTransition`
separado para esto.

---

<details>
<summary>Texto original de esta sección (reemplazado por el addendum de arriba)</summary>

> Cumplir 18 años no dispara ningún cambio de estado por sí mismo (detalle completo en
> `requirements.md` §7.2.8). Decisiones concretas:
>
> - La mayoría de edad es una condición computada en el momento de cada verificación de
>   acceso a partir de `Person.birth_date` — nunca un valor que un proceso programado
>   reescriba en la fecha exacta del cumpleaños. Fase 1 no incorpora Celery ni tareas
>   programadas; introducir esa infraestructura solo para esto violaría CLAUDE.md §13
>   (no agregar dependencias sin necesidad real).
> - Ninguna `ResponsiblePatientRelationship` existente se desactiva, modifica ni elimina por
>   el solo hecho de que el paciente cumpla 18 años. Continuidad del cuidado sobre revocación
>   silenciosa.
> - La UI debe hacer visible la transición (ver `docs/design/screens.md` §6.5 y §6.7) — esto
>   es una capa de presentación informativa, no un cambio de autorización en sí mismo.
> - No se diseña un mecanismo de consentimiento nuevo para esta transición. Si el paciente,
>   ya adulto, llega a tener su propia cuenta (`User`) — mecanismo todavía pendiente, §5 —,
>   cualquier `ResponsiblePatientRelationship` sobre su expediente, incluida la heredada de su
>   minoría de edad, queda sujeta a la misma regla de consentimiento de §3.7 (vincular a un
>   paciente con `User` propio requiere su consentimiento). Es el mismo mecanismo aplicado
>   también a relaciones preexistentes, no uno paralelo.
> - No se introduce una expiración forzosa por tiempo. Un límite estricto (p. ej. "N días tras
>   el cumpleaños") es una decisión separada y, si se toma, probablemente requeriría
>   infraestructura de tareas programadas — explícitamente fuera de alcance aquí.

</details>

---

## 4. Alternativas consideradas

### Alternativa A — Relajar `accounts.Invitation.doctor` a nullable

Rechazada. Debilitaría el invariante de seguridad de ADR-003 §9 ("el médico asociado a una
invitación debe obtenerse desde la entidad `Invitation`, el cliente no debe poder cambiarlo")
para una fila que, en este nuevo caso, no tendría médico en absoluto — obligaría a todo el
código que consume `Invitation` a manejar un `doctor` opcional que antes era garantizado,
aumentando la superficie de error para el flujo ya existente y probado.

### Alternativa B — El responsable llena todo en un solo paso, sin confirmación

Rechazada. Elimina la trazabilidad/segundo factor de confirmación que sí existe en el flujo
de invitación adulta, y no hay ninguna razón de negocio para dar menos garantías de seguridad
a este flujo que al otro.

### Alternativa C — El menor recibe y acepta la invitación como un prospecto adulto

Rechazada explícitamente por el propio requerimiento: obligaría a un menor a actuar como si
fuera un adulto creando su propia cuenta, exactamente lo que este flujo busca evitar.

### Alternativa D — Coincidencia difusa (fuzzy) de nombre para detectar duplicados

Rechazada. Un algoritmo de similitud (distancia de edición, fonética, etc.) introduce falsos
positivos y negativos sin un criterio determinista ni testeable, y complica innecesariamente
la explicación al usuario de por qué se bloqueó o no un registro. Se prefiere coincidencia
exacta normalizada (§3.7), con una categoría de confianza explícita en vez de un umbral de
similitud ajustable.

### Alternativa E — Vincular automáticamente cuando el CURP coincide

Rechazada. Aunque el CURP identifica de forma confiable a la persona, no identifica quién
tiene autorización legítima sobre su expediente — conocer o adivinar un CURP no debe bastar
para obtener acceso. Se exige aprobación de un responsable ya autorizado (§3.7).

### Alternativa F — Desactivar automáticamente la relación al cumplir 18 años (tarea programada)

Rechazada. Requeriría infraestructura de tareas programadas (Celery) que Fase 1 no tiene ni
necesita para nada más, solo para reescribir un estado en una fecha exacta. Además revocaría
silenciosamente un acceso legítimo sin ninguna razón de negocio que lo exija — contradice
`requirements.md` §7.2.8 y el principio general de preferir continuidad sobre revocación
silenciosa.

### Alternativa G — Exigir que el paciente cree su propia cuenta exactamente al cumplir 18 años

Rechazada. Obligar una acción inmediata en una fecha específica, sin período de gracia,
interrumpiría el cuidado si el paciente no está listo o disponible para hacerlo ese día. Se
prefiere una transición visible pero no bloqueante (§3.8).

### Alternativa H — Condicionar la transición a régimen adulto a que el paciente obtenga un `User`

Rechazada. Son dos decisiones independientes: "¿el paciente controla ahora su propio
expediente, fuera del alcance de sus responsables?" (resuelto en §3.8) y "¿el paciente tiene
credenciales propias para entrar al sistema?" (todavía pendiente, §5). Exigir la segunda para
resolver la primera bloquearía la transición — y por lo tanto el fin de la autorización de los
responsables — a un trámite adicional (verificación de identidad, creación de cuenta) que no
tiene nada que ver con la mayoría de edad en sí. Se prefiere desacoplarlas: la transición de
régimen no crea, exige ni modifica ningún `User`.

### Alternativa I — Desactivar las relaciones de responsables una por una, no en bloque

Rechazada. Dejaría una ventana en la que el paciente ya es legalmente adulto pero algún
responsable conserva acceso activo simplemente porque su relación no fue la primera en
procesarse. La transición se modela como una sola operación atómica que cierra todas las
relaciones `ACTIVE` a la vez (§3.8), sin estados intermedios observables.

---

## 5. Casos fuera de esta decisión (pendientes)

Lo siguiente se identificó durante el diseño de este flujo pero **no se resuelve aquí** — no
debe asumirse ni implementarse sin una decisión funcional adicional (ver `requirements.md`
§7.2.9):

- Si un paciente menor puede tener correo electrónico propio, y bajo qué condiciones.
- Bajo qué condiciones y quién autoriza que un paciente (menor o ya adulto) obtenga
  credenciales propias (`User`) más adelante, y qué verificación de identidad requiere ese
  trámite. Esta decisión es independiente de la transición de régimen (§3.8, addendum): un
  paciente puede quedar en `regime = ADULT` sin tener nunca un `User` propio.
- Mecanismo de consentimiento para vincular un responsable a un paciente que ya gestiona su
  propia cuenta (§3.7) — aplica cuando ese paciente exista con `User` propio, sea cual sea su
  `regime`. No aplica a la transición de régimen en sí (§3.8), que no crea ni requiere `User`.
- Si un paciente ya en `regime = ADULT` puede, más adelante y por su propia cuenta, revocar o
  volver a autorizar el acceso de un responsable — la transición de §3.8 solo cubre el cierre
  inicial en bloque ejecutado por el médico, no la gestión posterior por el propio paciente.
- Qué ocurre cuando una coincidencia por CURP no tiene ningún responsable activo a quien
  pedirle aprobación — hereda la indefinición ya marcada en ADR-004 §36 sobre el alcance del
  Administrador.

Cualquiera de estos puntos que implique un cambio de modelo o de invariante de seguridad
requiere actualizar esta ADR o crear una nueva, siguiendo CLAUDE.md §7.

---

## 6. Consecuencias

- `patients` ganó el punto de entrada principal para crear un `Patient` sin pasar por
  `accounts` (`patients/services/minors.py::register_minor_patient`, junto a
  `accounts.services.invitations.accept_invitation` como el otro camino existente).
- `ResponsiblePatientRelationship` obtuvo su primer camino real de creación (antes el modelo
  existía pero ningún código la creaba).
- No se necesitó ningún mecanismo de confirmación nuevo tipo token/enlace (§3.4 addendum) —
  la aprobación de una relación `PENDING` ocurre en la app, reusando la autorización de
  objeto ya existente.
- `ResponsiblePatientRelationship.is_active` (booleano) se reemplazó por `status`
  (`PENDING`/`ACTIVE`/`INACTIVE`, migración `patients.0002`) — el único cambio de esquema que
  requirió este ADR sobre lo ya implementado en Fase 1.
- No hubo impacto en el esquema de `accounts.Invitation`, `Person`, `Doctor`, `Clinic`:
  `Person.user` nullable ya cubría el caso (§3.3); se agregaron las propiedades computadas
  `Person.age`/`Person.is_minor` (sin migración).
- El addendum de §3.8 (2026-09-08) agregó `Patient.regime`/`regime_changed_at`/
  `regime_changed_by` y `ResponsiblePatientRelationship.deactivated_at`/`deactivation_reason`
  (migración `patients.0004`, con backfill de `regime` para filas ya existentes a partir de la
  edad cronológica de cada `Person` en el momento de migrar) y el servicio
  `transition_patient_to_adult` — ver checklist §8.

---

## 7. Relación con otras ADR

- **ADR-001** (Custom User Model): sin cambios — este flujo puede no crear ningún `User`.
- **ADR-002** (User/Person/Profile): confirma y formaliza el uso real de `Person.user`
  nullable (§16 de esa ADR ya contemplaba estados intermedios).
- **ADR-003** (Invitation Security): no aplica directamente — este flujo no usa tokens (§3.4
  addendum); su principio anti-enumeración sí se reutiliza para el mensaje genérico de
  coincidencia (§3.7).
- **ADR-004** (Roles y permisos de objeto): el acceso del responsable al menor sigue
  derivándose exclusivamente de `ResponsiblePatientRelationship` activa, sin excepción por
  haber sido quien lo registró.
- **ADR-005** (Límites de apps): el nuevo servicio de registro de menor vive en `patients`,
  no en `accounts`, porque su responsabilidad es el dominio de paciente/responsable, no
  identidad/autenticación general.
- **ADR-006** (Integridad de base de datos): la creación de `Patient` +
  `ResponsiblePatientRelationship` es una operación atómica
  (`@transaction.atomic` en `register_minor_patient`), igual que `accept_invitation`.

---

## 8. Checklist para cuando se implemente

Implementado 2026-09-08 (`patients/services/minors.py`, `patients/views.py`,
`patients/forms.py`, migración `patients.0002`). Los puntos marcados `[x]` están cubiertos por
tests (`patients/tests/test_minors.py`, `patients/tests/test_views_minors.py`,
`accounts/tests/test_person_age.py`); los `[ ]` siguen pendientes tal como los describe §5.

- [x] Existe un servicio en `patients` que crea `Person` + `Patient` +
      `ResponsiblePatientRelationship` de forma atómica (`register_minor_patient`).
- [x] El responsable autenticado se valida en servidor (`ResponsibleRequiredMixin` +
      `request.user.person.responsible_profile`, nunca un ID de cliente).
- [x] La edad se deriva de `birth_date` (`Person.age`/`Person.is_minor`, computadas, sin
      campo `is_minor` capturado por el usuario).
- [x] El mecanismo de confirmación no reutiliza `accounts.Invitation` con `doctor=NULL` — no
      se creó ninguna entidad de token (§3.4 addendum: aprobación en la app en su lugar).
- [x] No se crea ninguna `DoctorPatientRelationship` como efecto secundario (test dedicado).
- [x] `Person.user` permanece `NULL` a menos que exista una decisión explícita de habilitar
      cuenta propia.
- [x] Los casos de requirements.md §7.2.5 (menor existente, autorregistro, expiración/uso/
      cancelación no aplica a este mecanismo, múltiples responsables) tienen tests.
- [x] La búsqueda de "menor ya existente" usa coincidencia exacta normalizada (CURP primero,
      nombre+fecha de nacimiento después) — nunca coincidencia difusa.
- [x] Una coincidencia (por CURP o por nombre+fecha) nunca crea ni activa una
      `ResponsiblePatientRelationship` de forma inmediata sin aprobación.
- [x] Ninguna respuesta al responsable revela datos del registro existente (nombre de otro
      responsable, información del paciente) cuando hay coincidencia — mensaje genérico fijo.
- [x] `ResponsiblePatientRelationship` distingue nunca-aprobada / vigente / desactivada como
      tres estados distintos (`status`, `Status.PENDING/ACTIVE/INACTIVE`) — no colapsados en
      un solo booleano.
- [x] `status` no tiene `default` de campo; un `CheckConstraint` (no solo `choices`, que no es
      una garantía a nivel de base de datos) rechaza cualquier fila que no especifique uno de
      los tres valores válidos — probado en
      `test_status_has_no_default_and_must_be_supplied_explicitly`.
- [x] No existe ningún job/tarea programada que reescriba el estado de una relación al
      cumplir el paciente 18 años — la mayoría de edad se computa en cada verificación.
- [x] Cumplir 18 años no desactiva, elimina ni modifica ninguna `ResponsiblePatientRelationship`
      por sí solo (no hay código que lo haga).
- [x] Las pantallas que muestran esta relación señalan cuando el paciente ya es adulto
      (`docs/design/screens.md` §6.5, §6.7 — badge "Adulto" en `my_dependents.html`), sin
      bloquear el acceso por eso.
- [x] Los puntos de §5 de esta ADR siguen marcados como pendientes en el código (docstring de
      `patients/services/minors.py`), no resueltos por omisión.

**Transición a régimen adulto (§3.8, addendum 2026-09-08) — implementada 2026-09-08**
(`patients/models.py`, `patients/services/minors.py::transition_patient_to_adult`,
`patients/views.py::TransitionPatientToAdultView`, migración `patients.0004`). Los puntos
marcados `[x]` están cubiertos por tests (`patients/tests/test_models.py`,
`patients/tests/test_minors.py::AdultTransitionTests`,
`patients/tests/test_views_minors.py::TransitionToAdultViewTests`,
`patients/tests/test_permissions.py::DoctorHasActiveRelationshipTests`).

- [x] `Patient.regime` existe, sin `default` de campo, con `CheckConstraint` restringiendo a
      `MINOR`/`ADULT` — mismo patrón que `ResponsiblePatientRelationship.status` — probado en
      `test_regime_has_no_default_and_must_be_supplied_explicitly`.
- [x] `Patient.regime_changed_at`/`regime_changed_by` (FK a `doctors.Doctor`,
      `on_delete=PROTECT`) quedan `NULL` hasta la primera transición.
- [x] `ResponsiblePatientRelationship.deactivated_at`/`deactivation_reason` existen, sin
      `default` de campo, con `CheckConstraint` exigiendo ambos no nulos cuando
      `status=INACTIVE` — probado en `test_inactive_status_requires_deactivation_info`.
- [x] `register_minor_patient` pasa `regime=MINOR` explícitamente; `accept_invitation` pasa
      `regime=ADULT` explícitamente — ninguna creación de `Patient` depende de un default.
- [x] `reject_relationship_request` pasa `deactivation_reason=REQUEST_REJECTED` al desactivar
      — probado en `test_reject_records_deactivation_reason`.
- [x] Existe `transition_patient_to_adult(*, patient, performed_by_doctor)`, atómico, que
      rechaza: `regime` ya `ADULT` (`PatientAlreadyAdult`); `Person.is_minor` todavía `True`
      (`PatientStillMinor`); médico sin `DoctorPatientRelationship` activa hacia el paciente
      (`DoctorNotAuthorizedForTransition`).
- [x] La transición desactiva, en la misma operación, **todas** las
      `ResponsiblePatientRelationship` `ACTIVE` del paciente (`deactivation_reason=
      ADULT_TRANSITION`) — no una por una; una relación `PENDING` no se toca — probado en
      `test_deactivates_every_active_relationship_in_one_operation`.
- [x] La transición no crea, exige ni modifica ningún `User` — probado explícitamente en
      `test_never_creates_or_requires_a_user`.
- [x] No existe ninguna operación que revierta `regime` de `ADULT` a `MINOR` — probado en
      `test_is_irreversible`.
- [x] Cualquier `relationship_type` de `DoctorPatientRelationship` califica, no solo
      `TRATANTE` — probado en `test_any_relationship_type_qualifies_not_only_tratante`.
- [x] UI: acción "Marcar como adulto" en detalle de paciente (`docs/design/screens.md` §6.5),
      con confirmación vía `Modal` (`<dialog>` nativo), visible solo cuando `regime=MINOR`,
      `Person.is_minor=False` y el médico tiene relación activa — la autorización real se
      revalida en el servicio, no solo en la condición que oculta el botón.

---

## 9. Estado

**Accepted — implementado (2026-09-08)**, incluido el addendum de §3.8 (diseñado 2026-09-08,
implementado 2026-09-08): la transición a régimen adulto ya está construida, no solo
documentada (ver checklist §8).

El flujo de registro de paciente menor por responsable y el de transición a régimen adulto
están ambos implementados para Fase 1 (`patients/services/minors.py`, `patients/views.py`,
`patients/forms.py`, `patients/models.py`, migración `patients.0004`,
`docs/design/screens.md` §6.5/§6.7/§6.8). Los puntos de §5 siguen explícitamente no resueltos,
tal como se documentaron ahí — no se asumieron ni se implementaron por omisión.

Cualquier modificación significativa deberá documentarse mediante una actualización de esta
ADR o una nueva ADR relacionada.

---

## 10. Referencias

- `requirements.md` §3.1, §7.2
- `docs/architecture.md`
- `docs/design/screens.md`
- `docs/adr/ADR-001-custom-user-model.md`
- `docs/adr/ADR-002-user-person-profile.md`
- `docs/adr/ADR-003-invitation-security.md`
- `docs/adr/ADR-004-role-and-object-permissions.md`
- `docs/adr/ADR-005-django-app-boundaries.md`
- `docs/adr/ADR-006-database-integrity-and-transactions.md`

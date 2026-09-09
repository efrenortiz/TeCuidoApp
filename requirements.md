# TeCuidoApp — Requirements

## 1. Descripción del proyecto

**TeCuidoApp** es una aplicación Web para la gestión integral de un consultorio médico especializado en **gineco-obstetricia**.

La aplicación será desarrollada en:

- **Python**
- **Django**
- **PostgreSQL** como base de datos
- **Redis** y **Celery** para tareas asíncronas y programadas, cuando sea necesario
- Almacenamiento privado para documentos y archivos médicos
- Generación de documentos PDF

El sistema tendrá tres grandes áreas de operación:

1. Gestión administrativa del consultorio.
2. Gestión clínica y agenda por parte del médico.
3. Portal para pacientes y responsables.

La aplicación debe diseñarse con una arquitectura modular, segura, mantenible y preparada para incorporar funcionalidades futuras.

---

## 2. Objetivo general

Proporcionar una plataforma Web que permita administrar consultorios, médicos, pacientes, responsables, agenda y disponibilidad; facilitar la atención médica; mantener un expediente clínico histórico; emitir recetas y solicitudes de estudios; administrar documentos clínicos; y permitir al paciente o responsable consultar información y documentos asociados a sus citas.

El sistema debe priorizar:

- Seguridad.
- Privacidad.
- Trazabilidad.
- Integridad de la información clínica.
- Control de permisos.
- Usabilidad para médicos, administradores y pacientes/responsables.
- Historial de cambios y acciones relevantes.

---

# 3. Alcance funcional

## 3.1 Roles

El sistema debe contemplar inicialmente los siguientes roles:

### Administrador

Tiene acceso global a la aplicación y puede administrar:

- Usuarios.
- Médicos.
- Consultorios.
- Relaciones médico-consultorio.
- Configuraciones generales.
- Información administrativa.
- Auditoría.

El administrador debe tener acceso global a la información de la aplicación de acuerdo con los permisos establecidos.

Todo acceso del administrador a información clínica sensible debe quedar registrado en auditoría.

### Médico

Puede:

- Iniciar sesión.
- Administrar su disponibilidad.
- Consultar y administrar su agenda.
- Enviar invitaciones de registro a prospectos.
- Registrar y actualizar pacientes y responsables.
- Crear citas directamente, en nombre propio o del paciente/responsable (§13, §14 — sin
  solicitud previa ni confirmación posterior).
- Iniciar la consulta cuando el paciente esté físicamente presente (§16); marcar `NO_SHOW`
  cuando corresponda (§15).
- Consultar el contexto clínico del paciente.
- Crear y actualizar historia clínica.
- Registrar consultas médicas.
- Registrar diagnósticos e impresión diagnóstica.
- Registrar tratamientos y evolución.
- Emitir recetas.
- Generar solicitudes de laboratorio, gabinete y otros estudios.
- Generar documentos PDF.
- Consultar documentos históricos relacionados con el paciente.
- Concluir una consulta y marcar la cita como atendida.

El médico es responsable de las decisiones clínicas. TeCuidoApp no debe realizar diagnósticos automáticos ni indicar tratamientos de forma autónoma.

### Paciente

Puede:

- Registrarse mediante una invitación enviada por su médico.
- Verificar su correo electrónico.
- Iniciar sesión.
- Consultar y actualizar la información permitida de su perfil.
- Consultar sus citas.
- Crear citas directamente (§13, §14 — no existe flujo de solicitud ni confirmación
  posterior; la cita queda reservada al completar la operación).
- Cancelar y reprogramar las citas que gestiona.
- Consultar el historial de citas.
- Consultar y descargar recetas.
- Consultar y descargar indicaciones de tratamiento.
- Consultar y descargar solicitudes de estudios.
- Adjuntar archivos a solicitudes de atención/cita.
- Consultar los documentos que tenga autorización para visualizar.

### Responsable

Puede realizar las operaciones permitidas para un paciente y además:

- Gestionar uno o más pacientes a su cargo.
- Registrar pacientes menores de edad o personas que requieran responsable (flujo detallado
  en §7.2).
- Crear citas directamente para un paciente a su cargo, mientras la relación esté `ACTIVE`
  (§13, §14).
- Consultar citas por paciente.
- Consultar y descargar documentos de los pacientes que tenga autorizados.
- Actualizar la información permitida de los pacientes a su cargo.

La relación entre responsable y paciente debe quedar registrada de manera explícita y debe poder soportar al menos un paciente por responsable.

---

# 4. Modelo de identidad y usuarios

Debe existir un modelo de usuario central para autenticación y autorización.

No se deben crear sistemas independientes de autenticación para cada rol.

La arquitectura deberá permitir asociar a un mismo usuario diferentes perfiles funcionales de acuerdo con las necesidades futuras, manteniendo una separación clara entre:

- Usuario/autenticación.
- Persona.
- Paciente.
- Responsable.
- Médico.

La cuenta de correo electrónico utilizada para el registro debe ser única.

Debe implementarse:

- Verificación de correo electrónico.
- Recuperación de contraseña.
- Cambio de contraseña.
- Activación/desactivación de cuentas.
- Control de permisos por rol.
- Registro de fecha y hora de último acceso cuando resulte conveniente.

Un usuario cuyo correo electrónico no ha sido verificado no debe poder iniciar sesión. La
verificación de correo no es solo informativa: es una condición para autenticarse.

---

# 5. Pacientes y responsables

## 5.1 Paciente

Un paciente puede ser:

- Mayor de edad y no requerir responsable.
- Menor de edad.
- Persona que requiere responsable.

La información general del paciente debe contemplar como mínimo:

### Identificación

- Nombre(s).
- Apellido paterno.
- Apellido materno.
- Fecha de nacimiento.
- Sexo.
- CURP, si se decide incluir.
- Nacionalidad.

### Contacto

- Correo electrónico.
- Teléfono celular personal.
- Teléfono alternativo, si aplica.
- Contacto de emergencia.

### Domicilio

- Calle.
- Número.
- Colonia.
- Código postal.
- Municipio/alcaldía.
- Estado.
- País.

### Información médica relevante

- Alergias.
- Tipo sanguíneo, si se conoce.
- Enfermedades crónicas.
- Medicamentos actuales.
- Antecedentes quirúrgicos.
- Hospitalizaciones relevantes.

### Información gineco-obstétrica

La arquitectura debe permitir registrar y ampliar posteriormente:

- Menarca.
- FUM.
- Características del ciclo menstrual.
- Gestas.
- Partos.
- Cesáreas.
- Abortos.
- Embarazos ectópicos.
- Complicaciones obstétricas previas.
- Método anticonceptivo.
- Información relacionada con embarazo actual, cuando aplique.

## 5.2 Responsable

La información del responsable debe contemplar como mínimo:

- Nombre(s).
- Apellido paterno.
- Apellido materno.
- Fecha de nacimiento.
- Correo electrónico.
- Teléfono celular.
- Teléfono alternativo, si aplica.
- Domicilio.
- Relación con el paciente.
- Contacto alternativo.
- Datos de identificación, si posteriormente fueran requeridos.

Relaciones posibles:

- Madre.
- Padre.
- Tutor legal.
- Familiar.
- Cuidador.
- Otro.

La relación responsable-paciente debe ser una entidad explícita y debe permitir controlar qué acciones puede realizar el responsable.

---

# 6. Relación paciente-médico

Un paciente no debe quedar limitado arquitectónicamente a un único médico.

La relación entre paciente y médico debe permitir múltiples médicos, por ejemplo:

- Médico tratante.
- Médico sustituto.
- Otro médico del consultorio.

Cuando un prospecto se registra utilizando la liga de invitación enviada por un médico, el sistema debe asociar automáticamente al paciente con dicho médico.

---

# 7. Prospectos e invitaciones

Existen dos flujos de invitación distintos en Fase 1. No deben confundirse ni implementarse
como si fueran variantes del mismo formulario: representan dos casos de negocio diferentes
("quien se registra" vs. "quien está siendo registrado por otra persona").

## 7.1 Registro de prospecto adulto (invitación del médico)

Los prospectos no son considerados pacientes hasta que completen correctamente su registro.

El médico debe poder enviar a un prospecto una liga de registro al correo electrónico proporcionado.

La invitación debe:

- Contener un token seguro.
- Tener expiración.
- Ser de un solo uso o quedar invalidada después de completarse.
- Asociar al futuro paciente con el médico que generó la invitación.
- Registrar fecha y hora de creación.
- Registrar fecha y hora de utilización o expiración.
- Permitir identificar el estado de la invitación.

El correo electrónico debe verificarse mediante liga o código antes de concluir el proceso de registro.

Este es el flujo donde el propio prospecto adulto crea su identidad y acepta la invitación
directamente. No aplica a menores de edad — ver §7.2.

---

## 7.2 Registro de paciente menor por responsable

Un responsable con perfil `Responsible` ya existente puede incorporar a un paciente menor de
edad sin que el menor cree una cuenta de adulto ni acepte una invitación como si fuera un
prospecto. Este flujo es iniciado por el responsable, no por un médico ni por el menor.

### 7.2.1 Datos capturados

Como mínimo, el responsable proporciona:

- Nombre(s) del menor.
- Apellido paterno.
- Apellido materno.
- Fecha de nacimiento.
- Sexo.
- Correo electrónico del menor — **opcional**, sujeto a la política de la fase (ver §7.2.5);
  no debe exigirse si no aplica.
- Datos de contacto necesarios para el servicio, evitando pedir al menor datos que en
  realidad pertenecen al responsable (por ejemplo, no duplicar el teléfono del responsable
  como si fuera del menor).

La minoría de edad se determina siempre a partir de la fecha de nacimiento capturada, nunca
mediante un campo separado tipo "es menor" introducido por el usuario.

### 7.2.2 Qué crea el sistema

1. Un registro `Patient` para el menor (identidad clínica), sin exigir que tenga una cuenta
   de usuario propia en este paso.
2. Una relación `ResponsiblePatientRelationship` explícita: `responsible` = el responsable
   autenticado, `patient` = el menor recién creado, `relation_type` seleccionado por el
   responsable (Madre, Padre, Tutor legal, Familiar, Cuidador, Otro — mismo catálogo que el
   resto del sistema).
3. Un mecanismo de confirmación de un solo uso, con expiración, cuyo destinatario es el
   **responsable** (no el menor) — ver §7.2.4.

Que el responsable haya sido quien registró al menor no sustituye ni reemplaza la necesidad
de esta relación explícita: el acceso del responsable al expediente del menor se deriva
siempre de `ResponsiblePatientRelationship`, nunca de "ambos registros los creó el mismo
usuario".

### 7.2.3 Paciente clínico vs. usuario paciente

Deben distinguirse dos conceptos:

- **Paciente clínico** (`Patient`/`Person`): puede existir en TeCuido sin tener credenciales
  propias de acceso.
- **Usuario paciente** (`User` asociado): solo debe crearse/habilitarse cuando la persona
  vaya a usar el sistema directamente.

Para un menor registrado por su responsable, el registro inicial **no** debe obligar a crear
credenciales propias (`User`). El paciente puede quedar registrado clínicamente sin cuenta
propia hasta que exista una razón y una regla explícita para habilitarle acceso directo.

### 7.2.4 Confirmación por el responsable

Se genera un mecanismo de confirmación de un solo uso (token seguro, expiración, estado),
siguiendo los mismos principios de seguridad que ya aplican a las invitaciones (ver ADR-003 y
ADR-007): token impredecible, solo se persiste su hash, sin datos sensibles legibles en el
token, sin registrar el token completo en logs.

El destinatario/beneficiario de esta confirmación es el **responsable**, no el menor —
evitando diseñar un flujo donde el menor deba actuar como si fuera un adulto aceptando una
invitación.

Al completarse correctamente la confirmación, el sistema puede fijar `email_verified=True` e
`is_active=True` **únicamente si** se determinó que el menor tendrá una cuenta de usuario
propia (§7.2.3) — si no la tiene, estos campos no aplican todavía.

### 7.2.5 Casos que debe contemplar el flujo

- **Menor nuevo**: no existe un registro previo → se crea el paciente, la relación y la
  confirmación.
- **Menor ya existente**: el sistema no debe duplicar el registro; debe tratarse como una
  vinculación, no como un alta nueva. Regla definida en §7.2.7.
- **El responsable intenta registrarse a sí mismo como el menor**: debe rechazarse; el flujo
  es exclusivamente para incorporar a un tercero.
- **El paciente cumple 18 años**: el vínculo responsable-paciente no desaparece
  automáticamente. Regla definida en §7.2.8.
- **Confirmación expirada, usada o cancelada**: no permite completar el flujo; sigue las
  mismas reglas de invalidez que ya existen para invitaciones (§7.1).
- **Múltiples responsables para el mismo menor**: debe permitirse mediante múltiples
  registros de `ResponsiblePatientRelationship`, sujeto a las reglas de autorización
  correspondientes (ver `docs/adr/ADR-004-role-and-object-permissions.md`).

### 7.2.6 Qué NO hace este flujo

- No crea ni modifica ninguna `DoctorPatientRelationship`. Registrar al menor no otorga
  acceso automático a ningún médico — esa relación se establece por separado, cuando
  corresponda.
- No exige al menor crear ni aceptar nada como si fuera un prospecto adulto (§7.1 y §7.2 son
  flujos distintos, no variantes de un mismo formulario).

### 7.2.7 Detección y vinculación de un paciente ya existente

Antes de crear un `Patient` nuevo, el sistema debe buscar coincidencias entre los datos
capturados y los pacientes ya existentes. La búsqueda usa dos niveles de confianza, nunca
coincidencia difusa ("similar"):

1. **CURP (alta confianza).** Si el responsable capturó CURP, se busca un `Patient` existente
   con el mismo CURP (normalizado: mayúsculas, sin espacios). El CURP es un identificador
   único de persona en México — una coincidencia aquí significa, por definición, que es la
   misma persona.
2. **Nombre completo + fecha de nacimiento (confianza baja, solo si no hay CURP).** Si no se
   capturó CURP, se busca por coincidencia **exacta** (tras normalizar mayúsculas/espacios) de
   nombre(s) + apellido paterno + apellido materno + fecha de nacimiento. Esto no confirma
   identidad de forma confiable (dos personas distintas podrían compartir estos datos, y un
   error de captura evita que coincidan aunque sea la misma persona) — es una señal, no una
   confirmación.

Ninguna coincidencia debe manejarse igual. Reglas según lo que se encuentre:

- **Coincidencia por CURP, y el paciente encontrado no tiene `User` propio** (es únicamente
  paciente clínico, §7.2.3): no se crea un `Patient` nuevo. Se crea una
  `ResponsiblePatientRelationship` para el responsable actual, pero **no queda vigente de
  inmediato** — requiere que un responsable ya autorizado sobre ese paciente la apruebe. Esto
  es obligatorio incluso con coincidencia de CURP: conocer el CURP de alguien no debe bastar
  por sí solo para obtener acceso a su expediente.
- **Coincidencia por nombre + fecha de nacimiento (sin CURP), confianza baja**: el sistema
  **no** crea un `Patient` nuevo automáticamente ni vincula automáticamente. Se le informa al
  responsable, en lenguaje genérico y sin revelar ningún dato del registro existente (ver
  regla de privacidad más abajo), que ya existe un posible registro con datos similares y que
  debe continuar el trámite con el consultorio/médico para resolverlo manualmente. No es un
  flujo de autoservicio.
- **Coincidencia (por cualquiera de los dos criterios) contra un paciente que ya tiene `User`
  propio** (ya es "usuario paciente", §7.2.3, es decir, gestiona su propia cuenta): vincular a
  un responsable requiere el consentimiento de esa persona, no solo la afirmación de un
  tercero de ser su responsable. Este consentimiento **no está diseñado todavía** — queda
  pendiente (ver más abajo). Mientras no exista, el sistema no debe crear la relación ni
  aunque haya coincidencia de CURP.
- **Sin coincidencia**: se procede normalmente — se crea el `Patient`.

**Regla de privacidad (obligatoria en cualquiera de los casos anteriores):** el sistema nunca
debe revelar al responsable que está registrando datos de otro registro existente (nombre del
otro responsable, información del paciente, etc.). El mensaje debe ser genérico
("ya existe un registro relacionado con estos datos; contacta a tu médico o al consultorio
para continuar"), igual que ya se exige para invitaciones (`docs/adr/ADR-003-invitation-security.md`
§18, "Protección contra enumeración").

### 7.2.8 Transición a régimen adulto

Cumplir 18 años **no** desactiva, elimina ni modifica automáticamente ninguna
`ResponsiblePatientRelationship` existente, ni cambia por sí solo la condición de un paciente.
La mayoría de edad (`Person.is_minor`, derivada de `birth_date`, evaluada en cada verificación
— nunca mediante una tarea programada) y el **régimen de autorización del paciente** son dos
conceptos distintos:

```text
Person.birth_date → edad actual → ¿menor o adulto cronológicamente?
```

es independiente de:

```text
Patient.regime → MINOR | ADULT → ¿tiene el paciente autorización propia sobre su expediente?
```

Un paciente puede ser cronológicamente adulto y seguir en `regime = MINOR` indefinidamente —
eso es aceptado y deliberado, no un error. El régimen solo cambia mediante una **transición
explícita**, nunca automáticamente.

**Quién la ejecuta y cuándo:**

- La ejecuta **un médico con `DoctorPatientRelationship` activa** hacia ese paciente
  (cualquier `relationship_type` — tratante, sustituto u otro; no se restringe a uno solo).
  Ningún médico sin relación activa con el paciente puede hacerlo.
- El médico la ejecuta cuando el paciente manifiesta su voluntad de ser tratado como adulto
  (en consulta, por teléfono o de viva voz). El sistema no exige ni valida un artefacto de
  consentimiento separado — la acción del médico, bajo su responsabilidad profesional, **es**
  la constancia de esa manifestación. Mientras el médico no la ejecute en el sistema, el
  paciente se sigue tratando como menor, sin importar su edad cronológica.
- **Candado legal obligatorio:** el sistema debe impedir la transición si `Person.is_minor` es
  `True` en el momento de intentarla — no se puede reconocer como adulto, ni siquiera
  administrativamente, a alguien que todavía no cumple 18 años. Este candado se aplica tanto en
  la interfaz (la acción no debe estar disponible) como en el servidor (debe rechazarse aunque
  se intente forzar la operación).

**Qué hace la transición, en una sola operación atómica:**

1. `Patient.regime` pasa de `MINOR` a `ADULT`, y se registra cuándo y qué médico la ejecutó.
2. **Todas** las `ResponsiblePatientRelationship` `ACTIVE` de ese paciente pasan a `INACTIVE`
   en el mismo paso — no una por una, no quedan algunas vigentes y otras no. Ningún
   responsable conserva acceso operativo después de la transición.
3. **No crea, exige ni modifica ningún `User`.** Obtener una cuenta propia es una decisión
   distinta e independiente (ver §7.2.9) — un paciente puede quedar en `regime = ADULT` sin
   tener credenciales propias todavía; mientras eso no se resuelva, nadie tiene acceso
   operativo a su expediente hasta que él mismo autorice a alguien como adulto.

**Es irreversible:** una vez `ADULT`, el régimen no vuelve a `MINOR`. No existe una acción para
deshacer la transición dentro de este flujo.

**No se pierde el historial.** Las relaciones desactivadas no se eliminan — permanecen como
registro de que ese responsable tuvo autorización vigente desde su creación hasta la fecha en
que la transición las desactivó.

El `relationship_type` original de cada relación (Madre, Padre, Tutor legal, etc.) no cambia al
desactivarse — sigue describiendo qué relación tuvo con el paciente, no un estado vigente.

No afecta ninguna `DoctorPatientRelationship` (ya independiente de esta relación, §7.2.6).

### 7.2.9 Decisiones explícitamente pendientes

Lo siguiente **no** debe asumirse ni implementarse sin una decisión funcional adicional:

- Bajo qué condiciones (si alguna) un paciente menor puede tener correo electrónico propio.
- **Fuera de alcance de Fase 1 — diferido explícitamente a una fase posterior (decisión de
  cierre de Fase 1, 2026-09-09):** bajo qué condiciones y quién autoriza que un paciente (en
  `regime = ADULT` o no) obtenga credenciales propias (`User`), y qué verificación de
  identidad requiere ese trámite. No es un vacío accidental ni algo que deba inferirse en
  código — es una decisión de alcance tomada deliberadamente para poder cerrar Fase 1 sin
  resolverla (ver `docs/phases/phase-1-foundations.md` §27/§31 y
  `docs/adr/ADR-007-responsible-initiated-minor-registration.md` §5). Es independiente de la
  transición de régimen descrita en §7.2.8 — un paciente puede quedar en `regime = ADULT` sin
  cuenta propia indefinidamente, y esta decisión no bloquea ni condiciona esa transición.
- Mecanismo de consentimiento para vincular un responsable a un paciente que ya gestiona su
  propia cuenta (§7.2.7, último punto) — solo puede resolverse una vez que exista la política
  de cuenta propia anterior, así que queda diferido junto con ella a esa misma fase posterior;
  no aplica a la transición de régimen en sí, que no depende de que exista ningún `User`.
- Si un paciente ya en `regime = ADULT` puede, más adelante y por su propia cuenta, revocar o
  volver a autorizar el acceso de un responsable — depende igualmente de que el paciente tenga
  cuenta propia, así que queda diferido junto con esa decisión. La transición de §7.2.8 solo
  cubre el cierre inicial en bloque ejecutado por el médico, no la gestión posterior por el
  propio paciente.
- Qué ocurre cuando una coincidencia por CURP no tiene ningún responsable activo a quien
  pedirle autorización (por ejemplo, si esa relación fue desactivada) — probablemente requiera
  intervención del Administrador, pero su alcance exacto sobre invitaciones/vinculaciones ya
  está marcado como no definido en `docs/adr/ADR-004-role-and-object-permissions.md` §36, y
  esta decisión hereda esa misma indefinición.

Ver `docs/adr/ADR-007-responsible-initiated-minor-registration.md` para las implicaciones
arquitectónicas de este flujo (en particular, por qué no reutiliza el modelo `Invitation`
existente sin modificarlo, y qué implica la "aprobación pendiente" de §7.2.7 sobre
`ResponsiblePatientRelationship`).

---

# 8. Consultorios

El administrador puede:

- Consultar consultorios.
- Dar de alta consultorios.
- Modificar consultorios.
- Desactivar consultorios.

Cada consultorio debe poder almacenar información administrativa relevante, por ejemplo:

- Nombre.
- Descripción.
- Dirección, si aplica.
- Teléfono.
- Estatus activo/inactivo.

La aplicación debe permitir asignar médicos a consultorios.

La relación médico-consultorio debe poder registrar qué médicos trabajan en qué consultorios.

---

# 9. Configuración del consultorio

Debe existir una configuración general del consultorio, contemplando al menos:

- Nombre comercial.
- Nombre del establecimiento o consultorio.
- Dirección.
- Teléfono.
- Correo electrónico.
- Logo.
- Horarios de atención generales.
- Zona horaria.
- Datos que deban aparecer en documentos PDF.

Los documentos generados deben utilizar esta configuración y no valores codificados directamente en el código.

---

# 10. Agenda y disponibilidad

**Política decidida para Fase 2 (2026-09-09) — ver `docs/phases/phase-2-agenda.md` para el
contrato funcional completo, que es la fuente detallada; este capítulo resume solo lo que no
debe contradecirse.**

El médico (y el administrador, en apoyo operativo) puede:

- Crear disponibilidad.
- Modificar disponibilidad.
- Consultar disponibilidad.

La disponibilidad se define **por fecha concreta**, nunca como regla semanal recurrente:

```text
15/09/2026 09:00–13:00
18/09/2026 10:00–14:00
```

**No existen en Fase 2** reglas de disponibilidad recurrentes (`AvailabilityRule`) ni
excepciones (`AvailabilityException`) sobre una regla recurrente — esa idea, presente en
versiones anteriores de este documento, quedó descartada para Fase 2 y no está planeada para
ninguna fase posterior conocida; si en el futuro se decide agregar recurrencia, requiere una
decisión funcional explícita nueva, no debe inferirse de este texto.

La disponibilidad pertenece a la combinación **médico + consultorio + fecha**; no se permiten
disponibilidades solapadas dentro de esa misma combinación. Además, **un médico no puede tener
dos disponibilidades activas que se solapen temporalmente aunque correspondan a consultorios
distintos** (decisión de cierre, 2026-09-09) — el médico no puede estar disponible
simultáneamente en dos lugares.

La agenda utiliza la **zona horaria del `Clinic`** (decisión de cierre, 2026-09-09): la
fecha/hora de negocio de una disponibilidad o una cita pertenece al consultorio, no al usuario
que consulta ni al servidor.

La duración de las citas se configura por la combinación **médico + consultorio**, con
**60 minutos** como valor por defecto. Una cita ocupa simultáneamente al médico y al
consultorio durante toda su duración — no puede haber otra cita incompatible para ninguno de
los dos en ese lapso, y el sistema debe impedir dobles reservas del mismo horario mediante
control de concurrencia a nivel de base de datos, no solo validación de aplicación.

Modificar o eliminar una disponibilidad no puede invalidar citas ya existentes; el sistema no
las cancela automáticamente — el médico debe conciliar con los pacientes y usar reprogramación
antes de un cambio incompatible.

---

# 11. Bloqueo temporal durante la reserva (hold)

Cuando un usuario autorizado (paciente, responsable con relación `ACTIVE`, médico o
administrador) selecciona un horario disponible para iniciar una reserva, el sistema crea un
**hold** que protege ese horario durante **15 minutos como máximo**. El hold es un mecanismo
técnico de protección del slot, **no un estado de aprobación de la cita** — no existe ningún
flujo de confirmación posterior a la reserva (ver §14).

Reglas del hold:

- No se crea un hold solo por visualizar la agenda.
- Un usuario solo puede mantener **un hold activo a la vez**.
- El hold no puede renovarse ni extenderse.
- No se puede cambiar de horario mientras el hold esté activo — primero debe liberarse.
- El usuario puede liberarlo voluntariamente antes de que expire.
- Si la reserva no concluye dentro del periodo de bloqueo, el hold expira y el horario vuelve
  a estar disponible.
- Cuando la cita se crea correctamente, el hold se marca como consumido.
- Los holds expirados, liberados y consumidos se conservan como historial técnico.

La implementación debe utilizar mecanismos apropiados de concurrencia y transacciones de base
de datos para evitar dobles reservaciones — la reserva definitiva siempre revalida el slot
dentro de la transacción que la confirma; el hold no sustituye esa protección.

---

# 12. Solicitudes de atención — CareRequest

**Nota de alcance (2026-09-09):** `CareRequest` es funcionalidad de **Fase 5** (§41). No se
implementa en Fase 2, y **no es un requisito previo para crear una cita** en ninguna fase —
Fase 2 crea `Appointment` de forma directa, sin solicitud ni confirmación posterior (§13, §14,
`docs/phases/phase-2-agenda.md` §6). Esta sección describe el módulo tal como se construirá
cuando le toque su fase; no debe leerse como una dependencia de la agenda de Fase 2.

TeCuidoApp debe incluir un módulo funcional denominado **CareRequest**.

CareRequest representa una solicitud de atención iniciada por el paciente o responsable y es independiente de la cita definitiva.

La solicitud debe incluir:

- Paciente relacionado.
- Responsable que realiza la solicitud, cuando aplique.
- Fecha y hora de creación.
- Motivo de la solicitud.
- Padecimiento o síntoma reportado.
- Descripción libre del problema.
- Archivos adjuntos.
- Estado de la solicitud.
- Fecha y hora de actualización.

Ejemplos de archivos:

- PDF de laboratorio.
- Imagen.
- Fotografía.
- Documento clínico.

Cuando se implemente (Fase 5), la solicitud podrá convertirse posteriormente en una cita —
como un **origen alternativo y opcional** de creación de `Appointment`, coexistiendo con la
reserva directa de Fase 2, nunca reemplazándola ni condicionándola.

## 12.1 Estados de CareRequest

Como mínimo:

- Nueva.
- En revisión.
- Atendida.
- Convertida en cita.
- Cancelada.
- Cerrada.

La aplicación no debe efectuar diagnóstico automático sobre el contenido de CareRequest.

El médico debe decidir clínicamente la atención apropiada.

---

# 13. Citas

**Política decidida para Fase 2 (2026-09-09) — ver `docs/phases/phase-2-agenda.md` para el
contrato funcional completo.**

Una cita (`Appointment`) debe ser una entidad independiente de la consulta médica.

Debe asociarse como mínimo con:

- Paciente.
- Médico.
- Consultorio.
- Fecha/hora inicial.
- Fecha/hora final.
- Duración.
- Usuario que la creó.
- Responsable que gestionó la cita, cuando aplique.
- Estado.
- Fechas de creación y modificación.

`CareRequest` **no** es un campo obligatorio ni un requisito previo de `Appointment` en Fase
2 — cuando `CareRequest` se implemente (Fase 5), la relación entre ambos será opcional (§12).

Debe distinguirse claramente:

- Paciente que será atendido.
- Responsable que realizó o gestionó la cita.

## 13.1 Estados de una cita

Los únicos estados de `Appointment` son:

- `SCHEDULED` — estado inicial de toda cita creada correctamente; reservada y vigente, la
  consulta todavía no inició. La reprogramación no cambia este estado.
- `IN_CONSULTATION` — el paciente está físicamente presente y el médico asignado inició la
  atención. Solo el médico asignado ejecuta `SCHEDULED → IN_CONSULTATION`.
- `COMPLETED` — la atención terminó. Solo el médico asignado ejecuta
  `IN_CONSULTATION → COMPLETED`.
- `CANCELLED` — cita cancelada antes de iniciar la consulta. Terminal.
- `NO_SHOW` — inasistencia real determinada por el médico asignado, desde `SCHEDULED`.
  Terminal.

**No existen** como estados de `Appointment`: pendiente de confirmación, confirmada, en
espera, reprogramada, ni liberada — ninguno de estos representa un estado real del modelo. La
reprogramación y la liberación de un hold son *eventos* con su propio historial, no estados de
la cita (§14, §11).

El paso del tiempo nunca cambia por sí solo el estado de una cita; todo cambio de estado
requiere la acción humana autorizada correspondiente (ningún cron, signal ni tarea programada
transiciona una cita automáticamente).

---

# 14. Creación directa, cancelación y reprogramación

**Política decidida para Fase 2 (2026-09-09):** las citas se crean **directamente** — no
existe flujo de solicitud previa ni confirmación posterior. Al completarse correctamente una
reserva, la cita queda en `SCHEDULED`; no hay un paso adicional que "confirmarla". Pueden
crear una cita directamente: paciente, responsable con relación `ACTIVE`, médico (con acceso
legítimo al paciente — ver regla de primera cita más abajo) y administrador autorizado (con
`DoctorClinic` válida para el médico y consultorio involucrados, además del ámbito sobre la
clínica).

**Regla de primera cita por médico (decisión de cierre, 2026-09-09):** un médico puede crear
la primera cita de un paciente **sin que exista todavía una `DoctorPatientRelationship`
activa** entre ambos, siempre que tenga acceso legítimo — es decir, que opere dentro de una
combinación médico + consultorio para la que tiene una relación `DoctorClinic` válida; no se
exige ninguna condición adicional sobre el paciente. Crear la cita **no crea, activa ni
modifica** ninguna `DoctorPatientRelationship` ni ningún otro mecanismo de autorización de
Fase 1: `crear Appointment` y `crear DoctorPatientRelationship` son operaciones
conceptualmente separadas. Si la relación médico-paciente llega a establecerse, ocurre
mediante su propio flujo de autorización/alta, ajeno a Agenda.

El sistema debe permitir, además de la creación directa:

- Cancelar una cita.
- Reprogramar una cita.
- Registrar quién realizó cada acción y cuándo.
- Mantener trazabilidad de cambios.

Pueden cancelar o reprogramar: el paciente titular, el responsable con relación `ACTIVE`, el
médico correspondiente y el administrador autorizado. Una cita ya iniciada (`IN_CONSULTATION`
o posterior) no puede cancelarse ni reprogramarse.

La cancelación requiere registrar un motivo (`cancellation_reason`) — como mínimo: solicitud
del paciente, solicitud del responsable, solicitud del médico, solicitud del consultorio, u
otro. El horario se libera inmediatamente después de cancelar.

La reprogramación conserva el mismo `Appointment` lógico (no crea una cita nueva), mantiene el
mismo médico y la misma duración, puede cambiar fecha/hora/consultorio, requiere motivo
obligatorio, y el nuevo horario debe cumplir las mismas reglas que una reserva nueva. Cuando
una cita se reprograma, debe conservarse el historial completo del cambio (horario anterior,
horario nuevo, quién, cuándo, motivo) — puede reprogramarse varias veces mientras siga
`SCHEDULED`.

---

# 15. Pacientes que no se presentan

Cuando un paciente no se presenta, solo el **médico asignado** puede marcar la cita como
`NO_SHOW`, y únicamente mientras esté en `SCHEDULED`. Puede marcarse desde el minuto 1
posterior a la hora programada — Fase 2 no exige una espera mínima de 15 minutos. Si el
paciente llega antes de que se marque `NO_SHOW`, el médico puede iniciar la consulta
normalmente aunque ya haya pasado la hora programada.

Debe registrarse:

- Fecha y hora (`no_show_at`).
- Usuario que marcó la inasistencia (`no_show_by`).

`NO_SHOW` es terminal — no puede volver a ningún otro estado; si el paciente requiere
atención, debe crearse una nueva cita.

La aplicación no debe convertir automáticamente el solo paso del tiempo en una inasistencia —
siempre requiere la acción explícita del médico asignado.

Penalizaciones o bloqueos automáticos por acumulación de `NO_SHOW` están **fuera de alcance de
Fase 2** y de cualquier fase actualmente planeada; no deben implementarse ni inferirse.

---

# 16. Inicio de consulta

**Política decidida para Fase 2 (2026-09-09) — reemplaza el check-in/sala de espera de
versiones anteriores de este documento.** No existe check-in realizado por paciente,
responsable ni administrador, ni un estado `WAITING`/"en espera" en `Appointment`. La
operación visible es **"Iniciar consulta"**:

```text
Paciente llega físicamente al consultorio
        ↓
Médico asignado verifica su presencia
        ↓
Médico selecciona "Iniciar consulta"
        ↓
SCHEDULED → IN_CONSULTATION
```

Solo el médico asignado puede iniciar la consulta. El paso del tiempo por sí solo nunca inicia
una consulta.

La agenda del médico debe permitir visualizar las citas del día y distinguir únicamente los
estados reales de `Appointment` (§13.1): `SCHEDULED`, `IN_CONSULTATION`, `COMPLETED`,
`CANCELLED`, `NO_SHOW` — sin inventar estados intermedios de presentación en la interfaz.

---

# 17. Consulta médica

La **Consulta / MedicalEncounter** debe ser independiente de la cita.

Una cita puede generar una consulta médica. El estado `IN_CONSULTATION` de la cita (§13.1,
Fase 2) es la frontera hacia la atención clínica — la existencia de una cita o su estado
nunca debe interpretarse por sí solo como diagnóstico, tratamiento o decisión médica alguna;
eso pertenece exclusivamente al dominio clínico de Fase 3.

La consulta debe conservar un historial permanente y no debe sobrescribirse como si fuera un simple registro actual.

Debe contener como mínimo:

- Paciente.
- Médico.
- Cita relacionada.
- Fecha/hora.
- Motivo de consulta.
- Exploración física.
- Paraclínicos.
- Impresión diagnóstica.
- Manejo/tratamiento.
- Pronóstico.
- Evolución.
- Observaciones clínicas.

El médico debe poder registrar información adicional relevante.

TeCuidoApp no debe emitir diagnósticos ni recomendaciones clínicas autónomas.

---

# 18. Historia clínica

En la primera versión, la historia clínica puede utilizar campos de texto abierto guiados por secciones.

Debe contemplar como mínimo:

- Antecedentes heredofamiliares.
- Antecedentes personales patológicos.
- Antecedentes personales no patológicos.
- Tipo de vivienda.
- Antecedentes gineco-obstétricos.
- Otros antecedentes relevantes.

La historia clínica debe permanecer disponible como parte del expediente.

Los registros históricos de las consultas no deben sobrescribirse.

---

# 19. Resumen clínico para el médico

Al abrir el expediente de un paciente, el sistema debe mostrar un resumen de contexto clínico.

Debe contemplar, cuando exista información:

### Datos generales

- Edad.
- Fecha de nacimiento.
- Peso y talla recientes.
- IMC, si existe información suficiente.
- Alergias.
- Tipo sanguíneo, si se conoce.

### Antecedentes

- Enfermedades crónicas.
- Cirugías.
- Hospitalizaciones.
- Medicamentos actuales.
- Antecedentes familiares relevantes.

### Antecedentes gineco-obstétricos

- Gineco-obstétricos relevantes.
- Embarazos previos.
- Complicaciones obstétricas.
- Información de embarazo actual, si aplica.

### Información clínica reciente

- Últimos diagnósticos registrados.
- Tratamientos actuales.
- Medicamentos actuales.
- Últimas consultas.
- Últimos laboratorios.
- Últimos estudios de imagen.
- Resultados de histopatologías.
- Evolución reciente.

---

# 20. Alertas clínicas

Debe existir el concepto de **alerta clínica** visible al médico.

Ejemplos:

- Alergia a un medicamento.
- Embarazo actual.
- Hipertensión.
- Diabetes gestacional previa.
- Cesárea previa.
- Otro riesgo o consideración clínica.

Una alerta debe permitir almacenar:

- Tipo.
- Descripción.
- Fecha de creación.
- Usuario que la creó.
- Estatus activa/inactiva.
- Fecha de resolución, cuando aplique.

Las alertas activas deben mostrarse de forma destacada en el resumen clínico.

Las alertas son informativas y no sustituyen el criterio médico.

---

# 21. Recetas médicas

El médico debe poder elaborar recetas relacionadas con una consulta.

Una receta debe incluir como mínimo:

- Paciente.
- Médico.
- Consulta.
- Fecha de emisión.
- Medicamentos.
- Indicaciones de uso.
- Dosis.
- Frecuencia.
- Duración, cuando aplique.
- Observaciones.

Una receta debe generar un **PDF**.

El PDF debe poder:

- Consultarse.
- Descargar.
- Imprimirse.

El paciente/responsable autorizado debe poder consultar y descargar recetas desde su portal.

Las recetas históricas no deben modificarse sin dejar trazabilidad.

---

# 22. Solicitudes de laboratorio, gabinete y otros estudios

El médico debe poder generar solicitudes para:

- Laboratorios clínicos.
- Estudios de gabinete.
- Histopatologías.
- Otros estudios.

La solicitud debe incluir:

- Paciente.
- Médico.
- Consulta.
- Fecha de emisión.
- Tipo de estudio.
- Estudios solicitados.
- Indicaciones.
- Observaciones.

Debe generarse un PDF.

El paciente/responsable autorizado debe poder consultar y descargar la solicitud.

---

# 23. Documentos clínicos

Debe existir una entidad genérica para documentos asociados a:

- Paciente.
- Cita.
- Consulta.
- Receta.
- Solicitud de estudio.
- CareRequest.

Los documentos deben almacenar como mínimo:

- Archivo.
- Nombre original.
- Tipo de documento.
- Descripción.
- Fecha de creación.
- Usuario que lo cargó/generó.
- Paciente relacionado.
- Relaciones clínicas correspondientes.

Tipos iniciales:

- Laboratorio.
- Gabinete.
- Histopatología.
- Fotografía.
- Receta.
- Indicaciones.
- Solicitud de estudio.
- Otro.

Los documentos médicos deben almacenarse en un medio **privado**, no en una carpeta pública accesible directamente.

Toda descarga debe pasar por autorización en servidor.

La aplicación debe validar que el usuario tenga permiso para acceder al archivo solicitado.

---

# 24. Versionado y trazabilidad de documentos

Los documentos clínicos emitidos por TeCuidoApp deben conservar su versión histórica.

Una receta o solicitud que ya fue emitida no debe sobrescribirse silenciosamente.

Cuando exista una corrección, debe quedar registro de:

- Versión.
- Fecha/hora.
- Usuario.
- Motivo de modificación.
- Relación con la versión anterior.

El sistema debe poder identificar cuál es la versión vigente.

---

# 25. Dashboard del médico

Funcionalidad de Fase 5 (§41). Los estados que se listan aquí deben ser exactamente los
definidos en §13.1 — no deben inventarse estados de presentación adicionales.

El médico debe disponer de un panel principal con:

### Agenda del día

- Citas en `SCHEDULED`.
- Citas en `IN_CONSULTATION`.
- Citas en `COMPLETED`.
- Inasistencias (`NO_SHOW`).

### Alertas operativas

- Nuevas solicitudes CareRequest (cuando esa app exista, Fase 5).
- Documentos nuevos.
- Otras alertas relevantes.

### Próximas citas

Debe poder consultar sus siguientes citas de manera rápida.

---

# 26. Dashboard del paciente/responsable

Debe existir un panel con:

### Próxima cita

- Fecha.
- Hora.
- Médico.
- Consultorio.
- Estado.

### Mis citas

- Próximas.
- Históricas.
- Canceladas.
- No realizadas.

### Mis documentos

- Recetas.
- Indicaciones.
- Solicitudes.
- Resultados/documentos clínicos autorizados.

En caso de responsable, la información debe poder filtrarse por paciente.

---

# 27. Notificaciones por correo

El sistema debe enviar correos electrónicos para:

- Invitación de registro.
- Verificación de correo.
- Recuperación de contraseña.
- Cita creada (nota: es la notificación de que la reserva se completó — Fase 2 no tiene un
  paso de "confirmación" separado; no debe existir un correo de "confirmación de cita" como
  si fuera otra etapa).
- Cita modificada (reprogramación).
- Cita cancelada.
- Recordatorios.
- Otras notificaciones operativas definidas por la aplicación.

## 27.1 Recordatorios

Inicialmente deben contemplarse recordatorios:

- 15 días antes.
- 10 días antes.
- 5 días antes.
- 1 día antes.

Las reglas deben diseñarse de forma configurable para poder modificarse sin cambiar código.

Ninguna regla de recordatorio o notificación cancela ni cambia el estado de una cita por sí
sola — el paso del tiempo nunca cambia automáticamente el estado de un `Appointment` (§13.1);
un recordatorio es solo una comunicación, nunca un mecanismo de transición de estado.

---

# 28. Canales de notificación

El diseño deberá permitir posteriormente múltiples canales:

- Email.
- WhatsApp.
- SMS u otros canales futuros.

La integración con WhatsApp queda **fuera de la primera versión**.

Sin embargo, la arquitectura de notificaciones debe evitar acoplar la lógica de negocio directamente a un proveedor concreto.

---

# 29. Privacidad y seguridad

Dado que TeCuidoApp manejará información médica, se debe considerar la información clínica como información altamente sensible.

El sistema debe implementar:

- Autenticación segura.
- Autorización basada en roles/permisos.
- Verificación de correo.
- Recuperación segura de contraseña.
- Protección CSRF.
- Protección contra accesos no autorizados.
- Validación de archivos.
- Almacenamiento privado de documentos.
- Control de acceso por objeto.
- Auditoría.
- Baja lógica de registros sensibles.
- Registro de acciones relevantes.
- Configuración segura de producción.

No se debe asumir que ocultar una URL es suficiente para proteger un documento.

---

# 30. Consentimiento y aviso de privacidad

El sistema debe contemplar un mecanismo para registrar la aceptación de:

- Aviso de privacidad.
- Términos y condiciones.
- Consentimientos que correspondan al funcionamiento de la plataforma.

La aceptación debe registrar:

- Usuario.
- Fecha/hora.
- Versión del documento aceptado.

La implementación técnica no sustituye la revisión legal de los avisos, consentimientos y obligaciones aplicables.

---

# 31. Auditoría

Debe existir un módulo de auditoría.

Debe registrar acciones relevantes, especialmente sobre información clínica.

Ejemplos:

- Inicio de sesión.
- Consulta de expediente.
- Creación/modificación de consulta.
- Creación/modificación de receta.
- Generación de documento.
- Descarga de documento.
- Modificación de paciente.
- Cambio de permisos.
- Desactivación de usuario.
- Acceso de administrador a información sensible.

El registro debe incluir, cuando aplique:

- Usuario.
- Fecha/hora.
- Acción.
- Entidad afectada.
- Identificador del registro.
- Información suficiente para reconstruir el evento.

---

# 32. Baja lógica

Los registros clínicos y usuarios importantes no deben eliminarse físicamente de forma rutinaria.

Debe utilizarse un mecanismo de desactivación/baja lógica cuando corresponda.

Por ejemplo:

- Usuario activo/inactivo.
- Paciente activo/inactivo.
- Médico activo/inactivo.
- Consultorio activo/inactivo.

El historial clínico debe conservarse de acuerdo con las políticas definidas.

---

# 33. Control de permisos

El sistema debe aplicar permisos a nivel de funcionalidad y de objeto.

Ejemplos:

- Un paciente sólo puede consultar su información.
- Un responsable sólo puede consultar la información de los pacientes que tiene autorizados.
- Un médico puede consultar los pacientes con los que tiene relación y las reglas de acceso definidas.
- El administrador tiene acceso global, sujeto a auditoría.
- La información clínica no debe exponerse por URLs directas sin autorización.

---

# 34. Búsqueda de pacientes

El médico y los perfiles autorizados deben poder buscar pacientes por:

- Nombre.
- Apellidos.
- Teléfono.
- Correo electrónico.

Desde los resultados se debe poder acceder rápidamente, según permisos, a:

- Información general.
- Próximas citas.
- Historial de consultas.
- Recetas.
- Estudios.
- Documentos.
- Alertas clínicas.

---

# 35. Datos administrativos y médicos históricos

Debe distinguirse entre:

### Datos actuales

Por ejemplo:

- Teléfono actual.
- Domicilio actual.
- Medicamentos actuales.
- Alertas actualmente activas.

### Información histórica

Por ejemplo:

- Consultas anteriores.
- Diagnósticos registrados en consultas anteriores.
- Tratamientos anteriores.
- Recetas históricas.
- Estudios históricos.

Las modificaciones de información relevante deben mantener trazabilidad.

---

# 36. Reglas de negocio principales

1. La cuenta de correo del usuario debe ser única.
2. El correo debe verificarse para completar el registro.
3. Un usuario cuyo correo no ha sido verificado no debe poder iniciar sesión.
4. Los prospectos no son pacientes hasta concluir el registro.
5. Una invitación de médico asociará automáticamente al paciente con ese médico.
6. Un paciente puede estar relacionado con uno o más médicos.
7. Un responsable puede estar relacionado con uno o más pacientes.
8. Un responsable puede registrar a un paciente menor de edad sin que este cree una cuenta
   propia; la minoría de edad se determina desde la fecha de nacimiento, nunca desde un
   campo introducido manualmente (§7.2).
9. Registrar a un menor no crea automáticamente una relación médico-paciente.
10. El régimen de autorización de un paciente (menor/adulto) es independiente de su edad
    cronológica; solo cambia mediante una transición explícita, nunca automáticamente al
    cumplir 18 años (§7.2.8).
11. La transición a régimen adulto solo puede ejecutarla un médico con relación activa hacia
    ese paciente, y es irreversible.
12. La transición a régimen adulto desactiva, en la misma operación, todas las relaciones
    responsable-paciente vigentes de ese paciente — nunca deja algunas activas y otras no.
13. Una cita debe identificar al paciente que será atendido.
14. Cuando aplique, una cita debe identificar al responsable que la gestionó.
15. Una cita pertenece a un médico y un consultorio, y ocupa a ambos durante toda su duración.
16. No deben existir citas superpuestas para el mismo médico/consultorio.
17. Un médico no puede tener dos disponibilidades activas que se solapen temporalmente,
    aunque correspondan a consultorios distintos (§10).
18. La agenda utiliza la zona horaria del consultorio (`Clinic`) como referencia de negocio
    para disponibilidad y citas (§10).
19. El sistema debe impedir dobles reservas del mismo horario mediante control de
    concurrencia a nivel de base de datos, no solo validación de aplicación.
20. Una reserva en curso protege el horario mediante un hold temporal de 15 minutos como
    máximo; el hold no es un estado de aprobación de la cita (§11).
21. Las citas se crean directamente al completar la reserva — Fase 2 no exige solicitud
    previa (`CareRequest`) ni confirmación posterior (§12, §14).
22. Un médico puede crear la primera cita de un paciente sin que exista una
    `DoctorPatientRelationship` activa previa, siempre que tenga acceso legítimo
    (`DoctorClinic` válida); crear la cita no crea, activa ni modifica esa relación ni ningún
    otro mecanismo de autorización de Fase 1 (§14).
23. Toda operación administrativa de agenda exige, además del ámbito sobre la clínica, una
    relación `DoctorClinic` válida entre el médico y el consultorio involucrados (§10, §14).
24. El paso del tiempo nunca cambia por sí solo el estado de una cita; todo cambio de estado
    requiere la acción humana autorizada correspondiente — nunca un cron, signal o tarea
    programada (§13.1).
25. `NO_SHOW` solo puede marcarlo el médico asignado, desde `SCHEDULED`, y representa una
    inasistencia real que él determina — nunca una inferencia automática por falta de
    confirmación (que no existe) ni por el solo transcurso del tiempo (§15).
26. La consulta médica es independiente de la cita; `IN_CONSULTATION` es la frontera hacia el
    dominio clínico de Fase 3 (§17).
27. Las consultas concluidas deben conservar su historial.
28. Las recetas y solicitudes emitidas deben conservar su trazabilidad.
29. Los documentos médicos deben tener acceso privado y autorizado.
30. Las acciones sensibles deben auditarse.
31. Los registros clínicos no deben eliminarse físicamente de manera rutinaria.
32. TeCuidoApp no diagnostica ni decide tratamientos de forma autónoma.
33. Las decisiones clínicas pertenecen al médico.

---

# 37. Requisitos no funcionales

## Seguridad

La aplicación debe seguir las buenas prácticas de seguridad de Django y de aplicaciones Web.

Debe configurarse adecuadamente:

- `DEBUG=False` en producción.
- Variables de entorno para secretos.
- Protección de cookies.
- HTTPS en producción.
- Protección CSRF.
- Validación de entradas.
- Restricción de tipos y tamaños de archivos.
- Protección de descargas.
- Políticas apropiadas de contraseñas.
- Manejo seguro de tokens.

## Mantenibilidad

La aplicación debe utilizar una arquitectura modular.

Se recomienda separar responsabilidades funcionales en aplicaciones Django independientes cuando tenga sentido.

No se deben introducir dependencias innecesarias.

## Pruebas

Los módulos críticos deben disponer de pruebas automatizadas, especialmente:

- Autenticación.
- Permisos.
- Registro de pacientes.
- Relaciones responsable-paciente.
- Invitaciones.
- Agenda.
- Prevención de conflictos.
- Bloqueos temporales.
- CareRequest.
- Citas.
- Cambios de estado.
- Expediente.
- Recetas.
- Documentos.
- Seguridad de descargas.
- Auditoría.

---

# 38. Arquitectura Django propuesta

TeCuidoApp debe mantenerse dentro de un único proyecto Django.

Las funcionalidades podrán separarse en aplicaciones Django internas, por ejemplo:

```text
TeCuido/
├── manage.py
├── config/
├── accounts/
├── patients/
├── doctors/
├── clinics/
├── appointments/
├── care_requests/
├── medical_records/
├── prescriptions/
├── clinical_documents/
├── notifications/
└── audit/
```

Los nombres son una propuesta y pueden ajustarse durante el diseño técnico.

## 38.1 CareRequest

`CareRequest` debe ser una **Django app dentro del mismo proyecto**, no un proyecto
independiente, y separada de `appointments` (ver `docs/adr/ADR-005-django-app-boundaries.md`)
— `appointments` no depende de `care_requests` para funcionar; es Fase 2 completa sin que
`care_requests` exista todavía.

No necesita su propio `requirements.md`.

La especificación general de todo el sistema debe permanecer en este `requirements.md`.

En caso de que posteriormente alguna app requiera una especificación técnica específica, puede documentarse mediante documentación complementaria, pero no debe duplicarse innecesariamente el requerimiento general.

---

# 39. Separación por aplicaciones

La separación en Django debe utilizarse para organizar responsabilidades, no para crear sistemas independientes.

Las relaciones entre apps deben ser claras y evitar dependencias circulares.

El modelo de datos debe priorizar:

- Integridad referencial.
- Claridad.
- Facilidad de consulta.
- Historial.
- Seguridad.

---

# 40. Generación de PDFs

El sistema debe generar documentos PDF para:

- Recetas.
- Solicitudes de laboratorio.
- Solicitudes de gabinete.
- Otros documentos clínicos que se agreguen posteriormente.

Los documentos deben:

- Identificar al paciente.
- Identificar al médico.
- Identificar al consultorio.
- Mostrar fecha/hora.
- Contener la información emitida.
- Tener una presentación adecuada para impresión.
- Conservar la versión emitida.

---

# 41. MVP / evolución por fases

El desarrollo debe realizarse por fases.

## Fase 1 — Fundaciones

- Configuración del proyecto.
- Usuarios.
- Roles.
- Autenticación.
- Verificación de correo.
- Recuperación de contraseña.
- Médicos.
- Consultorios.
- Pacientes.
- Responsables.
- Invitaciones.

## Fase 2 — Agenda

Contrato funcional completo y detallado en `docs/phases/phase-2-agenda.md` (aprobado
2026-09-09) — lo que sigue es un resumen, ese documento manda en caso de duda.

- Disponibilidad por fecha concreta (sin reglas recurrentes ni excepciones).
- Creación directa de citas (sin solicitud previa ni confirmación posterior).
- Estados de `Appointment`: `SCHEDULED`, `IN_CONSULTATION`, `COMPLETED`, `CANCELLED`,
  `NO_SHOW` — únicamente estos cinco.
- Cancelaciones.
- Reprogramaciones.
- Hold temporal de 15 minutos.
- Prevención de conflictos y de doble reserva concurrente.
- Inicio de consulta por el médico asignado (reemplaza el check-in de versiones anteriores de
  este documento — no hay check-in ni sala de espera en Fase 2).
- `NO_SHOW` desde el minuto 1, marcado por el médico asignado.

## Fase 3 — Gestión clínica

- Historia clínica.
- Consultas.
- Evolución.
- Diagnósticos.
- Tratamientos.
- Pronóstico.
- Alertas clínicas.
- Resumen clínico.

## Fase 4 — Documentos

- Recetas.
- Solicitudes de laboratorio.
- Solicitudes de gabinete.
- PDFs.
- Archivos adjuntos.
- Descargas autorizadas.
- Versionado.

## Fase 5 — CareRequest y operación

- Solicitudes de atención.
- Conversión de CareRequest a cita (origen alternativo y opcional, no reemplaza ni condiciona
  la reserva directa de Fase 2 — §12).
- Dashboard médico.
- Dashboard paciente/responsable.
- Sala de espera — **pendiente de diseño**: Fase 2 no introdujo check-in ni un estado
  `WAITING` (§16), así que esta funcionalidad no puede asumir que esos mecanismos ya existen;
  requiere su propia decisión funcional explícita cuando le toque su fase, no debe inferirse
  del modelo de Fase 2.
- Búsqueda.

## Fase 6 — Notificaciones y auditoría

- Emails.
- Recordatorios.
- Confirmaciones.
- Auditoría.
- Consentimientos.
- Revisión de seguridad.

El desarrollo debe implementarse progresivamente. No se debe intentar construir todas las fases en una sola iteración.

---

# 42. Funcionalidades explícitamente fuera del alcance actual

Las siguientes funcionalidades no forman parte de la primera etapa y no deben incorporarse sin una decisión posterior:

- Integración con WhatsApp.
- MFA/2FA.
- Interoperabilidad FHIR.
- Facturación.
- Pagos en línea.
- Inventario.
- Farmacia.
- Aseguradoras.
- Videoconsultas.
- Aplicación móvil nativa.
- Multi-clínica.
- Firma electrónica avanzada.
- IA para diagnóstico.
- IA para prescripción o decisión clínica.
- Estadística clínica avanzada.

Estas funcionalidades pueden evaluarse en versiones futuras.

---

# 43. Principios de desarrollo para Claude Code

Claude Code debe tratar este archivo como la especificación funcional de referencia.

Antes de realizar cambios importantes en la arquitectura debe:

1. Revisar el alcance existente.
2. Mantener compatibilidad con las reglas de negocio.
3. Evitar duplicación innecesaria.
4. Preferir soluciones idiomáticas de Django.
5. Utilizar migraciones para cambios de base de datos.
6. Agregar pruebas para reglas críticas.
7. No introducir funcionalidades fuera del alcance sin indicarlo.
8. Mantener separación entre lógica clínica, lógica de agenda y lógica de autenticación.
9. Aplicar control de acceso tanto en interfaz como en servidor.
10. Mantener auditoría de operaciones sensibles.
11. No eliminar información clínica histórica de forma destructiva.
12. Explicar cualquier decisión arquitectónica que modifique significativamente el modelo definido aquí.

---

# 44. Definición conceptual de entidades principales

Como guía inicial, el dominio debe contemplar al menos:

```text
User
Person
Doctor
Patient
Responsible
ResponsiblePatientRelationship
Clinic
DoctorClinic
Invitation
Availability
Hold
Appointment
CareRequest
MedicalRecord
MedicalEncounter / Consultation
ClinicalAlert
Prescription
PrescriptionItem
StudyOrder
ClinicalDocument
Notification
AuditLog
Consent
```

Los nombres definitivos de modelos Django pueden cambiar durante el diseño técnico, pero las responsabilidades funcionales deben conservarse.

`Availability` es por fecha concreta (§10) — no un `AvailabilityRule` recurrente. `Hold` es el
bloqueo temporal de 15 minutos (§11), no un estado de `Appointment`.

---

# 45. Principio fundamental de diseño clínico

La información clínica debe tratarse como información histórica.

No se debe diseñar el expediente como una única colección de campos que se sobrescribe continuamente.

La información debe poder responder:

- Qué se sabía en cada consulta.
- Qué indicó el médico.
- Qué receta se emitió.
- Qué estudio se solicitó.
- Cuándo ocurrió.
- Quién lo registró.
- Qué cambios posteriores se realizaron.

La trazabilidad y el historial son requisitos fundamentales del sistema.

---

# 46. Resultado esperado

Al concluir las fases iniciales, TeCuidoApp deberá permitir que:

### Administrador

Administre usuarios, médicos, consultorios, asignaciones y configuración general.

### Médico

Administre su agenda, atienda pacientes, consulte contexto clínico, mantenga el expediente, registre consultas y emita documentos clínicos.

### Paciente

Administre su información permitida, solicite/gestione citas y consulte sus documentos.

### Responsable

Gestione pacientes a su cargo y realice las operaciones autorizadas en nombre de ellos.

### Sistema

Mantenga:

- Seguridad.
- Privacidad.
- Historial clínico.
- Auditoría.
- Documentos.
- Notificaciones.
- Integridad de citas.
- Control de acceso.

El sistema no debe realizar diagnósticos ni decisiones médicas autónomas.

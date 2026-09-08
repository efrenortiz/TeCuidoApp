# TeCuidoApp — Phase 1 Foundations

**Estado:** PARTIALLY COMPLETED (actualizado 2026-09-08 — ver §26-27)
**Fase:** 1 — Fundaciones
**Stack:** Python + Django + PostgreSQL
**Fuente funcional:** `requirements.md`
**Guía arquitectónica:** `docs/architecture.md`
**ADRs aplicables:** `docs/adr/ADR-001-custom-user-model.md` a `docs/adr/ADR-007-responsible-initiated-minor-registration.md`

La arquitectura base y el alcance funcional de Fase 1 están implementados, incluida la
transición a régimen adulto (ADR-007 §3.8 addendum, 144 tests en verde). Queda **PARTIALLY
COMPLETED**, no COMPLETADA, porque persisten decisiones funcionales explícitamente pendientes
sobre la cuenta propia (`User`) del paciente adulto (§7.2.9 de `requirements.md`, §5 de
ADR-007) — ver §26-27 para el detalle exacto de qué falta y por qué no se resuelve por
omisión.

---

## 1. Propósito

Este documento define el alcance técnico y operativo de la **Fase 1 — Fundaciones** de TeCuidoApp.

Su objetivo es proporcionar una base funcional, segura, testeable y extensible sobre la cual puedan implementarse las fases posteriores sin rehacer la arquitectura de identidad, perfiles, relaciones principales ni mecanismos fundamentales de seguridad.

La especificación funcional completa permanece en `requirements.md`.

Este documento **no sustituye** a `requirements.md`, `docs/architecture.md` ni a los ADR. Define únicamente el trabajo que debe realizarse en esta fase y cómo verificar que quedó correctamente terminado.

---

# 2. Alcance de la Fase 1

La Fase 1 comprende exclusivamente:

- configuración inicial del proyecto;
- usuarios;
- roles;
- autenticación;
- verificación de correo electrónico;
- recuperación de contraseña;
- médicos;
- consultorios;
- pacientes;
- responsables;
- invitaciones;
- registro de paciente menor iniciado por su responsable (ADR-007, `requirements.md` §7.2) —
  **implementado**, no debe tratarse en ningún lugar de este documento como pendiente de
  construir.

Este alcance corresponde a la planificación por fases definida en `requirements.md`.

---

# 3. Fuera de alcance

No implementar como funcionalidad de esta fase:

- disponibilidad del médico;
- reglas de disponibilidad;
- excepciones de disponibilidad;
- citas;
- estados de citas;
- confirmaciones de citas;
- cancelaciones;
- reprogramaciones;
- bloqueo temporal de 15 minutos;
- prevención de conflictos de agenda;
- check-in;
- sala de espera;
- CareRequest;
- historia clínica completa;
- MedicalEncounter / consulta médica;
- evolución clínica;
- diagnósticos;
- tratamientos;
- pronóstico;
- alertas clínicas;
- resumen clínico;
- recetas;
- solicitudes de laboratorio/gabinete;
- documentos clínicos;
- PDFs clínicos;
- almacenamiento de documentos médicos;
- versionado documental;
- dashboard médico funcional;
- dashboard paciente/responsable funcional;
- recordatorios operativos de fases posteriores;
- auditoría clínica completa;
- notificaciones avanzadas;
- WhatsApp;
- MFA/2FA;
- FHIR;
- facturación;
- pagos;
- inventario;
- farmacia;
- aseguradoras;
- videconsultas;
- aplicación móvil nativa;
- multi-clínica;
- firma electrónica avanzada;
- IA para diagnóstico o prescripción;
- estadística clínica avanzada.

Solo pueden implementarse bases arquitectónicas mínimas para facilitar fases posteriores, pero no la funcionalidad de dichas fases.

---

# 4. Documentos que deben consultarse

Antes de realizar cambios relevantes, Claude Code debe consultar:

```text
CLAUDE.md
requirements.md
docs/architecture.md
docs/adr/ADR-001-custom-user-model.md
docs/adr/ADR-002-user-person-profile.md
docs/adr/ADR-003-invitation-security.md
docs/adr/ADR-004-role-and-object-permissions.md
docs/adr/ADR-005-django-app-boundaries.md
docs/adr/ADR-006-database-integrity-and-transactions.md
docs/adr/ADR-007-responsible-initiated-minor-registration.md
```

Jerarquía:

```text
requirements.md
        ↓
docs/architecture.md
        ↓
ADRs
        ↓
Este documento
        ↓
Implementación
```

Interpretación:

- `requirements.md` define **qué necesita el sistema**.
- `docs/architecture.md` define **cómo debe estructurarse**.
- Los ADR explican **por qué se tomaron decisiones concretas**.
- Este documento define **qué debe construirse en la Fase 1 y cómo comprobarlo**.

No se deben modificar estos documentos silenciosamente para justificar una implementación.

---

# 5. Objetivos de la fase

Al concluir esta fase, TeCuidoApp debe contar con una base que permita:

1. autenticar usuarios mediante un modelo central;
2. distinguir roles y perfiles funcionales;
3. representar personas independientemente de su autenticación;
4. representar médicos, pacientes y responsables;
5. relacionar pacientes con médicos;
6. relacionar responsables con pacientes;
7. relacionar médicos con consultorios;
8. registrar prospectos mediante invitaciones seguras;
9. verificar correo electrónico;
10. recuperar y cambiar contraseñas;
11. aplicar permisos en servidor;
12. preservar integridad de datos;
13. mantener operaciones multi-entidad atómicas cuando corresponda;
14. dejar una base estable para Fase 2.

---

# 6. Revisión inicial obligatoria

Antes de modificar código, inspeccionar el repositorio existente.

Como mínimo revisar:

- versión de Python;
- versión de Django;
- estructura de directorios;
- `manage.py`;
- settings;
- URLs;
- apps existentes;
- modelos;
- migraciones;
- autenticación;
- templates;
- forms;
- serializers;
- views;
- servicios;
- tests;
- configuración PostgreSQL;
- variables de entorno;
- requirements / `pyproject.toml`;
- Docker o equivalente, si existe;
- README;
- herramientas de linting/formatting;
- CI/CD, si existe.

Antes de crear algo nuevo, determinar si ya existe una implementación reutilizable.

No sobrescribir componentes existentes sin entender primero su propósito.

---

# 7. Arquitectura objetivo de la Fase 1

La fase deberá respetar la arquitectura modular establecida.

Apps principales esperadas:

```text
config/
accounts/
patients/
doctors/
clinics/
```

No es obligatorio crear exactamente esta estructura si el repositorio ya posee una organización compatible y mejor justificada.

La regla es preservar responsabilidades claras y evitar dependencias circulares.

---

# 8. Identidad y autenticación

## 8.1 Custom User Model

Implementar el Custom User Model definido en `ADR-001`.

Debe existir un único sistema central de autenticación.

Debe configurarse `AUTH_USER_MODEL` apropiadamente.

No utilizar directamente `django.contrib.auth.models.User` en modelos de dominio.

Cuando el código necesite referenciar al usuario:

- utilizar `settings.AUTH_USER_MODEL` en relaciones de modelos;
- utilizar `get_user_model()` cuando corresponda en lógica de aplicación.

---

## 8.2 Responsabilidad de User

`User` debe concentrarse en:

- autenticación;
- email;
- contraseña;
- estado de cuenta;
- metadatos de cuenta;
- información necesaria para autorización.

No almacenar en `User` información clínica ni información específica de pacientes, médicos o responsables.

---

## 8.3 Person

Implementar la separación definida en `ADR-002`.

Conceptualmente:

```text
User
  ↓
Person
  ↓
Functional Profile
```

La información personal común debe mantenerse en `Person`, no repetirse innecesariamente en cada perfil.

---

# 9. Roles

Implementar inicialmente los roles funcionales:

```text
ADMINISTRATOR
DOCTOR
PATIENT
RESPONSIBLE
```

Los roles no deben utilizarse como sustituto de las entidades de dominio.

Debe conservarse la diferencia entre:

```text
Role
Profile
Relationship
```

Los permisos funcionales deberán utilizar los mecanismos apropiados de Django, manteniendo la posibilidad de evolución futura.

---

# 10. Perfiles funcionales

## 10.1 Doctor

Implementar el perfil `Doctor` relacionado con `Person`.

Debe quedar preparado para futuras relaciones con:

- pacientes;
- consultorios;
- disponibilidad;
- agenda;
- consultas.

No implementar dichas funcionalidades futuras.

---

## 10.2 Patient

Implementar el perfil `Patient` relacionado con `Person`.

Debe contemplar la información general definida en `requirements.md`:

### Identificación

- nombre(s);
- apellido paterno;
- apellido materno;
- fecha de nacimiento;
- sexo;
- nacionalidad;
- CURP si se decide incluirla.

### Contacto

- correo;
- teléfono celular;
- teléfono alternativo;
- contacto de emergencia.

### Domicilio

- calle;
- número;
- colonia;
- código postal;
- municipio/alcaldía;
- estado;
- país.

### Información médica relevante

- alergias;
- tipo sanguíneo;
- enfermedades crónicas;
- medicamentos actuales;
- antecedentes quirúrgicos;
- hospitalizaciones relevantes.

La información gineco-obstétrica futura debe poder incorporarse posteriormente sin comprometer la arquitectura, pero no debe desarrollarse como módulo clínico completo en esta fase.

---

## 10.3 Responsible

Implementar el perfil `Responsible` relacionado con `Person`.

Debe contemplar:

- relación con paciente;
- datos de contacto;
- domicilio;
- contacto alternativo;
- identificación futura cuando corresponda.

Relaciones iniciales:

```text
MADRE
PADRE
TUTOR_LEGAL
FAMILIAR
CUIDADOR
OTRO
```

---

# 11. Relaciones de dominio

Las relaciones relevantes deben ser entidades explícitas cuando tengan atributos o comportamiento propio.

## 11.1 Doctor ↔ Patient

Implementar una relación explícita equivalente a:

```text
DoctorPatientRelationship
```

Debe permitir que un paciente esté relacionado con múltiples médicos.

Debe poder evolucionar posteriormente para distinguir tipos como:

- médico tratante;
- médico sustituto;
- otro médico del consultorio.

---

## 11.2 Responsible ↔ Patient

Implementado:

```text
ResponsiblePatientRelationship
```

Permite:

- múltiples pacientes por responsable;
- tipo de relación (Madre/Padre/Tutor legal/Familiar/Cuidador/Otro);
- crecimiento futuro de reglas de autorización.

**Corrección respecto a la versión original de esta sección:** el estado de la relación **no**
es un booleano `is_active` (activo/inactivo). Es `status`, con tres valores distintos:

```text
PENDING    — nunca aprobada; no concede acceso operativo
ACTIVE     — vigente; concede acceso cuando la regla de negocio lo permita
INACTIVE   — previamente aprobada y luego desactivada
```

`status` no tiene un valor por defecto a nivel de campo — cada operación de negocio debe
elegirlo explícitamente (alta de menor nuevo → `ACTIVE`; coincidencia por CURP con paciente ya
existente → `PENDING`, pendiente de que un responsable ya autorizado la apruebe). Un
`CheckConstraint` en base de datos rechaza cualquier fila que no tenga uno de los tres valores
— omitir `status` falla, no se activa por accidente (deny-by-default, ADR-004).

**El registro de paciente menor iniciado por su responsable está implementado** — servicio
(`patients/services/minors.py`), vistas y pantallas (`docs/design/screens.md` §6.7-6.8),
conforme a `requirements.md` §7.2 y `docs/adr/ADR-007-responsible-initiated-minor-registration.md`.
No debe describirse en ningún lugar de este documento como pendiente de construir.

La operación de registro es atómica; el responsable se determina siempre por la sesión
autenticada del servidor, nunca por un identificador enviado por el cliente; y el flujo no crea
automáticamente ninguna `DoctorPatientRelationship`.

### 11.2.1 Mayoría de edad

La edad se deriva exclusivamente de `Person.birth_date`, calculada en el momento en que se
necesita (propiedades `Person.age`/`Person.is_minor`). No existe ni debe existir un campo
persistente que la almacene, ni una tarea programada (Celery u otra) que la recalcule al
cumplirse el cumpleaños — Fase 1 no incorpora infraestructura de tareas programadas para esto.

Cumplir 18 años, por sí solo:

- NO elimina al paciente ni al responsable;
- NO modifica ni desactiva automáticamente ninguna `ResponsiblePatientRelationship`;
- NO genera un `User` para el paciente;
- NO cambia `Patient.regime` — ese campo solo cambia mediante la transición explícita
  descrita en §7.2.8 de `requirements.md` y en `docs/adr/ADR-007-...md` §3.8 (addendum).

La UI puede señalar que el paciente ya es adulto cronológicamente pero sigue en
`regime = MINOR` (`docs/design/screens.md` §6.5, §6.7), pero eso es únicamente informativo —
nunca sustituye ni modifica la autorización real, que sigue derivándose exclusivamente de
`ResponsiblePatientRelationship.status`. Solo un médico con relación activa, ejecutando la
transición de §7.2.8, cambia esa autorización.

### 11.2.2 Política de consentimiento a los 18 años

**Resuelto e implementado (§7.2.8, `docs/adr/ADR-007-...md` §3.8 addendum, 2026-09-08):** el
mecanismo de transición a régimen adulto está diseñado, documentado y construido en código
(`Patient.regime`, `transition_patient_to_adult`, UI "Marcar como adulto"). Esto resuelve:

- quién ejecuta la transición: un médico con `DoctorPatientRelationship` activa (cualquier
  `relationship_type`) hacia el paciente;
- qué sucede con el/los responsable(s) previamente autorizados: se desactivan **todos** en
  bloque, en la misma operación (`ResponsiblePatientRelationship.status → INACTIVE`);
- reversibilidad: no la hay — una vez `regime = ADULT`, no vuelve a `MINOR`.

Lo que **sigue explícitamente pendiente** (no debe inferirse en código ni asumirse por
omisión) es un subconjunto más pequeño que el original:

1. cómo obtiene el paciente adulto una cuenta propia (`User`), cuando corresponda;
2. cómo se verifica su identidad para ese trámite;
3. cómo puede el paciente adulto, ya con cuenta propia, revocar o volver a autorizar el
   acceso de un responsable por su cuenta (la transición de §7.2.8 solo cubre el cierre
   inicial ejecutado por el médico, no la gestión posterior por el propio paciente);
4. qué ocurre si el paciente nunca crea una cuenta propia — queda en `regime = ADULT` sin
   `User`, sin que nadie tenga acceso operativo a su expediente hasta que él mismo autorice
   a alguien.

Ver `requirements.md` §7.2.9 y `docs/adr/ADR-007-responsible-initiated-minor-registration.md`
§5 para el registro formal de estos pendientes.

---

## 11.3 Doctor ↔ Clinic

Implementar la relación explícita:

```text
DoctorClinic
```

Debe permitir asociar médicos a consultorios sin limitar la relación a uno-a-uno.

---

# 12. Clinics

Implementar la app `clinics` y el modelo `Clinic`.

Debe contemplar como mínimo:

- nombre;
- descripción;
- dirección;
- teléfono;
- estado activo/inactivo.

El modelo debe quedar preparado para que futuras citas dependan de la combinación médico + consultorio.

No implementar agenda ni disponibilidad en esta fase.

---

# 13. Invitaciones

Implementar el mecanismo definido en `ADR-003`.

## 13.1 Entidad Invitation

La invitación debe registrar como mínimo:

- médico que la generó;
- email destinatario;
- token o referencia segura al token;
- estado;
- fecha de creación;
- fecha de expiración;
- fecha de utilización.

Estados iniciales recomendados:

```text
PENDING
USED
EXPIRED
CANCELLED
```

---

## 13.2 Seguridad del token

El token debe:

- ser criptográficamente seguro;
- ser impredecible;
- tener expiración;
- ser de un solo uso;
- no contener datos personales legibles;
- no registrarse completo en logs.

No utilizar IDs secuenciales ni parámetros manipulables de dominio como mecanismo de seguridad.

---

## 13.3 Médico asociado

El médico asociado a una invitación debe obtenerse desde la entidad `Invitation`.

El cliente no debe poder cambiar el médico asociado mediante parámetros de la solicitud.

---

## 13.4 Aceptación de invitación

La aceptación debe poder coordinar, de forma atómica cuando corresponda:

```text
User
Person
Patient
DoctorPatientRelationship
Invitation
```

Si falla alguna parte del proceso, no debe quedar un registro parcialmente creado.

---

## 13.5 Concurrencia

Debe protegerse el caso en que dos solicitudes intenten consumir simultáneamente la misma invitación.

Utilizar las estrategias definidas en `ADR-006`, incluyendo transacciones y locking apropiado cuando sea necesario.

Una invitación no podrá convertirse en dos registros válidos.

---

# 14. Verificación de correo

Implementar:

- generación de token seguro;
- envío de email;
- expiración;
- verificación;
- invalidación posterior al uso;
- protección contra reutilización.

La invitación y la verificación de email son mecanismos diferentes.

Conceptualmente:

```text
Invitation Token
      ≠
Email Verification Token
```

La cuenta no debe considerarse completamente verificada únicamente por haber recibido una invitación.

---

# 15. Recuperación y cambio de contraseña

Implementar las capacidades estándar de Django para:

- login;
- logout;
- recuperación de contraseña;
- cambio de contraseña;
- activación/desactivación.

No implementar mecanismos artesanales de almacenamiento de passwords.

---

# 16. Autorización

Aplicar `ADR-004`.

Debe existir separación entre:

```text
Authentication
Functional Permission
Object Permission
```

La autorización siempre debe validarse en servidor.

No confiar en:

- botones ocultos;
- JavaScript;
- URLs difíciles de adivinar;
- IDs no secuenciales.

La política general es:

```text
Deny by Default
```

---

# 17. Permisos mínimos de Fase 1

### Administrador

Debe poder gestionar las capacidades administrativas de esta fase según los permisos definidos.

### Médico

Debe poder gestionar sus invitaciones y trabajar con pacientes dentro de las relaciones autorizadas.

### Paciente

Debe acceder únicamente a su propia información permitida.

### Responsable

Debe acceder únicamente a los pacientes que tenga autorizados mediante las relaciones existentes.

No introducir permisos adicionales que no estén definidos en `requirements.md`.

---

# 18. Integridad de base de datos

Aplicar `ADR-006`.

Debe existir una estrategia consistente de:

- foreign keys;
- unique constraints;
- check constraints cuando sean apropiados;
- índices;
- transacciones;
- manejo de errores de integridad.

No usar validaciones de Python como única defensa para reglas estructurales importantes.

---

# 19. Transacciones

Utilizar transacciones para casos de uso que requieran atomicidad.

Ejemplo principal:

```text
Accept Invitation
    ↓
BEGIN
    ↓
Validate invitation
    ↓
Create User
    ↓
Create Person
    ↓
Create Patient
    ↓
Create DoctorPatientRelationship
    ↓
Mark Invitation USED
    ↓
COMMIT
```

No realizar llamadas externas lentas dentro de una transacción salvo que exista una necesidad explícita.

---

# 20. Baja lógica

Los registros importantes deben poder desactivarse sin eliminar físicamente información que deba conservarse.

Evaluar mecanismos de estado como:

```text
is_active
```

para:

- usuarios;
- médicos;
- pacientes;
- responsables;
- consultorios;
- relaciones donde corresponda.

Las decisiones de eliminación deben respetar `requirements.md` y `ADR-006`.

---

# 21. Seguridad de configuración

No almacenar en el repositorio:

- passwords;
- secret keys;
- credenciales PostgreSQL;
- API keys;
- tokens reales;
- credenciales SMTP.

Utilizar variables de entorno.

Actualizar:

```text
.env.example
```

sin credenciales reales.

---

# 22. Testing

La Fase 1 debe incluir una suite automatizada suficiente para demostrar que sus reglas críticas funcionan.

## 22.1 User / Authentication

Probar:

- creación de usuario;
- email único;
- login correcto;
- login incorrecto;
- usuario inactivo;
- cambio de contraseña;
- recuperación de contraseña.

## 22.2 Email verification

Probar:

- token válido;
- token inválido;
- token expirado;
- token usado nuevamente;
- verificación correcta.

## 22.3 Roles / Permissions

Probar:

- administrador;
- médico;
- paciente;
- responsable;
- usuario sin permisos;
- acceso no autenticado.

## 22.4 Patient

Probar:

- creación;
- actualización permitida;
- validaciones;
- relación con médico.

## 22.5 Responsible

Probar:

- creación;
- múltiples pacientes;
- relación activa/inactiva.

## 22.6 Doctor / Clinic

Probar:

- creación de médico;
- creación de consultorio;
- asociación médico-consultorio;
- desactivación.

## 22.7 Invitation

Probar:

- creación;
- token seguro;
- expiración;
- uso único;
- cancelación;
- asociación con médico;
- registro correcto del paciente;
- prevención de asociación manipulada;
- rollback ante fallo.

## 22.8 Object permissions

Probar explícitamente accesos negativos:

```text
Patient A ≠ Patient B
Responsible A ≠ Patient not authorized
Doctor A ≠ Patient unrelated
```

Modificar un identificador en una URL no debe conceder acceso a un objeto no autorizado.

---

# 23. Migraciones

Crear y probar migraciones para todos los cambios de modelos.

Ejecutar al menos:

```bash
python manage.py makemigrations
python manage.py migrate
```

Verificar que el proyecto pueda construirse desde una base de datos limpia.

No modificar manualmente el esquema como mecanismo normal.

---

# 24. Quality Gates

Antes de considerar terminada la fase, ejecutar los checks disponibles en el repositorio.

Como mínimo, cuando correspondan:

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate --plan
python manage.py test
```

Si el proyecto dispone de herramientas adicionales de linting, type checking o cobertura, ejecutarlas conforme a sus convenciones existentes.

No introducir nuevas herramientas únicamente para cumplir este documento si el proyecto no las necesita.

---

# 25. Documentación

Al finalizar la Fase 1, actualizar cuando corresponda:

- `README.md`;
- `CLAUDE.md` si cambian instrucciones permanentes;
- `docs/architecture.md` si hubo una decisión estructural relevante;
- ADR correspondiente si se modificó una decisión arquitectónica;
- documentación de configuración local.

No duplicar información funcional completa de `requirements.md` dentro de este documento.

---

# 26. Definition of Done

La Fase 1 se considera **COMPLETADA** únicamente cuando se cumplen todos los puntos aplicables.
Estado actual (2026-09-08): marcados `[x]` los ya verificados por código/tests; `[ ]` los que
siguen genuinamente pendientes — ver §27 para por qué el estado global sigue siendo
**PARTIALLY COMPLETED** y no COMPLETADA pese a que la mayoría de los puntos ya está resuelta.

## Proyecto

- [x] El proyecto inicia correctamente.
- [x] Django `check` pasa.
- [x] PostgreSQL está correctamente integrado.
- [x] La configuración se puede reproducir (`.env.example`, `README.md`).

## Identidad

- [x] Existe Custom User Model.
- [x] `AUTH_USER_MODEL` está configurado.
- [x] El email es único.
- [x] User está separado de Person.
- [x] Las aplicaciones no importan directamente el User estándar de Django.

## Roles

- [x] Existen los roles iniciales.
- [x] La autorización funcional está implementada.
- [x] El sistema puede evolucionar hacia múltiples perfiles.

## Perfiles

- [x] Doctor existe.
- [x] Patient existe.
- [x] Responsible existe.
- [x] Person está correctamente integrado.

## Relaciones

- [x] Doctor-Patient está modelado explícitamente.
- [x] Responsible-Patient está modelado explícitamente.
- [x] Doctor-Clinic está modelado explícitamente.
- [x] Las relaciones permiten las cardinalidades requeridas.

## Authentication

- [x] Login funciona (bloquea además correo no verificado — `requirements.md` §4/§36).
- [x] Logout funciona.
- [x] Cambio de password funciona.
- [x] Recuperación de password funciona.
- [x] Activación/desactivación funciona.
- [x] Verificación de email funciona.

## Invitations

- [x] Invitation existe.
- [x] Token seguro.
- [x] Expiración.
- [x] Uso único.
- [x] Cancelación/invalidez cuando corresponda.
- [x] Médico generador identificado.
- [x] El médico no puede ser alterado por el cliente.
- [x] Registro completo genera el paciente correctamente.
- [x] Se crea la relación médico-paciente correspondiente.
- [x] La operación es atómica.
- [x] Existe protección contra consumo concurrente.

## Menores (ADR-007)

- [x] Registro de menor iniciado por responsable está implementado
      (`patients/services/minors.py`).
- [x] No se crea automáticamente `DoctorPatientRelationship`.
- [x] `Person.user` permanece vacío salvo decisión explícita.
- [x] La edad se deriva de `birth_date` (`Person.age`/`Person.is_minor`), nunca de un campo
      enviado por el cliente.
- [x] No existe tarea programada para cambiar estado por cumpleaños.
- [x] Cumplir 18 años no modifica automáticamente ninguna relación.
- [x] La UI muestra la condición de adulto cuando corresponde, sin que eso otorgue ni quite
      acceso por sí solo.
- [x] Las coincidencias (CURP / nombre+fecha) no conceden acceso automáticamente.
- [x] Las respuestas de coincidencia respetan anti-enumeración (mensaje genérico fijo).
- [x] Mecanismo de transición a régimen adulto **diseñado y documentado** (§11.2.2,
      `requirements.md` §7.2.8, `docs/adr/ADR-007-...md` §3.8 addendum) — resuelve quién
      ejecuta la transición, qué pasa con los responsables previos y la reversibilidad.
- [x] Mecanismo de transición a régimen adulto **implementado en código** (2026-09-08) —
      `Patient.regime`/`regime_changed_at`/`regime_changed_by`,
      `patients/services/minors.py::transition_patient_to_adult`,
      `patients/views.py::TransitionPatientToAdultView`, UI "Marcar como adulto"
      (`docs/design/screens.md` §6.5), migración `patients.0004` con backfill de `regime` para
      filas existentes. Ver checklist completo en `docs/adr/ADR-007-...md` §8.
- [ ] Política de cuenta propia (`User`) del paciente adulto (§11.2.2, subconjunto todavía
      abierto) — **pendiente**, no resuelto por omisión.

## ResponsiblePatientRelationship

- [x] Existe `status` (reemplazó el `is_active` booleano original).
- [x] Existen `PENDING`, `ACTIVE`, `INACTIVE` como estados distintos.
- [x] `PENDING` no concede acceso (`patients/services/permissions.py`).
- [x] `INACTIVE` no concede acceso.
- [x] `status` no tiene default de campo; un `CheckConstraint` exige uno de los tres valores.
- [x] La documentación ya no usa `is_active` para describir esta relación
      (`docs/design/screens.md` corregido 2026-09-08).

## Seguridad

- [x] La autorización se valida en servidor.
- [x] Se aplica deny-by-default.
- [x] No existen secretos hardcodeados.
- [x] No se registran tokens sensibles en logs.
- [x] Los objetos no pueden accederse simplemente modificando un ID.

## Base de datos

- [x] Foreign keys correctas.
- [x] Unique constraints apropiados.
- [x] Check constraints donde corresponda.
- [x] Índices apropiados.
- [x] Migraciones correctas.
- [x] Transacciones implementadas donde corresponda.

## Testing

- [x] Tests de autenticación pasan.
- [x] Tests de permisos pasan.
- [x] Tests de perfiles pasan.
- [x] Tests de relaciones pasan.
- [x] Tests de invitaciones pasan.
- [x] Tests negativos de autorización pasan.
- [x] No existen regresiones conocidas (144/144 en verde, incluida la transición a régimen
      adulto).

## Documentación

- [x] README actualizado cuando corresponde.
- [x] Configuración documentada.
- [x] Decisiones arquitectónicas documentadas.
- [x] No existen referencias que indiquen que el registro de menor ni la transición a régimen
      adulto siguen sin implementar — verificado con grep sobre los 5 documentos afectados
      (2026-09-08); mismo criterio a reaplicar si se vuelve a tocar esta área.
- [x] Fase 2 no depende de ninguna decisión de §11.2.2 todavía no documentada — lo único
      genuinamente abierto (política de cuenta propia del paciente adulto) queda explícito en
      §11.2.2, `requirements.md` §7.2.9 y ADR-007 §5, no inferido.

---

# 27. Criterio de no completitud

La fase debe marcarse como:

```text
PARTIALLY COMPLETED
```

si ocurre cualquiera de los siguientes casos:

- existe una funcionalidad crítica sin pruebas;
- existen tests fallando relacionados con la implementación;
- el modelo de usuario no cumple ADR-001;
- la separación User/Person/Profile no cumple ADR-002;
- las invitaciones no cumplen ADR-003;
- la autorización depende solamente del rol;
- existe acceso a objetos no autorizados;
- las operaciones críticas dejan estados parciales;
- existen migraciones que no pueden ejecutarse desde una base limpia;
- se incorporaron funcionalidades fuera del alcance de Fase 1 sin justificación;
- existe documentación que contradice una decisión ya aceptada en un ADR (por ejemplo,
  describir el registro de menor como pendiente cuando ADR-007 ya lo define e implementa, o
  usar `is_active` para `ResponsiblePatientRelationship` cuando el campo real es `status`);
- la política de cuenta propia (`User`) para el paciente adulto (§11.2.2, puntos 1-4 del
  subconjunto todavía abierto) sigue sin definirse.

**Estado actual de Fase 1: PARTIALLY COMPLETED** por el último punto — la arquitectura, el
código y los tests de todo lo ya implementado están completos y en verde (incluyendo el
registro de menor por responsable y la transición a régimen adulto, ADR-007, implementada
2026-09-08). `ResponsiblePatientRelationship.status` y `Patient.regime` ya resuelven
"¿tiene el responsable autorización vigente sobre este paciente?" sin ambigüedad y Fase 2
puede consumir ambos directamente. Lo único que falta para marcar Fase 1 como COMPLETADA es
no asumir por omisión ninguna política de cuenta propia del paciente adulto — esa decisión
sigue siendo del negocio, no del código, y debe tomarse explícitamente antes de que Fase 2 (o
una fase posterior) dependa de ella.

---

# 28. Reporte final obligatorio

Cuando termine la implementación, Claude Code debe presentar:

## Estado

```text
COMPLETADA
```

o

```text
PARTIALLY COMPLETED
```

## Resumen ejecutivo

Descripción breve de lo implementado.

## Requerimientos completados

Relacionar cada bloque funcional con su implementación.

## Arquitectura

Indicar apps, modelos principales y relaciones.

## Base de datos

Indicar migraciones, constraints e índices importantes.

## Seguridad

Describir autenticación, autorización, seguridad de invitaciones y protección de acceso a objetos.

## Testing

Indicar tests ejecutados y resultado.

## Archivos modificados

Enumerar los archivos principales creados o modificados.

## Decisiones técnicas

Describir decisiones que no sean obvias o que hayan requerido interpretación.

## Pendientes

Enumerar únicamente pendientes reales.

## Preparación para Fase 2

Explicar brevemente cómo la arquitectura deja preparado el terreno para:

- disponibilidad;
- citas;
- conflictos;
- bloqueo temporal;
- check-in.

No implementar esas funcionalidades.

---

# 29. Reglas de comportamiento para Claude Code

Durante la implementación:

1. Leer primero la documentación aplicable.
2. Inspeccionar el código existente.
3. No asumir que el repositorio está vacío.
4. Reutilizar componentes existentes cuando sean correctos.
5. Implementar de forma incremental.
6. Mantener cambios pequeños y verificables.
7. Ejecutar tests frecuentemente.
8. No ocultar errores.
9. No introducir funcionalidades de fases posteriores.
10. No modificar decisiones arquitectónicas silenciosamente.
11. Documentar decisiones nuevas mediante ADR cuando corresponda.
12. Mantener el código consistente con Django y PostgreSQL.
13. Priorizar seguridad e integridad.
14. No declarar terminado algo que no esté probado.

---

# 30. Resultado esperado

Al finalizar la Fase 1, TeCuidoApp debe disponer de unas fundaciones sobre las que las fases posteriores puedan construir sin rehacer el núcleo de identidad y relaciones.

El resultado conceptual esperado es:

```text
                         ┌───────────────┐
                         │     User      │
                         │ Auth / Email  │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │    Person     │
                         └───────┬───────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
          ┌────────┐        ┌─────────┐        ┌────────────┐
          │ Doctor │        │ Patient │        │ Responsible│
          └───┬────┘        └────┬────┘        └──────┬─────┘
              │                  │                    │
              │                  │                    │
              └───────┐   ┌──────┘                    │
                      │   │                           │
                      ▼   ▼                           ▼
                 DoctorPatient              ResponsiblePatient
                   Relationship                 Relationship
                      │
                      │
                      ▼
                   Patient

             Doctor ───── DoctorClinic ───── Clinic

Doctor ─────── Invitation ─────── Prospect
                     │
                     ▼
              User/Person/Patient
```

La siguiente fase debe poder construirse sobre estas fundaciones sin rediseñar la identidad, el modelo de perfiles ni los límites de las apps.

---

# 31. Contrato Fase 1 → Fase 2

Antes de comenzar Fase 2 (Agenda), deben darse por ciertas estas invariantes — Fase 2 no debe
reconstruir ni reinterpretar lo siguiente, solo consumirlo:

**Identidad**
- Existe una única fuente de identidad personal (`Person`).
- `User` no contiene información clínica ni específica de un perfil.
- `Person` puede existir sin `User` (paciente menor sin cuenta propia).

**Paciente**
- `Patient` es la entidad canónica del paciente.
- La edad se deriva siempre de `birth_date`, nunca de un campo persistente ni de una tarea
  programada.

**Médico**
- `Doctor` es la entidad canónica del médico.
- Su disponibilidad y agenda son de Fase 2 — no existen en el modelo base de Fase 1.

**Responsable**
- `ResponsiblePatientRelationship.status` distingue `PENDING`, `ACTIVE`, `INACTIVE`.
- Únicamente `ACTIVE` concede autorización operativa. Esto es exactamente lo que Fase 2 debe
  consultar para decidir si un responsable puede solicitar/gestionar una cita en nombre de un
  paciente — no debe inventarse un mecanismo paralelo.

**Relaciones médico-paciente**
- El acceso depende de una relación explícita y vigente, nunca únicamente del rol global.

**Consultorio**
- `Clinic` es la entidad canónica; agenda y disponibilidad pertenecen a Fase 2.

**Régimen del paciente** — `requirements.md` §7.2.8, `docs/adr/ADR-007-...md` §3.8 addendum:
`Patient.regime` (`MINOR`/`ADULT`, implementado) determina si el paciente sigue bajo
autorización de responsables o ya la tiene sobre sí mismo; es independiente de
`Person.is_minor` (edad cronológica). La transición (`transition_patient_to_adult`) es
atómica, la ejecuta un médico con relación activa, es irreversible y desactiva en bloque toda
`ResponsiblePatientRelationship` `ACTIVE` del paciente. Fase 2 debe tratar `Patient.regime`
igual que cualquier otro campo de autorización del dominio, sin mecanismo paralelo — en
particular, "¿tiene el responsable autorización vigente?" sigue respondiéndose únicamente con
`ResponsiblePatientRelationship.status == ACTIVE` (que la transición ya mantiene consistente),
no con una consulta directa a `regime`.

**Lo que Fase 2 NO puede asumir todavía** (§11.2.2, `requirements.md` §7.2.9,
`docs/adr/ADR-007-responsible-initiated-minor-registration.md` §5): cómo/cuándo un paciente
adulto obtiene cuenta propia (`User`), la verificación de identidad para ese trámite, cómo
revoca o reautoriza un responsable por su propia cuenta una vez que tenga esa cuenta, y qué
ocurre cuando una coincidencia por CURP no tiene ningún responsable activo a quien pedir
aprobación. Si una funcionalidad de Fase 2 depende de resolver alguno de estos puntos, la
decisión debe tomarse explícitamente primero — documentada en `requirements.md` y, si cambia
una decisión ya aceptada, en una ADR — no inferirse dentro del código de Fase 2.

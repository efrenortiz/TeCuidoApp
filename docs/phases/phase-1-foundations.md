# TeCuidoApp — Phase 1 Foundations

**Estado:** Planned
**Fase:** 1 — Fundaciones
**Stack:** Python + Django + PostgreSQL
**Fuente funcional:** `requirements.md`
**Guía arquitectónica:** `docs/architecture.md`
**ADRs aplicables:** `docs/adr/ADR-001-custom-user-model.md` a `docs/adr/ADR-006-database-integrity-and-transactions.md`

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
- invitaciones.

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

Implementar:

```text
ResponsiblePatientRelationship
```

Debe permitir:

- múltiples pacientes por responsable;
- estado activo/inactivo;
- tipo de relación;
- crecimiento futuro de reglas de autorización.

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

La Fase 1 se considera **COMPLETADA** únicamente cuando se cumplen todos los puntos aplicables:

## Proyecto

- [ ] El proyecto inicia correctamente.
- [ ] Django `check` pasa.
- [ ] PostgreSQL está correctamente integrado.
- [ ] La configuración se puede reproducir.

## Identidad

- [ ] Existe Custom User Model.
- [ ] `AUTH_USER_MODEL` está configurado.
- [ ] El email es único.
- [ ] User está separado de Person.
- [ ] Las aplicaciones no importan directamente el User estándar de Django.

## Roles

- [ ] Existen los roles iniciales.
- [ ] La autorización funcional está implementada.
- [ ] El sistema puede evolucionar hacia múltiples perfiles.

## Perfiles

- [ ] Doctor existe.
- [ ] Patient existe.
- [ ] Responsible existe.
- [ ] Person está correctamente integrado.

## Relaciones

- [ ] Doctor-Patient está modelado explícitamente.
- [ ] Responsible-Patient está modelado explícitamente.
- [ ] Doctor-Clinic está modelado explícitamente.
- [ ] Las relaciones permiten las cardinalidades requeridas.

## Authentication

- [ ] Login funciona.
- [ ] Logout funciona.
- [ ] Cambio de password funciona.
- [ ] Recuperación de password funciona.
- [ ] Activación/desactivación funciona.
- [ ] Verificación de email funciona.

## Invitations

- [ ] Invitation existe.
- [ ] Token seguro.
- [ ] Expiración.
- [ ] Uso único.
- [ ] Cancelación/invalidez cuando corresponda.
- [ ] Médico generador identificado.
- [ ] El médico no puede ser alterado por el cliente.
- [ ] Registro completo genera el paciente correctamente.
- [ ] Se crea la relación médico-paciente correspondiente.
- [ ] La operación es atómica.
- [ ] Existe protección contra consumo concurrente.

## Seguridad

- [ ] La autorización se valida en servidor.
- [ ] Se aplica deny-by-default.
- [ ] No existen secretos hardcodeados.
- [ ] No se registran tokens sensibles en logs.
- [ ] Los objetos no pueden accederse simplemente modificando un ID.

## Base de datos

- [ ] Foreign keys correctas.
- [ ] Unique constraints apropiados.
- [ ] Check constraints donde corresponda.
- [ ] Índices apropiados.
- [ ] Migraciones correctas.
- [ ] Transacciones implementadas donde corresponda.

## Testing

- [ ] Tests de autenticación pasan.
- [ ] Tests de permisos pasan.
- [ ] Tests de perfiles pasan.
- [ ] Tests de relaciones pasan.
- [ ] Tests de invitaciones pasan.
- [ ] Tests negativos de autorización pasan.
- [ ] No existen regresiones conocidas.

## Documentación

- [ ] README actualizado cuando corresponde.
- [ ] Configuración documentada.
- [ ] Decisiones arquitectónicas documentadas.

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
- se incorporaron funcionalidades fuera del alcance de Fase 1 sin justificación.

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

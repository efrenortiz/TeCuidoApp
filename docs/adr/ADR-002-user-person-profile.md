# ADR-002 — User / Person / Functional Profile Separation

**Estado:** Accepted  
**Fecha:** 2026-08-31  
**Decisores:** Equipo de desarrollo  
**Área:** Arquitectura / Identidad / Modelo de dominio

---

## 1. Contexto

TeCuidoApp debe soportar diferentes tipos de participantes:

- Administrador
- Médico
- Paciente
- Responsable

La especificación funcional establece que debe existir un modelo central para autenticación y autorización, pero que debe mantenerse una separación clara entre:

```text
Usuario / autenticación
Persona
Paciente
Responsable
Médico
```

También establece que la arquitectura debe permitir asociar a un mismo usuario diferentes perfiles funcionales de acuerdo con necesidades futuras.

Esta decisión complementa `ADR-001-custom-user-model.md`, donde se definió que TeCuidoApp utilizará un Custom User Model como base de autenticación.

El problema ahora es definir **qué información pertenece a la cuenta (`User`) y qué información pertenece a la persona y a sus perfiles funcionales**.

---

# 2. Problema

Una solución simplificada podría almacenar toda la información dentro de `User`:

```text
User
├── email
├── password
├── first_name
├── last_name
├── birth_date
├── phone
├── address
├── medical_data
├── doctor_data
└── responsible_data
```

Esta aproximación provoca un acoplamiento excesivo entre:

- autenticación;
- identidad personal;
- dominio médico;
- relaciones funcionales.

Además, obligaría a que un usuario tenga una estructura rígida y dificultaría soportar correctamente casos como:

- una persona que todavía no tenga una cuenta;
- una persona que tenga diferentes funciones dentro del sistema;
- un paciente que también sea responsable de otro paciente;
- un médico que posteriormente tenga más de una función administrativa;
- datos personales compartidos por diferentes perfiles.

TeCuidoApp necesita una arquitectura que permita crecer sin convertir `User` en un objeto monolítico.

---

# 3. Decisión

Se establece una separación explícita entre:

```text
User
   ↓
Person
   ↓
Functional Profile(s)
```

Los conceptos serán:

### `User`

Representa la **cuenta de autenticación**.

### `Person`

Representa a la **persona física y sus datos de identidad/contacto**.

### Perfiles funcionales

Representan el papel que esa persona desempeña dentro de TeCuidoApp.

Perfiles iniciales:

```text
Doctor
Patient
Responsible
```

El administrador podrá representarse mediante mecanismos de autorización/rol asociados al usuario, según la implementación definida en `accounts`.

---

# 4. Modelo conceptual

La arquitectura conceptual será:

```text
┌──────────────────────┐
│         User         │
│──────────────────────│
│ authentication       │
│ email                │
│ password             │
│ account state        │
└──────────┬───────────┘
           │
           │ 1:1
           ▼
┌──────────────────────┐
│       Person         │
│──────────────────────│
│ identity             │
│ name                 │
│ birth date           │
│ contact              │
│ address              │
└──────────┬───────────┘
           │
           │
      ┌────┼───────────────┐
      │    │               │
      ▼    ▼               ▼
┌────────┐ ┌─────────┐ ┌─────────────┐
│ Doctor │ │ Patient │ │ Responsible │
└────────┘ └─────────┘ └─────────────┘
```

La relación exacta entre `User` y `Person` deberá ser definida como obligatoria u opcional según el estado funcional de cada flujo.

---

# 5. Responsabilidad de `User`

`User` debe contener únicamente información relacionada con la cuenta y autenticación.

Ejemplos conceptuales:

```text
email
password
is_active
is_staff
date_joined
last_login
email_verified
```

No debe utilizarse como contenedor de:

- dirección;
- información clínica;
- antecedentes;
- relación médico-paciente;
- relación responsable-paciente;
- información profesional específica.

El principio es:

> `User` responde quién puede autenticarse; `Person` responde quién es la persona.

---

# 6. Responsabilidad de `Person`

`Person` representa los datos personales que describen a una persona.

Puede contener información común como:

- nombre(s);
- apellido paterno;
- apellido materno;
- fecha de nacimiento;
- información de contacto;
- domicilio.

Cuando un dato pertenece conceptualmente a la persona y no al mecanismo de autenticación, debe evaluarse primero su ubicación en `Person`.

No se deben duplicar esos datos dentro de cada perfil funcional sin una necesidad específica.

---

# 7. Responsabilidad de `Doctor`

`Doctor` representa el perfil funcional de una persona como médico.

Conceptualmente:

```text
Person
   ↓
Doctor
```

El perfil de médico podrá posteriormente relacionarse con:

- consultorios;
- pacientes;
- disponibilidad;
- agenda;
- consultas.

Estas funcionalidades se incorporarán en las fases correspondientes.

El modelo de `Doctor` no debe absorber la información de autenticación de `User`.

---

# 8. Responsabilidad de `Patient`

`Patient` representa el perfil funcional de una persona como paciente.

Conceptualmente:

```text
Person
   ↓
Patient
```

Los datos específicos del paciente deben residir en `Patient` o en entidades de dominio relacionadas, según la naturaleza del dato.

Ejemplos de información específica del dominio de paciente:

- condición de paciente;
- información médica relevante definida para el perfil;
- relaciones con médicos;
- relaciones con responsables.

La información clínica histórica que se genere posteriormente no debe convertirse en campos sobrescribibles dentro de `Patient`.

---

# 9. Responsabilidad de `Responsible`

`Responsible` representa el perfil funcional de una persona como responsable de uno o más pacientes.

Conceptualmente:

```text
Person
   ↓
Responsible
```

Un responsable no representa necesariamente una persona diferente desde el punto de vista de identidad.

La misma persona puede, conceptualmente, tener más de una función.

Por ejemplo:

```text
Person
 ├── Patient
 └── Responsible
```

La arquitectura no debe impedir este escenario.

---

# 10. Principio "Persona primero"

Cuando se necesite modelar una persona que participa en diferentes partes del sistema, la identidad personal debe mantenerse centralizada.

Ejemplo:

```text
Person #123
   │
   ├── Patient #456
   │
   └── Responsible #789
```

Ambos perfiles representan a la misma persona.

No se deben crear dos entidades `Person` independientes solamente porque la persona tenga dos funciones.

Esto evita:

- duplicación;
- inconsistencias;
- datos personales desactualizados;
- problemas de reconciliación.

---

# 11. User ≠ Person

Debe mantenerse explícitamente la diferencia conceptual:

### User

Cuenta técnica.

### Person

Entidad de identidad personal.

Un `User` puede existir sin que necesariamente tenga todos los perfiles funcionales.

De la misma forma, una `Person` puede existir antes de contar con una cuenta de usuario, cuando el flujo de negocio lo requiera.

Este punto es especialmente relevante para escenarios de:

- prospectos;
- personas registradas por un médico;
- pacientes creados como parte de otros flujos.

La implementación concreta de esos escenarios deberá respetar los requisitos funcionales de cada fase.

---

# 12. Relación User / Person

La relación entre `User` y `Person` se modelará de forma que una cuenta de autenticación corresponda a una identidad personal, evitando duplicar datos personales en `User`.

La relación esperada es:

```text
User 1 ─────── 1 Person
```

como relación conceptual.

Sin embargo, el sistema podrá permitir estados intermedios cuando un flujo específico lo requiera.

No debe asumirse que todo objeto `Person` debe tener inmediatamente una cuenta autenticable.

---

# 13. Creación de perfiles

Los perfiles funcionales deben crearse de manera explícita.

Ejemplo:

```text
User
  ↓
Person
  ↓
Patient
```

y para un médico:

```text
User
  ↓
Person
  ↓
Doctor
```

No se debe representar un perfil únicamente mediante un campo genérico como:

```python
user.role = "PATIENT"
```

si el perfil requiere información propia del dominio.

Los roles/permisos y los perfiles funcionales cumplen responsabilidades distintas.

---

# 14. Roles vs. perfiles

Se establece la siguiente distinción:

## Rol

Determina principalmente:

> ¿Qué capacidades tiene el usuario?

Ejemplo:

```text
DOCTOR
PATIENT
RESPONSIBLE
ADMINISTRATOR
```

## Perfil

Determina:

> ¿Qué entidad funcional representa a esa persona dentro del dominio?

Ejemplo:

```text
Doctor
Patient
Responsible
```

No deben considerarse necesariamente equivalentes.

La implementación puede utilizar Django Groups/Permissions para autorización mientras mantiene entidades de dominio explícitas para los perfiles.

---

# 15. Caso: Patient + Responsible

El modelo debe permitir:

```text
User
  ↓
Person
  ├── Patient
  └── Responsible
```

Esto es importante porque una misma persona podría ser:

- paciente;
- responsable de un menor;
- responsable de otro paciente.

La arquitectura no debe obligar a crear cuentas separadas para cada función.

---

# 16. Caso: Prospecto

La especificación determina que un prospecto no es considerado paciente hasta completar correctamente su registro.

Por lo tanto, el modelo no debe asumir:

```text
Invitation = Patient
```

La invitación representa un proceso previo al establecimiento del perfil de paciente.

El flujo deberá ser conceptualmente:

```text
Invitation
    ↓
Prospect
    ↓
Registration
    ↓
User
    ↓
Person
    ↓
Patient
```

La implementación puede adaptar este flujo de acuerdo con la solución técnica concreta, pero debe respetar la regla funcional.

---

# 17. Datos de contacto

Los datos de contacto deben ubicarse según su naturaleza.

### Datos de autenticación

Pertenecen a `User`:

```text
authentication email
```

### Datos personales

Pertenecen a `Person`:

```text
phone
alternative phone
address
```

### Datos específicos del dominio

Pertenecen al perfil o a sus entidades relacionadas.

Debe evitarse almacenar el mismo concepto en tres lugares diferentes.

---

# 18. Datos clínicos

Los datos clínicos no deben utilizar `User` como almacenamiento.

Tampoco deben convertirse indiscriminadamente en atributos permanentes de `Person`.

La información clínica específica deberá ubicarse posteriormente en las entidades clínicas correspondientes.

Por ejemplo, las consultas médicas deberán mantenerse como registros independientes e históricos.

Esto es coherente con el principio funcional de que la información clínica debe conservar el historial de lo ocurrido y no simplemente sobrescribirse.

---

# 19. Integridad

Las relaciones deben utilizar claves foráneas y constraints apropiados.

Especialmente:

```text
User → Person
Person → Doctor
Person → Patient
Person → Responsible
```

deben mantener integridad referencial.

Las restricciones importantes deben ser respaldadas por PostgreSQL cuando corresponda.

---

# 20. Servicios de dominio

La creación coordinada de identidad y perfiles debe utilizar servicios cuando la operación implique múltiples entidades.

Ejemplo conceptual:

```text
RegistrationService
    ↓
create User
    ↓
create Person
    ↓
create Patient
```

La operación debe ser transaccional cuando corresponda.

No se recomienda colocar toda esta coordinación dentro de una view.

---

# 21. Ventajas

Esta decisión proporciona:

### Separación de responsabilidades

Autenticación, identidad y dominio permanecen desacoplados.

### Reutilización

Una persona puede tener múltiples funciones.

### Menor duplicación

La información personal se mantiene en un único lugar.

### Evolución

Se pueden incorporar nuevos perfiles sin modificar el núcleo de autenticación.

### Integridad

Se reducen inconsistencias entre registros duplicados.

### Escalabilidad funcional

Las fases futuras pueden extender los perfiles sin modificar la arquitectura base.

---

# 22. Desventajas

Esta arquitectura implica:

- más modelos;
- más relaciones;
- mayor complejidad inicial;
- necesidad de comprender correctamente la separación entre rol y perfil;
- necesidad de servicios para flujos complejos.

Estas desventajas son aceptables porque el dominio de TeCuidoApp requiere múltiples perfiles y relaciones.

---

# 23. Alternativas consideradas

## Alternativa A — Todo dentro de User

```text
User
├── personal data
├── doctor data
├── patient data
└── responsible data
```

**Decisión:** Rejected.

Razones:

- alto acoplamiento;
- duplicación conceptual;
- poca flexibilidad;
- difícil evolución;
- mezcla autenticación con dominio.

---

## Alternativa B — Un modelo diferente por tipo de usuario con autenticación independiente

```text
DoctorUser
PatientUser
ResponsibleUser
AdminUser
```

**Decisión:** Rejected.

Contradice el requerimiento de utilizar un modelo central de usuario y evita que un mismo usuario pueda tener múltiples perfiles.

---

## Alternativa C — Un User + role y todos los datos en modelos separados sin Person

```text
User
 ├── Doctor
 ├── Patient
 └── Responsible
```

**Decisión:** Rejected.

Aunque evita sobrecargar `User`, no proporciona una representación centralizada de la identidad personal y puede provocar duplicación de datos comunes.

---

## Alternativa D — User + Person + perfiles funcionales

```text
User
 ↓
Person
 ↓
Doctor / Patient / Responsible
```

**Decisión:** Accepted.

Es la alternativa que mejor representa las responsabilidades definidas para TeCuidoApp.

---

# 24. Reglas de implementación

Todo código nuevo debe respetar:

### Regla 1

`User` representa autenticación y cuenta.

### Regla 2

`Person` representa identidad personal.

### Regla 3

`Doctor`, `Patient` y `Responsible` representan perfiles funcionales.

### Regla 4

No duplicar datos personales sin una razón explícita.

### Regla 5

No utilizar roles como sustituto automático de entidades de dominio.

### Regla 6

Un usuario puede evolucionar hacia múltiples perfiles funcionales.

### Regla 7

La información clínica debe residir en entidades clínicas, no en `User`.

### Regla 8

Las relaciones importantes deben modelarse explícitamente.

### Regla 9

Las operaciones de creación de identidad compuesta deben ser transaccionales cuando corresponda.

### Regla 10

No introducir una segunda arquitectura de identidad en una app específica.

---

# 25. Impacto sobre las Django apps

La separación recomendada es:

```text
accounts/
    User
    Person
    Invitation

doctors/
    Doctor

patients/
    Patient
    DoctorPatientRelationship
    ResponsiblePatientRelationship

clinics/
    Clinic
    DoctorClinic
```

Los nombres definitivos pueden adaptarse a la implementación.

La regla importante es mantener clara la responsabilidad de cada entidad.

---

# 26. Evolución futura

La arquitectura permitirá agregar perfiles futuros sin modificar el modelo central de autenticación.

Conceptualmente:

```text
Person
 ├── Doctor
 ├── Patient
 ├── Responsible
 └── FutureProfile
```

Esto permite que el dominio evolucione sin convertir `User` en una entidad monolítica.

---

# 27. Relación con ADR-001

`ADR-001-custom-user-model.md` establece:

> TeCuidoApp utilizará un Custom User Model como núcleo de autenticación.

Este ADR establece:

> El Custom User Model no será utilizado como contenedor de identidad personal ni de perfiles funcionales.

Por tanto:

```text
ADR-001
Custom User Model
        +
ADR-002
User / Person / Profile Separation
        ↓
Arquitectura de identidad
```

Ambas decisiones deben considerarse conjuntamente.

---

# 28. Criterios de aceptación

La decisión se considera correctamente implementada cuando:

- [ ] Existe un Custom User Model.
- [ ] `User` está enfocado en autenticación/cuenta.
- [ ] Existe una entidad `Person` claramente separada.
- [ ] `Doctor` es un perfil funcional.
- [ ] `Patient` es un perfil funcional.
- [ ] `Responsible` es un perfil funcional.
- [ ] Los datos personales no se duplican innecesariamente.
- [ ] Un usuario puede evolucionar a múltiples perfiles.
- [ ] Patient y Responsible pueden coexistir para una misma persona.
- [ ] Las relaciones importantes están modeladas explícitamente.
- [ ] Los datos clínicos no se almacenan dentro de `User`.
- [ ] Las operaciones compuestas utilizan transacciones cuando corresponde.
- [ ] Los tests cubren la creación y asociación correcta de perfiles.

---

# 29. Estado

**Accepted**

Esta decisión forma parte de la arquitectura base de TeCuidoApp y deberá mantenerse salvo que un ADR posterior la sustituya explícitamente.

---

# 30. Referencias

- `requirements.md`
- `docs/architecture.md`
- `docs/adr/ADR-001-custom-user-model.md`
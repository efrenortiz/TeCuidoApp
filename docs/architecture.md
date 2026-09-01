# TeCuidoApp — Architecture

**Estado:** Propuesta inicial  
**Versión:** 1.0  
**Fase:** Fase 1 — Fundaciones  
**Stack:** Python + Django + PostgreSQL  
**Documento de referencia funcional:** `requirements.md`

---

## 1. Propósito

Este documento define la arquitectura técnica de **TeCuidoApp** y establece los principios que deben seguirse durante el desarrollo de la aplicación.

Su objetivo es proporcionar una base común para:

- desarrollo;
- revisión de código;
- diseño de nuevos módulos;
- evolución del sistema;
- incorporación de nuevas fases;
- control de decisiones arquitectónicas.

La arquitectura debe favorecer:

- seguridad;
- privacidad;
- mantenibilidad;
- modularidad;
- integridad de datos;
- trazabilidad;
- extensibilidad.

La especificación funcional de `requirements.md` permanece como la fuente principal de verdad del comportamiento funcional del sistema.

---

# 2. Contexto del sistema

TeCuidoApp es una aplicación Web para la gestión integral de un consultorio médico especializado en gineco-obstetricia.

El sistema contempla tres grandes áreas:

1. Gestión administrativa.
2. Gestión clínica y agenda.
3. Portal de pacientes y responsables.

La arquitectura debe permitir desarrollar estas áreas progresivamente sin convertirlas en sistemas independientes.

La aplicación debe mantenerse como **un único proyecto Django** con múltiples Django apps internas.

---

# 3. Stack tecnológico

## Backend

- Python
- Django
- Django REST Framework cuando sea necesario
- PostgreSQL

## Procesamiento asíncrono

- Redis
- Celery

Redis y Celery se utilizarán cuando exista una necesidad real de procesamiento asíncrono o tareas programadas.

## Archivos

Los documentos clínicos deberán almacenarse en un medio privado.

Los archivos médicos nunca deben depender de una URL pública para su protección.

## Documentos

La aplicación generará documentos PDF para determinados documentos clínicos en fases posteriores.

---

# 4. Principios arquitectónicos

## 4.1 Un solo proyecto Django

TeCuidoApp debe mantenerse dentro de un único proyecto Django.

No se crearán proyectos Django independientes para:

- pacientes;
- médicos;
- CareRequest;
- agenda;
- documentos;
- autenticación.

Las funcionalidades se organizarán mediante aplicaciones Django internas.

---

## 4.2 Separación de responsabilidades

Cada app debe representar una responsabilidad funcional clara.

La separación por apps no debe convertirse en una fragmentación artificial.

Una app puede depender de otra cuando exista una relación de dominio justificada, pero deben evitarse dependencias circulares.

---

## 4.3 Identidad separada del dominio

Debe mantenerse una separación clara entre:

```text
Authentication
     ↓
User
     ↓
Person
     ↓
Functional Profile
```

Los perfiles funcionales iniciales son:

```text
Doctor
Patient
Responsible
Administrator
```

No deben existir sistemas de autenticación independientes por rol.

---

## 4.4 Seguridad desde el diseño

La aplicación manejará información médica altamente sensible.

Por tanto, la seguridad debe formar parte de la arquitectura y no agregarse posteriormente.

Toda funcionalidad debe considerar:

- autenticación;
- autorización;
- protección de objetos;
- validación de entrada;
- protección de información sensible;
- almacenamiento privado;
- trazabilidad cuando corresponda.

---

## 4.5 Historial y trazabilidad

La información clínica debe diseñarse como información histórica.

No debe asumirse que un registro clínico puede simplemente sobrescribirse.

Las futuras funcionalidades clínicas deben permitir identificar:

- qué ocurrió;
- cuándo ocurrió;
- quién lo registró;
- qué información se emitió;
- qué cambios posteriores existieron.

---

## 4.6 Baja lógica

Los usuarios y registros clínicos importantes no deben eliminarse físicamente como operación rutinaria.

Cuando corresponda, debe utilizarse:

```text
active = false
```

o un mecanismo equivalente.

---

# 5. Arquitectura lógica

La arquitectura lógica propuesta es:

```text
                        ┌────────────────────┐
                        │      Browser       │
                        │ Médico / Paciente  │
                        │ Responsable / Admin│
                        └─────────┬──────────┘
                                  │
                                  ▼
                        ┌────────────────────┐
                        │      Django       │
                        │   Web / API       │
                        └─────────┬──────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
      ┌────────────┐       ┌────────────┐      ┌────────────┐
      │ Accounts   │       │  Patients  │      │  Doctors   │
      └────────────┘       └────────────┘      └────────────┘
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                                  ▼
                        ┌────────────────────┐
                        │    PostgreSQL      │
                        └────────────────────┘

                         Fases posteriores
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
      ┌────────────┐       ┌────────────┐      ┌────────────┐
      │Appointments│       │Medical     │      │Documents   │
      │            │       │Records     │      │            │
      └────────────┘       └────────────┘      └────────────┘
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                                  ▼
                           Redis / Celery
```

---

# 6. Django Apps

La arquitectura propuesta inicialmente contempla:

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

No todas las apps deben implementarse durante la Fase 1.

La aplicación debe evolucionar progresivamente.

---

# 7. Responsabilidad de cada app

## 7.1 `config`

Responsabilidad:

- configuración Django;
- URLs principales;
- ASGI/WSGI;
- configuración de infraestructura;
- configuración por entorno.

No debe contener lógica de negocio.

---

## 7.2 `accounts`

Responsabilidad:

- autenticación;
- usuario;
- credenciales;
- verificación de email;
- recuperación de contraseña;
- cambio de contraseña;
- activación/desactivación;
- roles;
- identidad común.

Modelos previstos:

```text
User
Person
Invitation
```

Las entidades de dominio como `Doctor`, `Patient` y `Responsible` no deben convertirse en mecanismos independientes de autenticación.

---

## 7.3 `patients`

Responsabilidad:

- información del paciente;
- información médica general que pertenezca al perfil del paciente;
- relaciones con médicos;
- relaciones con responsables.

Modelos previstos:

```text
Patient
DoctorPatientRelationship
ResponsiblePatientRelationship
```

Los nombres definitivos pueden ajustarse durante la implementación.

---

## 7.4 `doctors`

Responsabilidad:

- perfil de médico;
- información profesional;
- relación funcional con la aplicación.

Modelo principal:

```text
Doctor
```

Las funcionalidades de agenda y disponibilidad pertenecen a fases posteriores.

---

## 7.5 `clinics`

Responsabilidad:

- consultorios;
- información administrativa;
- relación médico-consultorio.

Modelos previstos:

```text
Clinic
DoctorClinic
```

---

## 7.6 `appointments`

Responsabilidad futura:

- disponibilidad;
- citas;
- conflictos;
- confirmaciones;
- cancelaciones;
- reprogramaciones;
- check-in;
- sala de espera.

**No forma parte de la Fase 1.**

---

## 7.7 `care_requests`

Responsabilidad futura:

- solicitudes de atención;
- archivos relacionados;
- estados;
- conversión a cita.

Debe permanecer como Django app dentro del mismo proyecto.

**No forma parte de la Fase 1.**

---

## 7.8 `medical_records`

Responsabilidad futura:

- historia clínica;
- consultas;
- evolución;
- diagnósticos;
- tratamientos;
- pronóstico;
- resumen clínico;
- alertas.

**No forma parte de la Fase 1.**

---

## 7.9 `prescriptions`

Responsabilidad futura:

- recetas;
- medicamentos;
- indicaciones;
- PDF;
- historial y versiones.

---

## 7.10 `clinical_documents`

Responsabilidad futura:

- documentos clínicos;
- archivos privados;
- autorización de acceso;
- versionado.

---

## 7.11 `notifications`

Responsabilidad futura:

- email;
- recordatorios;
- notificaciones;
- proveedores externos.

La lógica de negocio no debe depender directamente de un proveedor concreto.

---

## 7.12 `audit`

Responsabilidad futura:

- auditoría;
- trazabilidad;
- acciones sensibles;
- acceso a información clínica.

---

# 8. Modelo de identidad

La identidad del sistema se estructura de la siguiente forma:

```text
User
 │
 └── Person
       ├── Doctor
       ├── Patient
       └── Responsible
```

La relación conceptual debe permitir:

- un usuario sin perfil clínico;
- un usuario con un perfil funcional;
- eventualmente un usuario con múltiples perfiles.

No debe asumirse que:

```text
1 User = 1 Role
```

como restricción permanente de arquitectura.

---

# 9. User

`User` representa la cuenta de autenticación.

Responsabilidades:

- autenticación;
- contraseña;
- email;
- verificación;
- estado activo/inactivo;
- información técnica de acceso.

El email de autenticación debe ser único.

No debe almacenar información clínica.

---

# 10. Person

`Person` representa la identidad personal.

Puede contener información común como:

- nombre;
- apellido paterno;
- apellido materno;
- fecha de nacimiento;
- información de contacto;
- domicilio.

La intención es evitar duplicar información personal en cada perfil funcional.

---

# 11. Doctor

`Doctor` representa el perfil funcional de médico.

Relación conceptual:

```text
User
  ↓
Person
  ↓
Doctor
```

El médico podrá posteriormente tener:

- agenda;
- disponibilidad;
- pacientes;
- consultorios;
- consultas clínicas.

Estas capacidades se agregarán progresivamente.

---

# 12. Patient

`Patient` representa el perfil de paciente.

Un paciente puede estar asociado con uno o varios médicos.

Esto debe modelarse mediante una relación explícita.

No utilizar:

```text
patient.doctor_id
```

como único vínculo.

---

# 13. Responsible

`Responsible` representa una persona que puede actuar en nombre de uno o más pacientes.

Un responsable puede administrar múltiples pacientes.

La relación con cada paciente debe ser explícita.

---

# 14. ResponsiblePatientRelationship

Debe existir una entidad de relación:

```text
ResponsiblePatientRelationship
```

Conceptualmente:

```text
Responsible ────────< ResponsiblePatientRelationship >──────── Patient
```

La relación debe poder almacenar al menos:

- responsable;
- paciente;
- tipo de relación;
- estado activo/inactivo.

Tipos iniciales:

```text
MADRE
PADRE
TUTOR_LEGAL
FAMILIAR
CUIDADOR
OTRO
```

Debe mantenerse abierta la posibilidad de agregar reglas de autorización posteriormente.

---

# 15. DoctorPatientRelationship

Debe existir una relación explícita entre médico y paciente.

Conceptualmente:

```text
Doctor ────────< DoctorPatientRelationship >──────── Patient
```

Esto permite soportar:

- médico tratante;
- médico sustituto;
- otro médico del consultorio.

La relación no debe imponer que un paciente tenga únicamente un médico.

---

# 16. Clinic

`Clinic` representa un consultorio.

Información inicial:

- nombre;
- descripción;
- dirección;
- teléfono;
- activo/inactivo.

La aplicación debe permitir relacionar médicos con consultorios.

---

# 17. DoctorClinic

La relación:

```text
Doctor ↔ Clinic
```

debe poder representarse explícitamente.

Conceptualmente:

```text
Doctor ────────< DoctorClinic >──────── Clinic
```

Esto permitirá posteriormente asociar disponibilidad y citas a una combinación específica de médico + consultorio.

---

# 18. Invitation

`Invitation` representa una invitación de registro enviada por un médico.

Debe contener conceptualmente:

```text
Invitation
├── doctor
├── email
├── token
├── expires_at
├── created_at
├── used_at
├── status
└── ...
```

Estados sugeridos:

```text
PENDING
USED
EXPIRED
CANCELLED
```

El token debe ser seguro y de un solo uso.

---

# 19. Flujo de invitación

Flujo esperado:

```text
Doctor
   │
   ▼
Create Invitation
   │
   ▼
Generate Secure Token
   │
   ▼
Send Email
   │
   ▼
Prospecto
   │
   ▼
Open Invitation
   │
   ▼
Complete Registration
   │
   ▼
Verify Email
   │
   ▼
Create User / Person / Patient
   │
   ▼
Create DoctorPatientRelationship
   │
   ▼
Invalidate Invitation
```

El sistema debe impedir que una invitación utilizada vuelva a utilizarse.

---

# 20. Autenticación

Debe utilizarse Django Authentication como base.

Capacidades iniciales:

- login;
- logout;
- password reset;
- password change;
- email verification;
- activación/desactivación.

No debe existir autenticación independiente para cada tipo de usuario.

---

# 21. Autorización

La autenticación responde:

> ¿Quién es el usuario?

La autorización responde:

> ¿Qué puede hacer este usuario y sobre qué objeto?

Ambos conceptos deben mantenerse separados.

El acceso debe validarse del lado servidor.

Nunca se debe asumir que esconder un botón o una URL proporciona seguridad.

---

# 22. Control de acceso a objetos

La arquitectura debe prepararse para permisos a nivel de objeto.

Ejemplos:

```text
Patient A
```

no debe ser visible para:

```text
Patient B
```

Un responsable debe consultar únicamente los pacientes con los que tiene una relación autorizada.

Un médico debe consultar únicamente los pacientes que estén dentro de las reglas de relación y acceso establecidas.

---

# 23. Baja lógica

Las entidades importantes podrán contar con estado activo/inactivo.

Ejemplos:

```text
User.is_active
Doctor.is_active
Patient.is_active
Responsible.is_active
Clinic.is_active
```

La elección exacta de campos puede variar dependiendo del modelo.

No debe utilizarse eliminación física como mecanismo normal para información relevante.

---

# 24. PostgreSQL

PostgreSQL es la base de datos principal.

La integridad debe apoyarse tanto en Django como en restricciones de base de datos cuando corresponda.

Ejemplos:

- unique;
- foreign keys;
- indexes;
- check constraints;
- integridad referencial.

La base de datos debe ser considerada una parte activa del modelo de dominio.

---

# 25. Transacciones

Las operaciones que creen o modifiquen múltiples entidades relacionadas deben utilizar transacciones apropiadamente.

Ejemplo:

```text
Completar invitación
    ↓
crear User
    ↓
crear Person
    ↓
crear Patient
    ↓
crear relación DoctorPatient
    ↓
marcar Invitation como USED
```

Estas operaciones deben realizarse de forma atómica.

Si una parte falla, no debe quedar una estructura parcialmente creada.

---

# 26. Servicios y lógica de negocio

La lógica de negocio que coordine múltiples entidades debe poder vivir en una capa de servicios.

Ejemplo:

```text
accounts/services/invitations.py
```

podría encargarse de:

```text
create_invitation()
accept_invitation()
verify_invitation()
```

Las views no deben contener procesos de negocio complejos.

Los modelos tampoco deben convertirse en contenedores de toda la lógica de aplicación.

---

# 27. Views

Las views deben encargarse principalmente de:

- recibir solicitudes;
- validar entrada;
- invocar lógica de aplicación;
- devolver respuesta.

Evitar:

```text
View
 ├── 200 líneas de lógica
 ├── múltiples consultas
 ├── creación manual de varias entidades
 └── reglas de negocio complejas
```

Cuando el flujo sea complejo, utilizar servicios.

---

# 28. API

Cuando se utilice Django REST Framework:

```text
Request
   ↓
URL
   ↓
View / ViewSet
   ↓
Serializer
   ↓
Service
   ↓
Model
   ↓
PostgreSQL
```

Los serializers no deben convertirse en contenedores de toda la lógica de negocio.

---

# 29. Seguridad de archivos

Aunque la gestión completa de documentos pertenece a fases posteriores, la arquitectura debe respetar desde el inicio el principio:

```text
Medical files = private
```

Nunca deben utilizarse URLs públicas como mecanismo principal de seguridad.

El acceso futuro debe seguir:

```text
User
  ↓
Authentication
  ↓
Authorization
  ↓
Object permission
  ↓
File access
```

---

# 30. Configuración

La configuración debe separarse del código.

Información sensible:

- passwords;
- SECRET_KEY;
- credenciales;
- tokens;
- configuración SMTP;

debe residir en variables de entorno.

Debe existir:

```text
.env.example
```

sin secretos reales.

---

# 31. Entornos

La arquitectura debe contemplar al menos:

```text
development
test
production
```

No necesariamente deben existir tres proyectos completamente independientes.

La configuración debe poder variar por entorno.

---

# 32. Testing

Cada app debe poder probarse de forma aislada cuando sea posible.

Prioridades iniciales:

```text
accounts
patients
doctors
clinics
```

Debe existir cobertura especialmente para:

- autenticación;
- permisos;
- invitaciones;
- relaciones;
- integridad de datos.

---

# 33. Convenciones de código

Seguir:

- PEP 8;
- convenciones idiomáticas de Django;
- nombres explícitos;
- responsabilidades pequeñas;
- imports limpios;
- funciones testeables.

No introducir abstracciones solamente por anticipación.

La extensibilidad debe provenir principalmente de un dominio bien modelado y responsabilidades claras.

---

# 34. Dependencias

No agregar paquetes externos salvo que:

1. resuelvan una necesidad real;
2. exista una justificación técnica;
3. no exista una solución apropiada en Django/Python;
4. su incorporación sea consistente con la arquitectura.

La dependencia de terceros debe mantenerse controlada.

---

# 35. Evolución hacia Fase 2

La arquitectura de Fase 1 debe dejar preparado el sistema para:

```text
Doctor
   │
   ├── Clinic
   │
   ├── AvailabilityRule
   │
   ├── AvailabilityException
   │
   └── Appointment
```

Posteriormente las citas deberán depender de relaciones existentes de médico, paciente y consultorio.

La Fase 1 no implementa estas entidades.

---

# 36. Evolución hacia Gestión Clínica

Las entidades clínicas futuras deberán mantener el principio:

```text
Patient
   │
   ├── MedicalRecord
   ├── MedicalEncounter
   ├── ClinicalAlert
   ├── Prescription
   └── StudyOrder
```

Las consultas y registros clínicos deberán conservar historial.

No se debe construir un expediente como un único registro mutable que sobrescriba toda la información anterior.

---

# 37. Evolución hacia documentos

Posteriormente:

```text
Patient
   │
   ├── Appointment
   ├── MedicalEncounter
   ├── Prescription
   ├── StudyOrder
   └── ClinicalDocument
```

Los documentos deberán permanecer privados y protegidos por autorización.

---

# 38. Evolución hacia notificaciones

La arquitectura deberá permitir posteriormente:

```text
Business Logic
      │
      ▼
Notification Service
      │
      ├── Email
      ├── WhatsApp
      └── SMS
```

La lógica de negocio no debe depender directamente de un proveedor de transporte.

WhatsApp se encuentra fuera del alcance de la primera versión.

---

# 39. Funcionalidades fuera del alcance actual

No deben agregarse sin decisión explícita:

- WhatsApp;
- MFA/2FA;
- FHIR;
- facturación;
- pagos;
- inventario;
- farmacia;
- aseguradoras;
- videollamadas;
- aplicación móvil nativa;
- multi-clínica;
- firma electrónica avanzada;
- IA para diagnóstico;
- IA para prescripción;
- estadística clínica avanzada.

---

# 40. Reglas arquitectónicas obligatorias

Las siguientes reglas deben considerarse restricciones del sistema:

### Regla 1
Un único sistema de autenticación.

### Regla 2
El email del usuario es único.

### Regla 3
Los perfiles funcionales no sustituyen a `User`.

### Regla 4
Un paciente puede relacionarse con múltiples médicos.

### Regla 5
Un responsable puede relacionarse con múltiples pacientes.

### Regla 6
Las relaciones importantes deben representarse explícitamente.

### Regla 7
Las operaciones multi-entidad importantes deben ser atómicas.

### Regla 8
Los permisos deben validarse en servidor.

### Regla 9
La información sensible no debe protegerse únicamente mediante ocultamiento de URLs.

### Regla 10
La información clínica debe tratarse como histórica.

### Regla 11
Los registros importantes no deben eliminarse físicamente como operación rutinaria.

### Regla 12
Las funcionalidades futuras no deben implementarse anticipadamente sin requerimiento.

---

# 41. Decisiones arquitectónicas

Toda decisión importante que modifique significativamente la estructura del sistema debe documentarse.

Formato recomendado:

```text
## ADR-001 — Título

### Contexto

Descripción del problema.

### Decisión

Qué se decidió.

### Alternativas consideradas

Qué otras opciones se analizaron.

### Consecuencias

Beneficios y costos.

### Estado

Accepted / Superseded / Rejected
```

Las decisiones arquitectónicas históricas deben conservarse.

---

# 42. Definition of Done arquitectónico

La arquitectura de la Fase 1 puede considerarse estable cuando:

- existe un modelo central de usuario;
- identidad y perfiles están separados;
- los roles están definidos;
- paciente y médico tienen relaciones explícitas;
- responsable y paciente tienen una relación explícita;
- médico y consultorio tienen una relación explícita;
- invitaciones tienen seguridad y expiración;
- las operaciones críticas son transaccionales;
- los permisos se aplican en servidor;
- PostgreSQL mantiene integridad referencial;
- la estructura de Django está modularizada;
- existe documentación suficiente para continuar con Fase 2.

---

# 43. Regla para Claude Code

Claude Code debe considerar este documento como **guía arquitectónica**, mientras que `requirements.md` es la **fuente de verdad funcional**.

En caso de conflicto:

```text
requirements.md
        ↓
Architecture
        ↓
Implementation
```

La implementación debe adaptarse al requerimiento funcional, no al revés.

Claude Code no debe modificar una decisión arquitectónica importante silenciosamente.

Cuando sea necesario cambiarla debe:

1. identificar el problema;
2. explicar el impacto;
3. proponer la nueva decisión;
4. documentarla mediante un ADR.

---

# 44. Estado actual

### Fase 1

```text
[ ] Configuración
[ ] Accounts
[ ] User
[ ] Person
[ ] Roles
[ ] Authentication
[ ] Email verification
[ ] Password recovery
[ ] Doctor
[ ] Clinic
[ ] Patient
[ ] Responsible
[ ] Doctor-Patient relationship
[ ] Doctor-Clinic relationship
[ ] Responsible-Patient relationship
[ ] Invitations
[ ] Tests
[ ] Documentation
```

### Fases futuras

```text
Fase 2 — Agenda
Fase 3 — Gestión clínica
Fase 4 — Documentos
Fase 5 — CareRequest y operación
Fase 6 — Notificaciones y auditoría
```

---

# 45. Principio final

La arquitectura de TeCuidoApp debe optimizar para:

**seguridad + claridad del dominio + trazabilidad + evolución controlada**

y no para implementar el mayor número posible de funcionalidades desde el inicio.

Cada nueva fase debe construirse sobre las fundaciones existentes sin romper:

- identidad;
- autorización;
- integridad;
- historial;
- privacidad;
- separación de responsabilidades.
# ADR-004 — Role and Object Permissions

**Estado:** Accepted  
**Fecha:** 2026-08-31  
**Decisores:** Equipo de desarrollo  
**Área:** Seguridad / Autorización / Control de acceso

---

# 1. Contexto

TeCuidoApp tendrá diferentes tipos de usuarios:

- Administrador
- Médico
- Paciente
- Responsable

La especificación funcional establece que el sistema debe aplicar permisos:

- a nivel de funcionalidad;
- a nivel de objeto.

Además, define reglas concretas:

- un paciente solamente puede consultar su propia información;
- un responsable solamente puede consultar información de los pacientes que tiene autorizados;
- un médico puede consultar pacientes con los que tiene relación y de acuerdo con las reglas de acceso establecidas;
- el administrador tiene acceso global, sujeto a auditoría;
- la información clínica no debe exponerse mediante URLs directas sin autorización.

La arquitectura de identidad definida en:

```text
ADR-001-custom-user-model.md
ADR-002-user-person-profile.md
```

establece una separación entre:

```text
User
Person
Doctor
Patient
Responsible
```

Por tanto, la autorización no debe limitarse a determinar el rol del usuario.

También debe determinar si ese usuario tiene derecho a operar sobre **una instancia concreta de una entidad**.

---

# 2. Problema

Un sistema basado únicamente en roles permitiría escenarios como:

```text
if user.role == "DOCTOR":
    allow_patient_access()
```

Esto sería insuficiente.

Un médico podría entonces intentar acceder a cualquier paciente de la base de datos.

De igual manera:

```text
if user.role == "RESPONSIBLE":
    allow_patient_access()
```

permitiría potencialmente que un responsable consultara pacientes que no tiene autorizados.

Por tanto:

> Tener un rol válido no implica tener acceso a cualquier objeto perteneciente a ese dominio.

Se requiere un modelo de autorización de dos niveles:

```text
Role Permission
       +
Object Permission
```

---

# 3. Decisión

TeCuidoApp utilizará un modelo de autorización de dos capas:

```text
                 ┌─────────────────────┐
                 │        User         │
                 └──────────┬──────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ Role / Permission │
                  │ Functional access │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ Object Permission │
                  │ Record ownership  │
                  │ / relationship    │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │     Resource      │
                  └───────────────────┘
```

El acceso únicamente será concedido cuando ambas capas lo permitan.

Conceptualmente:

```text
Can user perform action?
        AND
Can user perform action on this object?
        =
        Access Granted
```

---

# 4. Diferencia entre autenticación y autorización

Debe mantenerse la separación:

### Autenticación

Responde:

> ¿Quién es el usuario?

### Autorización

Responde:

> ¿Qué puede hacer el usuario?

### Autorización a nivel de objeto

Responde:

> ¿Puede hacerlo sobre este registro específico?

Ejemplo:

```text
User: doctor@example.com
Role: DOCTOR

Action:
view patient

Patient:
Patient #123

Result:
Allowed
```

mientras:

```text
User: doctor@example.com
Role: DOCTOR

Action:
view patient

Patient:
Patient #987

Result:
Denied
```

si el paciente no pertenece a una relación autorizada.

---

# 5. Niveles de autorización

Se establecen tres niveles conceptuales:

## Nivel 1 — Autenticación

El usuario debe estar autenticado cuando la funcionalidad lo requiera.

```text
request.user.is_authenticated
```

## Nivel 2 — Permiso funcional

El usuario debe tener permiso para realizar la acción.

Ejemplos:

```text
view_patient
create_invitation
manage_clinic
```

## Nivel 3 — Permiso sobre objeto

El usuario debe tener acceso al objeto específico.

Ejemplo:

```text
can_view_patient(user, patient)
```

Las tres capas deben evaluarse cuando corresponda.

---

# 6. Principio de mínimo privilegio

El sistema debe aplicar el principio de:

> **Least Privilege**

Cada usuario debe tener únicamente los permisos necesarios para desempeñar su función.

No se debe asumir que:

```text
Doctor = acceso global
```

ni:

```text
Responsible = acceso a todos los patients
```

ni:

```text
Patient = acceso a cualquier información relacionada
```

Los permisos deben limitarse al contexto correspondiente.

---

# 7. Roles iniciales

Los roles funcionales iniciales son:

```text
ADMINISTRATOR
DOCTOR
PATIENT
RESPONSIBLE
```

Estos roles representan capacidades generales.

No deben utilizarse como sustituto de las relaciones del dominio.

---

# 8. Administrador

El administrador tendrá acceso global a la aplicación de acuerdo con los permisos definidos.

La especificación establece que puede administrar:

- usuarios;
- médicos;
- consultorios;
- relaciones médico-consultorio;
- configuraciones generales;
- información administrativa;
- auditoría.

El acceso del administrador a información clínica sensible debe quedar registrado en auditoría.

Por tanto:

```text
Administrator
    ↓
Global functional access
    +
    ↓
Audit when accessing sensitive clinical information
```

El rol administrativo no elimina la necesidad de auditoría.

---

# 9. Médico

El médico podrá acceder a pacientes de acuerdo con sus relaciones autorizadas.

Conceptualmente:

```text
Doctor
   │
   └── DoctorPatientRelationship
                 │
                 ▼
              Patient
```

No debe concederse acceso simplemente por:

```text
user.role == DOCTOR
```

La autorización debe considerar la relación entre médico y paciente.

La propia especificación determina que un paciente puede estar relacionado con múltiples médicos.

---

# 10. Paciente

Un paciente solamente puede consultar su propia información permitida.

Conceptualmente:

```text
Authenticated User
        ↓
Patient Profile
        ↓
Current Patient
```

La siguiente operación debe denegarse:

```text
GET /patients/999/
```

si `999` no corresponde al paciente autenticado y no existe una regla específica que conceda ese acceso.

Cambiar el identificador en la URL nunca debe ser suficiente para obtener otro paciente.

---

# 11. Responsable

Un responsable puede administrar uno o más pacientes a su cargo.

La autorización debe derivarse de:

```text
ResponsiblePatientRelationship
```

Conceptualmente:

```text
Responsible
    │
    └── ResponsiblePatientRelationship
                  │
                  ▼
               Patient
```

Si:

```text
Relationship(active=True)
```

y el tipo de acceso requerido está permitido, la operación puede autorizarse.

Si no existe una relación autorizada, el acceso debe rechazarse.

---

# 12. Relación como fuente de autorización

Las relaciones de dominio deben utilizarse como fuentes de autorización.

Ejemplos:

```text
DoctorPatientRelationship
ResponsiblePatientRelationship
DoctorClinic
```

No deben depender únicamente de roles globales.

Por ejemplo:

```text
Doctor A → Patient X
Doctor A → Patient Y

Doctor B → Patient Y
```

Entonces:

```text
Doctor A → Patient X = Allowed
Doctor A → Patient Y = Allowed
Doctor B → Patient X = Denied
Doctor B → Patient Y = Allowed
```

salvo que exista otra regla autorizada por el sistema.

---

# 13. Autorización en servidor

La autorización deberá validarse en el backend.

Nunca se considerará suficiente:

- ocultar botones;
- ocultar menús;
- desactivar controles mediante JavaScript;
- modificar la interfaz según rol;
- utilizar URLs no públicas;
- utilizar IDs difíciles de adivinar.

El servidor debe verificar cada operación protegida.

---

# 14. Object-Level Authorization

Las operaciones sobre entidades sensibles deben realizar una evaluación a nivel de objeto.

Conceptualmente:

```python
can_access_patient(user, patient)
```

debe responder:

```text
True / False
```

según:

- identidad;
- rol/permisos;
- relación;
- estado del objeto;
- reglas de negocio aplicables.

---

# 15. Política de autorización recomendada

La autorización puede expresarse conceptualmente como:

```text
ALLOW =
    authenticated
    AND functional_permission
    AND object_permission
```

Ejemplo:

```text
Patient
    view own profile
        =
    authenticated
    AND permission to view profile
    AND patient belongs to current user
```

Otro ejemplo:

```text
Responsible
    view patient
        =
    authenticated
    AND responsible permission
    AND active ResponsiblePatientRelationship exists
```

---

# 16. Deny by Default

La política general será:

> **Deny by default**

Cuando no exista una regla explícita que permita una operación, el acceso deberá denegarse.

No utilizar:

```text
"If no rule denies it, allow it"
```

La lógica debe ser:

```text
"If no rule allows it, deny it"
```

---

# 17. Ownership vs Relationship

El sistema no debe basar toda la autorización en ownership directo.

Algunas entidades son propiedad directa del usuario:

```text
User
  ↓
Patient
```

otras dependen de relaciones:

```text
Doctor
  ↓
DoctorPatientRelationship
  ↓
Patient
```

y otras pueden combinar:

```text
Responsible
  ↓
ResponsiblePatientRelationship
  ↓
Patient
```

La estrategia debe seleccionarse según el dominio de cada entidad.

---

# 18. Permisos de Django

La aplicación podrá utilizar los mecanismos nativos de Django para permisos funcionales:

- permissions;
- groups;
- decorators;
- mixins;
- permission checks.

Estos mecanismos deben utilizarse principalmente para responder:

> ¿Puede este usuario ejecutar esta funcionalidad?

No deben considerarse suficientes para responder:

> ¿Puede este usuario acceder a este objeto específico?

Para la segunda pregunta se requieren verificaciones a nivel de objeto.

---

# 19. Servicios de autorización

La lógica compleja de autorización deberá poder centralizarse en una capa reutilizable.

Ejemplo conceptual:

```text
patients/
    services/
        permissions.py
```

Funciones posibles:

```python
can_view_patient(user, patient)
can_edit_patient(user, patient)
can_view_patient_medical_data(user, patient)
```

Los nombres concretos pueden variar.

El propósito es evitar duplicar reglas de autorización en:

- views;
- templates;
- serializers;
- APIs;
- commands.

---

# 20. Evitar reglas duplicadas

No implementar la misma regla de seguridad en varios lugares de forma independiente.

Ejemplo incorrecto:

```text
View:
    if doctor == patient.doctor:
        allow

Serializer:
    if doctor == patient.doctor:
        allow

Template:
    if doctor == patient.doctor:
        show
```

Esto podría provocar que las reglas evolucionen de forma inconsistente.

La lógica central de autorización debe poder reutilizarse.

---

# 21. Templates

Los templates pueden ocultar o mostrar controles según permisos para mejorar UX.

Sin embargo:

```text
Template visibility ≠ Security
```

Un usuario que no vea el botón debe seguir recibiendo una respuesta de autorización denegada si intenta invocar directamente la operación.

---

# 22. APIs

Para endpoints protegidos:

```text
Request
   ↓
Authentication
   ↓
Functional Permission
   ↓
Object Permission
   ↓
Business Logic
```

La view o ViewSet no debe confiar en que el objeto solicitado pertenece al usuario.

Debe comprobarlo explícitamente.

---

# 23. Querysets seguros

Cuando sea posible, el acceso debe reducirse desde la consulta.

Ejemplo conceptual:

```python
Patient.objects.filter(
    doctorpatientrelationship__doctor=doctor
)
```

en lugar de:

```python
patient = Patient.objects.get(pk=patient_id)

if can_view_patient(...):
    ...
```

cuando ambas alternativas sean funcionalmente equivalentes.

Esto permite reducir el riesgo de exponer objetos fuera del conjunto autorizado.

Sin embargo, el filtrado de queryset no sustituye automáticamente todos los checks de autorización en operaciones individuales.

---

# 24. URLs e identificadores

Los identificadores internos pueden utilizarse para localizar recursos, pero nunca deben considerarse mecanismos de autorización.

Incorrecto:

```text
"El paciente no puede adivinar el ID"
```

Correcto:

```text
"El paciente puede conocer el ID, pero el servidor
comprueba si tiene autorización"
```

La seguridad no debe depender de la dificultad de adivinar un identificador.

---

# 25. Información clínica

La información clínica requiere especial protección.

Cuando se implementen fases clínicas, el acceso deberá considerar como mínimo:

```text
User
   ↓
Role / Functional Permission
   ↓
Relationship / Object Permission
   ↓
Clinical Resource
```

La autorización a un objeto `Patient` no necesariamente implica automáticamente acceso indiscriminado a todos los recursos relacionados.

Las reglas de cada recurso clínico deberán definirse conforme a su contexto.

---

# 26. Acceso del administrador a información sensible

El administrador tiene acceso global según sus permisos, pero los accesos administrativos a información clínica sensible deben registrarse en auditoría.

Esto significa que:

```text
Administrator
    ↓
Allowed
    +
Audit Event
```

El sistema no debe interpretar auditoría como una alternativa a autorización.

Son mecanismos diferentes:

```text
Authorization = Can I?
Audit = What did I do?
```

---

# 27. Estados de las relaciones

Cuando una relación de autorización tenga estado:

```text
active = false
```

no debe utilizarse para conceder acceso.

Ejemplo:

```text
ResponsiblePatientRelationship
active = False
```

debe producir:

```text
Access = Denied
```

salvo una regla explícita que indique lo contrario.

---

# 28. Baja lógica y autorización

La desactivación de una entidad debe considerarse durante la autorización.

Ejemplos:

```text
Patient inactive
Doctor inactive
Responsible inactive
Relationship inactive
```

No debe suponerse que una relación histórica continúa otorgando acceso operativo.

La implementación deberá distinguir entre:

- existencia histórica;
- acceso operativo actual.

---

# 29. Separación entre autorización y auditoría

Esta ADR define autorización.

La auditoría transversal será definida con mayor detalle en:

```text
docs/adr/ADR-XXX-audit.md
```

El sistema debe mantener la distinción:

```text
Authorization
    =
    decision to allow/deny

Audit
    =
    record of relevant actions
```

La autorización no debe ser implementada únicamente mediante el sistema de auditoría.

---

# 30. Seguridad contra IDOR / BOLA

La arquitectura debe prevenir vulnerabilidades del tipo:

```text
Insecure Direct Object Reference
```

o equivalentes de acceso a objetos por identificadores modificados.

Ejemplo:

```text
GET /patients/123/
```

no implica:

```text
"user requested it => user may see it"
```

Debe ejecutarse una verificación explícita.

El mismo principio aplica para:

- pacientes;
- relaciones;
- citas;
- consultas;
- recetas;
- documentos;
- CareRequests;
- cualquier entidad sensible futura.

---

# 31. Principio de autorización por dominio

La autorización debe basarse en relaciones y significado del dominio.

No implementar reglas arbitrarias como:

```python
if user.id < patient.id:
    allow
```

o:

```python
if patient.email == user.email:
    allow
```

salvo que el requisito específico defina esa relación.

La autorización debe representar reglas reales del negocio.

---

# 32. Alternativas consideradas

## Alternativa A — Autorización únicamente por roles

```text
DOCTOR → all patients
PATIENT → own features
RESPONSIBLE → all responsible features
```

**Decisión:** Rejected.

No permite controlar correctamente acceso por objeto.

Contradice los requisitos de acceso definidos en el alcance.

---

## Alternativa B — Autorización únicamente desde templates/frontend

**Decisión:** Rejected.

El cliente no es una frontera de seguridad.

---

## Alternativa C — Ocultamiento de URLs

**Decisión:** Rejected.

Una URL no es un mecanismo de autorización.

La especificación indica explícitamente que la información clínica no debe exponerse mediante URLs directas sin autorización.

---

## Alternativa D — Roles + object-level authorization

**Decisión:** Accepted.

Proporciona:

- control funcional;
- control por objeto;
- mínimo privilegio;
- capacidad de representar relaciones del dominio;
- escalabilidad para funcionalidades clínicas futuras.

---

# 33. Consecuencias positivas

Esta decisión proporciona:

- mayor seguridad;
- menor riesgo de exposición accidental;
- soporte para múltiples médicos por paciente;
- soporte para múltiples pacientes por responsable;
- separación entre rol y relación;
- protección contra manipulación de IDs;
- arquitectura preparada para documentos y datos clínicos;
- reutilización de políticas de autorización.

---

# 34. Consecuencias negativas

Implica:

- más complejidad de implementación;
- necesidad de construir políticas por entidad;
- mayor cantidad de tests;
- necesidad de revisar autorización en cada nueva funcionalidad;
- más trabajo que una solución puramente basada en roles.

Este costo se considera necesario debido a la sensibilidad de la información y a las reglas del dominio.

---

# 35. Reglas de implementación

### Regla 1

Nunca utilizar el rol como única prueba de acceso a un objeto sensible.

### Regla 2

Toda operación protegida debe autorizarse en servidor.

### Regla 3

Los permisos funcionales y los permisos de objeto son conceptos diferentes.

### Regla 4

Utilizar relaciones del dominio como fuentes de autorización cuando corresponda.

### Regla 5

Aplicar `Deny by Default`.

### Regla 6

No utilizar IDs o URLs como mecanismo de seguridad.

### Regla 7

Los templates nunca constituyen una frontera de seguridad.

### Regla 8

Las APIs deben validar autorización antes de devolver información.

### Regla 9

Las relaciones inactivas no deben conceder acceso operativo.

### Regla 10

La eliminación lógica no debe eliminar automáticamente la existencia histórica, pero sí puede afectar el acceso operativo.

### Regla 11

Las reglas complejas de autorización deben centralizarse y reutilizarse.

### Regla 12

Toda nueva entidad sensible debe definir explícitamente su política de autorización.

---

# 36. Matriz inicial de autorización

La siguiente matriz representa la política conceptual de Fase 1.

| Funcionalidad | Admin | Doctor | Patient | Responsible |
|---|---|---|---|---|
| Gestionar usuarios | Sí | No | No | No |
| Gestionar médicos | Sí | Propio | No | No |
| Gestionar consultorios | Sí | No | No | No |
| Crear invitaciones | No* | Sí | No | No |
| Consultar propio perfil | Sí | Sí | Sí | Sí |
| Consultar paciente propio | Sí | Según relación | Sí, propio | Según relación |
| Crear paciente | Según permisos | Según flujo | No directamente | Según flujo autorizado |
| Gestionar responsable | Según permisos | Según relación | Propio | Propio |
| Gestionar relación médico-paciente | Sí | Según permisos | No | No |

\* La capacidad exacta del administrador sobre invitaciones no está definida explícitamente en el alcance y no debe asumirse sin una decisión funcional adicional.

Esta matriz es una guía arquitectónica inicial; los permisos definitivos deben corresponder a los requerimientos funcionales de cada módulo.

---

# 37. Ejemplos de políticas

## Patient — Own profile

```text
User
  ↓
Patient profile belongs to user
  ↓
ALLOW
```

## Patient — Other patient

```text
User
  ↓
Patient profile does not belong to user
  ↓
DENY
```

## Responsible — Authorized patient

```text
User
  ↓
Responsible
  ↓
Active ResponsiblePatientRelationship
  ↓
Patient
  ↓
ALLOW
```

## Responsible — Unrelated patient

```text
User
  ↓
Responsible
  ↓
No authorized relationship
  ↓
DENY
```

## Doctor — Related patient

```text
User
  ↓
Doctor
  ↓
Active DoctorPatientRelationship
  ↓
Patient
  ↓
ALLOW
```

## Doctor — Unrelated patient

```text
User
  ↓
Doctor
  ↓
No authorized relationship
  ↓
DENY
```

---

# 38. Testing

Toda política de autorización relevante debe contar con pruebas automatizadas.

Como mínimo:

### Patient

- paciente puede consultar su información;
- paciente no puede consultar otro paciente;
- paciente no puede modificar información no permitida.

### Responsible

- responsable puede consultar paciente autorizado;
- responsable puede gestionar múltiples pacientes autorizados;
- responsable no puede consultar paciente no relacionado;
- relación inactiva no concede acceso.

### Doctor

- médico puede consultar paciente relacionado;
- médico no puede consultar paciente sin relación;
- relación eliminada/desactivada bloquea acceso cuando corresponda.

### Administrator

- administrador puede realizar operaciones administrativas autorizadas;
- acceso sensible genera el mecanismo de auditoría correspondiente cuando dicha auditoría esté implementada.

### API

- acceso no autenticado → rechazo;
- acceso autenticado sin permiso → rechazo;
- acceso por objeto no autorizado → rechazo;
- acceso autorizado → respuesta correcta.

---

# 39. Criterios de aceptación

Esta decisión se considera correctamente implementada cuando:

- [ ] Existen permisos funcionales.
- [ ] Existe autorización a nivel de objeto.
- [ ] Los roles no son la única frontera de seguridad.
- [ ] Pacientes solamente pueden acceder a su información permitida.
- [ ] Responsables solamente pueden acceder a pacientes autorizados.
- [ ] Médicos solamente pueden acceder a pacientes dentro de sus relaciones permitidas.
- [ ] El administrador mantiene acceso global según sus permisos.
- [ ] El acceso administrativo sensible puede ser auditado.
- [ ] Modificar un ID en una URL no permite acceder a otro objeto.
- [ ] La autorización se valida del lado servidor.
- [ ] Existen tests negativos de autorización.
- [ ] Las relaciones inactivas no conceden acceso.
- [ ] Las nuevas entidades sensibles deberán definir explícitamente sus reglas de acceso.

---

# 40. Relación con otros ADR

Esta decisión depende de:

```text
ADR-001
Custom User Model
```

que define la identidad central de autenticación.

También depende de:

```text
ADR-002
User / Person / Functional Profiles
```

que define los perfiles funcionales.

Y complementa:

```text
ADR-003
Invitation Security
```

porque una invitación debe respetar la identidad y autorización establecidas en este ADR.

Conceptualmente:

```text
ADR-001
    ↓
Identity
    ↓
ADR-002
    ↓
Profiles
    ↓
ADR-004
    ↓
Authorization
    ↓
Domain Relationships
```

---

# 41. Evolución hacia fases futuras

La estrategia deberá extenderse a:

### Fase 2

```text
Doctor
  ↓
Clinic
  ↓
Availability
  ↓
Appointment
```

La autorización deberá considerar quién puede:

- consultar;
- crear;
- modificar;
- cancelar;
- reprogramar.

### Fase 3

```text
Patient
  ↓
MedicalRecord
  ↓
MedicalEncounter
  ↓
ClinicalAlert
```

La autorización clínica deberá ser especialmente estricta.

### Fase 4

```text
ClinicalDocument
```

El acceso deberá combinar:

```text
Authentication
+
Functional Permission
+
Object Permission
+
Document Permission
```

### Fase 5

```text
CareRequest
Dashboard
Waiting Room
```

Cada recurso deberá definir su propia política.

---

# 42. Principio final

La seguridad de TeCuidoApp no debe depender de que el usuario:

- no conozca un ID;
- no encuentre una URL;
- no vea un botón;
- no manipule el frontend.

La seguridad debe depender de una decisión explícita del servidor:

```text
Who are you?
      ↓
What can you do?
      ↓
Can you do it to this object?
      ↓
ALLOW / DENY
```

Este principio deberá aplicarse a todas las funcionalidades presentes y futuras de TeCuidoApp.

---

# 43. Estado

**Accepted**

Esta decisión forma parte de la arquitectura de seguridad base de TeCuidoApp.

Cualquier modificación significativa deberá documentarse mediante una actualización de este ADR o un nuevo ADR.
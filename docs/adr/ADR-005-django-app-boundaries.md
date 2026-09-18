# ADR-005 — Django App Boundaries

**Estado:** Accepted  
**Fecha:** 2026-08-31  
**Decisores:** Equipo de desarrollo  
**Área:** Arquitectura / Modularidad / Django

---

# 1. Contexto

TeCuidoApp se implementará como un único proyecto Django compuesto por varias aplicaciones internas.

La especificación propone inicialmente una separación funcional:

```text
accounts
patients
doctors
clinics
appointments
care_requests
medical_records
prescriptions
clinical_documents
notifications
audit
```

La especificación aclara que:

- la aplicación debe mantenerse dentro de un único proyecto Django;
- las funcionalidades pueden separarse en aplicaciones Django internas;
- los nombres propuestos pueden ajustarse durante el diseño técnico;
- la separación debe utilizarse para organizar responsabilidades y no para crear sistemas independientes;
- las relaciones entre apps deben ser claras;
- deben evitarse dependencias circulares;
- el modelo de datos debe priorizar integridad referencial, claridad, facilidad de consulta, historial y seguridad.

En la Fase 1 se implementarán principalmente:

```text
accounts
patients
doctors
clinics
```

y posteriormente se incorporarán:

```text
appointments
care_requests
medical_records
prescriptions
clinical_documents
notifications
audit
```

La ausencia de límites claros puede provocar que una app termine siendo dependiente de demasiadas otras, que los modelos se dupliquen o que la lógica de negocio se disperse.

Por ello se establece esta decisión arquitectónica.

---

# 2. Problema

Django permite técnicamente colocar cualquier modelo o lógica dentro de cualquier app.

Por ejemplo, sería posible colocar:

```text
Patient
Doctor
Clinic
Appointment
Prescription
```

dentro de una sola app.

También sería posible repartir responsabilidades arbitrariamente hasta producir:

```text
patients → doctors → clinics → accounts → patients
```

generando dependencias circulares.

El problema no es únicamente organizativo.

Los límites incorrectos pueden provocar:

- acoplamiento excesivo;
- migraciones difíciles;
- dependencias circulares;
- lógica duplicada;
- dificultad para testear;
- modelos con responsabilidades excesivas;
- dificultad para incorporar nuevas fases;
- cambios aparentemente pequeños con alto impacto.

---

# 3. Decisión

TeCuidoApp utilizará **Django apps organizadas por responsabilidad funcional del dominio**.

Las apps no representan servicios independientes ni microservicios.

Todas forman parte del mismo proyecto Django y comparten:

- configuración;
- base de datos;
- proceso de aplicación;
- sistema de autenticación;
- infraestructura.

La división sirve para establecer **límites de responsabilidad y dependencias**.

---

# 4. Principio fundamental

Cada app debe responder principalmente a una pregunta:

> **¿Qué parte del dominio es responsable de mantener esta app?**

Una entidad debe pertenecer a la app que representa su responsabilidad principal.

No se debe mover una entidad a otra app solamente porque sea utilizada desde ella.

---

# 5. Mapa de aplicaciones

La arquitectura objetivo será:

```text
TeCuido/
│
├── config/
│
├── accounts/
├── patients/
├── doctors/
├── clinics/
│
├── appointments/
├── care_requests/
├── medical_records/
├── prescriptions/
├── clinical_documents/
├── notifications/
└── audit/
```

No todas las apps deben implementarse desde la Fase 1.

---

# 6. `config`

## Responsabilidad

Configuración global del proyecto Django.

Incluye:

- settings;
- URLs raíz;
- ASGI;
- WSGI;
- configuración por entorno.

## No debe contener

- modelos de negocio;
- reglas de pacientes;
- reglas de médicos;
- lógica clínica;
- lógica de agenda.

## Regla

`config` configura el sistema; no representa el dominio.

---

# 7. `accounts`

## Responsabilidad

Identidad y autenticación.

Debe contener:

- `User`;
- `Person` cuando así lo determine la arquitectura de identidad;
- autenticación;
- verificación de email;
- recuperación de contraseña;
- cambio de contraseña;
- activación/desactivación;
- mecanismos de roles/permisos de identidad;
- invitaciones cuando el flujo pertenezca a identidad/registro.

Esta decisión es consistente con `ADR-001`, `ADR-002` y `ADR-003`.

## Ejemplos

```text
User
Person
Invitation
```

## No debe contener

- agenda;
- citas;
- historia clínica;
- recetas;
- documentos clínicos;
- relaciones de negocio que no pertenezcan a identidad/registro.

---

# 8. `patients`

## Responsabilidad

Dominio del paciente.

Incluye:

- `Patient`;
- relaciones paciente-médico;
- relaciones responsable-paciente;
- información propia del perfil paciente.

Ejemplos:

```text
Patient
DoctorPatientRelationship
ResponsiblePatientRelationship
```

## No debe contener

- credenciales;
- contraseñas;
- login;
- disponibilidad del médico;
- definición de consultorios;
- lógica de agenda;
- recetas;
- consultas clínicas históricas.

---

# 9. `doctors`

## Responsabilidad

Dominio del médico.

Incluye:

- `Doctor`;
- información profesional propia del médico;
- capacidades específicas del perfil médico.

## No debe contener

- autenticación;
- password;
- gestión de usuarios;
- definición de pacientes;
- definición de consultorios;
- citas;
- historia clínica.

La relación médico-paciente puede pertenecer a `patients` porque representa principalmente una relación sobre el paciente, siempre que esa decisión se mantenga consistente.

---

# 10. `clinics`

## Responsabilidad

Dominio administrativo del consultorio.

Incluye:

```text
Clinic
DoctorClinic
```

Debe encargarse de:

- alta de consultorios;
- modificación;
- activación/desactivación;
- información administrativa;
- relaciones médico-consultorio.

## No debe contener

- autenticación;
- pacientes;
- historia clínica;
- consultas;
- recetas;
- notificaciones.

---

# 11. `appointments`

## Responsabilidad (Fase 2 — contrato completo en `docs/phases/phase-2-agenda.md`, aprobado
2026-09-09)

Agenda y citas.

Incluye:

```text
Availability   -- por fecha concreta; sin AvailabilityRule ni AvailabilityException recurrentes
Hold           -- bloqueo temporal de 15 minutos; no es un estado de Appointment
Appointment    -- SCHEDULED / IN_CONSULTATION / COMPLETED / CANCELLED / NO_SHOW
```

y:

- creación **directa** de citas (sin solicitud previa ni confirmación posterior);
- cancelación;
- reprogramación;
- inicio de consulta;
- estados;
- prevención de conflictos;
- bloqueo temporal.

`appointments` **no incluye** check-in ni sala de espera — no existen en el modelo de Fase 2
(no hay un estado `WAITING`), y **no depende de `care_requests`** (§12): es una app completa y
funcional sin que `care_requests` exista todavía.

La agenda se construirá utilizando las relaciones existentes entre:

```text
Doctor
Clinic
Patient
```

pero la lógica de citas debe permanecer dentro de `appointments`.

---

# 12. `care_requests`

## Responsabilidad futura

Solicitudes de atención.

Incluye:

```text
CareRequest
```

La especificación establece explícitamente que `CareRequest` debe ser una Django app dentro del mismo proyecto y no un proyecto independiente.

La app será responsable de:

- creación — con médico, fecha y hora solicitados de forma explícita, no una solicitud abierta
  (`requirements.md` §12, decisión de dominio 2026-09-14: sin aprobación ni revisión médica);
- estados: `NUEVA → CONVERTIDA` (confirmado, `requirements.md` §12.1) — sin estados de
  revisión/atención/cierre manual;
- archivos asociados — reutilizan `ClinicalDocument`/almacenamiento privado de Fase 4, tipos y
  límites confirmados en `requirements.md` §12.2;
- actualización;
- validación contra las reglas de Agenda de Fase 2 y creación **automática e inmediata** de la
  `Appointment` correspondiente cuando esas reglas se cumplen — un origen **alternativo y
  opcional** de `Appointment`, nunca un requisito previo (`requirements.md` §12).

La creación de una cita no debe convertir `appointments` en propietario del modelo `CareRequest`.
Tampoco a la inversa: `appointments` (Fase 2) queda completa y funcional sin que `care_requests`
exista — la dependencia, cuando exista, corre en un solo sentido: `care_requests` (Fase 5)
podrá invocar un caso de uso de `appointments` para crear una cita, nunca al revés.

---

# 13. `medical_records`

## Responsabilidad futura

Dominio clínico.

Incluye, según la evolución:

```text
MedicalRecord
MedicalEncounter
ClinicalAlert
```

y lógica relacionada con:

- historia clínica;
- consultas;
- evolución;
- diagnósticos;
- tratamientos;
- pronóstico;
- resumen clínico.

La información clínica debe conservar historial y no tratarse como un único registro mutable. Esto está establecido como principio fundamental en el alcance.

---

# 14. `prescriptions`

## Responsabilidad futura

Recetas médicas.

Incluye:

```text
Prescription
PrescriptionItem
```

y lógica para:

- emisión;
- medicamentos;
- indicaciones;
- dosis;
- frecuencia;
- duración;
- observaciones;
- generación de documento relacionado cuando corresponda.

La receta estará relacionada con una consulta médica, pero la responsabilidad del modelo `Prescription` permanecerá en esta app.

---

# 15. `clinical_documents`

## Responsabilidad futura

Documentos clínicos.

Incluye:

```text
ClinicalDocument
```

y responsabilidades relacionadas con:

- archivos;
- almacenamiento privado;
- metadatos;
- relaciones clínicas;
- autorización de acceso;
- versionado.

La especificación requiere que los documentos médicos se almacenen de forma privada y que toda descarga sea autorizada en servidor.

---

# 16. `notifications`

## Responsabilidad futura

Infraestructura y dominio de notificaciones.

Incluye:

- notificaciones;
- email;
- recordatorios;
- proveedores de transporte.

No debe acoplar la lógica de negocio directamente a un proveedor específico.

Arquitectura conceptual:

```text
Business Event
      ↓
Notification Service
      ↓
Transport
 ├── Email
 ├── WhatsApp
 └── SMS
```

WhatsApp queda fuera del alcance de la primera versión.

---

# 17. `audit`

## Responsabilidad futura

Auditoría transversal.

Incluye:

```text
AuditLog
```

y mecanismos para registrar operaciones relevantes.

La aplicación debe poder registrar eventos como:

- login;
- acceso a expediente;
- creación/modificación de consulta;
- creación/modificación de receta;
- generación/descarga de documentos;
- cambios de permisos;
- desactivación de usuarios.

La especificación exige especial atención a operaciones sobre información clínica sensible.

---

# 18. Regla de ownership

La regla principal será:

> La app que "posee" una entidad es responsable de su definición, reglas de dominio y ciclo de vida principal.

Ejemplo:

```text
Patient
   owner → patients

Doctor
   owner → doctors

Clinic
   owner → clinics

Appointment
   owner → appointments
```

Otra app puede utilizar la entidad, pero no debe redefinirla.

---

# 19. Relaciones entre apps

Las relaciones entre aplicaciones son permitidas cuando representan relaciones reales del dominio.

Ejemplo:

```text
patients
   └── Patient
          │
          └── DoctorPatientRelationship
                    │
                    └── Doctor
                           ↑
                        doctors
```

Esto no significa que `patients` sea dueña del modelo `Doctor`.

La relación únicamente utiliza la entidad `Doctor`.

---

# 20. Dirección de dependencias

La arquitectura debe evitar dependencias circulares.

Como principio general:

```text
config
  ↓
domain apps
```

y las aplicaciones de infraestructura pueden depender de las apps de dominio cuando exista una necesidad real.

Sin embargo, la dependencia exacta podrá variar según la funcionalidad.

Lo importante es evitar:

```text
A → B → C → A
```

sin una razón arquitectónica explícita.

---

# 21. Dependencias iniciales de Fase 1

La dependencia conceptual inicial será aproximadamente:

```text
accounts
   ↑
   │
patients ───────→ doctors
   │                  │
   │                  │
   └──────────────→ clinics
```

Esta representación es conceptual, no obliga a que `patients` importe directamente todo el módulo `doctors`.

Las relaciones deben utilizar las referencias apropiadas de Django.

---

# 22. No utilizar imports circulares para relaciones

No se deben resolver relaciones del dominio mediante imports cruzados innecesarios.

Por ejemplo, evitar estructuras donde:

```python
# doctors/models.py
from patients.models import Patient

# patients/models.py
from doctors.models import Doctor
```

sea necesario únicamente para definir relaciones.

Las relaciones deben modelarse de manera compatible con Django y con una dependencia mínima.

---

# 23. Foreign Keys entre apps

Es válido que un modelo tenga relaciones hacia otra app.

Ejemplo conceptual:

```python
doctor = models.ForeignKey(
    "doctors.Doctor",
    ...
)
```

cuando corresponda.

La app consumidora no se convierte por ello en propietaria del modelo referenciado.

---

# 24. Relaciones Many-to-Many

Cuando una relación Many-to-Many tenga comportamiento o atributos propios, debe utilizarse un modelo explícito.

Ejemplos:

```text
Doctor ↔ Patient
Doctor ↔ Clinic
Responsible ↔ Patient
```

donde la relación tiene significado de dominio.

No utilizar un `ManyToManyField` simple cuando sea necesario almacenar:

- estado;
- tipo de relación;
- fechas;
- permisos;
- información adicional.

Esto es especialmente relevante para:

```text
DoctorPatientRelationship
ResponsiblePatientRelationship
DoctorClinic
```

---

# 25. Servicios entre apps

Cuando una operación involucre varias apps, la coordinación puede realizarse mediante una capa de servicios.

Ejemplo:

```text
appointments
    ↓
BookingService
    ├── Patient
    ├── Doctor
    └── Clinic
```

El objetivo es evitar trasladar toda la lógica de coordinación a los modelos de una sola app.

La app responsable del caso de uso debe coordinar la operación, mientras cada app mantiene sus propias responsabilidades.

---

# 26. No duplicar modelos

Nunca crear una segunda representación de una entidad existente solamente para evitar importar otra app.

Incorrecto:

```text
patients.Doctor
doctors.Doctor
```

Debe existir una sola entidad canónica.

Correcto:

```text
doctors.Doctor
```

y las demás apps deben referenciarla.

---

# 27. No duplicar información

Evitar almacenar copias innecesarias.

Por ejemplo:

```text
Patient.doctor_name
Doctor.patient_name
```

en lugar de utilizar las relaciones reales del dominio.

Debe preferirse:

```text
Doctor
    ↓
DoctorPatientRelationship
    ↓
Patient
```

La información derivada no debe almacenarse como fuente primaria salvo que exista una razón técnica documentada.

---

# 28. Cross-App Queries

Una app puede consultar entidades de otra app cuando esa consulta forma parte legítima de su caso de uso.

Sin embargo:

- debe evitarse acoplamiento excesivo;
- deben reutilizarse servicios/selectors cuando la consulta sea compleja;
- no debe accederse arbitrariamente a detalles internos de otra app.

La interfaz entre apps debe permanecer clara.

---

# 29. Services vs Models

Los modelos deben mantener:

- estructura de datos;
- invariantes propias;
- comportamiento estrechamente ligado a la entidad.

Los servicios deben utilizarse para operaciones que:

- coordinan varias entidades;
- cruzan múltiples apps;
- requieren transacciones;
- representan un caso de uso.

Ejemplo:

```text
AcceptInvitationService
```

puede coordinar:

```text
accounts.User
accounts.Person
patients.Patient
patients.DoctorPatientRelationship
```

sin convertir `Patient` en responsable de toda la operación.

---

# 30. Signals

Los signals de Django no deben utilizarse como mecanismo principal para coordinar lógica de negocio entre apps.

Evitar cadenas difíciles de seguir como:

```text
User created
   ↓
signal
   ↓
Person created
   ↓
signal
   ↓
Patient created
   ↓
signal
   ↓
Relationship created
```

Cuando el flujo sea una operación de negocio explícita, preferir un servicio transaccional.

Los signals pueden utilizarse para casos claramente apropiados y de bajo acoplamiento.

---

# 31. Admin

Cada app debe registrar en Django Admin únicamente las entidades que le pertenecen.

Ejemplo:

```text
accounts/admin.py
patients/admin.py
doctors/admin.py
clinics/admin.py
```

No centralizar arbitrariamente todo el dominio en una sola app.

---

# 32. URLs

Las URLs relacionadas con una funcionalidad deben residir preferentemente en la app propietaria de esa funcionalidad.

Ejemplo:

```text
patients/urls.py
doctors/urls.py
clinics/urls.py
```

y posteriormente:

```text
appointments/urls.py
care_requests/urls.py
```

`config/urls.py` debe encargarse principalmente de ensamblar las rutas.

---

# 33. Serializers y Forms

Los serializers/forms deben vivir en la app propietaria del dominio correspondiente.

Ejemplo:

```text
patients/
├── models.py
├── serializers.py
├── views.py
└── services/
```

No crear serializers de `Patient` dentro de `appointments` únicamente porque una cita lo utiliza.

---

# 34. Tests

Los tests principales de una entidad deben vivir en su app propietaria.

Ejemplo:

```text
patients/tests/
doctors/tests/
clinics/tests/
accounts/tests/
```

Los tests de integración pueden involucrar múltiples apps cuando el caso de uso lo requiera.

---

# 35. Migraciones

Las migraciones deben pertenecer a la app propietaria del modelo.

No crear migraciones artificiales en una app solamente para modificar modelos de otra.

Django debe mantener la dependencia de migraciones de forma explícita.

---

# 36. Regla sobre importaciones

Las importaciones deben reflejar dependencias legítimas.

Se debe evitar:

```text
accounts → appointments → medical_records → accounts
```

cuando la relación pueda resolverse de una forma más limpia.

Las dependencias circulares deben considerarse una señal arquitectónica que requiere revisión.

---

# 37. Integración con `accounts`

`accounts` ocupa una posición central porque proporciona:

```text
User
Person
Authentication
Authorization foundation
```

Sin embargo, eso no significa que todas las apps deban colocar lógica de negocio dentro de `accounts`.

Por ejemplo:

```text
Patient
```

no pertenece a:

```text
accounts
```

aunque tenga una relación con `User`.

---

# 38. Integración con `patients`

`patients` puede utilizar:

```text
User
Person
Doctor
Clinic
```

cuando sea necesario, pero debe seguir siendo responsable del dominio del paciente.

No debe convertirse en una app "general" que contenga funcionalidades de todo el sistema.

---

# 39. Integración con `doctors`

`doctors` representa al médico.

Los datos de agenda futura no deben colocarse dentro de `Doctor`.

Por ejemplo, evitar:

```text
Doctor
├── monday_schedule
├── tuesday_schedule
├── appointment_1
└── appointment_2
```

La agenda pertenece a `appointments`.

---

# 40. Integración con `clinics`

`clinics` representa consultorios.

La disponibilidad del médico + consultorio pertenecerá posteriormente a la lógica de agenda.

`Clinic` no debe almacenar directamente:

- citas;
- horarios individuales del médico;
- sala de espera;
- notificaciones.

---

# 41. Preparación para Fase 2

La arquitectura debe permitir agregar:

```text
appointments/
```

sin modificar radicalmente:

```text
accounts/
patients/
doctors/
clinics/
```

Conceptualmente:

```text
Appointment
 ├── Patient
 ├── Doctor
 └── Clinic
```

`appointments` utilizará estas entidades, pero no las absorberá.

---

# 42. Preparación para Fase 3

`medical_records` utilizará:

```text
Patient
Doctor
Appointment
```

para crear:

```text
MedicalEncounter
```

pero no debe trasladar `Patient` o `Doctor` a su propia app.

---

# 43. Preparación para Fase 4

`clinical_documents` podrá relacionarse con:

```text
Patient
Appointment
MedicalEncounter
Prescription
StudyOrder
CareRequest
```

pero mantendrá la responsabilidad de almacenar y proteger documentos.

---

# 44. Preparación para Fase 5

`care_requests` invocará un caso de uso de `appointments` (nunca al revés) que valide la
solicitud contra las reglas de Agenda de Fase 2 y cree la `Appointment` de forma automática e
inmediata, sin aprobación ni revisión manual (`requirements.md` §12):

```text
CareRequest
    ↓
Appointment
```

Que los modelos coordinen mediante un caso de uso no implica que deban vivir en la misma app.

**Decisión de cierre técnico (2026-09-15) — opción B, con la FK invertida:** el "caso de uso"
invocado es exactamente `appointments.services.appointment.create_appointment_from_hold(*,
actor, hold, patient, doctor, clinic, idempotency_key="")` **sin modificar su firma** — no
recibe un parámetro `care_request`, y `Appointment` no gana ningún campo. La relación es
propiedad de `CareRequest`: `care_requests` asigna `CareRequest.appointment` (`OneToOneField`
opcional hacia `Appointment`) después de recibir la `Appointment` ya creada, dentro de la misma
transacción. `appointments` no queda enterado de `CareRequest` en ningún punto — ni en tiempo de
ejecución ni a nivel de modelo. Detalle completo en `docs/design/care-request-service-contracts.md`
§9.

**Precisión (2026-09-18, corrección post-cierre — `docs/phases/phase-5-final-report.md` §38.A):**
"a nivel de modelo" incluye la navegabilidad ORM, no solo columnas/migraciones. El campo
`CareRequest.appointment` usa `related_name="+"` explícitamente para que Django no genere un
accessor inverso Python (`appointment_instance.care_request`) — sin ese `related_name`, la
dirección única de dependencia se habría violado en el nivel de navegabilidad de objetos aunque
`appointments` no ganara ninguna columna ni migración real. Cualquier FK futura de
`care_requests` hacia otra app debe declarar `related_name="+"` salvo que exista una necesidad
real y documentada de navegación inversa.

---

# 45. Preparación para Fase 6

`notifications` y `audit` tendrán un carácter transversal.

Sin embargo, seguirán siendo apps separadas para evitar contaminar las apps de dominio con infraestructura transversal.

---

# 46. Regla de ownership para casos ambiguos

Cuando exista duda sobre dónde colocar una entidad:

1. identificar qué concepto representa;
2. identificar quién es responsable de su ciclo de vida;
3. identificar qué reglas de negocio le pertenecen;
4. ubicarla en la app que represente esa responsabilidad;
5. documentar la decisión si existe impacto arquitectónico relevante.

No decidir únicamente por conveniencia del código que la utiliza.

---

# 47. Criterios para crear una nueva app

No se debe crear una Django app para cada modelo.

Crear una nueva app solamente cuando exista:

- una responsabilidad funcional diferenciada;
- un límite de dominio claro;
- un ciclo de vida propio;
- suficiente cohesión entre las entidades que contiene.

Ejemplo:

```text
Prescription
PrescriptionItem
```

no requieren necesariamente apps separadas.

Pertenecen naturalmente a:

```text
prescriptions
```

---

# 48. Criterios para NO crear una nueva app

No crear una app únicamente porque:

- un modelo tenga muchas líneas;
- exista una nueva tabla;
- una funcionalidad sea pequeña;
- se quiera "modularizar" sin una responsabilidad clara.

La modularidad debe reducir complejidad, no aumentarla.

---

# 49. Señales de una mala frontera

Revisar la arquitectura si una app:

- importa demasiadas apps;
- conoce detalles internos de múltiples dominios;
- contiene modelos que pertenecen claramente a otro dominio;
- necesita modificar entidades de otras apps directamente;
- contiene lógica que podría pertenecer a varias apps;
- genera dependencias circulares.

---

# 50. Regla de dependencia

La pregunta que debe hacerse antes de agregar una dependencia entre apps es:

> ¿Esta dependencia representa una relación real del dominio o solamente una conveniencia de implementación?

Si es solamente conveniencia, buscar una solución más desacoplada.

---

# 51. Alternativas consideradas

## Alternativa A — Una sola app para todo el sistema

```text
core/
├── User
├── Patient
├── Doctor
├── Clinic
├── Appointment
├── Prescription
└── ...
```

**Decisión:** Rejected.

Motivos:

- alto acoplamiento;
- responsabilidades mezcladas;
- mayor dificultad de mantenimiento;
- evolución más compleja.

---

## Alternativa B — Una app por modelo

```text
user/
person/
doctor/
patient/
clinic/
appointment/
...
```

**Decisión:** Rejected.

Motivos:

- fragmentación excesiva;
- demasiadas dependencias;
- pérdida de cohesión;
- complejidad innecesaria.

---

## Alternativa C — Apps por responsabilidad funcional

```text
accounts
patients
doctors
clinics
appointments
medical_records
...
```

**Decisión:** Accepted.

Es la alternativa que mejor equilibra:

- cohesión;
- separación;
- mantenibilidad;
- evolución.

---

## Alternativa D — Microservicios

**Decisión:** Rejected.

No corresponde a la arquitectura definida para esta etapa.

La especificación establece un único proyecto Django, no múltiples servicios independientes.

---

# 52. Consecuencias positivas

Esta decisión proporciona:

- límites claros;
- mayor cohesión;
- menor acoplamiento;
- facilidad para testear;
- evolución por fases;
- menor riesgo de dependencias circulares;
- mejor comprensión del dominio;
- posibilidad de incorporar nuevas apps sin reorganizar todo el proyecto.

---

# 53. Consecuencias negativas

Implica:

- más estructura inicial;
- necesidad de definir correctamente las fronteras;
- coordinación entre apps;
- mayor atención a dependencias;
- necesidad de utilizar servicios y relaciones de forma disciplinada.

Estos costos son aceptables para la evolución prevista de TeCuidoApp.

---

# 54. Reglas de implementación

### Regla 1

Cada app debe tener una responsabilidad funcional clara.

### Regla 2

Una entidad debe tener un único propietario canónico.

### Regla 3

No duplicar modelos entre apps.

### Regla 4

No duplicar información sin una razón documentada.

### Regla 5

Las relaciones entre dominios se representan mediante referencias explícitas.

### Regla 6

Evitar dependencias circulares.

### Regla 7

Los servicios coordinan casos de uso que cruzan múltiples apps.

### Regla 8

No utilizar signals como mecanismo principal de workflows de negocio.

### Regla 9

Cada app administra sus propios modelos, migraciones, tests y administración.

### Regla 10

No crear una app por cada modelo.

### Regla 11

No crear una app solamente por conveniencia técnica.

### Regla 12

Las nuevas apps requieren una responsabilidad funcional diferenciada.

---

# 55. Criterios de aceptación

Esta decisión se considera correctamente implementada cuando:

- [ ] Existe un único proyecto Django.
- [ ] Las apps se organizan por responsabilidad funcional.
- [ ] `accounts` contiene identidad/autenticación.
- [ ] `patients` contiene el dominio del paciente.
- [ ] `doctors` contiene el dominio del médico.
- [ ] `clinics` contiene el dominio del consultorio.
- [ ] Las entidades futuras tienen fronteras claras.
- [ ] No existen modelos duplicados.
- [ ] No existen dependencias circulares injustificadas.
- [ ] Las relaciones entre apps son explícitas.
- [ ] Los servicios se utilizan para casos de uso multi-app cuando corresponda.
- [ ] Las migraciones pertenecen a las apps propietarias.
- [ ] Los tests se organizan por app.
- [ ] La arquitectura permite agregar Fase 2 sin rehacer Fase 1.

---

# 56. Relación con otros ADR

Esta decisión complementa:

```text
ADR-001
Custom User Model
```

porque `accounts` será propietaria de la infraestructura de identidad.

También complementa:

```text
ADR-002
User / Person / Functional Profiles
```

porque define dónde deben vivir esos conceptos.

Y:

```text
ADR-003
Invitation Security
```

porque el flujo de invitaciones pertenece al dominio de identidad/registro.

Y:

```text
ADR-004
Role and Object Permissions
```

porque las políticas de autorización deberán respetar las fronteras de cada dominio.

Conceptualmente:

```text
ADR-001
Identity
   ↓
ADR-002
Profiles
   ↓
ADR-005
App Boundaries
   ↓
ADR-004
Authorization
```

---

# 57. Estado

**Accepted**

Esta decisión forma parte de la arquitectura base de TeCuidoApp.

Las fronteras podrán evolucionar cuando el dominio lo requiera, pero los cambios significativos deben documentarse mediante un nuevo ADR o una actualización de este documento.
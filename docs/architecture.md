# TeCuidoApp — Architecture

**Estado:** Vigente — documento enmendado incrementalmente; redactado originalmente como
"Propuesta inicial" durante Fase 1. Ver §44 "Estado actual" para el estado real y consolidado del
proyecto por fase (hasta Fase 5 — `PHASE 5 — CLOSED`, `docs/phases/phase-5-final-report.md`
§41.K; Fase 6 — Notificaciones y auditoría está implementada, pendiente de auditoría de cierre
formal independiente — `docs/phases/phase-6-implementation-summary.md`).  
**Versión:** 1.0 (sin nueva versión mayor; los cambios incrementales quedan documentados en §44 y
en los ADR correspondientes)  
**Fase de redacción original:** Fase 1 — Fundaciones  
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

Redis y Celery se utilizarán cuando exista una necesidad real de procesamiento asíncrono o tareas programadas. Fase 2 (Agenda) no la tiene: ninguna transición de estado de `Appointment` ocurre por paso del tiempo — todas requieren la acción humana autorizada correspondiente (`docs/phases/phase-2-agenda.md` §14) — así que Fase 2 no introduce Redis/Celery.

## Archivos

Los documentos clínicos deberán almacenarse en un medio privado.

Los archivos médicos nunca deben depender de una URL pública para su protección.

## Documentos

La aplicación genera documentos PDF para recetas y solicitudes de estudio (Fase 4 — cerrada, ver
§7.9–§7.11): generación server-side y síncrona, sin Celery, dentro del mismo flujo transaccional
de emisión (ADR-027).

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

                    Fases 2-4 (implementadas)
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

**Nota (cierre de Fase 4):** "Appointments" (Fase 2), "Medical Records" (Fase 3) y "Documents"
(Fase 4 — `prescriptions`/`study_orders`/`clinical_documents`) ya están implementadas y cerradas
(§44); el rótulo original "Fases posteriores" quedaba desactualizado para las tres. Ninguna de
ellas usa Redis/Celery: las tres son síncronas — Fase 4 lo decide explícitamente en ADR-027 (sin
incorporar infraestructura asíncrona sólo para PDF). El bloque `Redis / Celery` permanece como
infraestructura contemplada condicionalmente (§1, "cuando corresponda") para necesidades futuras
aún sin decisión concreta — no representa una dependencia real de ninguna fase cerrada.

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

`Invitation` es específicamente el flujo médico → prospecto adulto (`requirements.md` §7.1).
No se reutiliza (ni se relaja su FK obligatoria a `Doctor`) para el flujo de registro de
paciente menor por responsable — ese flujo necesita su propia entidad de confirmación, vive
en `patients` (ver §7.3), y su justificación completa está en
`docs/adr/ADR-007-responsible-initiated-minor-registration.md`.

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
Responsible
DoctorPatientRelationship
ResponsiblePatientRelationship
```

`Responsible` no estaba listado explícitamente en una versión previa de este documento
aunque `ResponsiblePatientRelationship` sí lo estaba aquí — se documenta ahora que vive
en `patients`, junto a `Patient` y ambas relaciones, siguiendo el mismo patrón (perfil +
sus relaciones en la misma app). Esto llena un vacío de listado, no cambia ninguna
decisión arquitectónica previa.

`patients` también es responsable del flujo de registro de paciente menor por responsable
(`requirements.md` §7.2, `docs/adr/ADR-007-responsible-initiated-minor-registration.md`):
crea `Patient` directamente (no vía `accounts.Invitation`) y su propia entidad de
confirmación de un solo uso, cuyo nombre y forma exactos quedan pendientes de implementación
(esa ADR fija las restricciones que debe cumplir, no el modelo concreto).

Los nombres definitivos pueden ajustarse durante la implementación.

`patients` también posee la distinción entre régimen de menor y régimen adulto de un paciente
— un concepto de negocio separado de la edad cronológica (`Person.is_minor`, en `accounts`).
`Patient` almacena `regime` (`MINOR`/`ADULT`, sin `default` de campo) junto con
`regime_changed_at`/`regime_changed_by`; `ResponsiblePatientRelationship` almacena
`deactivated_at`/`deactivation_reason` para poder cerrar en bloque el acceso de los
responsables cuando el paciente pasa a régimen adulto. El mecanismo completo — quién puede
ejecutar la transición, sus validaciones y sus efectos — está fijado en
`docs/adr/ADR-007-responsible-initiated-minor-registration.md` §3.8; no se repite aquí.

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

Contrato funcional completo en `docs/phases/phase-2-agenda.md` (aprobado 2026-09-09) — esta
sección resume el alcance, ese documento manda en caso de duda.

Responsabilidad:

- disponibilidad por fecha concreta (`Availability`), sin reglas recurrentes ni excepciones;
- hold temporal de reserva (`Hold`, 15 minutos, no es un estado de `Appointment`);
- citas (`Appointment`), creadas **directamente** — sin solicitud previa ni confirmación
  posterior;
- conflictos y concurrencia de reserva;
- cancelaciones y reprogramaciones (con historial y motivo obligatorio);
- inicio de consulta (`SCHEDULED → IN_CONSULTATION`) e inasistencias (`NO_SHOW`).

No incluye check-in ni sala de espera — no existen en el modelo de Fase 2 (no hay un estado
`WAITING`). No depende de `care_requests`: `appointments` es una app completa y funcional en
Fase 2 sin que `care_requests` exista todavía.

Reglas adicionales de cierre (2026-09-09): un médico no puede tener dos disponibilidades
activas que se solapen aunque correspondan a consultorios distintos; la agenda usa la zona
horaria del `Clinic`; toda operación administrativa exige `DoctorClinic` válida — el
administrador tiene acceso funcional global (ADR-004 §8), sin ámbito territorial por clínica
(corregido 2026-09-10); y un médico puede crear la primera cita de un paciente sin
`DoctorPatientRelationship` previa — esa creación **no** crea, activa ni modifica dicha
relación (`crear Appointment` y `crear DoctorPatientRelationship` son operaciones
independientes).

**No forma parte de la Fase 1; es el contenido de Fase 2.**

---

## 7.7 `care_requests`

**Principio de orquestación (2026-09-15, `docs/design/care-request-service-contracts.md`):**

> `CareRequest` orquesta; Agenda reserva; `Appointment` representa la cita; `ClinicalDocument`
> gestiona los archivos.

`CareRequestService` invoca directamente `appointments.services.hold.create_hold` y
`appointments.services.appointment.create_appointment_from_hold` (firmas existentes, sin
wrapper) dentro de su propia transacción exterior — esos `atomic()` ya existentes se anidan
como SAVEPOINT (mismo mecanismo que ADR-027). **Opción B (D7), FK invertida (decisión de cierre
2026-09-15):** `AppointmentService` no conoce `CareRequest` ni cambia su firma; la relación es
propiedad de `CareRequest` — `CareRequest.appointment` (`OneToOneField` opcional hacia
`Appointment`) se asigna desde `CareRequestService` después de crear la `Appointment`, dentro de
la misma transacción. `Appointment` no gana ningún campo ni migración: `appointments` permanece
completamente ajena a `care_requests`, ni siquiera a nivel de modelo. Ningún contrato ni código
de `appointments`/`clinical_documents` se modifica para dar cabida a Fase 5.

**Estado: implementada y cerrada (2026-09-18, `docs/phases/phase-5-final-report.md` §41.K —
`PHASE 5 — CLOSED`).** El detalle que sigue describe el diseño aprobado que efectivamente se
implementó — se conserva en tiempo presente/descriptivo tal como fue escrito durante el diseño,
sin marcarlo `HISTORICAL`, porque sigue siendo una descripción exacta de la arquitectura vigente,
no un estado superado:

- solicitudes de atención: el paciente/responsable selecciona médico, fecha y hora concretos —
  no es una solicitud abierta ni queda pendiente de aprobación/revisión médica
  (`requirements.md` §12, decisión de dominio 2026-09-14). La fecha/hora se toma de un slot ya
  generado por `appointments.services.availability.get_available_slots(*, actor, doctor,
  clinic, date)` (mismo formato `{start, end, status}` que ya consume el frontend de Agenda) —
  `CareRequest` reutiliza ese `start`/`end` tal cual, sin calcular duración por su cuenta
  (`docs/design/care-request-service-contracts.md` §3);
- **precisión (2026-09-18, ADR-005 §44):** "`Appointment` no gana ningún campo ni migración"
  incluye también no ganar navegabilidad ORM inversa — `CareRequest.appointment` usa
  `related_name="+"` explícitamente por esta razón, no solo por omisión;
- archivos relacionados — reutilizan `ClinicalDocument`/almacenamiento privado de Fase 4 **sin
  modificarlo**: mismos tipos (PDF/JPEG/PNG) y mismo límite único de tamaño
  (`CLINICAL_DOCUMENTS_MAX_UPLOAD_SIZE_BYTES`) que ya soporta `clinical_documents.services.storage`
  (decisión de cierre 2026-09-14, `requirements.md` §12.2). Único elemento nuevo: máximo 5
  archivos por `CareRequest`, resuelto en la capa de `care_requests` invocando `upload()`
  repetidamente, sin tocar `clinical_documents`. Se crean **después** de la `Appointment` (y
  después de asignar `CareRequest.appointment`, §9 del contrato de servicio) y se asocian a ella
  mediante la FK `ClinicalDocument.appointment` que **ya existe** hoy — no se agrega una FK nueva
  `ClinicalDocument → CareRequest` (`care-request-service-contracts.md` §12);
- límite de creación: máximo 3 `CareRequest` por **actor autenticado** (el `User` que crea la
  solicitud — paciente o responsable; no por paciente destino, para que un responsable con
  varios pacientes no eluda el límite repartiendo solicitudes entre ellos) en ventana móvil de 1
  hora, implementado con PostgreSQL — sin Redis, Celery ni infraestructura adicional para esta
  regla. Concurrencia resuelta con `select_for_update()` sobre la fila del `User` actor (no la de
  `Patient`) antes de contar y crear, dentro de la misma transacción — mismo patrón ya usado en
  `create_version`/`void_or_inactivate` de Fase 4 (`requirements.md` §12.3);
- estados: `NUEVA → CONVERTIDA` (confirmado, `requirements.md` §12.1); una `CareRequest`
  `CONVERTIDA` permanece así aunque la `Appointment` resultante cambie de estado después — la
  cancelación pertenece exclusivamente al ciclo de vida de `Appointment`. Si la validación de
  Agenda Fase 2 falla al confirmar, la operación completa falla de forma atómica: no se
  persiste `CareRequest` ni `Appointment` (confirmado, `requirements.md` §12.1) — `CareRequest`
  no es un historial de intentos fallidos;
- creación de `Appointment` **automática e inmediata** cuando la solicitud cumple las reglas de
  Agenda de Fase 2 (single source of truth para la reserva, sin lógica duplicada) — origen
  **alternativo y opcional** de `Appointment`, no un requisito previo. `appointments` (Fase 2) no
  depende de esta app — ni en tiempo de ejecución ni a nivel de modelo/FK; `care_requests` sí
  invoca un caso de uso de `appointments` para crear la cita (ADR-005 §12/§44), nunca al revés;
- idempotencia opcional (`Idempotency-Key`). **Orden autoritativo (corregido 2026-09-15):**
  `select_for_update()` sobre la fila del `User` actor se adquiere **primero**, dentro de la
  transacción exterior; el re-check de idempotencia (¿ya existe `CareRequest` con `(created_by,
  idempotency_key)`?) ocurre bajo ese lock, **antes** del rate limit — el mismo lock sirve para
  ambos, sin adquirir uno segundo. Razón: adquirir el lock antes del re-check impide que dos
  transacciones concurrentes lean "no existe" a la vez; una repetición legítima nunca debe
  rechazarse por rate limit solo porque otra petición con la misma clave ya creó la
  `CareRequest`. El `UniqueConstraint` parcial sobre `(created_by, idempotency_key)` + captura de
  `IntegrityError` en SAVEPOINT propio (mismo patrón que `reschedule_appointment`) se conserva
  como defensa en profundidad, ya no como el mecanismo que determina el resultado. La clave **no**
  se propaga a `create_appointment_from_hold` — ese servicio se invoca con `idempotency_key=""`,
  porque la clave del cliente pertenece exclusivamente al namespace de `CareRequest`; compartirla
  con el namespace independiente de `Appointment` podría colisionar con una reserva directa no
  relacionada del mismo actor (`docs/design/care-request-service-contracts.md` §7/§11/§13/§14);
- modelo de datos completo (campos, constraints, nulls/defaults) en
  `docs/design/care-request-data-model.md`;
- contrato API mínimo (endpoint, autenticación, entrada, DTO de salida, mapeo de errores —
  reutilizando `_ERROR_MAP`/`JsonApiView` ya existentes, sin DRF) en
  `docs/design/care-request-service-contracts.md` §17;
- valor de retorno: `CareRequestService.create` devuelve un DTO explícito
  (`CareRequestResult`: ids de `CareRequest`/`Appointment`/`ClinicalDocument` + estado), no la
  instancia ORM — única excepción a como el resto de los servicios del proyecto devuelven su
  resultado, justificada porque esta operación abarca varias entidades a la vez
  (`care-request-service-contracts.md` §16).

Debe permanecer como Django app dentro del mismo proyecto.

**`CareRequest` tendrá una FK `OneToOneField` opcional/nullable hacia `Appointment`**
(`CareRequest.appointment`, `on_delete=PROTECT`; confirmado, `requirements.md` §13,
`docs/design/care-request-data-model.md` §3) exclusivamente para trazabilidad del origen — nunca
convierte a `Appointment` en requisito para crear `CareRequest`, ni viceversa. La relación vive
del lado de `CareRequest`, no de `Appointment` — `Appointment` no gana ningún campo.

No incluye sala de espera/check-in — decisión definitiva de alcance del sistema
(`requirements.md` §41), no exclusiva de esta app.

**No forma parte de la Fase 1 ni de la Fase 2.**

---

## 7.8 `medical_records`

Especificación funcional aprobada 2026-09-11, ver `docs/phases/phase-3-clinical-encounter.md` (documento rector), `docs/design/clinical-encounter-domain.md` y `docs/design/clinical-record-domain.md`.

Responsabilidad (ADR-008 — Clinical Domain Boundary):

- `ClinicalEncounter`: registro de la consulta clínica originada por una `Appointment` válida (`Appointment 1 ─── 0..1 ClinicalEncounter`), estados `IN_PROGRESS`/`COMPLETED` únicamente, cinco campos obligatorios al completar (motivo de consulta, padecimiento actual, exploración física, evaluación/diagnóstico en texto libre, plan/indicaciones), sin edición ni reapertura posterior al cierre;
- `MedicalRecord`: expediente longitudinal único por paciente (`Patient 1 ─── 1 MedicalRecord`, ADR-011), creación lazy, sin duplicar datos de `Patient` ni de los encuentros;
- evolución, pronóstico, tratamientos, paraclínicos y observaciones permanecen como información clínica opcional, no como requisitos de cierre;
- alertas clínicas, recetas, órdenes de estudio y documentos clínicos son entidades futuras separadas, fuera del núcleo de Fase 3.

`appointments` (Fase 2) sigue siendo propietario exclusivo de `Appointment` y su ciclo de vida de Agenda; `medical_records` no lo duplica ni lo sustituye.

**No forma parte de la Fase 1 ni de la Fase 2.**

---

## 7.9 `prescriptions`

Especificación funcional y de diseño en `docs/phases/phase-4-documents.md` y
`docs/design/prescription-domain.md`/`phase-4-documents-workflow.md`; cierre documentado en
`docs/phases/phase-4-final-report.md` (`PHASE 4 — CLOSED`).

Responsabilidad (implementada, Fase 4):

- `Prescription`/`PrescriptionItem`: emisión desde un `ClinicalEncounter` válido (ADR-022),
  medicamentos e indicaciones como texto estructurado, sin catálogo farmacológico obligatorio;
- generación de PDF server-side, síncrona, persistida dentro del mismo flujo transaccional de
  emisión (ADR-027);
- historial y versionado (nueva versión ante corrección, sin sobrescritura — ADR-023) y anulación
  lógica, sin borrado físico funcional (ADR-024).

**No forma parte de la Fase 1, Fase 2 ni Fase 3 — es contenido de Fase 4.**

---

## 7.10 `study_orders`

Especificación funcional y de diseño en `docs/phases/phase-4-documents.md` y
`docs/design/study-order-domain.md`; cierre documentado en `docs/phases/phase-4-final-report.md`
(`PHASE 4 — CLOSED`).

Responsabilidad (implementada, Fase 4) — mismo patrón que `prescriptions` (§7.9): emisión desde un
`ClinicalEncounter` válido, `StudyOrder`/`StudyOrderItem`, PDF server-side síncrono persistido
dentro de la misma transacción de emisión (ADR-027), historial/versionado y anulación lógica.

**No forma parte de la Fase 1, Fase 2 ni Fase 3 — es contenido de Fase 4.**

---

## 7.11 `clinical_documents`

Especificación funcional y de diseño en `docs/design/clinical-document-domain.md` y
`docs/design/clinical-documents-data-model.md`; cierre documentado en
`docs/phases/phase-4-final-report.md` (`PHASE 4 — CLOSED`).

Responsabilidad (implementada, Fase 4 — ADR-025):

- `ClinicalDocument`: entidad independiente de documento clínico, origen `GENERATED` (emitido
  desde `prescriptions`/`study_orders`) o `UPLOADED` (subido de forma standalone);
- almacenamiento privado fuera de cualquier URL pública (ADR-026), nunca servido por
  `MEDIA_ROOT`/`MEDIA_URL`;
- autorización de acceso por objeto, revalidada en cada descarga (ADR-028);
- versionado y anulación lógica, sin borrado físico funcional.

**No forma parte de la Fase 1, Fase 2 ni Fase 3 — es contenido de Fase 4.**

---

## 7.12 `notifications`

Responsabilidad futura:

- email;
- recordatorios;
- notificaciones;
- proveedores externos.

La lógica de negocio no debe depender directamente de un proveedor concreto.

---

## 7.13 `audit`

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

Este modelo cubre exclusivamente el flujo médico → prospecto adulto (`requirements.md` §7.1).
El registro de un paciente menor por su responsable (§7.2) es un flujo distinto, con su
propia entidad de confirmación — no una variante de `Invitation` con `doctor` opcional (ver
`docs/adr/ADR-007-responsible-initiated-minor-registration.md`).

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

La gestión de documentos (`clinical_documents`, Fase 4 — cerrada, ver §7.11) respeta desde su
implementación el principio ya exigido aquí desde la redacción original:

```text
Medical files = private
```

Nunca deben utilizarse URLs públicas como mecanismo principal de seguridad — verificado: `clinical_documents.services.storage` usa `CLINICAL_DOCUMENTS_STORAGE_ROOT`, fuera de
`MEDIA_ROOT`/`MEDIA_URL` (ADR-026).

El acceso sigue (verificado, Fase 4):

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

La arquitectura de Fase 1 debe dejar preparado el sistema para (contrato completo en
`docs/phases/phase-2-agenda.md`):

```text
Doctor + Clinic
       │
       └── Availability (por fecha concreta — sin AvailabilityRule/AvailabilityException)
               │
               └── Slots derivados
                       │
                       ├── Hold (bloqueo temporal, no es un estado de Appointment)
                       │
                       └── Appointment (SCHEDULED/IN_CONSULTATION/COMPLETED/
                                         CANCELLED/NO_SHOW — creación directa,
                                         sin CareRequest ni confirmación)
```

Las citas se autorizan a partir de las relaciones ya existentes de Fase 1
(`ResponsiblePatientRelationship.status == ACTIVE` para responsable, `DoctorClinic` para
médico/administrador) — Fase 2 las consume, no las reinterpreta. `DoctorPatientRelationship`
**no** es una condición para crear una cita: un médico con `DoctorClinic` válida puede crear la
primera cita de un paciente sin que esa relación exista todavía, y crear la cita no la crea ni
la modifica (decisión de cierre, 2026-09-09).

La Fase 1 no implementa estas entidades.

---

# 36. Gestión Clínica (Fase 3 — cerrada, ver §7.8)

Las entidades clínicas mantienen el principio:

```text
Patient
   │
   ├── MedicalRecord
   │      │
   │      └── ClinicalEncounter (vía Appointment)
   ├── ClinicalAlert       [futuro]
   ├── Prescription        (Fase 4 — cerrada, ver §7.9)
   └── StudyOrder          (Fase 4 — cerrada, ver §7.10)
```

Las consultas y registros clínicos deberán conservar historial.

No se debe construir un expediente como un único registro mutable que sobrescriba toda la información anterior.

`Appointment.IN_CONSULTATION` (Fase 2) es la frontera hacia este dominio — `appointments` no
debe absorber `ClinicalEncounter` ni decisiones clínicas; la existencia o el estado de una cita
nunca constituye por sí solo un diagnóstico o tratamiento.

---

# 37. Documentos (Fase 4 — cerrada, ver §7.9–§7.11)

Implementado (originalmente descrito aquí como trabajo posterior, durante la redacción de Fase 1):

```text
Patient
   │
   ├── Appointment ── ClinicalEncounter
   ├── Prescription        (Fase 4)
   ├── StudyOrder          (Fase 4)
   └── ClinicalDocument    (Fase 4)
```

Los documentos permanecen privados y protegidos por autorización (ADR-026/ADR-028), tal como
exigía este principio desde su redacción original.

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

**Corrección de consistencia (cierre documental de Fase 3, 2026-09-11):** las dos listas
originales de esta sección (checklist de Fase 1 sin marcar, y Fase 2/Fase 3 bajo "Fases
futuras") quedaron desactualizadas — Fase 1, Fase 2 y Fase 3 ya están completadas. Se
conservan íntegras más abajo como registro histórico de construcción; el resumen siguiente
es la fuente de verdad sobre el estado real y consolidado del proyecto.

**Corrección de consistencia (cierre documental de Fase 4, 2026-09-14):** Fase 4 fue
implementada, se perdió por una falla catastrófica de la VM de desarrollo, se recuperó
íntegramente desde un respaldo previo a la falla (implementación consolidada en el commit
`cf77662` sobre `recovery/fase4`, con Fase 3 como baseline en `7621bae`), se revalidó
exitosamente en el ambiente reconstruido, y quedó formalmente cerrada — ver
`docs/phases/phase-4-final-report.md` §16 (`PHASE 4 — CLOSED`). La lista "Fases futuras" más
abajo, que aún incluía a Fase 4, se corrige en el resumen siguiente; se conserva sin editar
por lo demás como registro histórico de las fases que seguían pendientes al cierre de Fase 3.

**Corrección de consistencia (cierre documental de Fase 5, 2026-09-18):** Fase 5 (`CareRequest`)
fue implementada, auditada en 4 rondas de corrección (dominio/idempotencia, UI/browser, higiene
de repositorio, consolidación final) y quedó formalmente cerrada — ver
`docs/phases/phase-5-final-report.md` §41.K (`PHASE 5 — CLOSED`, commit
`ff8abb8e1797dee728fe7c1d8d4052413b77d944` + consolidación documental `c4bf7f1`/`7ccfd7c`). Las
decisiones arquitectónicas aprobadas para Fase 5 — dirección única `care_requests →
appointments`, `AppointmentService` sin conocimiento de `CareRequest`, sin reverse accessor ORM
(`related_name="+"`, §44 más abajo), `ClinicalDocument` asociado al resultado de `Appointment`
sin nueva relación ni nuevo backend de almacenamiento — se mantienen sin cambio; este cierre es
documental, no arquitectónico. La sección "Fase 5 — CareRequest" (§7.7 más abajo) y la lista
"Fases futuras" más abajo, que aún describían Fase 5 como responsabilidad futura, se corrigen en
el resumen siguiente y se marcan como histórico donde corresponde.

### Resumen de fases

```text
Fase 1 — Fundaciones                COMPLETADA (docs/phases/phase-1-foundations.md)
Fase 2 — Agenda                     COMPLETADA (docs/phases/phase-2-agenda-final-report.md)
Fase 3 — Gestión clínica            COMPLETADA (docs/phases/phase-3-clinical-final-report.md — PHASE 3 — CLOSED)
Fase 4 — Documentos                 COMPLETADA (docs/phases/phase-4-final-report.md — PHASE 4 — CLOSED)
Fase 5 — CareRequest y operación    COMPLETADA (docs/phases/phase-5-final-report.md §41.K — PHASE 5 — CLOSED)
Fase 6 — Notificaciones y auditoría IMPLEMENTADA (docs/phases/phase-6-implementation-summary.md
                                     — pendiente de auditoría de cierre formal independiente,
                                     no autodeclarada como CLOSED)
```

### Fase 1 — checklist original de construcción (histórico)

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

### Fase 2 y Fase 3 — especificación funcional (histórico)

```text
Fase 2 — Agenda (especificación funcional aprobada 2026-09-09, ver docs/phases/phase-2-agenda.md)
Fase 3 — Gestión clínica (especificación funcional aprobada 2026-09-11, ver docs/phases/phase-3-clinical-encounter.md)
```

### Fases futuras (histórico, al cierre de Fase 4 — Fase 5 ya no es futura)

```text
Fase 5 — CareRequest y operación     [HISTORICAL — ver "Resumen de fases" arriba: COMPLETADA]
Fase 6 — Notificaciones y auditoría  [HISTORICAL — ver "Resumen de fases" arriba: IMPLEMENTADA,
                                       pendiente de auditoría de cierre]
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
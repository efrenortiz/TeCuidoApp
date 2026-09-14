# Fase 3 — Clinical Service Contracts

**Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11 — incluye la corrección de SC-065 para eliminar la contradicción con `clinical-api-contracts.md` API-067)  
**Fase:** Fase 3 — Atención clínica y expediente  
**Última actualización:** 2026-09-10  
**Stack:** Python + Django + PostgreSQL (vistas planas + `JsonResponse`, sin Django REST Framework — corregido en la revisión de consistencia de 2026-09-11 para alinearse con `clinical-api-contracts.md` y con `appointments/api.py` de Fase 2)

---

## 1. Propósito

Este documento define los contratos de servicio de dominio que deben mediar entre la interfaz/API y el modelo clínico de TeCuidoApp.

La regla central es:

```text
UI / API
   ↓
Service contract
   ↓
Authorization
   ↓
Transaction
   ↓
Domain invariants
   ↓
ORM / PostgreSQL
```

Los servicios constituyen la frontera donde una intención funcional se transforma en una operación de negocio segura y transaccional.

Este documento no define todavía los contratos HTTP detallados de `clinical-api-contracts.md`; define los contratos internos de aplicación/dominio que la API y la UI utilizarán.

---

## 2. Fuentes y jerarquía normativa

### 2.1 Fuentes inmediatas

La definición de estos contratos debe ser consistente con:

1. `phase-3-clinical-encounter.md`.
2. `clinical-encounter-workflow.md`.
3. `clinical-encounter-rules.md`.
4. `clinical-encounter-domain.md`.
5. `clinical-record-domain.md`.
6. `clinical-data-model.md`.
7. `clinical-permissions.md`.
8. `clinical-security-and-privacy.md`.

### 2.2 Fases anteriores

También se conserva la arquitectura y los patrones de Fase 2, especialmente:

- servicios como autoridad de negocio;
- permisos centralizados;
- transacciones explícitas;
- `select_for_update()` cuando el estado pueda competir;
- constraints de PostgreSQL como última línea de integridad;
- excepciones de dominio traducidas por la capa de presentación.

### 2.3 Regla de contradicción

Cuando una regla general antigua contradiga una decisión específica cerrada para Fase 3, prevalece la decisión específica de Fase 3.

---

# 3. Principios de diseño de servicios

## SC-001 — No usar CRUD genérico como contrato de negocio

Los servicios no se modelan como un espejo de `Model.save()`, `Model.delete()` y `Model.objects.create()`.

Cada operación expuesta representa una intención clínica concreta.

## SC-002 — El servicio es autoridad de negocio

Una vista, serializer o endpoint no debe decidir por sí mismo una transición clínica.

## SC-003 — El ORM no reemplaza autorización

Encontrar un objeto mediante ORM no implica que el actor pueda leerlo o modificarlo.

## SC-004 — La autorización precede a la mutación

El servicio debe validar autorización antes de realizar una mutación clínica.

## SC-005 — La transacción pertenece a la operación

Una operación que modifica más de una entidad relacionada debe ser atómica cuando la consistencia del dominio lo requiera.

## SC-006 — La base de datos es una barrera final

Las reglas críticas de unicidad, referencialidad y estados deben quedar protegidas también en PostgreSQL cuando sea técnicamente viable.

## SC-007 — Los errores internos no se filtran

Los servicios exponen errores de dominio estables y no excepciones internas de Django/PostgreSQL.

## SC-008 — Servicios pequeños y explícitos

Debe preferirse una cantidad pequeña de servicios con contratos claros frente a una capa de servicios genérica excesivamente abstracta.

## SC-009 — No usar señales para lógica clínica central

No se crearán encuentros clínicos ni se completarán consultas mediante Django signals.

## SC-010 — No usar `save()` como comando clínico

`Model.save()` persiste datos; no representa por sí mismo una operación de negocio.

---

# 4. Servicios de Fase 3

La propuesta mínima es:

```text
ClinicalEncounterService
MedicalRecordService
ClinicalHistoryService
ClinicalAccessService
```

Y, para componentes posteriores, contratos especializados:

```text
ClinicalAlertService
PrescriptionService
StudyOrderService
ClinicalDocumentService
ClinicalAuditService
```

Los últimos cinco se documentan aquí como fronteras futuras, pero no todos requieren implementación completa en la primera iteración de Fase 3.

---

# 5. `ClinicalEncounterService`

## SC-011 — Responsabilidad

`ClinicalEncounterService` es responsable de las operaciones de negocio sobre un `ClinicalEncounter`.

Incluye:

- iniciar;
- guardar parcialmente;
- completar;
- recuperar un encuentro autorizado;
- validar consistencia con `Appointment`.

No incluye:

- reservar citas;
- cancelar citas;
- marcar NO_SHOW;
- crear relaciones médico-paciente;
- modificar identidad del paciente;
- crear catálogos diagnósticos.

## SC-012 — Dependencia con Agenda

El servicio clínico no sustituye a `AppointmentService`.

`AppointmentService` gobierna la transición de agenda.

`ClinicalEncounterService` gobierna el encuentro clínico.

Cuando ambas operaciones son necesarias, se coordinan transaccionalmente sin duplicar las reglas de cada dominio.

## SC-013 — Actor explícito

Todas las operaciones que requieran autorización reciben explícitamente `actor`.

No se debe inferir el actor mediante variables globales, thread-local ni estado oculto.

---

# 6. Contrato `start_encounter`

## SC-014 — Firma conceptual

```python
start_encounter(*, actor, appointment) -> ClinicalEncounter
```

## SC-015 — Intención

Iniciar la consulta clínica correspondiente a una cita válida y crear el `ClinicalEncounter` asociado.

## SC-016 — Entrada `actor`

`actor` representa al usuario autenticado que intenta iniciar la atención.

## SC-017 — Entrada `appointment`

La cita debe ser una instancia de `Appointment` existente y debe ser recargada/validada dentro de la transacción antes de cambiar su estado.

## SC-018 — Autorización

Solo el médico asignado a la cita puede iniciar la consulta.

La pertenencia del médico a `DoctorClinic` forma parte de las precondiciones operativas establecidas en Agenda cuando corresponda.

## SC-019 — Presencia del paciente

El inicio presupone la verificación de presencia física del paciente según la política ya heredada de Agenda.

No se crea un nuevo estado `WAITING` en Fase 3.

## SC-020 — Estado requerido

La cita debe estar en `SCHEDULED`.

## SC-021 — Estados prohibidos

No se puede iniciar desde:

- `CANCELLED`;
- `NO_SHOW`;
- `COMPLETED`;
- cualquier estado inexistente o inválido.

## SC-022 — Cita ya iniciada

Si la cita ya está en `IN_CONSULTATION` y existe su encuentro correspondiente, la segunda solicitud debe ser tratada como idempotente.

## SC-023 — Doble inicio

Dos solicitudes concurrentes no deben crear dos encuentros para la misma cita.

## SC-024 — Orden de operación

El servicio debe:

1. abrir transacción;
2. bloquear la cita;
3. autorizar al actor;
4. verificar estado y precondiciones;
5. localizar el encuentro existente;
6. crear el encuentro si no existe;
7. cambiar la cita a `IN_CONSULTATION`;
8. confirmar la transacción.

El orden exacto de pasos 6 y 7 puede optimizarse técnicamente, pero el resultado debe ser atómico.

## SC-025 — `created_at`

Se asigna al momento de creación real del `ClinicalEncounter`.

## SC-026 — `started_at`

Se asigna al momento efectivo de inicio de consulta.

## SC-027 — `updated_at`

Inicialmente refleja la creación y cualquier posterior guardado exitoso.

## SC-028 — Resultado

Devuelve el `ClinicalEncounter` en estado `IN_PROGRESS`.

## SC-029 — Resultado idempotente

Una repetición válida debe devolver el encuentro existente sin duplicarlo.

## SC-030 — Integridad Appointment ↔ Encounter

El servicio debe impedir que se cree un encuentro cuyo paciente o médico contradiga la cita.

---

# 7. Contrato `save_encounter`

## SC-031 — Firma conceptual

```python
save_encounter(*, actor, encounter, data) -> ClinicalEncounter
```

## SC-032 — Intención

Guardar información clínica parcial de un encuentro abierto.

## SC-033 — Estado requerido

Solo puede guardarse un encuentro en `IN_PROGRESS`.

## SC-034 — Actor autorizado

Solo el médico asignado al encuentro puede modificarlo.

## SC-035 — Parcialidad

No es necesario que estén completos los cinco campos obligatorios para efectuar un guardado parcial.

## SC-036 — Persistencia

Solo la información que se guarda exitosamente se considera garantizada como persistida.

## SC-037 — Sin autosave obligatorio

Fase 3 no requiere autosave.

## SC-038 — Normalización

Los campos textuales se normalizan como mínimo eliminando espacios al inicio y final.

## SC-039 — Vacío real

Una cadena compuesta únicamente por espacios se trata como vacía.

## SC-040 — Placeholders

Para los campos que tengan reglas de contenido real, el servicio debe rechazar placeholders definidos por la política clínica.

## SC-041 — Sin evaluación clínica

El servicio no intenta determinar si el texto es médicamente correcto, suficiente o razonable.

## SC-042 — Actualización temporal

Un guardado exitoso actualiza `updated_at`.

## SC-043 — Campos permitidos

El servicio solo acepta campos definidos por el contrato de datos clínicos.

Campos desconocidos deben ser rechazados o ignorados de forma explícita y documentada; se recomienda rechazo para detectar errores de integración.

## SC-044 — No modificar estado

`save_encounter` no completa ni cancela el encuentro.

## SC-045 — No cambiar identidad

El servicio no permite cambiar paciente, médico ni cita del encuentro.

## SC-046 — Modificación después de cierre

Si el encuentro está `COMPLETED`, la operación es rechazada.

## SC-047 — Resultado

Devuelve la instancia persistida en `IN_PROGRESS`.

---

# 8. Contrato `complete_encounter`

## SC-048 — Firma conceptual

```python
complete_encounter(*, actor, encounter, data) -> ClinicalEncounter
```

## SC-049 — Intención

Persistir los últimos cambios enviados, validar los cinco campos obligatorios y cerrar de forma atómica la consulta clínica y la cita.

## SC-050 — Estado requerido

El encuentro debe estar `IN_PROGRESS`.

## SC-051 — Actor

Solo el médico autorizado para ese encuentro puede completarlo.

## SC-052 — Guardado final incluido

El servicio debe tratar `data` como el último conjunto de cambios que deben persistirse antes del cierre.

## SC-053 — Campos obligatorios

**Corrección de consistencia (auditoría de cierre, 2026-09-11):** nombres fijados definitivamente por ADR-012, sin variantes.

Debe comprobarse la presencia de contenido clínico real en:

- `reason_for_visit`;
- `present_illness`;
- `physical_exam`;
- `assessment`;
- `plan`.

## SC-054 — Placeholder

Un valor placeholder no satisface un campo obligatorio.

## SC-055 — Sin longitud mínima arbitraria

No se exige un número mínimo de caracteres.

## SC-056 — Diagnóstico libre

La evaluación/diagnóstico se maneja como texto libre en Fase 3.

## SC-057 — Transacción

El cierre debe ejecutarse dentro de una única transacción.

## SC-058 — Bloqueo

La implementación debe proteger la operación contra dos solicitudes concurrentes de cierre.

## SC-059 — Cambio de estado del encuentro

El encuentro pasa a `COMPLETED`.

## SC-060 — Cambio de estado de la cita

La cita pasa a `COMPLETED` dentro de la misma transacción.

## SC-061 — `completed_at`

Se asigna al momento del cierre exitoso.

## SC-062 — `updated_at`

El último guardado exitoso forma parte de la misma operación y actualiza `updated_at`.

## SC-063 — Atomicidad

Nunca debe quedar el encuentro completado mientras la cita permanece `IN_CONSULTATION`, salvo una situación excepcional de integridad de infraestructura que sea revertida por la transacción.

## SC-064 — Resultado

Devuelve el encuentro completado.

## SC-065 — Idempotencia de repetición posterior

**Corrección de consistencia (auditoría de cierre, 2026-09-11) — Decisión D-001:** una redacción anterior de esta sección recomendaba devolver un error de estado definitivo, lo cual contradecía directamente a `clinical-api-contracts.md` (API-067), que ya resolvía este mismo caso como éxito idempotente. Se corrige a favor de API-067, por simetría con la idempotencia ya cerrada sin ambigüedad para "doble inicio" (SC-022/SC-029) y con el precedente de Fase 2 (Hold/Appointment: un reintento exacto siempre reconoce el resultado existente, nunca produce un error).

Una segunda petición sobre un encuentro ya `COMPLETED`, que no intente enviar contenido distinto al ya persistido, no debe ejecutar una nueva mutación ni alterar `completed_at` — debe reconocerse como **operación idempotente exitosa** y devolver el encuentro ya completado, sin re-ejecutar el cierre.

Si la solicitud intenta enviar cambios de contenido distintos a los ya persistidos sobre un encuentro ya `COMPLETED`, debe rechazarse con `EncounterAlreadyCompleted` (SC-136 — no con el error de idempotencia). **Corrección de consistencia (revisión de cierre, 2026-09-11):** una redacción anterior de este párrafo usaba el nombre `EncounterImmutable`, que nunca existió en la taxonomía cerrada de §19 ni en el código; SC-136 (`EncounterAlreadyCompleted`, "ya se cerró y no admite nuevas mutaciones") ya describía exactamente este caso.

---

# 9. Contrato `get_encounter`

## SC-066 — Firma conceptual

```python
get_encounter(*, actor, encounter_id) -> ClinicalEncounter
```

## SC-067 — Autorización

La lectura debe pasar por la política de `clinical-permissions.md`.

## SC-068 — IDOR

Nunca se concede acceso por el simple hecho de conocer el UUID/PK.

## SC-069 — Resultado mínimo

La consulta debe devolver únicamente un encuentro al que el actor esté autorizado a acceder.

## SC-070 — Estado

La lectura no modifica el encuentro.

## SC-071 — Auditoría

La lectura de información clínica debe respetar las reglas de auditoría definidas para Fase 3.

---

# 10. `MedicalRecordService`

## SC-072 — Responsabilidad

`MedicalRecordService` gestiona el expediente longitudinal del paciente.

Incluye:

- obtener expediente;
- crear de forma idempotente cuando corresponda;
- actualizar datos longitudinales permitidos;
- validar integridad del expediente.

## SC-073 — No crear expediente por toda consulta HTTP

No se crea un `MedicalRecord` solo porque alguien abra una pantalla.

## SC-074 — Creación lazy

El expediente puede crearse cuando exista una primera necesidad clínica real.

## SC-075 — Idempotencia

La creación debe tolerar solicitudes concurrentes sin producir más de un expediente por paciente.

## SC-076 — Firma conceptual

```python
get_or_create_for_patient(*, patient, actor=None) -> MedicalRecord
```

## SC-077 — Autorización

Cuando el servicio se invoque para una operación protegida, debe recibir y verificar el actor.

## SC-078 — Integridad con Patient

El expediente pertenece a un único paciente y no puede reasignarse.

## SC-079 — No duplicar identidad

El servicio no crea copias de nombre, fecha de nacimiento u otros datos que ya pertenezcan a `Patient`.

## SC-080 — Actualización de antecedentes

Los antecedentes longitudinales permitidos pueden actualizarse mediante un contrato explícito.

## SC-081 — Sin borrado destructivo

No existe `delete_medical_record()` como operación funcional ordinaria.

## SC-082 — Sin estado clínico inventado

El servicio no establece automáticamente un diagnóstico actual derivado de los encuentros.

---

# 11. Contrato `get_medical_record`

## SC-083 — Firma conceptual

```python
get_medical_record(*, actor, patient) -> MedicalRecord
```

## SC-083a — Comportamiento cuando el expediente aún no existe

**Cerrado (revisión de consistencia, 2026-09-11) — Decisión D-005:** `get_medical_record` es una operación de **lectura pura** y nunca dispara la creación lazy definida en `clinical-record-domain.md` CR-002/CR-003 (esa creación solo ocurre como efecto de la primera operación clínica de escritura, típicamente `start_encounter`).

Se cierra la separación entre la capa de servicio y la capa de API, que en una redacción anterior quedaba delegada de forma ambigua entre ambas:

- **Servicio:** si el paciente aún no tiene `MedicalRecord` persistido, `get_medical_record` devuelve un **resultado explícito de ausencia** (`None`, siguiendo la convención ya usada en el resto de servicios del proyecto para "recurso no encontrado" — no una excepción, no una estructura vacía simulada) sin crear ninguna fila. La ausencia es un resultado normal y esperado de esta operación, no un caso de error.
- **API:** la capa de API traduce ese resultado explícito de ausencia a `404 Not Found` (`clinical-api-contracts.md` API-073). Esa traducción es responsabilidad exclusiva de la API; el servicio no conoce ni decide códigos HTTP.

Esto es consistente con `clinical-record-domain.md` CR-048 ("ninguna operación de 'abrir expediente' debe modificar datos clínicos").

## SC-084 — Autorización

Debe delegar la decisión de acceso longitudinal a `ClinicalAccessService` o al servicio de permisos clínicos equivalente.

## SC-085 — Lectura histórica

El expediente debe permitir reconstruir el historial sin modificarlo.

## SC-086 — Orden determinista

Los encuentros históricos deben poder recuperarse en orden cronológico determinista.

## SC-087 — Paginación

Las colecciones históricas extensas deben poder paginarse.

---

# 12. Contrato `update_medical_record`

## SC-088 — Firma conceptual

```python
update_medical_record(*, actor, patient, data) -> MedicalRecord
```

## SC-089 — Campos explícitos

Solo se actualizan campos expresamente permitidos en el modelo clínico longitudinal.

## SC-090 — No alterar historial

Actualizar el expediente no modifica el contenido histórico de un `ClinicalEncounter` completado.

## SC-091 — No alterar citas

El servicio no cambia estados ni horarios de `Appointment`.

## SC-092 — `updated_at`

Un cambio exitoso del expediente actualiza su `updated_at`.

---

# 13. `ClinicalHistoryService`

## SC-093 — Responsabilidad

Construir lecturas históricas del expediente sin introducir una nueva fuente de verdad.

## SC-094 — No almacenar proyecciones innecesarias

La vista de resumen no obliga a persistir un duplicado de todos los datos históricos.

## SC-095 — Última consulta

La última consulta puede derivarse ordenando encuentros completados/abiertos según la definición de negocio.

## SC-096 — Último diagnóstico

La presentación de un diagnóstico reciente no se convierte automáticamente en `diagnóstico actual` clínicamente válido.

## SC-097 — Resumen

Un resumen clínico es una lectura/proyección y no reemplaza el historial completo.

## SC-098 — No inferencia

El servicio no realiza diagnóstico automático a partir de texto, resultados o patrones.

---

# 14. `ClinicalAccessService`

## SC-099 — Responsabilidad

Centralizar las decisiones de acceso a información clínica.

## SC-100 — Lectura de expediente

Determina si un actor puede leer un `MedicalRecord`.

## SC-101 — Lectura de encuentro

Determina si un actor puede leer un `ClinicalEncounter`.

## SC-102 — Modificación de encuentro

Determina si un actor puede modificar un encuentro abierto.

## SC-103 — Completado

Determina si un actor puede completar un encuentro.

## SC-104 — No confundir roles

Ser `Doctor` no equivale a tener acceso a todos los pacientes.

## SC-105 — No confundir cita con acceso longitudinal

Haber atendido o tener una cita no necesariamente concede acceso permanente al expediente, salvo la política explícita vigente.

## SC-106 — Responsables

El acceso del responsable se basa en la relación de responsabilidad activa y las reglas de alcance definidas en `clinical-permissions.md`.

## SC-107 — Administradores

El acceso administrativo se rige por la política clínica; no se debe convertir el privilegio funcional del administrador en un bypass silencioso de auditoría o privacidad.

## SC-108 — Fail closed

Ante duda o inconsistencia de autorización, el servicio deniega.

---

# 15. Flujos compuestos

## SC-109 — Inicio completo

El flujo de inicio puede expresarse conceptualmente como:

```python
transaction.atomic(
    lock Appointment
    authorize actor
    validate SCHEDULED
    get/create MedicalRecord when needed
    get/create ClinicalEncounter
    set Appointment = IN_CONSULTATION
    return encounter
)
```

La creación del expediente y del encuentro solo debe incluirse si la política de datos elegida requiere crear el expediente en ese momento.

## SC-110 — Cierre completo

```python
transaction.atomic(
    lock Appointment + Encounter
    authorize actor
    validate IN_PROGRESS
    persist final clinical data
    validate five required fields
    set Encounter = COMPLETED
    set Appointment = COMPLETED
    set completed_at
)
```

## SC-111 — No dividir cierre en dos requests obligatorias

La UI puede separar formularios internamente, pero el comando funcional de `complete_encounter` debe poder garantizar la atomicidad en una sola operación.

---

# 16. Transacciones

## SC-112 — `atomic()` en inicio

La creación del encuentro y transición de cita deben ser atómicas.

## SC-113 — `atomic()` en completion

La escritura final y el cierre deben ser atómicos.

## SC-114 — Guardado parcial

Un guardado parcial de un único encuentro no necesita una transacción compleja más allá de la necesaria para persistencia y timestamps, pero puede utilizar `atomic()` como patrón uniforme.

## SC-115 — Operaciones de lectura

Las lecturas ordinarias no necesitan transacción explícita salvo que deban proporcionar una vista consistente sobre múltiples registros bajo concurrencia.

## SC-116 — Bloqueo selectivo

`select_for_update()` se utilizará solo cuando proteja una transición o condición susceptible de carrera.

## SC-117 — Evitar locks innecesarios

No se bloquearán tablas o expedientes completos para una lectura ordinaria.

---

# 17. Concurrencia

## SC-118 — Doble inicio

Debe resolverse mediante combinación de:

- transacción;
- bloqueo de `Appointment`;
- unicidad de `ClinicalEncounter.appointment_id`;
- comportamiento idempotente.

## SC-119 — Doble completion

Debe impedir dos cierres válidos del mismo encuentro.

## SC-120 — Guardado contra completion

El servicio debe garantizar que un guardado que llegue después de `COMPLETED` sea rechazado.

## SC-121 — Completion contra guardado

El último cambio incluido en `complete_encounter` debe quedar persistido dentro de la misma transacción del cierre.

## SC-122 — Solicitud concurrente después de completar

Una solicitud que use una instancia obsoleta debe recargar y verificar el estado real antes de mutar.

## SC-123 — IntegrityError

Una violación de unicidad causada por una carrera debe traducirse a un resultado de dominio consistente, no a un error crudo.

---

# 18. Validación de entrada

## SC-124 — Tipos

La capa de presentación puede hacer validación sintáctica; el servicio debe repetir las validaciones de negocio críticas.

## SC-125 — Campos inesperados

Los campos fuera del contrato no deben terminar accidentalmente persistidos.

## SC-126 — Textos

Se normalizan espacios extremos antes de evaluar vaciedad/placeholders.

## SC-127 — Valores nulos

`None` debe distinguirse de cadena vacía cuando el campo tenga semántica distinta.

## SC-128 — Campos clínicos obligatorios

No son `NOT NULL` necesariamente durante la vida `IN_PROGRESS`; su obligatoriedad de negocio aplica al completion.

## SC-129 — Valores estructurales

Estado, actor, patient, doctor y appointment no deben ser modificables mediante el payload clínico ordinario.

---

# 19. Errores de servicio

La capa de servicios debe mantener una taxonomía estable.

## SC-130 — `ClinicalError`

Clase base de errores clínicos.

## SC-131 — `ClinicalNotFound`

Recurso clínico inexistente o no accesible, según política de no divulgación.

## SC-132 — `ClinicalNotAuthorized`

El actor no está autorizado para la operación.

## SC-133 — `EncounterNotStartable`

Las precondiciones de inicio no se cumplen.

## SC-134 — `EncounterAlreadyStarted`

Se recomienda utilizarlo solo cuando el caso no pueda tratarse idempotentemente; una repetición equivalente de inicio debe ser idempotente.

## SC-135 — `EncounterNotInProgress`

La operación requiere un encuentro abierto.

## SC-136 — `EncounterAlreadyCompleted`

El encuentro ya se cerró y no admite nuevas mutaciones.

## SC-137 — `IncompleteClinicalContent`

Uno o más campos obligatorios están **vacíos o ausentes** al intentar completar.

## SC-137a — `ClinicalContentPlaceholder`

**Añadido en la auditoría de cierre (2026-09-11)** para resolver una discrepancia de granularidad: `clinical-api-contracts.md` §19 ya distingue dos códigos HTTP distintos (`REQUIRED_CLINICAL_CONTENT` vs `INVALID_PLACEHOLDER_CONTENT`), pero este contrato de servicio solo exponía una excepción (`IncompleteClinicalContent`) para ambos casos, dejando indefinido cómo la API elegiría el código correcto.

Uno o más campos obligatorios contienen un valor de relleno reconocido (`N/A`, `No aplica`, `Sin datos`, etc., per `clinical-encounter-rules.md` R-053) en lugar de estar simplemente vacíos. Se distingue de `IncompleteClinicalContent` para que la capa de API pueda mapear cada caso a su código HTTP correspondiente sin inventar la distinción por su cuenta.

## SC-138 — `InvalidClinicalData`

El payload viola una regla estructural del dominio.

## SC-139 — `EncounterAppointmentMismatch`

La cita y el encuentro presentan identidad incompatible.

## SC-140 — `ClinicalRecordNotFound`

No existe expediente cuando la operación exige uno.

## SC-141 — `ClinicalRecordIntegrityError`

La estructura del expediente no cumple invariantes.

## SC-142 — `ClinicalConcurrencyError`

Se detectó una carrera que no pudo resolverse de forma segura.

## SC-143 — `ClinicalAuditError`

Solo cuando una política explícita requiera que la auditoría exitosa sea condición de la operación; no debe utilizarse indiscriminadamente.

---

# 20. Traducción de errores

## SC-144 — API

La API traduce errores clínicos a códigos HTTP definidos en `clinical-api-contracts.md`.

## SC-145 — UI

La UI transforma errores de servicio en mensajes comprensibles para el usuario.

## SC-146 — No exponer SQL

Nunca se devuelve SQL, traceback o mensaje interno de PostgreSQL.

## SC-147 — No filtrar existencia indebida

Cuando revelar la existencia de un recurso no autorizado pueda filtrar información sensible, la capa de servicio puede responder como recurso inexistente/no accesible según política de seguridad.

---

# 21. Idempotencia

## SC-148 — Inicio

`start_encounter` es idempotente para una segunda solicitud equivalente sobre una cita ya iniciada correctamente.

## SC-149 — Completion

La recomendación para Fase 3 es no tratar un cierre posterior como una nueva operación; el encuentro cerrado permanece definitivo.

## SC-150 — Guardado

`save_encounter` no requiere una clave de idempotencia general si el efecto deseado es simplemente persistir el estado enviado.

## SC-151 — Repetición de save

Una repetición exacta de un guardado es segura, aunque puede modificar `updated_at` al representar un nuevo save exitoso.

---

# 22. Integridad con `Appointment`

## SC-152 — Appointment es autoridad de agenda

El servicio clínico no recalcula disponibilidad.

## SC-153 — Cita obligatoria

Un `ClinicalEncounter` siempre nace de un `Appointment` válido.

## SC-154 — Cita única

No debe existir más de un encuentro asociado a la misma cita.

## SC-155 — Identidad del paciente

Paciente de encuentro y cita deben coincidir.

## SC-156 — Identidad del doctor

Médico del encuentro y cita deben coincidir.

## SC-157 — Cita y encuentro sincronizados

Durante una consulta activa:

```text
Appointment.IN_CONSULTATION
ClinicalEncounter.IN_PROGRESS
```

## SC-158 — Cierre sincronizado

Después de completar:

```text
Appointment.COMPLETED
ClinicalEncounter.COMPLETED
```

---

# 23. Integridad con `MedicalRecord`

## SC-159 — No redundancia

No debe enviarse `medical_record_id` desde la UI para decidir qué expediente pertenece a un paciente.

## SC-160 — Paciente como vínculo común

El paciente es la identidad común entre expediente y encuentros.

## SC-161 — Consistencia

Un encuentro no puede aparecer en la historia de un paciente distinto al de su cita.

## SC-162 — No cambio retroactivo

Cambiar datos administrativos del paciente no reescribe el contenido histórico del encuentro.

---

# 24. Separación con `DoctorPatientRelationship`

## SC-163 — Independencia

Ningún servicio de consulta crea automáticamente una `DoctorPatientRelationship`.

## SC-164 — Inicio no activa relación

`start_encounter` no debe invocar un servicio de relación médico-paciente para activarla como efecto secundario.

## SC-165 — Cierre no activa relación

`complete_encounter` tampoco modifica esa relación.

## SC-166 — Permiso de atención vs. relación longitudinal

El servicio puede comprobar una relación para una operación que explícitamente la requiera, pero no debe confundirla con la identidad del médico asignado a la cita.

---

# 25. MedicalRecord y operaciones de presentación

## SC-167 — No cargar todo por defecto

La vista de expediente no debe traer indefinidamente todos los encuentros, documentos, estudios y alertas en una sola consulta.

## SC-168 — Consultas especializadas

Se recomienda separar:

- resumen;
- encuentros paginados;
- documentos;
- estudios;
- recetas;
- alertas.

## SC-169 — Optimización prudente

Se deben utilizar `select_related`/`prefetch_related` donde eliminen consultas repetitivas sin ampliar innecesariamente el conjunto de datos expuesto.

---

# 26. Auditoría

## SC-170 — Servicio responsable

Las operaciones clínicas relevantes deben generar los eventos de auditoría definidos por `clinical-audit-and-history.md` cuando esa funcionalidad esté implementada.

## SC-171 — Auditoría no sustituye timestamps

Los timestamps de dominio siguen siendo parte del modelo clínico.

## SC-172 — Auditoría no controla autorización

La auditoría registra la operación; no sustituye la decisión de autorización.

## SC-173 — No registrar contenido clínico completo en logs técnicos

Los logs operativos deben evitar el contenido clínico sensible salvo que exista una necesidad explícita y controlada.

---

# 27. Seguridad del contrato

## SC-174 — Actor autenticado

Las operaciones mutantes requieren identidad autenticada.

## SC-175 — Denegación por defecto

Ausencia de autorización = rechazo.

## SC-176 — No confiar en IDs del cliente

Patient, doctor, clinic y appointment suministrados por el cliente no deben poder sobreescribir la identidad canónica de una operación ya enlazada.

## SC-177 — No confiar en estado enviado

El cliente nunca determina por payload que el encuentro está `COMPLETED` o la cita `IN_CONSULTATION`.

## SC-178 — No usar hidden fields como seguridad

Campos ocultos en formularios no constituyen autorización.

## SC-179 — Protección CSRF

Las mutaciones Web deberán respetar la protección CSRF estándar de Django donde aplique.

## SC-180 — API authentication

Los endpoints API clínicos deben exigir el mecanismo de autenticación y autorización definido por el proyecto.

---

# 28. Contratos futuros especializados

## SC-181 — `ClinicalAlertService`

Será responsable de crear, actualizar y cerrar alertas clínicas sin mezclarlas con antecedentes generales ni encuentros.

## SC-182 — `PrescriptionService`

Será responsable de recetas/prescripciones como entidad independiente.

## SC-183 — `StudyOrderService`

Será responsable de solicitudes de estudios, no de sus resultados como texto incrustado en el encuentro.

## SC-184 — `ClinicalDocumentService`

Gestionará documentos privados y su autorización de acceso.

## SC-185 — `ClinicalAuditService`

Podrá encapsular la creación de eventos de auditoría sin convertirse en una segunda base de verdad clínica.

---

# 29. No introducir servicios prematuros

## SC-186 — Evitar service factory genérica

No se recomienda crear una infraestructura genérica de `BaseClinicalService` salvo que exista una necesidad real.

## SC-187 — Evitar repository pattern artificial

Django ORM puede usarse directamente dentro de servicios bien delimitados mientras no se mezcle con la presentación.

## SC-188 — Evitar domain event bus prematuro

Fase 3 no requiere introducir un bus interno de eventos solo para coordinar dos cambios transaccionales.

## SC-189 — Evitar Celery en operaciones de cierre

Inicio y completion son operaciones síncronas y transaccionales; no deben delegarse a Celery.

---

# 30. Contratos internos recomendados

## 30.1 `ClinicalEncounterService`

| Método | Actor | Mutación | Estado entrada | Resultado |
|---|---|---|---|---|
| `start_encounter` | sí | sí | Appointment `SCHEDULED` | Encounter `IN_PROGRESS` |
| `save_encounter` | sí | sí | Encounter `IN_PROGRESS` | Encounter `IN_PROGRESS` |
| `complete_encounter` | sí | sí | Encounter `IN_PROGRESS` | Encounter `COMPLETED` |
| `get_encounter` | sí | no | cualquiera permitido | Encounter autorizado |

## 30.2 `MedicalRecordService`

| Método | Actor | Mutación | Resultado |
|---|---|---|---|
| `get_or_create_for_patient` | opcional según contexto | sí | Record único |
| `get_medical_record` | sí | no | Record autorizado |
| `update_medical_record` | sí | sí | Record actualizado |

## 30.3 `ClinicalAccessService`

| Método | Actor | Resultado |
|---|---|---|
| `can_view_record` | sí | bool / decisión explícita |
| `can_view_encounter` | sí | bool / decisión explícita |
| `can_edit_encounter` | sí | bool / decisión explícita |
| `can_complete_encounter` | sí | bool / decisión explícita |

---

# 31. Contrato de retorno

## SC-190 — Entidad persistida

Los métodos mutantes deben devolver la entidad persistida cuando el consumidor necesite su estado final.

## SC-191 — No devolver QuerySet abierto como comando

Un comando de negocio no debe devolver un QuerySet ambiguo para representar éxito.

## SC-192 — Lecturas especializadas

Las consultas históricas pueden devolver DTOs o querysets especializados en capas posteriores, pero el contrato debe ser explícito.

---

# 32. Validación de consistencia

## SC-193 — Appointment `IN_CONSULTATION` sin encounter

Debe considerarse una inconsistencia clínica.

## SC-194 — Encounter sin Appointment

Debe ser imposible por FK y por contrato de servicio.

## SC-195 — Encounter con paciente distinto

Debe rechazarse.

## SC-196 — Encounter con doctor distinto

Debe rechazarse.

## SC-197 — Encounter `COMPLETED` con Appointment `IN_CONSULTATION`

Debe considerarse inconsistencia.

## SC-198 — Appointment `COMPLETED` sin encounter cuando la consulta se inició

Debe considerarse inconsistencia para el flujo clínico.

---

# 33. Reglas de recarga de objetos

## SC-199 — No confiar en instancia antigua

Antes de una mutación de estado sensible, el servicio debe recargar la entidad desde la base de datos.

## SC-200 — Locks sobre la versión real

Cuando corresponda, el lock debe aplicarse a la fila real mediante `select_for_update()`.

## SC-201 — Validación después del lock

Las condiciones dependientes del estado deben verificarse después de adquirir el lock.

## SC-202 — No mantener instancias obsoletas

Tras una carrera resuelta, la operación debe trabajar con la instancia resultante real.

---

# 34. Reglas de timestamps

## SC-203 — `created_at`

Solo se establece al crear la entidad.

## SC-204 — `started_at`

Solo se establece al iniciar la consulta.

## SC-205 — `updated_at`

Se modifica en cada guardado exitoso permitido.

## SC-206 — `completed_at`

Solo se establece durante el completion exitoso.

## SC-207 — No manipular desde UI

El cliente no suministra timestamps de transición como autoridad.

---

# 35. Reglas de estado

## SC-208 — Estado como enum de dominio

Los estados deben seguir el conjunto cerrado definido por el dominio.

## SC-209 — No aceptar estado arbitrario

Un payload como `status=COMPLETED` no es un comando válido para guardar un encuentro.

## SC-210 — Transición por método

Las transiciones deben estar asociadas a operaciones explícitas.

## SC-211 — No auto-close

Ningún servicio periódico cierra consultas por el simple transcurso del tiempo en Fase 3.

---

# 36. Compatibilidad con UI

## SC-212 — Formulario parcial

La UI puede enviar subconjuntos de campos durante guardados parciales.

## SC-213 — Completion

El botón de completar debe invocar el mismo contrato de `complete_encounter`, no una serie improvisada de saves.

## SC-214 — Error de validación

Cuando falte contenido obligatorio, el servicio debe devolver información suficiente para que la UI marque los campos correspondientes sin revelar detalles internos.

## SC-215 — Reanudación

La UI puede volver a abrir un encuentro `IN_PROGRESS`; el servicio no necesita una operación especial de “resume”.

---

# 37. Compatibilidad con API

## SC-216 — API delgada

Los endpoints deben delegar al servicio y limitarse a autenticación de transporte, parsing y serialización.

## SC-217 — No duplicar reglas

No se implementará una segunda versión de `start_encounter` dentro del serializer/view.

## SC-218 — Errores estables

La API recibirá excepciones de dominio que pueda traducir a contratos HTTP estables.

---

# 38. Tests mínimos de servicio

## SC-219 — Inicio normal

Debe existir prueba del inicio exitoso.

## SC-220 — Inicio no autorizado

Debe rechazarse.

## SC-221 — Inicio desde estado inválido

Debe rechazarse.

## SC-222 — Doble inicio secuencial

Debe ser idempotente.

## SC-223 — Doble inicio concurrente

No debe duplicar encuentro.

## SC-224 — Guardado parcial

Debe permitir datos incompletos mientras el encuentro permanezca abierto.

## SC-225 — Guardado del actor incorrecto

Debe rechazarse.

## SC-226 — Completion con contenido incompleto

Debe rechazarse sin cierre parcial.

## SC-227 — Completion normal

Debe cerrar encounter y appointment atómicamente.

## SC-228 — Completion concurrente

Solo un cierre efectivo.

## SC-229 — Save después de completion

Debe rechazarse.

## SC-230 — Consistencia de timestamps

Debe verificarse orden temporal y semántica.

---

# 39. Fixtures y datos de prueba

## SC-231 — Datos sintéticos

Las pruebas deben preferir pacientes, médicos y contenido clínico sintéticos.

## SC-232 — No copiar datos clínicos reales

No se incorporarán datos reales a fixtures del repositorio.

## SC-233 — Casos mínimos

Cada servicio debe tener casos nominales y negativos.

## SC-234 — Concurrencia real cuando importa

Las reglas de doble inicio y completion deben probarse con mecanismos de concurrencia reales o una estrategia equivalente que demuestre la garantía.

---

# 40. Reglas de implementación Django

## SC-235 — `transaction.atomic`

Las operaciones transaccionales deben delimitarse explícitamente.

## SC-236 — `select_for_update`

Se usará para las filas cuyo estado sea parte de una carrera.

## SC-237 — Constraints

Las restricciones críticas del modelo deben reflejarse en migraciones.

## SC-238 — `IntegrityError`

Se captura únicamente cuando pueda traducirse con seguridad a un error de dominio.

## SC-239 — `timezone.now()`

Los timestamps deben utilizar el mecanismo de timezone configurado por Django.

## SC-240 — `update_fields`

Puede utilizarse para actualizaciones específicas, siempre que no omita accidentalmente campos de auditoría/timestamps necesarios.

## SC-241 — Signals

No se usarán signals para iniciar/completar consultas.

## SC-242 — Admin

Django Admin no debe permitir evadir reglas clínicas mediante edición directa de estados, salvo capacidades administrativas explícitas y auditadas definidas posteriormente.

---

# 41. Política de excepciones de integración

## SC-243 — Fallo de DB

Un error transitorio o interno de base de datos no debe convertirse en falso éxito clínico.

## SC-244 — Rollback

Si la operación transaccional falla, todas sus mutaciones deben revertirse.

## SC-245 — Reintentos

Los reintentos automáticos solo son seguros cuando el contrato garantiza idempotencia o puede detectar la operación ya realizada.

## SC-246 — Celery

No reintentar `complete_encounter` de forma asíncrona sin un contrato explícito de idempotencia adicional.

---

# 42. Reglas de observabilidad

## SC-247 — Métricas

Pueden medirse conteos y latencias de servicios sin registrar contenido clínico.

## SC-248 — Logs

Los logs deben identificar la operación y resultado técnico sin volcar el contenido completo de los campos clínicos.

## SC-249 — Correlation ID

Se recomienda conservar un identificador técnico de correlación por request cuando la infraestructura lo permita.

## SC-250 — Errores clínicos trazables

Los errores de dominio pueden quedar asociados a una correlación técnica, manteniendo minimización de datos.

---

# 43. Reglas de rendimiento

## SC-251 — No N+1

Las pantallas de historial deben diseñarse para evitar N+1 evidente.

## SC-252 — No optimizar prematuramente

No introducir caches clínicos complejos en Fase 3 antes de demostrar necesidad.

## SC-253 — Paginación

Los historiales potencialmente largos deben paginarse.

## SC-254 — Índices alineados

Las consultas principales deben estar respaldadas por los índices definidos en `clinical-data-model.md`.

---

# 44. Reglas de caché

## SC-255 — No cachear autorización

Una decisión de acceso clínico no debe permanecer cacheada más allá de la ventana segura definida por la infraestructura.

## SC-256 — No cachear respuestas clínicas públicamente

Las respuestas de expediente y consulta no deben almacenarse en caches públicos.

---

# 45. Regla sobre transacciones distribuidas

## SC-257 — Una DB como límite transaccional

Mientras el sistema opere sobre la misma base PostgreSQL, las operaciones de inicio/cierre deben aprovechar la transacción local.

## SC-258 — No introducir saga

Fase 3 no necesita patrones de saga/distributed transaction para las operaciones básicas.

---

# 46. Reglas de extensibilidad

## SC-259 — Servicios nuevos por intención

Cuando aparezca una nueva capacidad clínica, debe añadirse un servicio específico si constituye una nueva intención de negocio.

## SC-260 — Evitar método universal

No crear un `ClinicalService.execute(action=...)` genérico que concentre todas las reglas.

## SC-261 — Encapsulación

Los consumidores no deben depender de consultas ORM internas específicas de un servicio.

---

# 47. Matriz de contrato de operación

| Operación | Autoridad principal | Transacción | Lock esperado | Estado |
|---|---|---:|---:|---|
| iniciar consulta | ClinicalEncounterService + Appointment | sí | Appointment; Encounter por unicidad | SCHEDULED → IN_CONSULTATION / IN_PROGRESS |
| guardar | ClinicalEncounterService | sí/simple | según necesidad | IN_PROGRESS |
| completar | ClinicalEncounterService + Appointment | sí | Encounter + Appointment | IN_PROGRESS → COMPLETED |
| leer encuentro | ClinicalAccessService + History | no ordinaria | no | cualquiera autorizado |
| obtener expediente | MedicalRecordService + Access | no ordinaria | no | longitudinal |
| actualizar expediente | MedicalRecordService + Access | sí | según operación | record existente |

---

# 48. Casos nominales

## Caso A — Inicio de consulta

1. Médico asignado solicita iniciar.
2. Servicio bloquea la cita.
3. Cita `SCHEDULED`.
4. No existe encuentro.
5. Se crea `ClinicalEncounter(IN_PROGRESS)`.
6. Cita pasa a `IN_CONSULTATION`.
7. Commit.

## Caso B — Inicio repetido

1. El mismo médico vuelve a solicitar iniciar.
2. Cita ya está `IN_CONSULTATION`.
3. Encuentro existente es localizado.
4. Se devuelve sin duplicar.

## Caso C — Guardado parcial

1. Encuentro `IN_PROGRESS`.
2. Médico guarda motivo y padecimiento.
3. Datos persisten.
4. `updated_at` cambia.
5. Encuentro sigue `IN_PROGRESS`.

## Caso D — Completion

1. Médico envía cambios finales.
2. Se bloquea encounter/cita.
3. Se validan cinco campos.
4. Se guardan cambios.
5. Encounter `COMPLETED`.
6. Appointment `COMPLETED`.
7. `completed_at` se establece.
8. Commit.

## Caso E — Completion incompleto

1. Falta un campo obligatorio.
2. El servicio rechaza.
3. Encounter sigue `IN_PROGRESS`.
4. Appointment sigue `IN_CONSULTATION`.
5. No se persiste cierre.

---

# 49. Casos inválidos

## SC-262 — Iniciar cita cancelada

Rechazar.

## SC-263 — Iniciar NO_SHOW

Rechazar.

## SC-264 — Modificar encuentro completado

Rechazar.

## SC-265 — Cambiar patient_id

Rechazar.

## SC-266 — Cambiar doctor_id

Rechazar.

## SC-267 — Completar sin actor autorizado

Rechazar.

## SC-268 — Crear segundo encuentro para la misma cita

Rechazar o devolver el existente según idempotencia.

## SC-269 — Cerrar sin cinco campos

Rechazar.

---

# 50. Decisiones cerradas

Se consideran cerradas para esta propuesta:

1. Servicios como autoridad de negocio.
2. `ClinicalEncounterService` como servicio principal del encuentro.
3. `MedicalRecordService` para expediente longitudinal.
4. Servicio centralizado de acceso clínico.
5. Inicio idempotente.
6. Guardado parcial.
7. Completion atómico.
8. Últimos cambios incluidos en completion.
9. Solo médico asignado modifica.
10. Encounter completado inmutable.
11. No señales para lógica clínica central.
12. No Celery para transiciones clínicas.
13. No CRUD genérico como interfaz de dominio.
14. No creación automática de `DoctorPatientRelationship`.

---

# 51. Dependencias con documentos siguientes

Este documento será base para:

- `clinical-api-contracts.md` — contratos HTTP/API;
- `phase-3-clinical-ux.md` — acciones de UI;
- `clinical-audit-and-history.md` — eventos de trazabilidad;
- `phase-3-testing-strategy.md` — pruebas de servicios y concurrencia.

---

# 52. Criterios de salida

`clinical-service-contracts.md` está listo para implementación cuando:

- cada operación clínica principal tenga un único servicio responsable;
- cada mutación tenga actor y autorización claros;
- las operaciones críticas tengan límites transaccionales definidos;
- la concurrencia tenga comportamiento esperado;
- los errores de dominio estén separados de errores internos;
- la API no necesite duplicar reglas de negocio;
- no existan dependencias circulares innecesarias;
- el contrato sea compatible con `clinical-data-model.md`.

---

# 53. Resumen ejecutivo

La propuesta mantiene Fase 3 simple y coherente con Fase 2:

```text
AppointmentService
      │
      │ agenda
      ▼
Appointment SCHEDULED
      │
      │ start_encounter()
      ▼
ClinicalEncounterService
      │
      ├── authorize
      ├── transaction
      ├── ClinicalEncounter IN_PROGRESS
      └── Appointment IN_CONSULTATION
      │
      │ save_encounter()
      ▼
ClinicalEncounter IN_PROGRESS
      │
      │ complete_encounter()
      ▼
      ├── validate five fields
      ├── persist final changes
      ├── ClinicalEncounter COMPLETED
      └── Appointment COMPLETED
```

El principio operativo queda establecido:

> **La UI y la API expresan intención; el servicio aplica autorización y reglas; la transacción protege la consistencia; PostgreSQL protege los invariantes estructurales.**

---

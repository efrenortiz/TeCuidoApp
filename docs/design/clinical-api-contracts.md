# Fase 3 — Clinical API Contracts

**Documento:** `clinical-api-contracts.md`  
**Fase:** Fase 3 — Atención clínica y expediente  
**Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11)  
**Stack previsto:** Django + PostgreSQL (vistas planas + `JsonResponse`, sin Django REST Framework — corregido en la auditoría de cierre, 2026-09-11, para alinearse con `appointments/api.py` de Fase 2: no hay justificación de dependencia nueva per CLAUDE.md §13, y el contrato aquí descrito no requiere serialización compleja, negociación de contenido ni un browsable API)  
**Fecha:** 2026-09-11

---

## 1. Propósito

Este documento define el contrato HTTP/API del dominio clínico de Fase 3.

Su función es traducir los contratos internos de `clinical-service-contracts.md` a una interfaz estable para UI y futuros clientes, sin trasladar la lógica de negocio a views, serializers o rutas.

La frontera obligatoria es:

```text
HTTP request
    ↓
Authentication
    ↓
API validation / parsing
    ↓
Authorization
    ↓
Domain service
    ↓
Transaction
    ↓
ORM / PostgreSQL
    ↓
HTTP response
```

La API no constituye una segunda implementación del dominio. Los endpoints deben invocar los servicios clínicos definidos previamente.

---

# 2. Fuentes normativas

La definición de este contrato debe ser consistente con:

1. `phase-3-clinical-encounter.md`
2. `clinical-encounter-workflow.md`
3. `clinical-encounter-rules.md`
4. `clinical-encounter-domain.md`
5. `clinical-record-domain.md`
6. `clinical-data-model.md`
7. `clinical-permissions.md`
8. `clinical-security-and-privacy.md`
9. `clinical-service-contracts.md`
10. `requirements.md`
11. `docs/architecture.md`

### 2.1 Regla de contradicción

Cuando exista una contradicción entre una forma genérica de API y una decisión clínica cerrada de Fase 3, prevalece la decisión específica de Fase 3.

### 2.2 API como capa de transporte

La API no define nuevas reglas de negocio. Solo define:

- formato de entrada;
- formato de salida;
- autenticación del request;
- traducción de errores;
- códigos HTTP;
- paginación;
- versionado;
- metadatos mínimos del transporte.

---

# 3. Principios de diseño de la API

## API-001 — No CRUD genérico

No se expondrá un CRUD genérico de `MedicalRecord` o `ClinicalEncounter`.

Las operaciones de negocio se expresan mediante endpoints orientados a intención.

## API-002 — La API no modifica directamente modelos

Un endpoint no debe ejecutar directamente `serializer.save()` cuando esa operación represente una mutación clínica.

Debe delegar en el servicio correspondiente.

## API-003 — Autorización en backend

Todo endpoint clínico aplica autorización en servidor, aun cuando la UI haya ocultado el recurso.

## API-004 — Deny by default

Una ruta clínica sin autorización explícita debe responder con denegación.

## API-005 — Identificadores no son autorización

Conocer un `patient_id`, `medical_record_id` o `encounter_id` no concede acceso.

## API-006 — Contratos explícitos

Cada endpoint define expresamente sus campos aceptados.

Los campos desconocidos no deben persistirse silenciosamente.

## API-007 — No exponer detalles internos

Los errores de Django, PostgreSQL, stack traces y detalles de implementación no forman parte del contrato público.

## API-008 — JSON como representación F3

El contrato F3 utiliza JSON para operaciones clínicas normales.

La carga de archivos se reserva para el futuro `ClinicalDocument` y no forma parte del núcleo de estos endpoints.

---

# 4. Base path y versionado

## API-009 — Prefijo de API

La propuesta es utilizar:

```text
/api/v1/clinical/
```

El prefijo conserva separación entre API clínica y las rutas UI existentes.

## API-010 — Versionado explícito

Fase 3 utiliza `v1` desde el primer endpoint clínico público.

No se versionará por fecha ni por encabezados ocultos.

## API-011 — Cambios incompatibles

Un cambio incompatible del contrato requiere una nueva versión de API.

Cambios aditivos compatibles pueden permanecer en `v1`.

## API-012 — No crear múltiples versiones prematuramente

No se crearán `v2`, `v3`, etc. antes de que exista un cambio real incompatible.

---

# 5. Autenticación

## API-013 — Usuario autenticado

Todos los endpoints clínicos requieren usuario autenticado, salvo futuras rutas públicas que se documenten explícitamente fuera del dominio clínico.

## API-014 — Actor derivado del contexto autenticado

El servidor obtiene el actor del contexto de autenticación.

Nunca se aceptará `actor_id` como sustituto de la identidad autenticada.

## API-015 — Usuario inactivo

Un usuario autenticado pero inactivo no puede operar sobre recursos clínicos.

## API-016 — Identidad del actor

La identidad usada para autorización debe corresponder al usuario autenticado que realizó el request.

---

# 6. Autorización por operación

## API-017 — Separación read/write

La capacidad de leer no implica capacidad de modificar.

## API-018 — Encuentro abierto

Solo el médico asignado puede modificar un `ClinicalEncounter` `IN_PROGRESS`.

## API-019 — Completar

Solo el médico asignado puede completar el encuentro.

## API-020 — Historia longitudinal

La lectura histórica por otro médico requiere la relación clínica autorizante definida en `clinical-permissions.md`.

## API-021 — Primera atención

La primera atención válida no requiere una `DoctorPatientRelationship` previa, siempre que las reglas de Agenda permitan la cita y el actor sea el médico asignado.

Esto no concede acceso histórico permanente automático.

## API-022 — Paciente

El paciente solo puede consultar recursos propios dentro del alcance del portal.

## API-023 — Responsable

El responsable solo puede consultar pacientes cubiertos por una `ResponsiblePatientRelationship.ACTIVE` válida.

## API-024 — Administrador

El privilegio administrativo no se convierte en bypass clínico silencioso. Los accesos excepcionales se rigen por el contrato de permisos y auditoría.

---

# 7. Convenciones HTTP

| Intención | Método | Patrón |
|---|---|---|
| Consultar recurso | `GET` | `/resources/{id}/` |
| Crear/iniciar operación de negocio | `POST` | `/resources/.../start/` |
| Modificar parcialmente | `PATCH` | `/resources/{id}/` o acción explícita |
| Completar operación | `POST` | `/resources/{id}/complete/` |
| No soportado en clínicos | `DELETE` | no expuesto |

La propuesta evita `PUT` de reemplazo total para recursos clínicos F3.

---

# 8. Recursos expuestos en Fase 3

Los recursos principales son:

```text
Appointment       → recurso de Agenda preexistente
ClinicalEncounter → recurso clínico transaccional
MedicalRecord     → recurso clínico longitudinal
```

En F3 inicial no se exponen como recursos principales:

```text
ClinicalAlert
Prescription
StudyOrder
ClinicalDocument
```

Estos se incorporarán mediante contratos especializados cuando su dominio quede cerrado.

---

# 9. Endpoint — iniciar consulta

## API-025 — Ruta

```http
POST /api/v1/clinical/appointments/{appointment_id}/encounter/start/
```

## API-026 — Intención

Iniciar la consulta clínica correspondiente a un `Appointment` válido.

## API-027 — Body

No requiere body en F3.

Se recomienda `Content-Length: 0` o `{}` si el cliente HTTP lo exige.

## API-028 — Actor

El actor se obtiene de autenticación.

## API-029 — Entrada funcional

El único identificador funcional requerido en la URL es `appointment_id`.

## API-030 — Precondiciones

El servicio verifica:

1. cita existente;
2. cita en `SCHEDULED`;
3. médico asignado;
4. actor autorizado;
5. presencia del paciente verificada conforme Agenda;
6. ausencia de encuentro previamente creado, salvo solicitud idempotente;
7. consistencia relacional.

## API-031 — Éxito

Respuesta propuesta:

```http
201 Created
```

cuando se creó efectivamente un nuevo `ClinicalEncounter`.

## API-032 — Inicio repetido idempotente

Una solicitud repetida que corresponda a la misma cita y actor, cuando el encuentro ya existe y la operación es equivalente, devuelve el recurso existente sin duplicarlo.

La respuesta propuesta es:

```http
200 OK
```

## API-033 — Semántica de idempotencia

La idempotencia funcional no depende de un header obligatorio `Idempotency-Key` en F3.

La unicidad de `ClinicalEncounter.appointment_id` y la transacción protegen la operación.

Un futuro `Idempotency-Key` puede añadirse como mecanismo de transporte sin cambiar la semántica de dominio.

## API-034 — Respuesta

Ejemplo conceptual:

```json
{
  "id": "encounter-id",
  "appointment_id": "appointment-id",
  "patient_id": "patient-id",
  "doctor_id": "doctor-id",
  "status": "IN_PROGRESS",
  "created_at": "2026-09-11T01:00:00Z",
  "started_at": "2026-09-11T01:00:02Z",
  "updated_at": "2026-09-11T01:00:02Z",
  "completed_at": null,
  "clinical": {
    "motivo_consulta": "",
    "padecimiento_actual": "",
    "exploracion_fisica": "",
    "evaluacion_diagnostico": "",
    "plan_indicaciones": ""
  }
}
```

El ejemplo no implica que los cinco campos sean obligatorios para iniciar; solamente son obligatorios para completar.

---

# 10. Endpoint — consultar encuentro

## API-035 — Ruta

```http
GET /api/v1/clinical/encounters/{encounter_id}/
```

## API-036 — Autorización

La lectura pasa por `ClinicalAccessService`.

## API-037 — IDOR

Si el actor no está autorizado, no se debe recuperar el objeto para filtrarlo después en memoria.

La consulta debe construirse sobre un queryset autorizado o verificar la autorización antes de serializar datos clínicos.

## API-038 — Respuesta

```http
200 OK
```

## API-039 — Estado

La respuesta incluye el estado clínico y los timestamps del encuentro.

## API-040 — Campos clínicos

La representación inicial debe contener los campos explícitos definidos por el modelo de Fase 3, incluidos los opcionales cuando tengan valor.

## API-041 — Campos ausentes vs null

Para mantener un contrato estable, el servidor puede devolver explícitamente `null` para valores opcionales no definidos.

Los campos requeridos de negocio del encuentro siguen existiendo en la representación aunque aún estén vacíos durante `IN_PROGRESS`.

## API-042 — Lectura no muta

Un `GET` nunca debe actualizar `updated_at`, crear el expediente ni modificar estados.

---

# 11. Endpoint — guardar encuentro

## API-043 — Ruta

```http
PATCH /api/v1/clinical/encounters/{encounter_id}/
```

## API-044 — Intención

Guardar parcialmente información clínica de un encuentro abierto.

## API-045 — Solo `IN_PROGRESS`

Solo un encuentro `IN_PROGRESS` puede recibir modificaciones.

## API-046 — Actor autorizado

Solo el médico asignado puede modificarlo.

## API-047 — Partial update real

El body contiene únicamente los campos que el cliente pretende cambiar.

## API-048 — Body de ejemplo

```json
{
  "motivo_consulta": "Dolor abdominal de 3 días",
  "padecimiento_actual": "Inicio gradual..."
}
```

## API-049 — Campos clínicos permitidos

La API inicial permite los campos definidos explícitamente por `clinical-data-model.md`.

No permite:

```text
id
appointment_id
patient_id
doctor_id
status
created_at
started_at
completed_at
```

como campos mutables por el cliente.

## API-050 — Timestamps controlados por servidor

`updated_at` es generado por servidor al guardar con éxito.

El cliente no puede establecerlo manualmente.

## API-051 — No cambio de identidad

No se puede usar `PATCH` para cambiar paciente, cita o médico.

## API-052 — No cambio de estado

No se cambia `status` mediante este endpoint.

La transición a `COMPLETED` usa el endpoint específico de completion.

## API-053 — Éxito

```http
200 OK
```

con la representación actualizada del encuentro.

## API-054 — Persistencia garantizada

La respuesta `200 OK` implica que la información aceptada se persistió correctamente antes de responder.

## API-055 — Fallo

Ante error de persistencia o concurrencia, el endpoint no debe devolver `200 OK`.

## API-056 — Sin autosave

El contrato no obliga a la UI a guardar automáticamente cambios no enviados.

---

# 12. Endpoint — completar consulta

## API-057 — Ruta

```http
POST /api/v1/clinical/encounters/{encounter_id}/complete/
```

## API-058 — Intención

Persistir los últimos cambios enviados y completar atómicamente el `ClinicalEncounter` y su `Appointment`.

## API-059 — Body

El body es opcionalmente el conjunto final de campos clínicos modificables.

Ejemplo:

```json
{
  "motivo_consulta": "Dolor abdominal de 3 días",
  "padecimiento_actual": "Inicio gradual...",
  "exploracion_fisica": "Abdomen blando...",
  "evaluacion_diagnostico": "Dolor abdominal de etiología a determinar",
  "plan_indicaciones": "Hidratación, vigilancia y seguimiento..."
}
```

## API-060 — Guardado final incluido

El cliente no necesita enviar primero un `PATCH` obligatorio y después completar.

`complete/` debe poder persistir el último contenido enviado y cerrar en una sola transacción.

## API-061 — Campos obligatorios

Para completar deben existir con contenido clínico real:

1. `motivo_consulta`;
2. `padecimiento_actual`;
3. `exploracion_fisica`;
4. `evaluacion_diagnostico`;
5. `plan_indicaciones`.

## API-062 — Validación de contenido

Se aplican las reglas del dominio:

- trim de extremos;
- rechazo de contenido compuesto solo por espacios;
- rechazo de placeholders definidos;
- comparación de placeholders sin distinguir mayúsculas/minúsculas;
- sin longitud mínima arbitraria;
- sin evaluar corrección médica.

## API-063 — Diagnóstico

`evaluacion_diagnostico` es texto libre en F3.

No requiere `cie10_code` ni catálogo diagnóstico.

## API-064 — Éxito

```http
200 OK
```

La respuesta contiene el encuentro ya `COMPLETED`.

## API-065 — Estado final

La respuesta debe mostrar:

```json
{
  "status": "COMPLETED",
  "completed_at": "2026-09-11T01:30:00Z"
}
```

## API-066 — Atomicidad

La respuesta `200 OK` solo puede emitirse si la transacción completó correctamente:

```text
ClinicalEncounter → COMPLETED
Appointment → COMPLETED
```

## API-067 — Solicitud repetida después de completar

**Ratificado (auditoría de cierre, 2026-09-11) — Decisión D-001:** esta es ahora la única respuesta normativa; `clinical-service-contracts.md` SC-065, que anteriormente recomendaba un error para este mismo caso, fue corregido para alinearse con esta sección.

Una repetición posterior que no intente modificar contenido y corresponda al mismo encuentro ya completado debe tratarse como operación idempotente y devolver:

```http
200 OK
```

con el recurso final.

Si la solicitud intenta enviar cambios distintos después del cierre, debe ser rechazada con `EncounterAlreadyCompleted` (código HTTP `ENCOUNTER_COMPLETED` — corregido en la revisión de consistencia documental, 2026-09-11; el nombre `EncounterImmutable` no existe en la taxonomía cerrada de `clinical-service-contracts.md` §19 ni en el código).

---

# 13. Endpoint — consultar expediente

## API-068 — Ruta

```http
GET /api/v1/clinical/patients/{patient_id}/medical-record/
```

## API-069 — Identidad del recurso

El paciente es el recurso estable de navegación. El `MedicalRecord` se resuelve internamente.

No es necesario exponer un endpoint de creación manual del expediente.

## API-070 — Creación lazy

**Cerrado (auditoría de cierre, 2026-09-11) — Decisión D-005:** un `GET` nunca crea un `MedicalRecord` como efecto secundario, sin excepción — es consistente con `clinical-service-contracts.md` SC-083a y con `clinical-record-domain.md` CR-048. La creación lazy solo ocurre como efecto de la primera operación clínica de **escritura** (`start_encounter`).

## API-071 — Autorización

La lectura pasa por `ClinicalAccessService`.

## API-072 — Respuesta

```http
200 OK
```

cuando el expediente existe y el actor está autorizado.

## API-073 — Paciente sin expediente

**Cerrado (revisión de consistencia, 2026-09-11) — Decisión D-005:** la vista traduce el resultado explícito de ausencia que devuelve `get_medical_record` (`clinical-service-contracts.md` SC-083a — `None`, nunca creado implícitamente) a:

```http
404 Not Found
```

La API es la única responsable de esta traducción a código HTTP; el servicio no decide ni conoce códigos HTTP, solo indica ausencia de forma explícita.

Esto distingue:

```text
paciente existente
≠
expediente clínico existente
```

## API-074 — No convertir 404 de recurso en 403 de otro recurso

La política exacta para evitar divulgación de existencia de recursos no autorizados debe seguir `clinical-security-and-privacy.md` y `clinical-permissions.md`.

Cuando sea necesario, la implementación debe usar respuesta uniforme para acceso no autorizado/no visible.

---

# 14. Representación del `MedicalRecord`

## API-075 — Identidad

La representación debe incluir:

```json
{
  "id": "medical-record-id",
  "patient_id": "patient-id"
}
```

## API-076 — Datos no duplicados

No se deben copiar en el expediente campos de identidad que ya sean responsabilidad de `Patient`.

La UI puede resolver los datos del paciente por la relación autorizada.

## API-077 — Resumen clínico

Cuando se exponga un resumen, debe identificarse como proyección de lectura, no como una copia independiente del historial.

## API-078 — Historial

El expediente puede incluir o enlazar una colección paginada de `ClinicalEncounter`.

## API-079 — Orden histórico

La colección debe tener orden determinista, preferentemente por `started_at` y un identificador estable como desempate.

## API-080 — No cargar historia infinita

La primera respuesta no debe devolver todo el historial de forma ilimitada.

Se recomienda paginación.

---

# 15. Endpoint — historial de encuentros

## API-081 — Ruta

```http
GET /api/v1/clinical/patients/{patient_id}/encounters/
```

## API-082 — Autorización

Se aplica la autorización longitudinal correspondiente al actor.

## API-083 — Parámetros de paginación

La propuesta mínima es:

```text
?page=1&page_size=20
```

con un límite máximo definido por la API.

## API-084 — Parámetros de orden

No se aceptarán expresiones SQL ni nombres arbitrarios de columnas.

El orden clínico permitido será limitado a opciones explícitas, por ejemplo:

```text
?ordering=-started_at
```

## API-085 — Filtros F3

F3 no necesita un buscador clínico avanzado.

Se podrá filtrar por estados permitidos si existe una necesidad real, pero no se debe crear un DSL de consulta clínica en esta fase.

## API-086 — Respuesta paginada

Ejemplo conceptual:

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    { "id": "...", "status": "COMPLETED", "started_at": "..." }
  ]
}
```

---

# 16. Endpoint — actualizar expediente longitudinal

## API-087 — Ruta

```http
PATCH /api/v1/clinical/patients/{patient_id}/medical-record/
```

## API-088 — Intención

Actualizar exclusivamente campos longitudinales explícitos del `MedicalRecord`.

## API-089 — No reemplazo total

No existe `PUT /medical-record/` en Fase 3.

## API-090 — No mutar historia

Modificar el expediente longitudinal no modifica encuentros históricos.

## API-091 — Autorización

La escritura longitudinal se rige por la política explícita del dominio. La lectura no implica escritura.

## API-092 — Campos no permitidos

No se pueden modificar por este endpoint:

```text
patient_id
id
created_at
```

ni contenidos pertenecientes a encuentros históricos.

## API-093 — Timestamps

`updated_at` es generado por servidor.

## API-094 — Éxito

```http
200 OK
```

## API-095 — Ausencia de expediente

**Propuesta:** el `PATCH` no crea silenciosamente un expediente a partir de un request de actualización.

Si se requiere creación, debe existir una operación interna de servicio explícita.

---

# 17. Prohibición de endpoints de borrado clínico

## API-096 — No DELETE

No se exponen:

```http
DELETE /api/v1/clinical/encounters/{id}/
DELETE /api/v1/clinical/patients/{id}/medical-record/
```

## API-097 — Integridad histórica

La ausencia de `DELETE` evita presentar la eliminación como operación clínica normal.

## API-098 — Eliminación administrativa futura

Cualquier operación excepcional debe quedar fuera de la API clínica ordinaria y requerir un contrato administrativo explícito, autorización fuerte y auditoría.

---

# 18. Errores HTTP

La API traduce errores de dominio a una estructura JSON uniforme.

## API-099 — Formato de error

Propuesta:

```json
{
  "error": {
    "code": "clinical_error_code",
    "message": "Descripción segura para el cliente",
    "details": {}
  }
}
```

## API-100 — `code` estable

El frontend debe depender de `error.code`, no de textos libres de `message`.

## API-101 — `message` legible

`message` sirve para presentación y diagnóstico funcional básico, sin revelar internals.

## API-102 — `details`

`details` contiene únicamente información segura y relevante para el cliente.

No debe incluir:

- SQL;
- stack traces;
- nombres de tablas internas;
- secretos;
- datos clínicos de terceros;
- reglas de seguridad internas.

---

# 19. Mapeo de errores

| Error de dominio | HTTP | Código sugerido |
|---|---:|---|
| autenticación ausente | 401 | `AUTHENTICATION_REQUIRED` |
| usuario no autorizado | 403 | `CLINICAL_ACCESS_DENIED` |
| recurso no visible | 404/403 según política | `CLINICAL_RESOURCE_NOT_FOUND` o `CLINICAL_ACCESS_DENIED` |
| paciente/cita/encuentro inexistente | 404 | `RESOURCE_NOT_FOUND` |
| cita en estado incompatible | 409 | `APPOINTMENT_STATE_INVALID` |
| encuentro ya completado para una mutación | 409 | `ENCOUNTER_COMPLETED` |
| actor no es médico asignado | 403 | `CLINICAL_ACCESS_DENIED` (caso específico de "usuario no autorizado"; no existe un código distinto — corregido en la revisión de consistencia documental, 2026-09-11, para coincidir con `medical_records/api.py`) |
| contenido clínico requerido ausente | 422 | `REQUIRED_CLINICAL_CONTENT` |
| placeholder inválido | 422 | `INVALID_PLACEHOLDER_CONTENT` |
| datos de entrada inválidos | 400/422 | `VALIDATION_ERROR` |
| conflicto de concurrencia | 409 | `CLINICAL_CONCURRENCY_CONFLICT` |
| inconsistencia entre Appointment y Encounter | 409 | `CLINICAL_REFERENCE_INCONSISTENCY` |
| operación no soportada | 405 | `METHOD_NOT_ALLOWED` |

La elección exacta entre `403` y `404` para recursos no visibles queda subordinada a la estrategia anti-divulgación definida por seguridad.

---

# 20. Errores de validación de contenido

## API-103 — Campo individual

Para errores de contenido de campos, `details` puede identificar campos sin repetir datos clínicos completos.

Ejemplo:

```json
{
  "error": {
    "code": "REQUIRED_CLINICAL_CONTENT",
    "message": "Faltan campos clínicos obligatorios para completar la consulta.",
    "details": {
      "fields": [
        "padecimiento_actual",
        "plan_indicaciones"
      ]
    }
  }
}
```

## API-104 — No evaluar calidad médica

La API no devuelve mensajes como “diagnóstico insuficiente” o “contenido clínicamente incorrecto”.

Solo valida las condiciones objetivas de presencia y formato.

---

# 21. Concurrencia y respuestas

## API-105 — Doble inicio

Dos requests simultáneos para iniciar la misma cita deben terminar con un único `ClinicalEncounter`.

## API-106 — Doble completion

Dos requests simultáneos de completion no pueden producir dos cierres diferentes.

## API-107 — Guardado concurrente con completion

Un request que llegue después del cierre debe observar `COMPLETED` y rechazar la mutación.

## API-108 — Instancias obsoletas

El backend debe recargar/verificar estado real dentro de la transacción cuando la operación dependa de estado mutable.

## API-109 — Error de base de datos

Una carrera de unicidad o constraint no debe salir como 500 genérico si puede traducirse a una condición de dominio conocida.

---

# 22. Cache y datos clínicos

## API-110 — No cache público

Las respuestas clínicas autenticadas no deben publicarse mediante caché compartido público.

## API-111 — Cache-Control

Se recomienda política que impida almacenamiento por proxies compartidos para respuestas con datos clínicos sensibles.

## API-112 — No cachear mutaciones

Las respuestas de `POST`, `PATCH` y endpoints de transición no deben reutilizarse desde cachés HTTP.

---

# 23. CSRF y transporte

## API-113 — HTTPS

Toda API clínica en entornos no locales debe operar sobre HTTPS.

## API-114 — Protección CSRF

El mecanismo concreto seguirá la estrategia de autenticación de la aplicación.

Si F3 usa autenticación basada en cookies para la UI, las mutaciones deben respetar CSRF.

## API-115 — No confiar en CORS como seguridad

CORS no sustituye autenticación ni autorización.

---

# 24. Serialización de fechas

## API-116 — ISO 8601

Los timestamps deben representarse en formato ISO 8601.

Ejemplo:

```text
2026-09-11T01:30:00Z
```

## API-117 — Zona horaria

La API transmite instantes inequívocos. La aplicación puede presentar la hora local posteriormente.

## API-118 — Significado estable

Los campos conservan la semántica definida en dominio:

| Campo | Significado |
|---|---|
| `created_at` | creación del encounter |
| `started_at` | inicio real de consulta |
| `updated_at` | último guardado exitoso |
| `completed_at` | cierre exitoso |

---

# 25. Campos clínicos del encuentro

La representación F3 debe conservar nombres explícitos y estables.

**Corrección de consistencia (auditoría de cierre, 2026-09-11) — Decisión D-002:** el JSON expuesto por la API usa nombres en español (convención ya usada en el resto de la API de TeCuidoApp orientada al frontend), mientras que el modelo/servicio internos usan los nombres en inglés fijados por ADR-012. Una redacción anterior de este documento no incluía el mapeo entre ambos, lo que dejaba a cada implementador la tarea de inventarlo. Se agrega la tabla de mapeo explícita:

| Campo API (español) | Atributo interno (ADR-012) | Obligatorio al completar | Tipo |
|---|---|---:|---|
| `motivo_consulta` | `reason_for_visit` | Sí | string |
| `padecimiento_actual` | `present_illness` | Sí | string |
| `exploracion_fisica` | `physical_exam` | Sí | string |
| `evaluacion_diagnostico` | `assessment` | Sí | string |
| `plan_indicaciones` | `plan` | Sí | string |
| `signos_vitales` | `vital_signs` | No | estructura explícita o futura entidad |
| `peso` | `weight` (`weight_kg` en el modelo físico) | No | decimal |
| `talla` | `height` (`height_cm` en el modelo físico) | No | decimal |
| `antecedentes_relevantes` | `relevant_history` | No | string |
| `estudios` | `studies` | No | string / relación futura |
| `observaciones` | `observations` | No | string |

Esta tabla es la única fuente autoritativa del mapeo español↔inglés; el serializer debe implementarla literalmente, sin variantes por endpoint.

La forma exacta de los campos opcionales debe seguir el modelo físico finalmente aprobado; no se crea un JSON clínico genérico solo para evitar tomar esa decisión.

---

# 26. No exponer `status` como campo libre

## API-119 — Status de lectura

`status` sí se devuelve al leer.

## API-120 — Status no es entrada general

No se acepta:

```json
{ "status": "COMPLETED" }
```

como sustituto de las operaciones de negocio.

## API-121 — Acciones explícitas

Las transiciones se expresan mediante endpoints semánticos:

```text
start
complete
```

Esto evita combinaciones inválidas enviadas desde el cliente.

---

# 27. Appointment como recurso externo al dominio clínico

## API-122 — No duplicar endpoints de Agenda

F3 no debe crear endpoints alternativos para cancelar, reprogramar o hacer NO_SHOW.

Esas operaciones continúan perteneciendo a Agenda.

## API-123 — Iniciar desde Appointment

El único vínculo API inicial entre Agenda y clínica es el endpoint de inicio del encuentro.

## API-124 — No CANCELLED/NO_SHOW después de inicio

La API clínica debe reflejar la regla de dominio de que un Appointment que ya está `IN_CONSULTATION` no vuelve a `CANCELLED` ni `NO_SHOW`.

---

# 28. Integridad entre recursos

## API-125 — Encounter siempre tiene Appointment

Una respuesta de `ClinicalEncounter` siempre debe mostrar `appointment_id` válido.

## API-126 — Encounter pertenece a paciente de la cita

El `patient_id` del encounter se deriva de la cita y no es editable por cliente.

## API-127 — Encounter pertenece al médico de la cita

El `doctor_id` es consistente con la asignación del appointment.

## API-128 — No permitir relaciones cruzadas

La API no aceptará una combinación independiente de IDs que pueda asociar accidentalmente:

```text
patient A
appointment B
encounter C
```

si las relaciones reales no coinciden.

---

# 29. Seguridad contra IDOR

## API-129 — Endpoint por ID no equivale a acceso

Todo `GET /encounters/{id}/` y `GET /patients/{id}/medical-record/` debe comprobar autorización sobre el objeto.

## API-130 — Queryset autorizado

Cuando sea posible, la implementación puede restringir el queryset antes de buscar el objeto.

## API-131 — No enumeración sencilla

El contrato de errores y tiempos debe minimizar la posibilidad de enumerar IDs clínicos no autorizados.

## API-132 — No devolver relaciones de terceros

Una respuesta autorizada para un actor debe incluir únicamente relaciones y datos que ese actor pueda conocer.

---

# 30. Auditoría de API

## API-133 — Operaciones auditables

Se deben auditar al menos:

- inicio de encuentro;
- guardado clínico;
- completion;
- lectura de expediente cuando la política de auditoría lo requiera;
- exportaciones futuras;
- accesos excepcionales.

## API-134 — Qué no audita la API

La API no crea su propio historial clínico aparte del módulo de auditoría.

## API-135 — Actor del evento

La auditoría registra el actor autenticado real, no un `actor_id` enviado por el cliente.

## API-136 — Resultado

El evento de auditoría debe diferenciar éxito y rechazo cuando el contrato de auditoría lo requiera.

---

# 31. Paginación

## API-137 — Colecciones paginadas

Las colecciones clínicas históricas deben paginarse.

## API-138 — Límite máximo

El cliente no puede solicitar un `page_size` arbitrariamente grande.

## API-139 — Orden estable

Toda paginación debe tener un orden determinista.

## API-140 — No cursor complejo en F3

F3 puede iniciar con paginación por página si el volumen y rendimiento lo permiten.

No se agrega cursor pagination hasta existir una necesidad real.

---

# 32. Expansión de recursos

## API-141 — No `include=*`

No se permitirá una expansión arbitraria de relaciones clínicas mediante parámetros genéricos.

## API-142 — Representación estable

La respuesta debe contener el conjunto previsto de campos y relaciones autorizadas.

## API-143 — Evitar N+1

La implementación puede usar `select_related`/`prefetch_related` donde corresponda, sin cambiar el contrato externo.

---

# 33. Límites de tamaño

## API-144 — Longitud de campos

La API debe respetar los límites físicos definidos por el modelo y validación.

## API-145 — Request excesivo

Se deben rechazar cargas que superen límites razonables de transporte antes de entrar a operaciones clínicas costosas.

## API-146 — No usar truncamiento silencioso

Nunca se recortará silenciosamente texto clínico para hacerlo caber en almacenamiento.

---

# 34. Contrato de actualización final

## API-147 — Última escritura válida

La respuesta exitosa de `PATCH` representa exactamente la última versión persistida por esa operación.

## API-148 — Completion como comando

`complete` es una intención de negocio, no una actualización masiva de `status`.

## API-149 — No reabrir

No existe endpoint:

```http
POST /api/v1/clinical/encounters/{id}/reopen/
```

## API-150 — No editar completado

`PATCH` sobre un encounter `COMPLETED` debe rechazarse.

---

# 35. Concurrencia optimista — propuesta de simplicidad

## API-151 — Sin ETag obligatorio en F3

No se requiere un sistema de `ETag`/`If-Match` para todas las ediciones clínicas en la primera implementación.

La protección principal reside en estado, transacciones y locks de dominio.

## API-152 — Instancia obsoleta

Aunque no exista `ETag`, el backend debe verificar que el recurso continúe `IN_PROGRESS` antes de guardar.

## API-153 — Evolución futura

Un control de versión optimista puede incorporarse posteriormente sin alterar la semántica de los comandos.

---

# 36. Compatibilidad con UI

## API-154 — UI puede mapear formularios

La UI puede tener varios formularios o pestañas que terminen enviando `PATCH` parciales.

## API-155 — UI no necesita conocer transacciones

El cliente solo observa resultado final y errores; no implementa atomicidad de servidor.

## API-156 — Botón Completar

La UI invoca `POST /complete/` y usa la respuesta como fuente de verdad del estado final.

## API-157 — Doble click

La UI puede deshabilitar temporalmente el botón, pero el servidor sigue siendo responsable de soportar requests duplicados/concurrentes.

---

# 37. Campos administrativos y clínicos

## API-158 — Separación

La API no mezclará en un único body datos de identidad, agenda y clínica sin necesidad.

## API-159 — Patient como fuente de verdad

El cliente no actualiza nombre, fecha de nacimiento u otros datos canónicos de `Patient` a través del endpoint del expediente.

## API-160 — Appointment como fuente de verdad

El cliente no modifica datos de Agenda desde `ClinicalEncounter`.

---

# 38. Documentos y archivos

## API-161 — Fuera del núcleo F3

No se incluye un endpoint de subida de archivos en este contrato base.

## API-162 — Futura entidad

Los archivos clínicos deberán utilizar un `ClinicalDocumentService` y contrato propio cuando esa política sea cerrada.

## API-163 — No base64 clínico

No se almacenarán documentos grandes como strings base64 dentro de JSON de `MedicalRecord` o `ClinicalEncounter`.

---

# 39. Futuras extensiones no activadas

Estas rutas no se consideran parte del contrato cerrado de F3 inicial:

```text
POST /clinical/prescriptions/
POST /clinical/study-orders/
POST /clinical/alerts/
POST /clinical/documents/
GET  /clinical/analytics/
POST /clinical/diagnosis/suggest/
```

En particular, no se expone ninguna API de diagnóstico automático o recomendación clínica automatizada.

---

# 40. Contratos de errores de seguridad

## API-164 — No filtrar autorización

Una denegación no debe revelar qué relación faltó si esa información podría facilitar enumeración o inferencia sobre terceros.

## API-165 — No diferenciar existencia innecesariamente

La política de `403` vs `404` debe minimizar la exposición de la existencia del recurso cuando corresponda.

## API-166 — No devolver permisos internos

No se incluirán respuestas como:

```json
{
  "can_view": false,
  "reason": "DoctorPatientRelationship inactive"
}
```

para recursos de terceros si eso expone reglas internas o información de relaciones.

---

# 41. Pruebas de contrato API

Cada endpoint debe probar al menos:

### Inicio

- actor correcto;
- actor incorrecto;
- cita `SCHEDULED`;
- cita `CANCELLED`;
- cita `NO_SHOW`;
- cita `IN_CONSULTATION`;
- doble request;
- paciente no presente;
- recurso inexistente.

### Guardado

- actor asignado;
- otro médico;
- encuentro `IN_PROGRESS`;
- encuentro `COMPLETED`;
- actualización parcial;
- placeholder;
- whitespace;
- `updated_at` actualizado;
- campos protegidos enviados.

### Completar

- cinco campos válidos;
- uno o más faltantes;
- placeholders;
- doble completion;
- cambios finales incluidos;
- Appointment actualizado atómicamente;
- fallo transaccional.

### Lectura

- paciente propio;
- paciente ajeno;
- responsable activo;
- responsable inactivo;
- médico con relación activa;
- médico sin relación;
- médico asignado;
- administrador;
- IDOR.

---

# 42. Matriz resumida de endpoints

| Endpoint | Método | Actor principal | Mutación | Estado |
|---|---|---|---|---|
| `/appointments/{appointment_id}/encounter/start/` | POST | médico asignado | sí | F3 |
| `/encounters/{encounter_id}/` | GET | actor clínico autorizado | no | F3 |
| `/encounters/{encounter_id}/` | PATCH | médico asignado | sí | F3 |
| `/encounters/{encounter_id}/complete/` | POST | médico asignado | sí | F3 |
| `/patients/{patient_id}/medical-record/` | GET | actor autorizado | no | F3 |
| `/patients/{patient_id}/medical-record/` | PATCH | actor autorizado según política | sí | F3 |
| `/patients/{patient_id}/encounters/` | GET | actor autorizado | no | F3 |

No se expone `DELETE` clínico.

---

# 43. Decisiones de simplificación adoptadas

## API-167 — Acciones explícitas sobre estados libres

Se prefieren comandos `start` y `complete` sobre PATCH de estados.

## API-168 — No Idempotency-Key obligatorio

La idempotencia necesaria de F3 se resuelve en dominio/DB.

## API-169 — No ETag obligatorio

F3 no introduce control de versión HTTP adicional sin necesidad demostrada.

## API-170 — No búsqueda clínica avanzada

La consulta histórica inicia con paginación sencilla.

## API-171 — No expansión arbitraria

Se evita un API altamente genérica que complique permisos y privacidad.

## API-172 — No endpoint manual de creación de expediente

La creación del `MedicalRecord` permanece una responsabilidad del servicio y no una acción rutinaria del cliente.

## API-173 — No endpoints por especialidad aún

Ginecología, obstetricia, colposcopia, menopausia y otras especialidades se agregarán después sobre el núcleo genérico.

---

# 44. Invariantes API

La API nunca debe permitir que una request exitosa produzca:

**I-API-001** — un `ClinicalEncounter` sin `Appointment`.

**I-API-002** — más de un `ClinicalEncounter` efectivo para el mismo `Appointment`.

**I-API-003** — un encounter `COMPLETED` que pueda editarse mediante API ordinaria.

**I-API-004** — un encounter iniciado sin médico asignado autorizado.

**I-API-005** — una cita `IN_CONSULTATION` que vuelva a `CANCELLED` o `NO_SHOW` por la API clínica.

**I-API-006** — un completion exitoso con alguno de los cinco campos obligatorios ausente o placeholder.

**I-API-007** — un cierre donde `ClinicalEncounter` y `Appointment` queden con estados finales incompatibles.

**I-API-008** — una modificación de paciente/cita/médico desde un endpoint clínico de contenido.

**I-API-009** — acceso clínico obtenido únicamente por conocer un identificador.

**I-API-010** — creación de un expediente duplicado para el mismo paciente.

---

# 45. Contrato de implementación de vistas

**Corrección de consistencia (auditoría de cierre, 2026-09-11):** una redacción anterior asumía Django REST Framework. Se corrige para usar el mismo patrón que `appointments/api.py` de Fase 2: vistas planas basadas en `django.views.View` + `JsonResponse`, con una vista base compartida (equivalente a `JsonApiView`) que centraliza la traducción de excepciones de dominio a respuestas HTTP. Los principios de esta sección (views delgadas, serializers/parseo separados de la regla de negocio, traducción centralizada de errores) se mantienen sin cambio — solo cambia el framework concreto.

## API-174 — Views delgadas

Las views deben limitarse a:

1. obtener request/actor;
2. parsear/validar entrada;
3. invocar servicio;
4. mapear resultado a serializer;
5. traducir errores.

## API-175 — Serializers

Los serializers pueden validar:

- tipos;
- formato;
- campos desconocidos;
- límites de payload.

Pero las reglas críticas de negocio permanecen en servicios/dominio.

## API-176 — Excepciones

Las excepciones de dominio deben traducirse centralmente cuando sea posible.

## API-177 — No lógica duplicada

No se debe implementar una validación clínica distinta en cada endpoint.

---

# 46. Esquema de respuesta de éxito

**Cerrado (auditoría de cierre, 2026-09-11):** una redacción anterior dejaba esto condicionalmente sin resolver. La API de Agenda de Fase 2 (`appointments/api.py`) ya usa respuestas de recurso directas, sin wrapper `data` — la API clínica sigue exactamente esa convención, sin excepción:

```json
{
  "id": "...",
  "status": "IN_PROGRESS"
}
```

No se introduce un wrapper `{"data": {...}}` en ningún endpoint clínico.

---

# 47. Content negotiation

## API-178 — JSON

JSON es el formato principal.

## API-179 — No HTML para API

Los errores de API no deben depender de páginas HTML de Django.

## API-180 — Content-Type

Las mutaciones que reciben JSON requieren:

```http
Content-Type: application/json
```

---

# 48. Estado de recursos y códigos HTTP

La API debe distinguir tres conceptos:

```text
HTTP status
    ≠
clinical status
    ≠
appointment status
```

Por ejemplo:

```text
HTTP 200
ClinicalEncounter COMPLETED
Appointment COMPLETED
```

La API no utiliza códigos HTTP para sustituir los estados de dominio.

---

# 49. Datos sensibles en URLs

## API-181 — Minimizar datos en path

La URL utiliza identificadores técnicos, no nombres, diagnósticos ni texto clínico.

## API-182 — No datos clínicos en query string

Los textos de expediente no deben enviarse en parámetros de URL.

Esto evita exposición accidental en logs, historial del navegador y proxies.

---

# 50. Logs de request

## API-183 — No registrar bodies clínicos por defecto

Los logs de aplicación no deben registrar automáticamente bodies completos de requests clínicos.

## API-184 — Identificador técnico mínimo

Cuando sea necesario diagnosticar una operación, debe ser posible correlacionarla sin copiar contenido clínico sensible al log.

## API-185 — Correlation ID

Se recomienda soportar un identificador de correlación por request, pero sin convertirlo en identidad clínica ni en secreto.

---

# 51. Exportaciones

## API-186 — Fuera del CRUD clínico

No existe una exportación genérica de expediente en esta primera versión de API.

## API-187 — Contrato futuro separado

Cualquier exportación requiere endpoint, autorización y auditoría propios.

---

# 52. Compatibilidad con evolución clínica

## API-188 — Campos opcionales aditivos

Se pueden agregar campos opcionales sin crear nueva versión si no alteran el significado existente.

## API-189 — Renombrados incompatibles

Cambiar el significado o nombre de un campo existente requiere migración de contrato o nueva versión.

## API-190 — Diagnóstico libre en v1

F3 mantiene texto libre de diagnóstico y no debe anticipar un contrato CIE-10 que todavía no existe.

---

# 53. Límites con especialidades

La API genérica de F3 no tendrá campos específicos de:

- embarazo;
- puerperio;
- colposcopia;
- menopausia;
- osteoporosis;
- ginecología especializada.

Una futura extensión puede introducir subrecursos o módulos especializados, pero no debe contaminar el contrato base.

---

# 54. Flujo nominal completo

```text
POST /clinical/appointments/{id}/encounter/start/
        ↓
201/200
        ↓
GET /clinical/encounters/{encounter_id}/
        ↓
PATCH /clinical/encounters/{encounter_id}/
        ↓
PATCH /clinical/encounters/{encounter_id}/
        ↓
POST /clinical/encounters/{encounter_id}/complete/
        ↓
200 COMPLETED
```

El flujo permite cero, uno o varios `PATCH` antes de `complete`.

---

# 55. Flujo interrumpido

```text
start
  ↓
IN_PROGRESS
  ↓
PATCH parcial
  ↓
interrupción
  ↓
IN_PROGRESS
  ↓
GET
  ↓
PATCH
  ↓
complete
```

La API no expira ni completa automáticamente el encuentro por inactividad.

---

# 56. Flujo de doble inicio

```text
Request A ─┐
           ├─ transaction/constraint → 1 Encounter
Request B ─┘
```

Una request recibe creación efectiva y la otra reutilización idempotente o resultado equivalente.

---

# 57. Flujo de doble completion

```text
Request A ─┐
           ├─ lock → una sola transición a COMPLETED
Request B ─┘
```

Una segunda solicitud no puede editar un encounter ya cerrado.

---

# 58. Criterios de aceptación

Este documento puede considerarse cerrado para implementación cuando:

1. los paths anteriores estén aceptados;
2. los códigos de error sean compatibles con la infraestructura actual;
3. la estructura de serializers coincida con el modelo físico final;
4. las views deleguen en servicios;
5. los tests cubran autorización y concurrencia;
6. no exista endpoint clínico que permita CRUD genérico;
7. no existan rutas de reapertura o borrado ordinario;
8. el contrato de Agenda siga siendo la autoridad para estados de cita.

---

# 59. Decisiones diferidas correctamente

Quedan expresamente fuera del cierre de este archivo:

- formato definitivo de `ClinicalDocument`;
- recetas;
- órdenes de estudios;
- alertas clínicas;
- catálogos diagnósticos/CIE-10;
- firma electrónica avanzada;
- exportación legal completa del expediente;
- interoperabilidad FHIR u otro estándar;
- telemedicina;
- especialidades clínicas específicas.

No deben introducirse accidentalmente como requisitos implícitos de los endpoints genéricos.

---

# 60. Relación con los siguientes documentos

Este contrato debe servir como base para:

```text
clinical-api-contracts.md
        ↓
phase-3-clinical-ux.md
        ↓
clinical-screens.md
        ↓
clinical-audit-and-history.md
        ↓
phase-3-testing-strategy.md
```

La UX debe consumir este contrato y no inventar operaciones que la API no soporta.

---

# 61. Resumen de políticas cerradas

| Área | Decisión |
|---|---|
| Versionado | `/api/v1/clinical/` |
| Inicio | `POST .../start/` |
| Guardado | `PATCH` parcial |
| Completion | `POST .../complete/` |
| Lectura encounter | `GET` |
| Lectura record | `GET` |
| Historial | `GET` paginado |
| Edición record | `PATCH` intencional |
| DELETE clínico | No |
| PUT completo | No |
| Reapertura | No |
| Status por PATCH | No |
| Diagnóstico | texto libre |
| CIE-10 | fuera de F3 |
| Idempotency-Key | no obligatorio |
| ETag/If-Match | no obligatorio |
| Autorización | servidor, object-level |
| IDOR | prohibido |
| Autosave | no obligatorio |
| Completion | guarda + cierra atómicamente |
| Appointment | sigue bajo Agenda |
| ClinicalEncounter | bajo servicio clínico |
| MedicalRecord | bajo servicio de expediente |

---

# 62. Próximo documento

Con este contrato cerrado, el siguiente documento de la secuencia es:

```text
phase-3-clinical-ux.md
```

La UX debe reflejar exactamente los comandos y estados definidos aquí, especialmente:

```text
Iniciar consulta
Guardar
Completar consulta
```

sin crear estados clínicos adicionales ni permitir edición posterior a `COMPLETED`.

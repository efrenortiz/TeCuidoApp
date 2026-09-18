# Fase 5 — Modelo de datos de `CareRequest`

**Decisiones de cierre técnico:** 2026-09-15. Complementa, sin sustituir,
`requirements.md` §12/§12.1/§12.2/§12.3/§13 (fuente funcional) y
`docs/design/care-request-service-contracts.md` (contrato de servicio).

## 1. Objetivo

Definir un modelo pequeño, explícito y compatible con PostgreSQL para `CareRequest`, sin
duplicar información ya modelada en `Patient`, `Doctor`, `Clinic`, `Responsible` ni `Appointment`.

## 2. Entidad `CareRequest`

Campos mínimos:

| Campo | Tipo conceptual | Obligatorio | Nota |
|---|---|---:|---|
| id | PK | Sí | Identidad |
| patient | `ForeignKey(Patient, on_delete=PROTECT)` | Sí | Paciente para el que se solicita la cita |
| created_by | `ForeignKey(User, on_delete=PROTECT)` | Sí | Actor autenticado que crea la solicitud (paciente o responsable) — mismo campo/semántica que `Appointment.created_by` (`appointments/models.py`) |
| responsible | `ForeignKey(Responsible, on_delete=PROTECT, null=True, blank=True)` | No | Presente solo cuando quien solicita es un responsable (§5); `NULL` cuando el paciente solicita para sí mismo |
| doctor | `ForeignKey(Doctor, on_delete=PROTECT)` | Sí | Médico solicitado |
| clinic | `ForeignKey(Clinic, on_delete=PROTECT)` | Sí | Consultorio solicitado |
| appointment | `OneToOneField(Appointment, on_delete=PROTECT, null=True, blank=True)` | No | **Decisión definitiva (2026-09-15):** `CareRequest` es propietaria de la relación — ver §3. `NULL` mientras `status=NUEVA`; se establece antes de pasar a `CONVERTIDA` (§6) |
| start_at | datetime | Sí | Tomado tal cual del slot de Agenda (`get_available_slots`) — nunca calculado por `CareRequest` (§6, `care-request-service-contracts.md` §3) |
| end_at | datetime | Sí | Idem — nunca `start_at + duration` calculado aquí |
| motivo | `TextField` | Sí | Texto libre |
| padecimiento | `TextField(blank=True, default="", null=False)` | No | Texto libre |
| descripcion | `TextField(blank=True, default="", null=False)` | No | Texto libre |
| status | choices (`NUEVA`, `CONVERTIDA`) | Sí | Único workflow — sin `EN_REVISION`/`ATENDIDA`/`CERRADA`/`WAITING` (`requirements.md` §12.1) |
| idempotency_key | text | No, default `""` | Mismo patrón que Fase 2/4 (§4 más abajo) |
| created_at | datetime | Sí | server-side, automático |
| updated_at | datetime | Sí | server-side, automático |

Todas las FK de `CareRequest` hacia entidades de negocio (`patient`, `created_by`,
`responsible`, `doctor`, `clinic`) usan **`on_delete=PROTECT`**, sin excepción y sin
alternativa — decisión definitiva, no "`PROTECT` o `RESTRICT`" ni "`PROTECT` o `SET_NULL`".
Motivo: preservar la trazabilidad histórica y evitar que una eliminación administrativa deje una
`CareRequest` parcialmente descontextualizada.

`motivo`, `padecimiento` y `descripcion` son texto libre — **no** se modelan como `choices`,
`enum`, catálogo ni FK a un catálogo. Solo `motivo` es obligatorio.

No existe un campo de edición de contenido posterior a la creación — no hay operación funcional
de `update CareRequest` (§3 más abajo).

## 3. Relación con `Appointment` — `CareRequest` es propietaria (decisión de cierre, 2026-09-15)

**Reemplaza la versión anterior de esta sección**, que ponía la FK del lado de `Appointment`.
La relación definitiva es:

```text
CareRequest.appointment → Appointment
    OneToOneField(Appointment, on_delete=PROTECT, null=True, blank=True)
```

Cardinalidad: `CareRequest 1 ─── 0..1 Appointment`.

`Appointment` (`appointments/models.py`) **no** gana ningún campo, migración ni dependencia hacia
`care_requests` — el modelo de Fase 2 permanece exactamente como está. La relación se consulta
siempre desde `CareRequest` (`care_request.appointment`).

**Corrección de cierre (2026-09-18) — reemplaza la conclusión anterior de este párrafo, que
proponía usar el `related_name` inverso por defecto de Django sobre `Appointment` si alguna vez
se necesitara el sentido contrario:** esa propuesta quedó descartada. `related_name` se fija
explícitamente en `"+"`, que suprime por completo el accessor inverso — `Appointment` nunca
expone `.care_request`, ni con el nombre por defecto ni con uno explícito. Un `related_name`
por defecto no agrega columna ni migración en `appointments`, pero sí crea navegabilidad ORM en
el sentido `appointments → care_requests`, exactamente lo que ADR-005 §12/§44 prohíbe — la
prohibición es sobre la dirección de la dependencia, no solo sobre el esquema de base de datos,
y un accessor Python es una forma real de esa dependencia aunque no toque una columna. Ningún
código del proyecto usaba `appointment.care_request` (verificado por `grep` antes de este
cambio) — no había una necesidad legítima que este cambio rompiera.

**Por qué el cambio de dirección:** una FK en `Appointment` hacia `CareRequest` obligaría al
modelo de `appointments` a importar el modelo de `care_requests`, creando una dependencia
`appointments → care_requests` a nivel de código — exactamente lo contrario del principio ya
establecido (ADR-005 §12/§44: `care_requests` invoca a `appointments`, nunca al revés). Con la
FK del lado de `CareRequest`, `care_requests` es quien importa `Appointment` (dependencia
`care_requests → appointments`, la única dirección permitida), y `appointments` permanece
completamente ajena a Fase 5, ni siquiera a nivel de modelo — cero cambios, cero migraciones en
`appointments` para dar cabida a `CareRequest`.

Es opcional (`null=True, blank=True`) porque durante `status=NUEVA` la operación todavía no ha
creado la `Appointment`; una `CareRequest` `CONVERTIDA` sí debe tenerla siempre (§6 — invariante
transaccional).

`ClinicalDocument` (Fase 4) **no** gana una FK hacia `CareRequest` — los adjuntos se asocian a
la `Appointment` ya creada mediante la FK `ClinicalDocument.appointment` que ya existe
(`clinical_documents/models.py`/`clinical_documents/services/document.py`, verificado en código;
`care-request-service-contracts.md` §12).

### 3.1 `clinical_document_ids` — identidad estable de adjuntos (nuevo campo, corrección 2026-09-18)

```text
clinical_document_ids = ArrayField(PositiveBigIntegerField(), blank=True, default=list)
```

Hallazgo B de la auditoría: comparar/reportar los adjuntos de una `CareRequest` consultando
`ClinicalDocument.objects.filter(appointment_id=...)` es incorrecto, porque ese conjunto puede
crecer después con documentos que otro flujo agregue a la misma `Appointment` — un documento
ajeno contaminaría retroactivamente la identidad de idempotencia y el resultado de un replay.

`clinical_document_ids` guarda, una sola vez, en el momento en que `status` pasa a `CONVERTIDA`,
los `pk` exactos de los `ClinicalDocument` creados durante esa ejecución. No es una FK ni una
`ManyToManyField` hacia `ClinicalDocument` (evitaría exactamente el mismo problema del hallazgo
A, esta vez del lado de `ClinicalDocument`, y una `ManyToManyField` además crearía una tabla
intermedia nueva) — es una referencia lógica por identificador, el mismo criterio que el
proyecto ya usa en `AuditEvent.resource_id` (`medical_records/models.py`). `ArrayField` viene de
`django.contrib.postgres`, ya instalado y ya usado por `appointments` (`ExclusionConstraint`,
`DateTimeRangeField`) — no es una dependencia nueva.

Vacío (`[]`) por defecto — válido tanto para una `CareRequest` sin adjuntos como, transitoriamente,
mientras `status=NUEVA`.

## 4. Constraints

- `UniqueConstraint(fields=["created_by", "idempotency_key"], condition=~Q(idempotency_key=""),
  name="care_request_idempotency_key_unique")` — mismo patrón exacto que
  `appointment_idempotency_key_unique`/`reschedule_idempotency_key_unique`
  (`appointments/models.py`): parcial, solo aplica cuando la clave no está vacía, para no
  colisionar entre solicitudes sin clave.
- **Decisión definitiva:**
  `CheckConstraint(condition=models.Q(start_at__lt=models.F("end_at")), name="care_request_start_before_end")`
  — mismo patrón exacto ya usado en `appointments/models.py`
  (`availability_start_before_end`, sobre `Availability.start_time`/`end_time`). No es una
  invariante nueva ni una decisión distinta: es la misma protección de integridad temporal que
  el proyecto ya aplica, aplicada aquí sobre `CareRequest`. Es una invariante mínima de
  integridad, independiente de que Agenda ya valide el intervalo completo contra
  disponibilidad/conflictos (defensa en profundidad, no la autoridad — esa sigue siendo Agenda).

No se agregan índices adicionales sin una consulta real que los justifique — las consultas ya
previstas (conteo de `CareRequest` por actor en la última hora para rate limiting,
`requirements.md` §12.3; búsqueda por `(created_by, idempotency_key)` para replay) quedan
cubiertas por el índice implícito del `UniqueConstraint` de arriba y por un índice simple sobre
`(created_by, created_at)` si el conteo por ventana de tiempo lo requiere — decisión de
implementación normal, no arquitectónica.

## 5. Nulls y defaults

- `responsible`: FK nullable — `NULL` por defecto; presente solo si quien solicita es un
  responsable. (Aquí sí aplica `NULL`: es una FK, no un campo de texto — no hay ambigüedad
  posible entre "sin responsable" y "cadena vacía".)
- `padecimiento`, `descripcion`: **una sola semántica, sin ambigüedad** — `blank=True,
  default="", null=False`, igual que el resto de los campos de texto opcionales ya existentes en
  el proyecto (`medical_records/models.py`: `reason_for_visit`, `present_illness`,
  `physical_exam`, `assessment`, `plan`, `observations`, etc., todos `blank=True, default=""`,
  ninguno `null=True`). "Vacío" se representa siempre como `""`, nunca como `NULL` — no hay dos
  formas de representar "sin dato" para estos campos.
- `idempotency_key`: `""` por defecto (nunca `NULL`), igual que `Appointment.idempotency_key` —
  necesario para que la condición del `UniqueConstraint` parcial funcione igual que en
  `appointments`.
- `status`: `NUEVA` al crear; nunca `NULL`.

## 6. Integridad referencial

- `patient`, `created_by`, `doctor`, `clinic` — obligatorios, **`on_delete=PROTECT`** (decisión
  única y definitiva, sin alternativa — §2). `CareRequest` es información histórica de una
  solicitud; no debe desaparecer ni quedar huérfana si esas entidades cambian, y la eliminación
  de un `Patient`/`Doctor`/`Clinic`/`User` referenciado por una `CareRequest` existente debe
  rechazarse en base de datos.
- `responsible` — opcional, también **`on_delete=PROTECT`** cuando está presente. Cuando está
  presente, debe existir una `ResponsiblePatientRelationship` con `status=ACTIVE`
  (`ResponsiblePatientRelationship.Status.ACTIVE`, `patients/models.py`) entre `responsible` y
  `patient` (ADR-004, `requirements.md` §5). Esta validación se hace en el servicio/autorización
  de negocio, **no** como `CheckConstraint` de PostgreSQL — requeriría consultar otra tabla, algo
  que un `CheckConstraint` no puede expresar.
- `appointment` — también **`on_delete=PROTECT`**: si alguna vez existiera una operación de
  borrado de `Appointment` (no existe hoy en Fase 2), no debe poder ejecutarse silenciosamente
  dejando una `CareRequest` `CONVERTIDA` sin su cita asociada.

### Invariante transaccional — `CONVERTIDA` implica `appointment` no nulo

**Debe ser imposible que exista una `CareRequest` persistida con `status=CONVERTIDA` sin
`appointment` asignado.** Esto se garantiza dentro de la misma transacción de
`CareRequestService` (`care-request-service-contracts.md` §4/§7/§9): `CareRequest.appointment`
se asigna inmediatamente después de que `AppointmentService.create_appointment_from_hold` crea
la `Appointment`, y la transición a `CONVERTIDA` ocurre **después** de esa asignación, ambas
dentro del mismo `COMMIT` — si cualquier paso falla antes de llegar a `CONVERTIDA`, la
transacción entera revierte (D9/D15) y no queda una fila a medio camino. Es una invariante de
secuencia transaccional, no una validación posterior. Un `CheckConstraint` sobre las propias
columnas de `CareRequest` (`status` + `appointment_id`, sin consultar otra tabla) sería una
defensa en profundidad razonable y consistente con el estilo del proyecto — se deja como opción
de diseño técnico posterior, no como decisión nueva de esta revisión.

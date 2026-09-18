# Fase 5 — Dominio de `CareRequest`

**Estado:** diseño técnico cerrado
**Fecha de referencia:** 2026-09-15

## 1. Propósito

`CareRequest` representa la intención explícita de un actor autenticado de reservar una cita concreta. Es una operación de origen, no una cita alternativa ni una cola de solicitudes.

La entidad `Appointment` continúa representando la cita efectiva.

## 2. Responsabilidad del dominio

`CareRequest` es responsable de:

- registrar quién inicia la operación;
- identificar al paciente para quien se solicita la cita;
- conservar el contexto solicitado (médico, consultorio, intervalo y motivo);
- orquestar la conversión inmediata hacia `Appointment`;
- aplicar el límite de creación definido para el actor;
- conservar la identidad idempotente de la operación, cuando se proporciona;
- conservar la trazabilidad de la `Appointment` resultante.

`CareRequest` no es responsable de calcular disponibilidad, resolver concurrencia de Agenda ni representar la cita efectiva.

## 3. Participantes del dominio

### Patient

Paciente para quien se solicita la cita. Es obligatorio.

### Created By / actor

`created_by` identifica el `User` autenticado que ejecuta la operación.

Puede ser:

- el propio paciente; o
- un responsable autorizado que solicita por un paciente relacionado.

### Responsible

Es opcional.

Cuando el actor es el propio paciente:

```text
patient = paciente
created_by = usuario del paciente
responsible = NULL
```

Cuando el actor es un responsable:

```text
patient = paciente objetivo
created_by = usuario del responsable
responsible = responsable
```

En el segundo caso debe existir una `ResponsiblePatientRelationship` válida con estado `ACTIVE`.

### Doctor / Clinic

La solicitud identifica explícitamente el médico y consultorio seleccionados. Ambos son obligatorios.

### Appointment

Es el resultado de la conversión exitosa y se referencia desde:

```text
CareRequest.appointment
```

La relación es `OneToOneField` opcional porque una `CareRequest` recién creada aún no tiene cita durante la operación.

## 4. Lenguaje libre

Los tres campos de contenido son texto abierto:

```text
motivo
padecimiento
descripcion
```

Solamente `motivo` es obligatorio.

No son catálogos, choices, enums ni ForeignKey.

## 5. Estados

El dominio tiene exclusivamente:

```text
NUEVA
CONVERTIDA
```

### NUEVA

Estado transitorio de una operación que está siendo procesada. No significa pendiente de aprobación o revisión.

### CONVERTIDA

La `Appointment` fue creada correctamente, la relación `CareRequest.appointment` fue establecida y los adjuntos de la operación fueron procesados satisfactoriamente antes del commit.

Una `CareRequest` convertida permanece `CONVERTIDA` aunque la `Appointment` cambie posteriormente de estado o sea cancelada; la cancelación pertenece al ciclo de vida de `Appointment`.

## 6. Invariantes

1. `motivo` nunca puede estar vacío en una creación válida.
2. `start_at < end_at`.
3. Una `CareRequest` puede tener como máximo una `Appointment`.
4. Una `CareRequest` `CONVERTIDA` debe tener `appointment` no nulo.
5. Una `Appointment` puede existir sin una `CareRequest`.
6. Una operación fallida no deja una `CareRequest` persistida como intento fallido.
7. Una clave de idempotencia, cuando existe, pertenece al namespace de `CareRequest`.
8. La existencia de una relación `responsible` requiere autorización válida sobre el paciente destino.
9. La identidad de adjuntos de una `CareRequest` `CONVERTIDA` (`clinical_document_ids`) es fija desde el momento de la conversión — un `ClinicalDocument` agregado después por otro flujo a la misma `Appointment` nunca forma parte de esa identidad (corrección 2026-09-18, hallazgo B).

## 7. Dependencias de dominio

La dirección permitida es:

```text
care_requests → appointments
```

No existe dependencia inversa:

```text
appointments ↛ care_requests
```

`AppointmentService` permanece agnóstico de `CareRequest`.

**Precisión de cierre (2026-09-18):** "sin dependencia inversa" incluye la navegabilidad del
ORM, no solo imports de módulos ni migraciones. `CareRequest.appointment` se declara con
`related_name="+"` precisamente para que `Appointment` nunca exponga un accessor `.care_request`
— un `related_name` por defecto no habría tocado ni una columna ni una migración de
`appointments`, pero sí habría permitido navegar desde una `Appointment` hasta su `CareRequest`
en código, que es exactamente la dependencia inversa que este principio prohíbe. Ver
`care-request-data-model.md` §3 para el detalle técnico.

## 8. Integraciones

### Agenda

CareRequest utiliza el slot generado por Agenda y delega en ella la validación definitiva y la reserva.

### ClinicalDocument

Los adjuntos representan documentos y permanecen bajo responsabilidad de `ClinicalDocument`. Durante Fase 5 se asocian a la `Appointment` resultante, no directamente a `CareRequest`.

## 9. Ausencia de capacidades no requeridas

El dominio no contiene:

- workflow de aprobación;
- triage;
- recomendaciones automáticas;
- check-in/waiting room;
- edición independiente;
- cancelación propia;
- estado de rechazo persistente.

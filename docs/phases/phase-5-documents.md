# Fase 5 — Paquete funcional de `CareRequest`

**Estado:** diseño técnico cerrado (`TECHNICAL DESIGN FREEZE`)
**Fecha de referencia:** 2026-09-15

## 1. Propósito

Fase 5 incorpora `CareRequest` como una operación de solicitud directa de una cita concreta. No crea un segundo sistema de agenda: `Appointment` sigue siendo la cita efectiva y Agenda de Fase 2 continúa siendo la única fuente de verdad para disponibilidad, Hold, concurrencia y reserva.

La app `care_requests` orquesta la operación y reutiliza servicios existentes de Fase 2 y Fase 4.

Principio rector:

> **CareRequest orquesta; Agenda reserva; Appointment representa la cita; ClinicalDocument gestiona los archivos.**

## 2. Alcance funcional

Fase 5 cubre:

- creación de una `CareRequest` por un actor autenticado;
- selección de médico, consultorio y slot concreto;
- motivo obligatorio y texto libre opcional para padecimiento y descripción;
- conversión automática e inmediata a `Appointment` cuando Agenda acepta el slot;
- asociación de la `CareRequest` con la `Appointment` mediante `CareRequest.appointment`;
- adjuntos reutilizando `ClinicalDocument`;
- idempotencia opcional mediante `Idempotency-Key`;
- rate limiting de creación;
- autorización por objeto conforme a ADR-004;
- comportamiento transaccional y compensación de archivos definidos en el diseño técnico.

## 3. Fuera de alcance

No forman parte de Fase 5:

- aprobación o revisión médica previa;
- bandeja de solicitudes pendientes;
- estados `EN_REVISION`, `ATENDIDA`, `CERRADA`, `WAITING` u otros equivalentes;
- cancelación de `CareRequest` — la cancelación pertenece a `Appointment`;
- diagnóstico automático, triage automático o recomendaciones clínicas automáticas;
- sala de espera/check-in;
- antivirus o ClamAV/proveedor externo;
- Redis, Celery, colas o microservicios para resolver estos requisitos;
- edición independiente posterior de una `CareRequest`;
- una arquitectura de almacenamiento de archivos distinta de `ClinicalDocument`.

La sala de espera/check-in está fuera del alcance de TeCuidoApp, no solamente de Fase 5 (`requirements.md` §41).

## 4. Resultado esperado

El camino exitoso es único:

```text
NUEVA → CONVERTIDA
        +
Appointment creada
```

Si cualquier validación u operación falla, la transacción se revierte y no queda una `CareRequest` persistida como intento fallido.

## 5. Dependencias de fases anteriores

### Fase 2 — Agenda

Se reutilizan sin duplicación:

- `AvailabilityService` / `get_available_slots()` para generar los slots visibles;
- `HoldService.create_hold()` para reservar transaccionalmente el intervalo;
- `AppointmentService.create_appointment_from_hold()` para convertir el Hold en `Appointment`;
- las reglas existentes de disponibilidad, DoctorClinic, duración, conflictos, concurrencia y timezone.

`care_requests` depende de `appointments`; `appointments` no depende de `care_requests`.

### Fase 4 — ClinicalDocument

Se reutiliza:

- `ClinicalDocumentService.upload()`;
- almacenamiento privado;
- validación de contenido/tipos;
- límite de tamaño existente;
- asociación `ClinicalDocument.appointment`.

Fase 5 agrega únicamente el máximo de 5 archivos por `CareRequest`.

## 6. Documentos normativos de Fase 5

| Documento | Responsabilidad |
|---|---|
| `phase-5-documents.md` | Alcance y mapa del paquete documental |
| `care-request-domain.md` | Concepto, responsabilidades e invariantes del dominio |
| `care-request-data-model.md` | Persistencia, campos, relaciones y constraints |
| `care-request-workflow.md` | Flujo técnico completo y caminos de error |
| `care-request-permissions.md` | Reglas de autorización de CareRequest |
| `care-request-service-contracts.md` | Contratos internos de servicio |
| `care-request-api-contracts.md` | Contrato HTTP externo |
| `care-request-security-and-privacy.md` | Seguridad y privacidad |
| `care-request-ux.md` | Flujo de interacción |
| `care-request-screens.md` | Especificación de pantallas |
| `care-request-audit-and-history.md` | Auditoría y trazabilidad |
| `phase-5-testing-strategy.md` | Estrategia y evidencia de pruebas |
| `phase-5-documentation-index.md` | Índice y precedencia documental |
| `phase-5-design-freeze.md` | Certificación del cierre de diseño |

## 7. Precedencia documental

Cuando exista solapamiento:

1. `requirements.md` define el requisito funcional global.
2. Los ADR definen decisiones arquitectónicas aceptadas.
3. `care-request-data-model.md` define la persistencia de CareRequest.
4. `care-request-service-contracts.md` define la orquestación interna.
5. `care-request-api-contracts.md` define la frontera HTTP.
6. Los documentos UX/screen detallan la interacción sin modificar reglas de dominio.

Ningún documento de UX o API puede introducir una regla de negocio incompatible con los requisitos o ADR aceptados.

## 8. Criterio de implementación

Un desarrollador debe poder implementar Fase 5 reutilizando primero los componentes existentes. Una decisión ya cerrada no debe volver a resolverse en código.

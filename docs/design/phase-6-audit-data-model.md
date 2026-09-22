# Fase 6 — Audit Data Model

**Estado:** Diseño técnico derivado — **implementado** (ver `docs/phases/phase-6-implementation-summary.md`).

## 1. Reutilización obligatoria

El modelo existente `medical_records.AuditEvent` permanece como fuente de verdad de persistencia.

No se crea `AuditLog`, `AuditRecord` ni otra tabla paralela con la misma función.

## 2. Estructura existente relevante

La implementación actual ya dispone de:

- `occurred_at` asignado por servidor;
- `actor` con protección referencial;
- `actor_role`;
- `action`;
- `result`;
- `reason_code`;
- `resource_type`;
- `resource_id`;
- referencias opcionales a Patient, Appointment, ClinicalEncounter, Prescription, StudyOrder y ClinicalDocument;
- índices por paciente/fecha, actor/fecha y acción/fecha.

Fase 6 debe aprovechar esta estructura antes de agregar campos nuevos.

## 3. Extensiones permitidas

Una extensión solo está justificada si un requisito de F6 no puede expresarse con:

- action;
- result;
- resource;
- actor;
- reason_code;
- referencias existentes.

No introducir `metadata` genérico como depósito de datos arbitrarios.

## 4. Inmutabilidad

La auditoría es append-only a nivel funcional:

- no update de eventos;
- no delete de eventos por usuarios normales;
- no edición mediante Admin.

## 5. Retención

La retención es indefinida.

No existe job automático de limpieza por edad.

La depuración, cuando se requiera liberar espacio, es un procedimiento manual y explícitamente fuera de la automatización de F6.

## 6. Índices

Conservar los índices existentes y solo agregar nuevos cuando la consulta administrativa real los justifique.

## 7. Migraciones

Cualquier acción faltante en `AuditEvent.Action`, `Result` o `ResourceType` que requiera cambio de choices/constraints debe llevar la migración Django correspondiente y sus pruebas.

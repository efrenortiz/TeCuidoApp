# Fase 6 — Consent Service Contracts

**Estado:** Diseño técnico derivado — **implementado** (ver `docs/phases/phase-6-implementation-summary.md`).

## 1. `record_acceptance(...)`

Registra una aceptación de documento de plataforma para un usuario autenticado.

Entrada lógica:

```text
user
policy_type
policy_version
accepted_at
```

`accepted_at` es asignado por el servidor salvo que una capa superior del proyecto ya establezca otra convención.

## 2. `get_current_acceptance(...)`

Devuelve la aceptación de la versión relevante para un usuario sin permitir que el cliente modifique el historial.

## 3. `has_accepted_version(...)`

Consulta booleana para flujos que necesiten comprobar si existe aceptación de una versión concreta.

## 4. Idempotencia

`phase-6-consent-domain.md` §8 cierra la unicidad para esta combinación:
`UNIQUE(user, policy_type, policy_version)`. Si el mismo usuario ya aceptó exactamente el mismo
documento y versión, repetir `record_acceptance(...)` no produce un segundo registro ni un error —
devuelve la aceptación ya existente (comportamiento `get_or_create`, mismo patrón ya usado por
`medical_records.services.record.get_or_create_for_patient`).

## 5. Cambios de versión

Aceptar una versión nueva nunca debe reescribir la anterior.

## 6. Errores

Códigos mínimos:

- policy inexistente;
- version inexistente;
- user no autenticado.

No existe un código de error "duplicate acceptance": por la unicidad `get_or_create` de §4, una
repetición exacta es una operación válida e idempotente, no un conflicto.

## 7. Auditoría

La aceptación puede generar una traza de auditoría administrativa/seguridad si el catálogo definitivo de Fase 6 la incluye. No debe almacenar el texto completo del documento en `AuditEvent`.

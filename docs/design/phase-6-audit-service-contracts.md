# Fase 6 — Audit Service Contracts

**Estado:** Diseño técnico derivado — **implementado** (ver `docs/phases/phase-6-implementation-summary.md`).

## 1. Entrada única

Las apps de dominio deben emitir auditoría mediante una frontera central de servicio, reutilizando el patrón existente en `medical_records.services.audit`.

No dispersar la creación manual de `AuditEvent` en vistas, templates o código de infraestructura.

## 2. Contratos

### `record_event(...)`

Uso preferente para mutaciones dentro de su límite transaccional.

Requisito: el actor real es obligatorio.

### `safe_record_event(...)`

Uso para lecturas cuando el proyecto ya haya establecido que la auditoría auxiliar no debe bloquear una lectura legítima por una falla del mecanismo de auditoría.

No debe ocultar bugs de identidad como `actor=None`.

### `list_audit_events(...)`

Consulta exclusivamente administrativa, con filtros mínimos y paginación estable.

### `record_denied(...)`

Conveniencia para registrar rechazos del catálogo base con `result=DENIED` o `REJECTED` según la semántica del caso.

## 3. Transacciones

Para una mutación:

```text
mutation + audit success
        │
        └── mismo límite transaccional
```

El propósito es impedir un cambio persistido sin el evento de éxito correspondiente cuando la auditoría es requisito obligatorio de esa mutación.

## 4. Rollback

Un evento exitoso no debe sobrevivir a un rollback de la operación que pretendía describir.

## 5. Rechazos

Los rechazos deben auditarse después de haber identificado el motivo seguro del rechazo y sin almacenar información clínica adicional.

## 6. Consulta administrativa

El servicio debe validar explícitamente `can_view_audit_log` o el equivalente centralizado. No depender únicamente de ocultar rutas en UI.

## 7. Filtrado

Soportar, como mínimo cuando sea necesario:

- paciente;
- acción;
- resultado;
- intervalo temporal.

Orden estable recomendado:

```text
occurred_at DESC, id DESC
```

## 8. No autorización

El servicio de auditoría nunca decide si una operación clínica puede ejecutarse. Esa decisión pertenece al servicio de dominio/autorización correspondiente.

# Fase 6 — Screens

**Estado:** Diseño técnico derivado — **implementado** (ver `docs/phases/phase-6-implementation-summary.md`).

## 1. Pantallas de aceptación de documentos

### Estado: documento pendiente de aceptación

Debe mostrar:

- documento;
- versión;
- acción de lectura;
- acción explícita de aceptación.

### Estado: aceptado

Mostrar estado de aceptación sin permitir editar el registro histórico.

## 2. Pantalla administrativa de audit trail

### Acceso

Solo Administrador autorizado.

### Filtros

- fecha desde/hasta;
- acción;
- resultado;
- paciente cuando exista filtro autorizado.

### Tabla mínima

| Columna | Contenido |
|---|---|
| Fecha/hora | `occurred_at` |
| Actor | Identificador seguro |
| Rol | Snapshot del rol |
| Acción | `AuditEvent.Action` |
| Resultado | `AuditEvent.Result` |
| Recurso | Tipo + ID |
| Motivo | `reason_code` seguro |

### Estados

- cargando;
- resultados;
- sin resultados;
- error de consulta;
- acceso no autorizado.

## 3. Pantallas de notificaciones

No se requiere una bandeja compleja de notificaciones en Fase 6 salvo requerimiento superior.

Cualquier pantalla de diagnóstico de notificaciones, si se implementa, debe ser administrativa/operativa y no contener datos clínicos innecesarios.

## 4. No existe pantalla de opt-out

La ausencia de configuración de opt-out es una regla de producto, no un descuido de UX.

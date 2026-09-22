# Fase 6 — Audit API Contracts

**Estado:** Diseño técnico derivado — **implementado** (ver `docs/phases/phase-6-implementation-summary.md`).

## 1. Audiencia

La API de consulta del audit trail es administrativa.

Solo un Administrador autorizado puede usarla.

## 2. Operación de consulta

Contrato conceptual:

```text
GET /.../audit/events
```

El path exacto debe seguir el namespace/API style existente del proyecto; este documento fija la semántica, no obliga a una URL si existe una convención superior.

## 3. Filtros

Parámetros opcionales:

- `patient_id`;
- `action`;
- `result`;
- `date_from`;
- `date_to`;
- `page` / `page_size` según el patrón API existente.

## 4. Respuesta

Cada evento puede exponer:

- id;
- occurred_at;
- actor identifier seguro;
- actor_role;
- action;
- result;
- reason_code seguro;
- resource_type;
- resource_id;
- referencias funcionales mínimas necesarias para consulta.

No exponer contenido clínico ni cuerpos de solicitudes.

## 5. Autorización

Una petición de no administrador debe producir el mismo resultado de seguridad ya establecido en la API del proyecto para recursos no autorizados, sin filtrar información del audit trail.

## 6. No mutaciones

No se ofrecen endpoints públicos de:

- crear manualmente un evento;
- editar un evento;
- borrar un evento.

La creación se realiza desde la frontera de servicios de auditoría.

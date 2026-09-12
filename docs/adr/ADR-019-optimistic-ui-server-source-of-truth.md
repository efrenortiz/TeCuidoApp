# ADR-019 — Server and Database as Clinical Source of Truth

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / UI / Concurrencia

## 1. Contexto

Una consulta puede tener guardados parciales, reintentos, doble clic y concurrencia entre solicitudes. El cliente no puede decidir por sí mismo si una consulta está abierta o completada.

## 2. Decisión

Para estado y datos clínicos persistidos, el servidor y la base de datos son la fuente de verdad.

La UI puede mantener estado temporal de formulario, pero solo considera confirmado aquello que el servidor haya aceptado.

No se requiere autosave en Fase 3.

## 3. Reglas

- Un cambio de estado solo se acepta en servidor.
- Un botón deshabilitado no sustituye una validación servidor.
- El último guardado confirmado es el último estado garantizado.
- Una respuesta de conflicto/estado final obliga a refrescar el contexto clínico cuando sea necesario.
- La concurrencia crítica se resuelve con transacción, constraints y locking apropiado.

## 4. Razón

Evita que una pestaña del navegador tenga autoridad ficticia sobre un recurso clínico compartido.

## 5. Consecuencias

Positivas:
- comportamiento consistente entre navegadores y API;
- pruebas de concurrencia verificables;
- menor riesgo de pérdida o sobrescritura silenciosa.

Negativas:
- requiere feedback de UI para guardados exitosos o rechazados;
- el usuario puede perder cambios no guardados al abandonar la pantalla.

## 6. Alternativas rechazadas

### Autosave obligatorio
**Rejected.** Aumentaría llamadas, estados intermedios y complejidad sin ser requisito F3.

### Frontend como autoridad de estados
**Rejected.** No constituye una frontera de seguridad o integridad.

## 7. Relación

Complementa `ADR-010`, `ADR-018`, `clinical-encounter-workflow.md` y `phase-3-testing-strategy.md`.

## 8. Estado

**Accepted.**

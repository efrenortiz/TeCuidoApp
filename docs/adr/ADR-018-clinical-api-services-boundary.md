# ADR-018 — Clinical Services as Application Boundary

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Servicios / API

## 1. Contexto

El sistema tiene UI, API, servicios de dominio y persistencia. Las invariantes clínicas no deben depender de que una interfaz concreta las aplique correctamente.

## 2. Decisión

Los casos de uso clínicos deberán pasar por servicios de dominio/aplicación que concentren autorización, transacciones e invariantes.

Patrón:

```text
UI / API
   ↓
Clinical Service
   ↓
Authorization
   ↓
Transaction
   ↓
ORM / PostgreSQL
```

Los endpoints no ejecutarán directamente secuencias de ORM que cambien estados clínicos críticos.

## 3. Operaciones núcleo

Como mínimo:

- `start_encounter`;
- `save_encounter`;
- `complete_encounter`;
- lectura de encuentro;
- lectura de expediente/historial;
- actualización de datos longitudinales cuando exista contrato.

## 4. Razón

Una sola implementación de cada caso de uso reduce divergencias entre HTML, API y futuras interfaces.

## 5. Consecuencias

Positivas:
- reglas centralizadas;
- tests reutilizables;
- menor riesgo de bypass.

Negativas:
- mayor disciplina de arquitectura;
- algunos endpoints serán más delgados que el código Django tradicional.

## 6. Alternativas rechazadas

### Lógica de negocio directamente en views
**Rejected.** Facilita duplicación y hace más difícil proteger la misma regla desde API y UI.

### ORM directo desde templates o JavaScript
**Rejected.** No es posible ni seguro como frontera del dominio.

## 7. Relación

Complementa `ADR-005` y `ADR-006`, y define la arquitectura de implementación de `clinical-service-contracts.md` y `clinical-api-contracts.md`.

## 8. Estado

**Accepted.**

# ADR-012 — Explicit Clinical Fields

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Modelo de datos clínico

## 1. Contexto

Fase 3 necesita almacenar información clínica genérica con estructura clara. Un campo JSON universal sería flexible, pero dificultaría validación, evolución controlada, permisos y consultas.

## 2. Decisión

Los campos clínicos núcleo de Fase 3 se modelarán como campos explícitos y tipados en el esquema de datos.

Para `ClinicalEncounter`, los cinco campos mínimos son:

- `reason_for_visit` — Motivo de consulta
- `present_illness` — Padecimiento actual
- `physical_exam` — Exploración física
- `assessment` — Evaluación / diagnóstico
- `plan` — Plan / indicaciones

Los campos opcionales también deberán ser explícitos cuando se incorporen al modelo aprobado.

## 3. JSON

No se utilizará un campo `clinical_data = JSON` como mecanismo general de expansión del núcleo F3.

JSON puede utilizarse en una futura extensión aislada cuando exista una razón arquitectónica concreta y un contrato propio.

## 4. Razón

La estructura explícita facilita:

- constraints y nullability claros;
- validación de contenido;
- serialización estable;
- pruebas de contrato;
- migraciones controladas;
- lectura y mantenimiento por desarrolladores.

## 5. Consecuencias

El esquema requerirá migraciones cuando se agreguen nuevas categorías clínicas. Eso se acepta como costo de mantener un dominio explícito.

## 6. Alternativa rechazada

### JSON como contenedor principal
**Rejected.** Pospondría decisiones de dominio y permitiría estructuras inconsistentes entre consultas.

## 7. Relación

Complementa `clinical-data-model.md` y será relevante para futuras ADRs de especialidades.

## 8. Estado

**Accepted.**

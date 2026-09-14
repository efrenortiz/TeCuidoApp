# ADR-016 — No Reopen or Functional Delete of Clinical History

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Integridad histórica

## 1. Contexto

Los registros clínicos tienen valor histórico y regulatorio. Fase 3 requiere que un encuentro completado no pueda reabrirse ni editarse.

## 2. Decisión

Una vez que `ClinicalEncounter` pasa a `COMPLETED`:

- queda bloqueado;
- no puede reabrirse;
- no puede editarse;
- no admite `DELETE` funcional;
- su contenido debe permanecer como parte del historial clínico.

`MedicalRecord` tampoco tendrá eliminación destructiva por operación clínica ordinaria.

## 3. Correcciones futuras

Fase 3 no implementará enmiendas ni versionado. Si una fase futura necesita corregir información cerrada, deberá introducir un mecanismo explícito y auditable de enmienda/versionado mediante una nueva decisión arquitectónica.

## 4. Razón

La inmutabilidad evita que el histórico cambie silenciosamente y simplifica la auditoría.

## 5. Consecuencias

Positivas:
- trazabilidad fuerte;
- reglas de estado simples;
- menor riesgo de pérdida histórica.

Negativas:
- errores clínicos posteriores requieren un mecanismo futuro de corrección, no un simple update.

## 6. Alternativas rechazadas

### Editar libremente después de completar
**Rejected.** Destruye la semántica histórica.

### Soft delete como forma de corrección
**Rejected.** Ocultar un registro no constituye una enmienda clínica válida.

## 7. Relación

Complementa `ADR-010` y `ADR-017`.

## 8. Estado

**Accepted.**

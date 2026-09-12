# ADR-017 — Clinical History and Audit Trail Are Separate

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Auditoría / Trazabilidad

## 1. Contexto

El contenido clínico histórico y el registro técnico de acciones responden preguntas diferentes.

## 2. Decisión

Se mantendrán dos conceptos separados:

```text
Clinical History
    = qué información clínica quedó registrada

Audit Trail
    = quién hizo qué operación, cuándo y con qué resultado
```

Un `AuditEvent` no sustituye a `ClinicalEncounter` ni a `MedicalRecord`.

El historial clínico no se reconstruirá únicamente a partir de logs.

## 3. Auditoría mínima

Las operaciones clínicas relevantes podrán generar eventos como:

- `CREATE_MEDICAL_RECORD`;
- `READ_MEDICAL_RECORD`;
- `READ_CLINICAL_HISTORY`;
- `START_ENCOUNTER`;
- `SAVE_ENCOUNTER`;
- `COMPLETE_ENCOUNTER`;
- `ACCESS_DENIED`.

Los eventos no deben almacenar innecesariamente el contenido clínico completo cuando basta con identificar recurso, actor, instante y resultado.

## 4. Razón

La separación reduce acoplamiento, evita duplicación de datos clínicos y permite políticas de retención diferentes.

## 5. Consecuencias

La auditoría añade persistencia adicional y requiere controles de acceso propios. A cambio, proporciona trazabilidad de acceso y modificación.

## 6. Alternativa rechazada

### Usar AuditLog como expediente
**Rejected.** Los logs son eventos técnicos; no constituyen una historia clínica legible y estable.

## 7. Relación

Complementa `ADR-016` y el documento `clinical-audit-and-history.md`.

## 8. Estado

**Accepted.**

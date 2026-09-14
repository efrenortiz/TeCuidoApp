# Fase 4 — Auditoría e historial documental

## 1. Principio

Se conserva la separación de Fase 3:

```text
Clinical History ≠ Audit Trail
```

## 2. Operaciones auditables

Como mínimo:

- ISSUE_PRESCRIPTION;
- ISSUE_STUDY_ORDER;
- UPLOAD_CLINICAL_DOCUMENT;
- GENERATE_CLINICAL_DOCUMENT;
- READ_CLINICAL_DOCUMENT;
- DOWNLOAD_CLINICAL_DOCUMENT;
- CREATE_DOCUMENT_VERSION;
- VOID_PRESCRIPTION;
- VOID_STUDY_ORDER;
- acciones administrativas sensibles relacionadas.

Los nombres concretos deben seguir la convención del AuditEvent existente.

## 3. Actor

Las operaciones humanas requieren actor real. No usar UNKNOWN para esconder una pérdida de contexto.

## 4. Recurso auditado

Registrar tipo y referencia del recurso, no su contenido binario.

## 5. Historial

El historial documental se obtiene de las entidades y sus versiones. No se reconstruye a partir del audit trail.

## 6. Versiones

Cada versión mantiene actor, timestamp y motivo cuando corresponda.

## 7. Anulación

El evento de anulación debe identificar el recurso y el motivo sin eliminar el registro anterior.

## 8. Lectura/descarga

**Corrección de consistencia (2026-09-11):** esta sección decía que las lecturas sensibles "pueden"
auditarse, en aparente contradicción con §2, que lista `READ_CLINICAL_DOCUMENT` como auditable "como
mínimo". Se corrige: la lectura de un `ClinicalDocument` sensible SIEMPRE intenta auditarse
(`READ_CLINICAL_DOCUMENT`), con la misma tolerancia a fallo del mecanismo auxiliar que ya rige las
lecturas clínicas en Fase 3 (AH-089: un fallo del registro de auditoría no bloquea la lectura, pero
el intento de auditar no es opcional). La descarga (`DOWNLOAD_CLINICAL_DOCUMENT`) se audita siempre,
sin excepción, por ser una operación de mayor sensibilidad (exposición del binario).

## 9. Privacidad

No almacenar el binario ni el contenido clínico completo en AuditEvent.

## 10. Concurrencia

Un evento de auditoría de éxito debe representar una operación realmente persistida. Los fallos tolerables del mecanismo de auditoría conservan la política de Fase 3.

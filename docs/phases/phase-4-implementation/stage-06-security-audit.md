# Stage 6 — Auditoría y seguridad

## Objetivo

Verificar explícitamente (no sólo asumir por diseño) que la auditoría de Fase 4 es correcta,
completa y consistente con la política ya cerrada de Fase 3, y que no existe ninguna vía por la
que un evento clínico se registre con `actor` nulo o exponga contenido sensible.

## Alcance

Verificación y tests dedicados sobre lo ya implementado en Stages 2-5 (no se agregó código de
producción nuevo, salvo lo que los propios tests revelaron — ver "Problemas encontrados" de
Stage 5, ya corregido ahí).

## Implementación realizada

- `prescriptions/tests/test_audit.py`, `study_orders/tests/test_audit.py`,
  `clinical_documents/tests/test_audit.py`: 20 tests nuevos verificando, por cada acción
  auditable mínima de `phase-4-audit-and-history.md` §2 (`ISSUE_PRESCRIPTION`,
  `ISSUE_STUDY_ORDER`, `UPLOAD_CLINICAL_DOCUMENT`, `GENERATE_CLINICAL_DOCUMENT`,
  `READ_CLINICAL_DOCUMENT`, `DOWNLOAD_CLINICAL_DOCUMENT`, `CREATE_DOCUMENT_VERSION`,
  `VOID_PRESCRIPTION`, `VOID_STUDY_ORDER`, `VOID_CLINICAL_DOCUMENT`) que:
  - el evento `SUCCESS` existe, con `actor` igual al usuario autenticado real (nunca un sustituto);
  - el evento `DENIED` también existe cuando corresponde, con el mismo `actor` real;
  - los eventos generados por una emisión (`ISSUE_*`) y su documento (`GENERATE_CLINICAL_DOCUMENT`)
    quedan correlacionados por `clinical_encounter`/`resource_id`;
  - ningún evento contiene contenido clínico (nombres de medicamentos, etc.), verificado tanto por
    valor como estructuralmente (`AuditEvent` no tiene ningún campo de tipo archivo/binario).
- Verificación explícita (no asumida) de que `Prescription.get()`/`StudyOrder.get()` NO generan un
  evento de auditoría de lectura — decisión ya cerrada en `phase-4-audit-and-history.md` §2 (esas
  dos acciones no están en la lista mínima auditable; sólo la lectura/descarga de
  `ClinicalDocument`, por tratarse de un binario, lo está).
- Test explícito de que `actor=None` sigue siendo rechazado con `ValueError` por el mismo guard de
  `medical_records.services.audit` ya endurecido durante el cierre de Fase 3 (hallazgo
  `AuditEvent.actor_id`) — confirma que ese endurecimiento protege también a los nuevos llamadores
  de Fase 4 sin necesitar ningún cambio adicional.

## Decisiones aplicadas

- **`Clinical History ≠ Audit Trail` preservado sin cambios**: `Prescription`/`StudyOrder`/
  `ClinicalDocument` (con sus versiones) son la historia clínica navegable; `AuditEvent` (mismo
  modelo de Fase 3, con las 10 acciones/3 tipos de recurso nuevos) sigue siendo el único registro
  de auditoría — ningún dato clínico se reconstruye a partir de él (verificado: `AuditEvent` no
  tiene campos de contenido clínico, sólo referencias por FK/id).
- **Ningún archivo público**: verificado (ver Stage 3/4) que `CLINICAL_DOCUMENTS_STORAGE_ROOT` no
  está enlazado a ninguna URL (`urls.py` completo revisado); toda lectura pasa por
  `ClinicalDocumentDownloadView`, que reautoriza en cada solicitud.
- **`storage_key` nunca expuesto**: verificado en `prescriptions/tests/test_api.py`
  (`assertNotIn("storage_key", body)`) y por inspección de los tres serializadores de API.

## Archivos creados

- `prescriptions/tests/test_audit.py`, `study_orders/tests/test_audit.py`,
  `clinical_documents/tests/test_audit.py`.

## Archivos modificados

Ninguno de producción (esta etapa fue de verificación; los 2 bugs reales que salieron a la luz
durante Stage 5 ya se corrigieron ahí, no aquí).

## Migraciones

Ninguna.

## Tests ejecutados

```bash
python manage.py test prescriptions study_orders clinical_documents -v 2
```

## Resultado de tests

```text
Ran 152 tests in 120.551s
OK
```

(20 tests de auditoría nuevos + 132 de Stages 1-5 → 152 tests de Fase 4 hasta este punto).

## Validaciones manuales

No aplica (cubierto por la validación de navegador de Stage 5, que ya ejercitó el flujo real de
extremo a extremo bajo el cual se generan estos mismos eventos).

## Problemas encontrados

Ninguno nuevo en esta etapa — la instrumentación de auditoría ya estaba correctamente implementada
desde Stage 2 (siguiendo el patrón ya establecido en Fase 3); esta etapa es de verificación
explícita, no de corrección.

## Problemas resueltos

No aplica.

## Gaps conocidos

Ninguno.

## Riesgos

Ninguno nuevo.

## Gate

PASS

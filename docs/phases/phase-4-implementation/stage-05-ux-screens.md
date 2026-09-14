# Stage 5 — UX y pantallas

## Objetivo

Implementar las pantallas de `docs/design/phase-4-ux.md`/`phase-4-screens.md` (S1–S7),
reutilizando los patrones visuales ya establecidos en Fase 3, sin usar el frontend como mecanismo
de seguridad.

## Alcance

Vistas server-rendered (Django views + templates), sin JavaScript nuevo. Reutiliza `layouts/app_base.html`
y los componentes ya existentes (`_patient_context_header`, `_page_header`, `_badge`, `_empty_state`).

## Implementación realizada

- `prescriptions/views.py` + `urls_ui.py` + templates: S1 (`prescription_create.html`), S2
  (`prescription_detail.html`), S7 (`prescription_version.html`).
- `study_orders/views.py` + `urls_ui.py` + templates: S3 (`study_order_create.html`), S4
  (`study_order_detail.html`), versión análoga a S7.
- `clinical_documents/views.py` + `urls_ui.py` + templates: S5 (`document_list.html`, con filtros
  por tipo y fecha, paginado), subida (`document_upload.html`), S6 (`document_detail.html`).
- Botones "Emitir receta"/"Solicitar estudios"/"Ver documentos" añadidos a
  `templates/medical_records/encounter_detail.html` (visibles sólo cuando `can_edit`, es decir,
  encuentro `IN_PROGRESS` y médico asignado — igual que el resto de esa pantalla); enlace "Ver
  documentos, recetas y solicitudes" añadido a `templates/medical_records/medical_record.html`.
- Descarga: los templates enlazan directamente al endpoint de la API
  (`clinical_documents_api:document_download`) en vez de duplicar lógica de servir el archivo en la
  capa UI — funciona porque ambos comparten la misma sesión autenticada del navegador.
- `TeCuidoApp/urls.py`: las tres apps montadas bajo el mismo prefijo `clinica/` ya existente.

## Decisiones aplicadas

- **Formularios de items sin JavaScript**: filas fijas (5) en vez de agregar filas dinámicamente
  con JS — coherente con el resto de Fase 3 (ningún flujo clínico depende de JavaScript) y con el
  principio de simplicidad; las filas vacías se descartan en el servidor.
- **Seguridad visual real, no sólo oculta botones**: cada acción mutante (`Nueva versión`, `Anular`)
  sólo se muestra si `prescription.status == "ISSUED" and prescription.is_current_version`, pero la
  autorización real la sigue verificando el servicio (probado explícitamente: un actor no
  autorizado que fuerce el POST igual recibe `DocumentPermissionDenied`).
- **IDOR en UI**: `Http404` genérico para "no existe" y "no autorizado" (mismo criterio que Fase 3).

## Archivos creados

- `prescriptions/views.py`, `prescriptions/urls_ui.py`, 3 templates, `prescriptions/tests/test_ui.py`.
- `study_orders/views.py`, `study_orders/urls_ui.py`, 3 templates, `study_orders/tests/test_ui.py`.
- `clinical_documents/views.py`, `clinical_documents/urls_ui.py`, 3 templates,
  `clinical_documents/tests/test_ui.py`.
- `docs/phases/evidence/phase-4-browser-validation-2026-09-11/` (README + 8 capturas + `results.json`).

## Archivos modificados

- `TeCuidoApp/urls.py` (3 nuevos `include()`).
- `templates/medical_records/encounter_detail.html`, `templates/medical_records/medical_record.html`.

## Migraciones

Ninguna.

## Tests ejecutados

```bash
python manage.py test prescriptions study_orders clinical_documents -v 2
python manage.py check
python manage.py makemigrations --check --dry-run
```

Adicionalmente, validación real de navegador (ver más abajo).

## Resultado de tests

```text
Ran 132 tests in 104.925s
OK
```

(19 tests de UI nuevos + 113 de Stages 1-4 → 132 tests de Fase 4 hasta este punto).

## Validaciones manuales

**Validación real de navegador** (Chromium vía Playwright — la extensión Claude-in-Chrome no
estaba conectada en este entorno, verificado explícitamente antes de usar el mecanismo
alternativo, mismo patrón ya usado en la validación de navegador de Fase 3): servidor de
desarrollo real contra PostgreSQL real (no test DB), datos de prueba sembrados y eliminados
después. **13/13 verificaciones OK**:

1. Login como médico asignado.
2. Navegación consulta → "Emitir receta".
3. Formulario de receta llenado y enviado.
4. Receta emitida se muestra correctamente.
5. Descarga real del PDF — header `%PDF-` verificado en el archivo descargado.
6. Nueva versión de receta — valor actualizado visible, enlace a versión anterior presente.
7. Anulación de receta — badge "Anulada" visible.
8. Solicitud de estudio emitida desde el mismo encuentro.
9. Lista de documentos del paciente muestra los PDFs generados.
10. Acceso no autorizado (médico sin relación) a la URL directa de la receta → 404 genérico.

Evidencia completa en `docs/phases/evidence/phase-4-browser-validation-2026-09-11/`.

## Problemas encontrados

1. **`DocumentPermissionDenied` no estaba en el mapa de mensajes amigables** de
   `prescriptions/views.py`/`study_orders/views.py` (sólo `clinical_documents/views.py` lo tenía) —
   detectado por `test_unauthorized_doctor_sees_error_not_created`.
2. **Mi propio test de carga de documento (`test_upload_redirects_to_detail`) asumía que cualquier
   médico asignado a un encuentro podía subir un documento standalone del paciente** — la
   implementación (correcta, P-009/P-010) exige relación activa para esa operación patient-scoped,
   igual que `list_for_patient`. El test estaba mal, no la vista.
3. **Limpieza de datos de prueba post-validación de navegador**: el primer intento de borrado
   falló por el orden de dependencias reales del esquema (`Prescription.previous_version` es
   auto-referencial y `PROTECT`; `MedicalRecord.patient` también `PROTECT` — no contemplado en el
   primer intento). Resuelto desacoplando `previous_version` antes de borrar, y añadiendo el borrado
   de `MedicalRecord` y `AuditEvent` al orden correcto.

## Problemas resueltos

Los tres corregidos y verificados: (1)/(2) con la suite completa de las tres apps en verde
(132/132); (3) con una consulta posterior confirmando 0 usuarios de prueba restantes en la base de
datos de desarrollo.

## Gaps conocidos

Ninguno bloqueante. El formulario de items con un número fijo de filas (5) es una limitación de UX
menor y deliberada (ver "Decisiones aplicadas").

## Riesgos

Ninguno nuevo.

## Gate

PASS

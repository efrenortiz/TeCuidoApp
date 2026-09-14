# Stage 3 — Archivos y PDF

## Objetivo

Almacenamiento privado de archivos clínicos, validación real de contenido, generación server-side
de PDF, y su integración atómica con `Prescription`/`StudyOrder`.

## Alcance

`clinical_documents/services/storage.py` (almacenamiento privado, validación, rutas seguras) y
`clinical_documents/services/pdf.py` (generación de PDF). Construido junto con Stage 2 por la razón
ya explicada en ese documento.

## Implementación realizada

- **Dependencias nuevas** (justificadas — CLAUDE.md §13): `fpdf2==2.8.8` (generación de PDF —
  puro Python, sin dependencias de sistema; se evaluó WeasyPrint/xhtml2pdf y se descartaron por
  requerir librerías de sistema — Pango/Cairo — no disponibles en este entorno sin `sudo`, ya
  verificado indisponible en una sesión anterior de este mismo proyecto) y `filetype==1.2.0`
  (detección de MIME por contenido real — magic bytes —, alternativa pura Python a `python-magic`,
  ya recomendada por la skill `django-security` de este mismo repositorio para entornos sin
  `libmagic`).
- **Almacenamiento privado** (ADR-026): `TeCuidoApp.settings.CLINICAL_DOCUMENTS_STORAGE_ROOT`
  (nueva, `private_media/clinical_documents/` por defecto) — deliberadamente NO usa
  `MEDIA_ROOT`/`MEDIA_URL` (que sirven bajo una URL pública fija); el proyecto no tenía ninguna
  configuración de medios previa que esta decisión pudiera contradecir. Añadido a `.gitignore`.
- `storage.validate_and_detect_mime`: tamaño máximo (10 MB por defecto,
  `CLINICAL_DOCUMENTS_MAX_UPLOAD_SIZE_BYTES` configurable), MIME real por contenido (nunca por
  `Content-Type` del cliente ni por extensión), y verificación cruzada extensión↔MIME real (un
  `.pdf` que en realidad es un ejecutable se rechaza).
- `storage.build_storage_key`: `storage_key` siempre generado en servidor (UUID4, particionado por
  fecha) — el nombre del cliente nunca participa en la ruta física, lo que hace la path traversal
  estructuralmente imposible (no depende de sanitizar un input, elimina el input de la ruta por
  completo).
- `storage.save`/`read`/`delete_best_effort`.
- `pdf.render_prescription_pdf`/`render_study_order_pdf`: layout simple (consultorio, paciente,
  médico, fecha/hora en zona horaria de la `Clinic`, versión si > 1, items) — determinista a partir
  de los datos ya persistidos de esa versión concreta.
- Integración atómica (ADR-027): `PrescriptionService.issue`/`create_version` (y su análogo de
  `StudyOrderService`) generan el PDF y llaman a
  `clinical_documents.services.document.create_generated_document` DENTRO de su propio
  `with transaction.atomic()` — Django anida `atomic()` como SAVEPOINT sobre la misma conexión, así
  que Prescription/StudyOrder + su documento comparten una única transacción real: si algo falla
  después de escribir el archivo, todo se revierte junto (más fuerte que la compensación
  best-effort, que sólo hace falta en `ClinicalDocumentService.upload`, que no tiene una
  transacción padre preexistente).

## Decisiones aplicadas

- **Refinamiento de secuencia respecto al diseño documental original**: `clinical-documents-data-model.md`/ADR-027
  describían "el archivo se genera fuera de la transacción de base de datos, y si falla la
  persistencia posterior se compensa". Para el caso `GENERATED` (Prescription/StudyOrder), la
  implementación real hace la escritura del archivo DENTRO de la misma transacción que crea la fila
  padre, en vez de estrictamente antes de abrirla. Esto no contradice ninguna invariante cerrada —
  sigue siendo cierto que "no debe quedar una receta marcada como emitida sin su representación
  documental" y que el PDF nunca se regenera con datos mutables — y es una garantía MÁS fuerte
  (atomicidad real de base de datos en vez de compensación aplicativa best-effort). Para el caso
  `UPLOADED` (sin transacción padre preexistente), se conserva exactamente el diseño original:
  archivo escrito antes de abrir la transacción, con borrado best-effort si la fila falla después
  (verificado con un test dedicado — ver Stage 2).
- **`fpdf2` en vez de un motor HTML→PDF**: evita agregar dependencias de sistema en un entorno que
  ya demostró no tener acceso a instalación de paquetes vía `apt`/`sudo` (ver sesión de validación
  de navegador de Fase 3). Layout basado en texto plano es suficiente para el contrato ("PDFs deben
  identificar paciente, médico, consultorio, fecha/hora, contener la información emitida, ser
  imprimibles") sin necesitar plantillas HTML.

## Archivos creados

- `clinical_documents/services/storage.py`
- `clinical_documents/services/pdf.py`

## Archivos modificados

- `requirements.txt` (`fpdf2`, `filetype`).
- `TeCuidoApp/settings.py` (`CLINICAL_DOCUMENTS_STORAGE_ROOT`).
- `.gitignore` (`private_media/`).
- `prescriptions/services/prescription.py`, `study_orders/services/study_order.py` (wiring de
  generación de documento dentro de `issue`/`create_version`).

## Migraciones

Ninguna (sin cambios de modelo en esta etapa).

## Tests ejecutados

Incluidos en la misma corrida de Stage 2 (`clinical_documents/tests/test_services.py` cubre
específicamente: archivo válido PDF/PNG/JPEG, MIME/extensión no soportados, ejecutable disfrazado
de PDF, archivo vacío, archivo excede tamaño máximo, limpieza de huérfano ante fallo posterior,
lectura/descarga autorizada y no autorizada, consistencia metadatos↔archivo).

## Resultado de tests

Incluido en el resultado de Stage 2 (`Ran 83 tests — OK`).

## Validaciones manuales

No aplica todavía (sin UI/navegador — ver Stage 5).

## Problemas encontrados

1. **`fpdf2` no soporta el em-dash (`—`, U+2014) con la fuente core `helvetica`** (codificación
   latin-1): `FPDFUnicodeEncodingException` al generar el PDF de una receta con un item. Detectado
   inmediatamente por los tests de Stage 2 al intentar emitir la primera receta con formato de
   itemización.
2. **`multi_cell` sin `new_x`/`new_y` explícitos deja el cursor en una posición que produce
   `"Not enough horizontal space to render a single character"`** en la siguiente llamada
   (indicaciones de un item, o el segundo párrafo de indicaciones/observaciones de una solicitud de
   estudio).
3. **`ClinicalDocumentService.upload` no inicializaba `version_number`/`is_current_version`** —
   un documento recién subido quedaba con `is_current_version=None`, lo que hacía que la primera
   corrección (`create_version`) fallara con `DocumentImmutableResource` (`not None` es `True`)
   incluso sobre la única versión existente. Detectado por `test_version_chain`.

## Problemas resueltos

1. Se reemplazó el em-dash por un guion simple (`-`, ASCII/latin-1) en la única línea de texto
   renderizado que lo usaba.
2. Se agregó `new_x="LMARGIN", new_y="NEXT"` explícito a las seis llamadas a `multi_cell` de
   `pdf.py`.
3. Se corrigió `upload()` para establecer `version_number=1, is_current_version=True` al crear un
   documento standalone.

Los tres se verificaron re-ejecutando la suite completa de las tres apps (83/83 `OK`).

## Gaps conocidos

- El layout del PDF es deliberadamente simple (texto, sin logotipo/membrete gráfico) — suficiente
  para el contrato, ampliable después sin decisión arquitectónica nueva.

## Riesgos

- `fpdf2`/`filetype` son dependencias nuevas de terceros; ambas puras Python, activamente
  mantenidas, sin dependencias de sistema — riesgo de mantenimiento bajo.

## Gate

PASS

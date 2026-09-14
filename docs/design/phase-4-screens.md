# Fase 4 — Pantallas

## 1. Pantallas base

### S1 — Crear receta

Responsabilidad: capturar una nueva Prescription.

Componentes:

- PatientContextHeader;
- EncounterContext;
- PrescriptionItemsTable;
- botón Emitir;
- cancelación de UI.

### S2 — Receta emitida

Muestra estado, fecha, médico, versión, acciones Ver PDF/Descargar, Nueva versión y Anular cuando estén permitidas.

### S3 — Solicitar estudios

Captura StudyOrder y StudyOrderItems.

### S4 — Orden emitida

Muestra detalle, estado, versión y PDF.

### S5 — Documentos del paciente

Lista paginada; filtros tipo/fecha; acceso al detalle.

### S6 — Detalle de documento

Metadatos, origen, relaciones clínicas, versión y acción de descarga autorizada.

### S7 — Nueva versión

Presenta claramente versión previa y nueva información; exige motivo cuando corresponda.

## 2. Estados visuales

Usar badges consistentes con Fase 3 para `ISSUED` y `VOIDED`.

## 3. Seguridad visual

Ocultar acciones no autorizadas como conveniencia UX, pero el servidor debe volver a verificarlas.

## 4. Estados de carga/error

Cada pantalla debe manejar:

- loading;
- empty;
- validation error;
- permission denied;
- not found;
- conflict;
- storage/download failure.

## 5. No incluir

No crear carpetas, drag-and-drop tipo Drive, etiquetas libres, búsqueda avanzada ni edición de PDFs.

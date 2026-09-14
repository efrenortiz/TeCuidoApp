# Fase 4 — Estrategia de pruebas

## 1. Objetivo

Validar que documentos, recetas y solicitudes se comporten como un conjunto clínico seguro y trazable sin romper Fases 1–3.

## 2. Modelo

Probar:

- FK e integridad referencial;
- unicidad de versiones;
- posiciones de items;
- estados;
- constraints;
- Patient obligatorio en ClinicalDocument.

## 3. Prescription

Casos mínimos:

- emisión válida;
- sin items;
- actor no autorizado;
- paciente ajeno;
- doble emisión;
- versión nueva;
- versión histórica inmutable;
- anulación;
- doble anulación;
- PDF generado.

## 4. StudyOrder

Casos análogos a Prescription, incluyendo tipos válidos y resultados fuera de alcance.

## 5. ClinicalDocument

- upload PDF válido;
- upload imagen válida;
- MIME incorrecto;
- extensión incorrecta;
- tamaño excedido;
- nombre peligroso;
- documento sin Patient;
- documento vinculado a recurso ajeno;
- descarga autorizada;
- IDOR;
- descarga no autorizada;
- documento privado.

## 6. Versionado

- version 1;
- version 2;
- cadena 1→2→3;
- previous_version válida;
- self-reference rechazada;
- dos versiones simultáneas;
- una sola vigente.

## 7. PDF

- contenido correcto;
- datos de Patient/Doctor/Clinic;
- timestamp;
- orden de items;
- impresión;
- regeneración no altera historial.

## 8. Servicios

Validar autorización, transacción, errores, idempotencia y ausencia de CRUD genérico.

## 9. API

Validar paths, métodos, payloads, errores, códigos HTTP, autenticación, autorización, uploads y downloads.

## 10. Seguridad

Probar IDOR, acceso horizontal, URLs directas, fuga en errores y logs.

## 11. Concurrencia

Probar como mínimo:

- dos emisiones simultáneas;
- dos versiones simultáneas;
- versión vs anulación;
- dos uploads con intención idéntica;
- descarga durante anulación.

## 12. UX/browser

Validar flujos críticos reales:

- emitir receta;
- generar PDF;
- emitir StudyOrder;
- cargar documento;
- listar documentos;
- descargar;
- crear versión;
- anular.

## 13. Regresión

Después de cada etapa relevante ejecutar regresión de Fases 1–3.

## 14. Gate de cierre

Fase 4 no se considera lista para cierre con:

- migraciones pendientes;
- errores de autorización;
- archivos públicos;
- documentos históricos sobrescritos;
- resultados de tests fallando;
- inconsistencias API/servicio/modelo;
- HIGH/CRITICAL abiertos.

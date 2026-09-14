# ADR-030 — Fase 4 Scope Boundary

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Alcance / Gestión de fases

## 1. Contexto

`requirements.md` describe una visión de producto más amplia que el núcleo mínimo de cada fase.
Fase 4 necesita una frontera explícita para no absorber funcionalidad de fases posteriores ni
convertir el módulo documental en un gestor genérico.

## 2. Decisión

Fase 4 incluye exclusivamente: `Prescription`/`PrescriptionItem`, `StudyOrder`/`StudyOrderItem`,
`ClinicalDocument`, generación de PDF, almacenamiento privado, descarga autorizada, versionado y
anulación lógica.

Fase 4 **no** incluye (quedan explícitamente fuera, aunque puedan ser extensiones futuras):

- resultados de laboratorio/gabinete/histopatología, ni su interpretación;
- catálogo farmacológico obligatorio, catálogo diagnóstico o catálogo exhaustivo de estudios;
- CIE-10;
- firma electrónica o biométrica, receta electrónica regulatoria avanzada;
- `CareRequest` como flujo operativo (pertenece a Fase 5 — la relación arquitectónica futura de
  `ClinicalDocument` con `CareRequest` no implica su implementación en esta fase);
- notificaciones complejas;
- búsqueda documental avanzada, exportación masiva, gestor de archivos genérico tipo Drive;
- dashboards de Fase 5;
- almacenamiento externo especializado, salvo necesidad explícita futura;
- hash criptográfico obligatorio como garantía de integridad regulatoria.

## 3. Reglas derivadas

- Ningún documento de Fase 4 introduce un modelo, endpoint o regla de las áreas excluidas.
- Una necesidad futura de estas funcionalidades requiere una decisión explícita posterior (nuevo
  ADR), no una extensión silenciosa durante la implementación de Fase 4.

## 4. Alternativas consideradas

### Modelar StudyOrder con soporte de resultados desde el inicio ("por si acaso")
**Rejected.** Contradice el principio de alcance de `CLAUDE.md` §14 ("no agregar funcionalidades
porque probablemente se necesiten después") y el principio de simplicidad del contrato (§4).

## 5. Consecuencias

Positivas:
- alcance verificable y auditable; facilita declarar Fase 4 lista para implementación sin
  ambigüedad de scope creep.

Negativas:
- funcionalidades relacionadas (resultados, firma electrónica) requerirán una fase o decisión
  posterior explícita antes de poder construirse.

## 6. Relación

Complementa `requirements.md` §41/§42 y el contrato `phase-4-documents.md` §3.2/§24.

## 7. Estado

**Accepted.**

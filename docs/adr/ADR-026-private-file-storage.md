# ADR-026 — Private File Storage and Authorized Download Only

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Seguridad / Almacenamiento

## 1. Contexto

Fase 4 introduce archivos clínicos binarios (PDFs generados, imágenes y documentos subidos). El
proyecto no tenía, antes de Fase 4, ninguna configuración de almacenamiento de medios (`MEDIA_ROOT`
no está definido en `TeCuidoApp/settings.py`) — no existe una implementación previa que esta
decisión pudiera contradecir.

## 2. Decisión

Los archivos clínicos se almacenan en un medio privado, nunca en `static/` ni bajo una URL pública
permanente. Cada `ClinicalDocument` conserva un `storage_key` generado por el servidor,
independiente del nombre original suministrado por el cliente (que se conserva sólo como
metadato). Toda descarga se sirve mediante un mecanismo que revalida autorización por objeto en
cada solicitud — nunca mediante un enlace público reutilizable.

Validación obligatoria en la carga: extensión, MIME informado (nunca de confianza exclusiva),
tamaño máximo configurado, y autorización del actor. No se aceptan ejecutables ni formatos fuera
de los tipos permitidos inicialmente (PDF e imágenes comunes).

## 3. Reglas derivadas

- `storage_key` nunca se deriva directamente del nombre de archivo enviado por el cliente
  (previene path traversal y colisiones).
- Las respuestas de API nunca exponen `storage_key` en crudo (`phase-4-api-contracts.md` §5).
- No se introduce almacenamiento externo especializado (S3, etc.) salvo necesidad explícita
  futura — el mecanismo de almacenamiento de archivos privados del framework es suficiente para el
  volumen y los requisitos de Fase 4.

## 4. Alternativas consideradas

### Servir archivos directamente desde `MEDIA_ROOT` con URL predecible
**Rejected.** Un identificador secuencial o predecible en la URL es, por definición, IDOR si no se
revalida autorización en cada solicitud — contradice el principio de seguridad ya establecido
(`CLAUDE.md` §11: "nunca asumir que una URL privada constituye por sí misma un mecanismo de
autorización").

### Almacenamiento externo (S3/GCS) desde el inicio de Fase 4
**Rejected para esta fase.** No hay necesidad funcional que lo justifique todavía; introduce una
dependencia y complejidad operativa sin un requisito de escala actual (principio de simplicidad,
contrato §4).

## 5. Consecuencias

Positivas:
- ningún binario clínico queda expuesto por URL pública o por adivinar un identificador;
- el mecanismo es el más simple compatible con las garantías de seguridad requeridas.

Negativas:
- servir archivos vía la aplicación (en vez de un CDN/proxy de archivos estáticos) tiene un costo
  de rendimiento mayor que servir estáticos — aceptado explícitamente por seguridad.

## 6. Relación

Complementa el principio de "Seguridad" de `CLAUDE.md` §6 y `docs/architecture.md`.

## 7. Estado

**Accepted.**

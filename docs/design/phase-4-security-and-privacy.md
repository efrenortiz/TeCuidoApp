# Fase 4 — Seguridad y privacidad

## 1. Principios

- almacenamiento privado por defecto;
- mínimo privilegio;
- autorización por objeto;
- trazabilidad;
- minimización de datos;
- no exposición pública de binarios.

## 2. Almacenamiento

Los archivos deben estar fuera de `static/` y no exponerse mediante un URL público permanente.

La aplicación conserva un `storage_key` seguro, generado por servidor.

## 3. Upload

Validar:

1. autorización;
2. tamaño;
3. extensión;
4. MIME;
5. nombre seguro;
6. almacenamiento privado.

No confiar únicamente en el header del cliente.

## 4. Download

Toda descarga pasa por autorización del recurso. No se permite que un usuario descargue un archivo sólo por conocer un identificador.

## 5. PDF

Los PDFs generados se consideran artefactos clínicos históricos. No se regeneran posteriormente con datos mutables para sustituir una versión anterior.

## 6. Logs

No registrar:

- contenido clínico completo;
- binarios;
- tokens;
- credenciales;
- URLs con secretos.

Los logs deben contener sólo información técnica mínima.

## 7. Privacidad del PDF

El PDF debe contener sólo los datos necesarios para su finalidad y debe utilizar la zona horaria de la Clinic cuando corresponda.

## 8. Errores

Las respuestas de error no deben revelar información de otros pacientes ni rutas físicas de almacenamiento.

## 9. Integridad

No se requiere hash criptográfico obligatorio en F4 inicial. El control principal es la inmutabilidad/versionado y almacenamiento privado.

## 10. Fuera de alcance

No se incorpora firma electrónica regulatoria, cifrado documental aplicativo adicional ni infraestructura externa especializada salvo que el stack existente ya lo requiera.

# Fase 6 — Notification API Contracts

**Estado:** Diseño técnico derivado — **implementado** (ver `docs/phases/phase-6-implementation-summary.md`).

## 1. Principio

La API expone capacidades operativas de notificación solo cuando existe una necesidad de UI/integración. No se ofrece al cliente un endpoint genérico que permita elegir arbitrariamente destinatarios o plantillas.

## 2. Endpoints conceptuales

Los paths concretos deben alinearse con las convenciones REST ya existentes en el repositorio.

### Operaciones internas

La creación de notificaciones de citas debe originarse desde servicios de dominio, no desde una petición HTTP arbitraria del cliente.

### Consulta administrativa

Puede existir un endpoint administrativo para diagnóstico operacional de notificaciones, separado del audit trail. Debe devolver únicamente metadatos operativos, no contenido clínico innecesario.

## 3. Prohibiciones

El cliente no puede:

- elegir un proveedor;
- alterar `dedupe_key`;
- forzar el envío a un usuario no determinado por reglas de dominio;
- desactivar recordatorios definidos por Fase 6;
- cambiar el contenido legal de Aviso de Privacidad o Términos.

## 4. Idempotencia

Cuando una operación HTTP que crea una intención requiera idempotencia, debe reutilizar las convenciones ya presentes en Fases 1–5.

## 5. Autorización

El servidor debe validar autorización aun cuando la UI o ruta de navegación oculten una operación.

## 6. Serialización mínima

Una respuesta de diagnóstico puede incluir:

- id;
- event_type;
- channel;
- recipient masked/controlled;
- status;
- scheduled_for;
- sent_at;
- attempt_count;
- safe reason_code.

No incluir secretos ni cuerpo completo del correo por defecto.

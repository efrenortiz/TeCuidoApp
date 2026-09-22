# Fase 6 — UX

**Estado:** Diseño técnico derivado — **implementado** (ver `docs/phases/phase-6-implementation-summary.md`).

## 1. Principio

La UX representa reglas ya congeladas. No crea nuevas reglas de negocio.

## 2. Notificaciones

El usuario recibe las comunicaciones de Email definidas por el dominio.

No existe configuración para desactivar:

- notificaciones de cita creada;
- notificaciones de cita modificada/reprogramada;
- notificaciones de cita cancelada;
- recordatorios 15/10/5/1 días.

## 3. Recordatorios

La UX no presenta al Doctor asignado como destinatario de recordatorios periódicos.

El Doctor sí puede recibir mensajes de creación, modificación/reprogramación y cancelación.

## 4. Consentimientos

Cuando la plataforma deba presentar Aviso de Privacidad o Términos para aceptación, la pantalla debe mostrar claramente:

- nombre del documento;
- versión;
- acceso al contenido presentado;
- acción explícita de aceptación.

No se presenta una pantalla de consentimiento clínico dentro de Fase 6.

## 5. Auditoría

No hay pantalla de audit trail para Patient, Responsible o Doctor.

Sí existe una superficie administrativa para consulta del historial de auditoría por Administradores autorizados.

## 6. Seguridad UX

Ocultar un enlace no sustituye autorización server-side.

Errores de permisos no deben revelar eventos de auditoría ni datos sensibles.

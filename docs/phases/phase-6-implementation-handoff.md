# Fase 6 — Implementation Handoff

**Estado:** implementación realizada — ver `docs/phases/phase-6-implementation-summary.md` para
código, tests y las decisiones finales del propietario (PD-001 a PD-008). Este documento
conserva el plan de implementación original como referencia histórica; no declara por sí mismo
el cierre formal de la fase.
**Fecha:** 2026-09-20

## 1. Regla de entrada

La implementación comienza únicamente después de que los documentos derivados sean coherentes entre sí y con el Design Freeze.

## 2. Orden recomendado

1. Baseline y discovery del código existente.
2. Confirmar `AuditEvent` y servicios de auditoría existentes.
3. Crear la app/frontera `notifications` sin duplicar Agenda.
4. Implementar el modelo mínimo de intención/notificación.
5. Implementar transporte Email desacoplado del dominio.
6. Integrar invitación, verificación y recuperación de cuenta sin alterar sus reglas.
7. Integrar Appointment created/modified/cancelled.
8. Implementar recordatorios 15/10/5/1 con deduplicación y concurrencia segura.
9. Integrar auditoría transversal y catálogo base.
10. Incorporar auditoría de rechazos.
11. Exponer consulta administrativa del audit trail.
12. Implementar registro de aceptación de Aviso de Privacidad y Términos.
13. Implementar UX/screens.
14. Ejecutar estrategia de pruebas y regresión.
15. Corregir hallazgos.
16. Preparar evidencia y reporte final.

## 3. Restricciones no negociables

No agregar:

- WhatsApp;
- SMS real;
- MFA/2FA;
- una nueva fuente de verdad para Appointment;
- una segunda tabla de auditoría;
- microservicios;
- event sourcing;
- CQRS;
- broker sin necesidad demostrada;
- opt-out de las comunicaciones congeladas;
- acceso al audit trail para roles no autorizados.

## 4. Reutilización prioritaria

Antes de crear código nuevo, revisar:

- accounts;
- appointments/services;
- patients/services/permissions;
- medical_records/services/audit;
- ClinicalDocument;
- patrones de tests y transacciones ya utilizados.

## 5. Cambios de diseño

Si la implementación descubre una contradicción real:

```text
detener en la frontera afectada
        ↓
documentar discrepancia
        ↓
proponer alternativas
        ↓
decidir
        ↓
actualizar Design Freeze
        ↓
continuar
```

No cambiar silenciosamente una política congelada.

## 6. Gate antes de producción

Debe existir evidencia de:

- migraciones limpias;
- tests del subsistema;
- regresión de Fases 1–5;
- browser/UI;
- seguridad;
- concurrencia/idempotencia;
- documentación actualizada.

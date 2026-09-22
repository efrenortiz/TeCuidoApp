# Fase 6 — Testing Strategy

**Fuente normativa:** `docs/phases/phase-6-design-freeze.md` v1.1
**Estado:** Estrategia de pruebas — **con evidencia de implementación** (ver
`docs/phases/phase-6-implementation-summary.md` §13: 828/828 tests de la suite completa del
proyecto, incluidas las suites propias de Fase 6).

## 1. Objetivo

Demostrar que Fase 6 cumple el Design Freeze sin romper Fases 1–5.

## 2. Matriz funcional mínima

| Área | Casos obligatorios |
|---|---|
| Cita creada | Patient + Responsible + Doctor reciben intención |
| Cita modificada | Patient + Responsible + Doctor reciben intención |
| Cita cancelada | Patient + Responsible + Doctor reciben intención |
| Recordatorio 15d | Patient + Responsible; Doctor no |
| Recordatorio 10d | Patient + Responsible; Doctor no |
| Recordatorio 5d | Patient + Responsible; Doctor no |
| Recordatorio 1d | Patient + Responsible; Doctor no |
| Opt-out | No existe ruta válida para desactivarlo |
| Cancelación | No se ejecutan recordatorios futuros inelegibles |
| Reprogramación | El recordatorio usa `Appointment.start_at` vigente |
| Dedupe | No se generan duplicados bajo concurrencia |
| Transporte | Fallo no revierte cita confirmada |
| Auditoría | Éxitos del catálogo base registrados |
| Auditoría | Rechazos del catálogo base registrados |
| Auditoría | Contenido clínico no copiado |
| Audit access | Solo Administrador puede consultar |
| Retención | No existe limpieza automática por antigüedad |
| Consentimiento | Usuario + fecha/hora + versión |
| Consentimiento | Versión inexistente rechazada |
| Consentimiento clínico | No existe aceptación dentro de F6 |

## 3. Concurrencia

Probar al menos:

- dos workers procesando la misma notificación;
- dos intentos simultáneos de creación de la misma intención;
- dos consultas administrativas concurrentes;
- registro concurrente de aceptación si el contrato exige unicidad.

## 4. Integración

Ejecutar regresión de Fases 1–5, con especial atención a:

- autenticación;
- email verification;
- password recovery;
- Agenda;
- Appointment;
- CareRequest;
- ClinicalDocument;
- auditoría clínica existente.

## 5. API

Probar:

- autorización administrativa;
- paginación/filtros;
- entradas inválidas;
- no exposición de secretos;
- no acceso al audit trail por roles no autorizados.

## 6. Browser/UI

Validar en navegador:

- aceptación de documento;
- pantalla administrativa de auditoría;
- estados de error/carga/vacío;
- ausencia real de opt-out.

## 7. Seguridad

Casos explícitos:

- actor falsificado en payload;
- acceso directo a endpoint administrativo por usuario no administrador;
- modificación/borrado de `AuditEvent`;
- exposición de tokens en logs;
- exposición de contenido clínico en correo.

## 8. Criterio de cierre

No declarar Fase 6 cerrada hasta disponer de evidencia de pruebas de dominio, servicios, API, UI/browser, seguridad, regresión y comportamiento de concurrencia.

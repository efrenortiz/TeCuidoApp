# TeCuidoApp — Fase 6 — Documentation Index

**Estado:** DESIGN PACKAGE — derivado del Design Freeze v1.1
**Fecha:** 2026-09-20

> **Estado de implementación (2026-09-22):** el paquete descrito por este índice ya está
> implementado, corregido y validado — `PHASE 6 — PREPARED FOR FINAL VALIDATION` (ver
> `docs/phases/phase-6-implementation-summary.md` para el estado técnico completo y
> `docs/phases/phase-6-final-report.md` para el reporte consolidado). Este documento aún **no**
> declara `PHASE 6 — CLOSED` — esa declaración solo puede hacerse tras la revalidación completa y
> el commit definitivo de cierre (segunda etapa de esta consolidación). Este índice conserva su
> función original de navegación del paquete de diseño; no se reescribe como historial de
> implementación.

## 1. Propósito

Este índice define el conjunto de documentos derivados de Fase 6 — Notificaciones y auditoría, su ubicación recomendada en el repositorio y el orden de lectura para implementación.

El contrato normativo es `docs/phases/phase-6-design-freeze.md`. Ningún documento de este paquete puede contradecirlo, `requirements.md`, `docs/architecture.md` ni los ADR vigentes.

## 2. Estructura y ubicación

| Orden | Documento | Folder | Propósito |
|---:|---|---|---|
| 1 | `phase-6-design-freeze.md` | `docs/phases/` | Contrato normativo de la fase |
| 2 | `phase-6-documentation-index.md` | `docs/phases/` | Navegación y trazabilidad documental |
| 3 | `phase-6-notification-domain.md` | `docs/design/` | Dominio y reglas de notificaciones |
| 4 | `phase-6-notification-data-model.md` | `docs/design/` | Modelo lógico/físico de persistencia |
| 5 | `phase-6-notification-service-contracts.md` | `docs/design/` | Contratos internos de servicios |
| 6 | `phase-6-notification-api-contracts.md` | `docs/design/` | Contrato HTTP/API |
| 7 | `phase-6-notification-security-and-privacy.md` | `docs/design/` | Seguridad, privacidad y contenido mínimo |
| 8 | `phase-6-audit-domain.md` | `docs/design/` | Dominio y taxonomía de auditoría |
| 9 | `phase-6-audit-data-model.md` | `docs/design/` | Persistencia y reutilización de `AuditEvent` |
| 10 | `phase-6-audit-service-contracts.md` | `docs/design/` | Emisión y consulta de auditoría |
| 11 | `phase-6-audit-api-contracts.md` | `docs/design/` | Consulta administrativa del audit trail |
| 12 | `phase-6-audit-and-history.md` | `docs/design/` | Reglas de historial, append-only y retención |
| 13 | `phase-6-consent-domain.md` | `docs/design/` | Aceptación de documentos de plataforma |
| 14 | `phase-6-consent-service-contracts.md` | `docs/design/` | Servicios de aceptación |
| 15 | `phase-6-ux.md` | `docs/design/` | Comportamiento UX transversal |
| 16 | `phase-6-screens.md` | `docs/design/` | Estados concretos de pantallas |
| 17 | `phase-6-testing-strategy.md` | `docs/phases/` | Estrategia y matriz de pruebas |
| 18 | `phase-6-implementation-handoff.md` | `docs/phases/` | Orden de implementación y handoff |
| 19 | `phase-6-final-report.md` | `docs/phases/` | Reporte de cierre — consolidado, no ya una plantilla (ver estado en la nota al inicio de este documento) |

## 3. Orden de lectura

```text
requirements.md
    ↓
ADRs aplicables
    ↓
docs/architecture.md
    ↓
phase-6-design-freeze.md
    ↓
phase-6-documentation-index.md
    ↓
Notificaciones
    ↓
Auditoría
    ↓
Consentimientos
    ↓
UX / Screens
    ↓
Testing
    ↓
Implementation Handoff
```

## 4. Reglas de coherencia

- Todos los archivos nuevos de Fase 6 usan el prefijo `phase-6-`.
- `notifications` no se convierte en dueño de reglas de Agenda.
- `audit` no autoriza operaciones ni se convierte en un repositorio clínico paralelo.
- El `AuditEvent` existente es la fuente de verdad de auditoría; no se crea una segunda tabla de auditoría.
- La consulta del audit trail es exclusiva de Administradores autorizados.
- No existe opt-out de las notificaciones operativas o recordatorios congelados.
- Los recordatorios periódicos no se envían al Doctor asignado.
- La retención de auditoría es indefinida; no hay depuración automática.

## 5. Estado

Este índice documenta el paquete de diseño. El estado real de implementación es
`PHASE 6 — PREPARED FOR FINAL VALIDATION` (ver la nota al inicio de este documento y
`docs/phases/phase-6-implementation-summary.md`) — no declara, ni antes ni ahora,
`PHASE 6 — CLOSED`; esa declaración solo se hará una vez que la etapa de revalidación final
(segunda etapa del cierre formal) confirme el commit definitivo y no queden hallazgos abiertos.

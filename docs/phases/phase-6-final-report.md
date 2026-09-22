# TeCuidoApp — Fase 6 Final Report

**Estado:** `PHASE 6 — READY FOR CLOSURE`. No es una autodeclaración de cierre — el cierre formal
(`PHASE 6 — CLOSED`) sigue reservado a una auditoría independiente que no fue quien implementó el
código. Este documento registra la evidencia con la que esa auditoría puede verificar el estado,
sin sustituirla.
**Fecha del diseño:** 2026-09-20
**Fecha de esta consolidación:** 2026-09-22

> Ver `docs/phases/phase-6-implementation-summary.md` para la bitácora técnica completa (ITD-001
> a ITD-015, correcciones C-001 a C-018, y la ronda de corrección post-implementación de 7 prompts
> secuenciales que llevó el estado de `IMPLEMENTED / READY FOR FINAL AUDIT` a `READY FOR CLOSURE`).

## 1. Identidad

**Fase:** 6
**Nombre:** Notificaciones y auditoría
**Design Freeze:** v1.1 (`docs/phases/phase-6-design-freeze.md`, con la precisión PD-002 de esta
ronda en §11/§12)

## 2. Alcance implementado

- Email (único canal — `Notification.Channel.EMAIL`), vía `django.core.mail.send_mail`,
  con clasificación de resultado transitorio/permanente (ITD-015).
- Recordatorios de cita por ventana configurable (`ReminderWindow`, seed inicial 15/10/5 días
  — PD-004: hacia adelante desde la activación, sin recalcular el histórico).
- Notificaciones de ciclo de vida de `Appointment`: creada, modificada, cancelada — disparadas
  vía señales propias (`appointment_created`/`appointment_modified`/`appointment_cancelled`,
  `appointments/signals.py`) y `transaction.on_commit`, nunca dentro de la transacción de negocio.
- Auditoría transversal no clínica sobre el mismo `AuditEvent`/`medical_records` (PD-008, sin
  segunda tabla ni segunda infraestructura): `LOGIN`, `MODIFY_PATIENT`, `CHANGE_PERMISSIONS`,
  `DISABLE_USER`, `ADMIN_SENSITIVE_ACCESS` (sin emisor — PD-001, por diseño).
- Auditoría de rechazos dentro del boundary instrumentado con actor real resolvible (PD-002,
  precisado esta ronda en el Design Freeze — C-017).
- Consulta administrativa del audit trail (API + UI), restringida a `is_superuser` (hallazgo
  12.1, cerrado con tests que distinguen `is_staff` de `is_superuser`).
- Aceptación de Aviso de Privacidad y Términos y Condiciones (`PolicyAcceptance`), con
  referencia canónica versionada a documento externo (`LEGAL_DOCUMENT_URLS`, PD-006, ITD-014).
- Controles de seguridad: retries limitados con backoff exponencial y huérfanas `SENDING`
  recuperadas de forma segura (PD-007, ITD-011/ITD-012/ITD-015, corregido esta ronda —
  C-012/C-013), idempotencia por `dedupe_key`, sin opt-out (F6-D03), sin contenido clínico en
  el correo (PD-005), enlaces que no crean bypass de autorización (verificado esta ronda —
  C-016).

## 3. Decisiones funcionales verificadas

| Decisión | Verificación |
|---|---|
| F6-D01 (Email + recordatorios) | Código: `notifications/services.py`. Tests: `notifications/tests/test_services.py`. Evidencia browser: `docs/phases/evidence/phase-6-browser-validation/README.md` §5. |
| F6-D02 (Notificaciones de ciclo de vida de cita) | Código: `appointments/signals.py` + `notifications/receivers.py`. Tests: `EmailContentTests` (creada/modificada/cancelada). |
| F6-D03 (Sin opt-out) | Ausencia estructural verificada por `NoOptOutTests` + evidencia browser §4. |
| F6-D04 (Consentimiento) | Código: `accounts/services/consent.py`. Tests: `accounts/tests/test_consent.py` (18 tests, incl. `ConsentDocumentReferenceTests` de esta ronda). Evidencia browser §1. |
| F6-D05 (Audit trail administrativo) | Código: `medical_records/views.py::AuditTrailView`, `medical_records/admin.py`. Tests: `medical_records/tests/test_fase6_audit.py` (20 tests, incl. cobertura explícita por rol de esta ronda). Evidencia browser §2/§3. |
| F6-D06 (Auditoría de rechazos con actor real) | Precisión PD-002 en Design Freeze §11/§12 (C-017). Tests: `LoginAuditTests`, `RejectionAuditCoverageTests`. |
| F6-D07 (Reutilización de `AuditEvent`, sin segunda infraestructura) | Confirmado por `grep` sin resultados de una segunda fuente de verdad (`notifications/`, `accounts/api.py`, `accounts/services/consent.py`, `medical_records/api.py`). |

## 4. Implementación

- **App nueva:** `notifications/` (`models.py`, `services.py`, `receivers.py`, `apps.py`,
  `admin.py`, `management/commands/process_due_notifications.py`).
- **Modelos nuevos:** `notifications.Notification`, `notifications.ReminderWindow`;
  `accounts.PolicyAcceptance` (consentimiento).
- **Modelo modificado:** `medical_records.AuditEvent` — catálogo `Action`/`ResourceType`
  extendido con las entradas transversales de Fase 6 (ver §2), sin tabla paralela.
- **Migraciones:** `notifications/migrations/0001_initial.py`,
  `0002_seed_reminder_windows.py`; `accounts/migrations/0004_policyacceptance.py`;
  `medical_records/migrations/0005_auditevent_study_order_alter_auditevent_action_and_more.py`
  a `0007_alter_auditevent_resource_type.py`. `makemigrations --check --dry-run` confirma cero
  migraciones pendientes al cierre de esta ronda.
- **Servicios:** `notifications/services.py` (envío, reintentos, backoff, recuperación de
  huérfanas, render de contenido); `accounts/services/consent.py` (aceptación, estado,
  referencia canónica de documento).
- **Señales:** `appointments/signals.py` (emisor) + `notifications/receivers.py` (consumidor) —
  dirección de dependencia Fase 6 → Fase 2, nunca al revés (ITD-002).
- **APIs/Views:** `medical_records/views.py::AuditTrailView` (UI, `/clinica/auditoria/`),
  API de audit trail (`/api/v1/clinical/audit/events/`), API de consentimiento
  (`/api/v1/consent/status/`).
- **Django Admin:** `notifications/admin.py`, `medical_records/admin.py` (restricción a
  `is_superuser`), `accounts/admin.py` (instrumentación de `PatientAdmin`/`PersonAdmin`/
  `UserAdmin` para `MODIFY_PATIENT`/`DISABLE_USER`/`CHANGE_PERMISSIONS`).
- **Scheduler:** `management/commands/process_due_notifications.py` (comando invocable por
  cron/systemd-timer — ningún scheduler de proceso persistente añadido, sin justificación de
  Celery/Redis para el volumen actual, conforme a `docs/architecture.md`).
- **Transporte:** `EmailTransport` sobre `django.core.mail.send_mail` (backend de consola en
  desarrollo, configurable vía `EMAIL_BACKEND`); clasificación transitorio/permanente (ITD-015).
- **Settings nuevos:** `SITE_BASE_URL` (ITD-013), `LEGAL_DOCUMENT_URLS` (ITD-014) — ambos
  respaldados por variables de entorno, sin secretos hardcodeados.

## 5. Evidencia de pruebas

```text
python manage.py check                                     -> System check identified no issues (0 silenced)
python manage.py makemigrations --check --dry-run           -> No changes detected
python manage.py test -v 1                                  -> Ran 840 tests in 563.110s — OK
```

- 840/840 tests de la suite completa del proyecto (no solo Fase 6) — cero regresiones en
  Fases 1-5. 828 → 840 en esta ronda (+12: +6 `notifications`, +3 `medical_records`,
  +3 `accounts` — ver `phase-6-implementation-summary.md` para el detalle por corrección).
- Pruebas de seguridad: acceso al audit trail denegado explícitamente por rol (paciente,
  médico, responsable, usuario inactivo, anónimo) y por mecanismo (API + UI + Django Admin);
  distinción `is_staff` vs. `is_superuser`.
- Pruebas de concurrencia/idempotencia: `dedupe_key` único, guarda de efecto-idempotencia en
  `_attempt_send`, `select_for_update(skip_locked=True)` para el reclamo de filas debidas,
  recuperación de `SENDING` huérfanas sin duplicar filas (`test_retry_after_orphan_recovery_
  does_not_duplicate_notification_row`).
- Pruebas de navegador (Claude in Chrome, interacción real — no `django.test.Client`):
  `docs/phases/evidence/phase-6-browser-validation/README.md`, 8 capturas + contenido de correo
  real por consola. Incluye la divulgación transparente de un incidente propio de la
  automatización (sesión no cerrada correctamente en los primeros dos intentos) y su corrección.

## 6. Auditoría final

- **Catálogo implementado:** ver §2 y §4 — `Action`/`ResourceType` de `AuditEvent` listados en
  `medical_records/models.py` líneas 234-283 (incluye las 5 entradas transversales de Fase 6).
- **Eventos de éxito:** `LOGIN` (éxito), `MODIFY_PATIENT`, `CHANGE_PERMISSIONS`, `DISABLE_USER` —
  cada uno con `actor` real resuelto por el servidor, nunca por el cliente (AH-084/086/173/175).
- **Eventos de rechazo:** cubiertos dentro del boundary instrumentado y con actor identificable
  (PD-002, precisado en Design Freeze §11/§12 esta ronda — C-017); un intento de login contra un
  correo inexistente queda deliberadamente fuera (sin actor resolvible), documentado, no oculto.
- **Acceso administrativo:** restringido a `is_superuser` en API, UI y Django Admin por igual
  (hallazgo 12.1, con tests que distinguen explícitamente de `is_staff`).
- **Ausencia de contenido clínico innecesario:** verificado en `EmailContentTests` (incluida la
  cobertura nueva de "cita modificada" — C-016) contra `_CLINICAL_TERMS`.
- **Retención indefinida:** sin `DELETE`/purga automática de `Notification` ni `AuditEvent` en
  ningún flujo — tratamiento histórico conforme a `CLAUDE.md` §6 "Información clínica".
- **Procedimiento manual de depuración:** no se implementó ninguno en esta fase — fuera de
  alcance por no estar solicitado (regla de alcance, `CLAUDE.md` §14).

## 7. Hallazgos y correcciones

- Ronda de auditoría inicial (previa a implementación): H-01, M-01, M-02, M-03, L-01, L-02 —
  cerrados mediante ediciones documentales dirigidas antes de implementar (ver historial de
  `phase-6-implementation-summary.md`).
- Ronda de implementación: hallazgos 12.1-12.9 y correcciones post-implementación PD-001 a
  PD-008, correcciones C-001 a C-011 (detalle completo en `phase-6-implementation-summary.md`).
- **Ronda de corrección post-implementación (7 prompts secuenciales, esta consolidación):**
  - C-012/C-013 (ITD-015): fallo permanente vs. transitorio en el transporte de email; una
    `SENDING` huérfana ya agotada en `MAX_DELIVERY_ATTEMPTS` podía reclamarse para un sexto
    intento — corregido.
  - C-014/C-015/C-016: cobertura de tests ampliada (acceso por rol explícito, referencia de
    documento configurada, email de cita modificada, enlace sin bypass de autorización) — sin
    cambios de código de producción, el comportamiento ya era correcto.
  - C-017: precisión de PD-002 incorporada formalmente al Design Freeze (antes solo estaba en
    documentos derivados).
  - C-018: `README.md` y `docs/architecture.md` — nunca actualizados en la ronda anterior — ahora
    reflejan el estado real (implementada, pendiente de auditoría de cierre).
  - Evidencia de navegador real capturada y verificada (Prompt 6), con un incidente propio de
    automatización divulgado con transparencia, no ocultado.
  - No se registró ningún `PD-009` — todos los hallazgos de esta ronda fueron técnicos o
    documentales, resueltos sin tocar alcance, política ni ninguna de las ocho decisiones
    cerradas del propietario.

## 8. Estado de cierre

```text
PHASE 6 — READY FOR CLOSURE
```

Esto no es `PHASE 6 — CLOSED`. Significa que, hasta donde la implementación puede verificar por
sí misma: las 7 decisiones F6-D01..F6-D07 y las 8 decisiones del propietario PD-001..PD-008 están
implementadas, probadas (840/840) y documentadas sin contradicciones; existe evidencia de
navegador real; y no quedan hallazgos técnicos abiertos de la ronda de corrección de 7 prompts.
El cierre formal (`PHASE 6 — CLOSED`) requiere una auditoría independiente de quien implementó
el código — ver la nota de riesgo conocido sobre la rutina de auditoría en la nube programada
contra `origin/main`, que a la fecha de esta consolidación no incluye estos commits (pendiente de
`git push` por decisión explícita del propietario del repositorio).

Fecha de esta consolidación: 2026-09-22

Commit de esta consolidación: ver auto-referencia en el commit inmediatamente posterior a este
documento (mismo patrón que `79697e0` — no confiar en un hash citado por adelantado; volver a
ejecutar `git rev-parse HEAD` en cualquier auditoría posterior).

Evidencia principal: `docs/phases/phase-6-implementation-summary.md` (bitácora técnica completa),
`docs/phases/evidence/phase-6-browser-validation/README.md` (evidencia de navegador).

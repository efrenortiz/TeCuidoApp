# TeCuidoApp — Fase 6
# Resumen de Implementación

## 1. Información general

- Fase: Fase 6 — Notificaciones y auditoría
- Fecha de inicio: 2026-09-21
- Fecha de finalización (implementación inicial): 2026-09-21
- Fecha de corrección post-implementación: 2026-09-21
- Rama: main
- Commit inicial: `cafa22b7a77fd5a1e5fc4de9979ecbe70abc2f49`
- Commit final: `14d3318e5c4f3e8b3a73eb14f5e042e429e6136b` (documentación; el trabajo de
  código/tests de esta fase está en `fd535e4`/`03c929c`, inmediatamente anteriores). Como en
  rondas anteriores de este proyecto, no asumir que este hash sigue siendo el HEAD real — volver
  a ejecutar `git rev-parse HEAD` en cualquier auditoría posterior.

> Este documento cubre dos rondas: la implementación inicial (§§1-17, texto original conservado
> salvo actualizaciones de estado) y la corrección post-implementación que incorpora las
> decisiones finales del propietario PD-001 a PD-008 y los hallazgos técnicos 12.1 a 12.9 (nuevas
> secciones "Decisiones del propietario incorporadas" y "Correcciones post-implementación").

## 2. Alcance implementado

- Notificaciones por Email para: invitación de registro, verificación de correo, cita
  creada/modificada/cancelada, recordatorios 15/10/5/1 días (F6-D01/F6-D02).
- Ausencia estructural de opt-out (F6-D03) — verificado por test, no solo por omisión.
- Auditoría transversal ampliada sobre el `AuditEvent` ya existente: `LOGIN`,
  `MODIFY_PATIENT`, `CHANGE_PERMISSIONS`, `DISABLE_USER` conectados a puntos de entrada reales
  — incluida la edición de `Person` de un paciente (corrección 12.6, C-006), no solo `Patient`;
  `ADMIN_SENSITIVE_ACCESS` agregado al catálogo, deliberadamente sin conectar (PD-001, decisión
  final del propietario, ya no "pendiente").
- Auditoría de rechazos para `LOGIN` en el alcance cerrado por PD-002 (antes ITD-008).
- Consulta administrativa del audit trail (API + UI + Django Admin — los tres puntos de acceso
  ahora exigen `is_superuser` consistentemente, corrección 12.1/C-001).
- Retención indefinida (F6-D07) — sin ningún job/command de depuración automática.
- Registro de aceptación de Aviso de Privacidad/Términos y Condiciones (F6-D04), con
  trazabilidad completa (quién/qué/versión/cuándo/dónde publicada) por versión, incluidas
  versiones ya superadas (PD-006, corrección C-011).
- Recuperación de contraseña: **no** integrada al nuevo transporte (PD-003, decisión final del
  propietario, antes ITD-005).
- Correos de citas con información esencial real (fecha/hora, médico, consultorio) + enlace a
  TeCuidoApp, sin contenido clínico, corrigiendo el lenguaje "Cita confirmada" → "Cita reservada"
  (PD-005, corrección C-010).
- Reintentos limitados con backoff exponencial, tope de intentos y recuperación de notificaciones
  huérfanas en `SENDING` (PD-007, corrección C-003/C-004, ITD-011/ITD-012).
- Configuración de recordatorios con efecto hacia adelante únicamente, sin reconciliación
  retroactiva (PD-004). *Corrección posterior:* la afirmación original de esta línea ("ya el
  comportamiento natural de la implementación") resultó falsa — ver C-019 más abajo
  ("Ronda de corrección funcional de recordatorios") para el hallazgo real y su corrección.
- Arquitectura de auditoría confirmada como decisión final: `medical_records.AuditEvent` +
  `medical_records.services.audit`, sin app `audit` nueva (PD-008, ya implementado, ahora
  ratificado por el propietario).

Explícitamente NO implementado (decisión, no omisión — ver §15/§17): WhatsApp/SMS, MFA, un
catálogo de versiones de política editable desde UI/Admin (PD-006 usa un registro en
`settings.LEGAL_DOCUMENT_URLS`), retry automatizado vía Celery/Redis (ITD-006 usa un management
command), reconciliación retroactiva de recordatorios ya programados (PD-004), una app `audit`
separada (PD-008), una operación conectada a `ADMIN_SENSITIVE_ACCESS` (PD-001).

## 3. Componentes existentes reutilizados

- `medical_records.AuditEvent` / `medical_records.services.audit` (`record_event`,
  `safe_record_event`, `list_audit_events`, ahora con filtros `result`/`date_from`/`date_to`) —
  fuente única de auditoría, ampliada con nuevas `Action`/`ResourceType`, sin tabla paralela.
- `medical_records.services.permissions.can_view_audit_log` — reutilizado tal cual para F6-D05.
- `appointments.services.appointment.create_appointment_from_hold` / `cancel_appointment` /
  `reschedule_appointment` — punto de enganche único de notificaciones de Agenda (verificado con
  `grep` que tanto `appointments/api.py` como `care_requests/services/care_request.py` llaman a
  `create_appointment_from_hold`, cubriendo reserva directa F2 y `CareRequest` F5 por igual).
- `django.core.mail` (`EMAIL_BACKEND`/`DEFAULT_FROM_EMAIL` ya configurados vía env en
  `settings.py`) como transporte real de Email — sin nuevo cliente SMTP.
- `patients.services.permissions` (`ResponsiblePatientRelationship.Status.ACTIVE`) para resolver
  destinatarios autorizados.
- Patrón de servicios basados en módulos con funciones (no clases `*Service`), consistente con
  `medical_records.services.*`, `care_requests.services.*`.
- Patrón `JsonApiView` local por app (Django + `JsonResponse`, sin DRF) — mismo patrón ya usado en
  `appointments/api.py`/`medical_records/api.py`; `accounts/api.py` define su propia copia mínima,
  siguiendo la convención existente de no compartir una base entre apps.
- Django Admin existente (`patients.admin.PatientAdmin`, `accounts.admin.UserAdmin`) como el único
  punto de entrada real hoy para `MODIFY_PATIENT`/`CHANGE_PERMISSIONS`/`DISABLE_USER` — confirmado
  por inspección de código antes de escribir nada (no existía ninguna vista propia de TeCuidoApp
  para estas operaciones).
- `django.contrib.auth.views.LoginView`, ya usado en `accounts/urls.py`, subclasificado para
  auditar `LOGIN` explícitamente (no vía signal — ver ITD-003).
- `django.contrib.auth.views.PasswordResetView`/`PasswordResetForm` (mecanismo ya existente y
  funcional de Fase 1) — ver ITD-005.
- `medical_records/services/record.py::get_or_create_for_patient` como precedente del patrón
  `get_or_create` idempotente reutilizado en `ConsentService.record_acceptance`.

## 4. Componentes nuevos

### App `notifications` (nueva, Fase 6)
- `notifications/models.py`: `ReminderWindow`, `Notification`.
- `notifications/services.py`: `EmailTransport`, `create_registration_invitation_notification`,
  `create_email_verification_notification`, `create_password_recovery_notification` (sin invocar,
  ver ITD-005), `notify_appointment_created/modified/cancelled`, `schedule_appointment_reminders`,
  `reschedule_appointment_reminders`, `cancel_appointment_reminders`, `process_due_notifications`.
- `notifications/receivers.py` + `notifications/apps.py::ready()`: conecta las señales de
  `appointments` sin que `appointments` importe `notifications` (ITD-002).
- `notifications/admin.py`: `ReminderWindowAdmin`, `NotificationAdmin` (solo lectura).
- `notifications/management/commands/process_due_notifications.py` (ITD-006).
- Migraciones `notifications/migrations/0001_initial.py`,
  `0002_seed_reminder_windows.py` (datos semilla 15/10/5/1).

### `appointments` (Fase 2, modificación aditiva mínima)
- `appointments/signals.py` (nuevo): `appointment_created`, `appointment_modified`,
  `appointment_cancelled`.
- `appointments/services/appointment.py`: tres líneas de `transaction.on_commit(...)` añadidas al
  final de `create_appointment_from_hold`/`cancel_appointment`/`reschedule_appointment` — ninguna
  lógica de negocio existente modificada, ningún valor de retorno alterado.

### `medical_records` (Fase 3, extensión del catálogo transversal)
- `medical_records/models.py`: `AuditEvent.Action` +5 (`LOGIN`, `MODIFY_PATIENT`,
  `CHANGE_PERMISSIONS`, `DISABLE_USER`, `ADMIN_SENSITIVE_ACCESS`); `AuditEvent.ResourceType` +2
  (`USER`, `PATIENT`). Migraciones `0006_alter_auditevent_action_and_more.py`,
  `0007_alter_auditevent_resource_type.py` (solo choices, sin cambio de esquema).
- `medical_records/services/audit.py::list_audit_events`: parámetros `result`/`date_from`/
  `date_to` agregados (mismo servicio, sin duplicar).
- `medical_records/api.py`: `AuditEventListView` (F6-D05).
- `medical_records/urls.py`: `audit/events/`.
- `medical_records/views.py`: `AuditTrailView`.
- `medical_records/urls_ui.py`: `auditoria/`.
- `templates/medical_records/audit_trail.html` (nuevo).

### `accounts` (Fase 1, extensión)
- `accounts/models.py`: `PolicyAcceptance` (ITD-001).
- `accounts/services/consent.py`: `record_acceptance`, `get_current_acceptance`,
  `has_accepted_version`, `acceptance_status` (ITD-009).
- `accounts/api.py` (nuevo): `ConsentAcceptView`, `ConsentStatusView`.
- `accounts/urls_api.py` (nuevo), registrado en `TeCuidoApp/urls.py` bajo `api/v1/consent/`.
- `accounts/views.py`: `AuditedLoginView` (ITD-003/ITD-008), `ConsentView`.
- `accounts/urls.py`: `login/` ahora usa `AuditedLoginView`; `consentimiento/` nuevo.
- `accounts/admin.py`: `UserAdmin.save_model`/`save_related` auditan `DISABLE_USER`/
  `CHANGE_PERMISSIONS`; `PolicyAcceptanceAdmin` (solo lectura).
- `accounts/views.py`: dos `send_mail(...)` directos reemplazados por
  `notification_service.create_registration_invitation_notification`/
  `create_email_verification_notification`.
- `templates/accounts/consent.html` (nuevo); `templates/accounts/home.html` — enlaces a
  "Audit trail" (admin) y "Aviso de privacidad y términos" (todos).
- Migración `accounts/migrations/0004_policyacceptance.py`.

### `patients` (Fase 1, extensión)
- `patients/admin.py`: `PatientAdmin.save_model` audita `MODIFY_PATIENT`.

### `TeCuidoApp/settings.py`
- `'notifications'` agregado a `INSTALLED_APPS`.

## 5. Decisiones técnicas tomadas durante la implementación

### ITD-001 — Consent sin app propia

- Problema: los documentos de diseño no asignan `PolicyAcceptance` a ninguna app concreta.
- Alternativas: (A) app `consent` nueva; (B) vivir en `accounts`.
- Decisión: (B).
- Justificación: `phase-6-design-freeze.md` §8 solo anticipa dos apps transversales nuevas
  (`notifications`, `audit`); un único modelo pequeño, atado 1:1 a `User`, no justifica una
  tercera app (principio de infraestructura mínima, §18.1/§22 del Design Freeze).
- Impacto: `PolicyAcceptance` y sus servicios/endpoints viven en `accounts`.
- Archivos: `accounts/models.py`, `accounts/services/consent.py`, `accounts/api.py`.

### ITD-002 — Notificaciones de Agenda vía Django signals, no llamada directa

- Problema: `notify_appointment_created/modified/cancelled` deben ejecutarse cuando
  `appointments.services.appointment` crea/cancela/reprograma una cita, pero `appointments`
  (Fase 2) no debe importar `notifications` (Fase 6) — ninguna fase anterior del proyecto importa
  una fase posterior (`care_requests`/`medical_records` importan `appointments`, nunca al revés).
- Alternativas: (A) `appointments` importa y llama directamente a `notifications.services`;
  (B) `appointments` despacha señales propias (`appointments/signals.py`), `notifications` las
  escucha.
- Decisión: (B).
- Justificación: preserva la dirección de dependencia ya establecida en todo el proyecto; el
  efecto es por diseño desacoplado de la transacción de negocio
  (`phase-6-design-freeze.md` §21), exactamente el caso de uso de Django signals +
  `transaction.on_commit`. No es el mismo caso que `medical_records/services/audit.py`'s AH-156
  ("nunca delegar auditoría a signals") — esa regla es sobre fidelidad de auditoría clínica, no
  sobre notificaciones con degradación ya tolerada por diseño.
- Impacto: `appointments/signals.py` (nuevo), 3 líneas en `appointment.py`,
  `notifications/receivers.py` + `apps.py::ready()`.
- Archivos: `appointments/signals.py`, `appointments/services/appointment.py`,
  `notifications/receivers.py`, `notifications/apps.py`.

### ITD-003 — `LOGIN` auditado por subclase de vista, no por signal

- Problema: dónde registrar `AuditEvent(action=LOGIN)`.
- Alternativas: (A) señales `user_logged_in`/`user_login_failed` de Django;
  (B) subclase de `LoginView` con `form_valid`/`form_invalid` explícitos.
- Decisión: (B).
- Justificación: AH-156 (`medical_records/services/audit.py`) cierra que la auditoría nunca se
  delega a un signal genérico — el significado de la operación lo decide el código que conoce el
  resultado real, en el punto exacto. Una subclase de vista cumple ese principio para `LOGIN`
  igual que un servicio de dominio lo cumple para operaciones clínicas.
- Impacto: `accounts/urls.py` usa `AuditedLoginView` en vez de `auth_views.LoginView` directo.
- Archivos: `accounts/views.py`, `accounts/urls.py`.

### ITD-004 — Auditoría de `MODIFY_PATIENT`/`CHANGE_PERMISSIONS`/`DISABLE_USER` vía Django Admin

- Problema: no existe ninguna vista propia de TeCuidoApp para modificar un `Patient` o cambiar
  `is_active`/`is_staff`/`is_superuser`/`groups`/`user_permissions` de un `User` — Django Admin
  (`/admin/`) es la única superficie real donde esto ocurre hoy.
- Decisión: instrumentar `PatientAdmin.save_model` y `UserAdmin.save_model`/`save_related`
  (M2M se guarda en un paso separado en Django Admin) para emitir el `AuditEvent`
  correspondiente después de la persistencia real, dentro de la misma transacción que ya envuelve
  `_changeform_view`.
- Alcance explícito: solo se audita el **éxito**. Un rechazo (usuario sin permiso de Django Admin)
  nunca llega a `save_model` — Django Admin ya lo bloquea con su propio sistema de permisos antes;
  duplicar esa auditoría sería redundante con un mecanismo que el framework ya garantiza.
- Impacto: `patients/admin.py`, `accounts/admin.py`.

### ITD-005 — Recuperación de contraseña no se envuelve en el nuevo transporte

- Problema: `phase-6-notification-service-contracts.md` §2 define
  `create_password_recovery_notification(...)`, pero la recuperación de contraseña ya existente
  usa `django.contrib.auth.views.PasswordResetView`/`PasswordResetForm`, que genera y envía su
  propio correo internamente (token firmado, plantilla propia) sin ningún punto de extensión
  limpio sin reimplementar ese flujo.
- Decisión: dejar `PasswordResetView`/`PasswordResetForm` exactamente como están; implementar
  `create_password_recovery_notification` por contrato (existe, es invocable, tiene tests
  implícitos de que no rompe nada) pero **no conectarla**.
- Justificación: reescribir el flujo de Django ya battle-tested para forzarlo a pasar por
  `notifications` no tiene una necesidad demostrada (CLAUDE.md §13/§14, "no crear
  infraestructura... sin necesidad real") y arriesga la seguridad de un mecanismo crítico
  (recuperación de contraseña) sin beneficio funcional — el correo se sigue enviando, solo que por
  el camino ya existente.
- Impacto: `create_password_recovery_notification` queda disponible pero sin llamador; ver §7
  (desviación documentada) y §17 (recomendación posterior).
- Archivos: `notifications/services.py`.

### ITD-006 — `process_due_notifications` como management command, no Celery/Redis

- Problema: los recordatorios requieren ejecución diferida.
- Decisión: `python manage.py process_due_notifications`, pensado para cron del SO.
- Justificación: `phase-6-design-freeze.md` §19/§24 prohíbe infraestructura asíncrona sin
  necesidad real; el proyecto no tiene Celery/Redis instalado; CLAUDE.md §8 prefiere management
  commands cuando corresponden.
- Impacto: requiere que operaciones/infraestructura configure un cron externo — ver §15/§17.
- Archivos: `notifications/management/commands/process_due_notifications.py`.

### ITD-007 — Recordatorios materializados al crear la cita, no calculados bajo demanda

- Problema: `phase-6-notification-data-model.md` §5 deja abiertas ambas opciones.
- Decisión: materializar 4 filas (una por ventana activa × destinatario elegible) en
  `schedule_appointment_reminders`, invocada desde `notify_appointment_created`.
- Justificación: mantiene la deduplicación trivial por `dedupe_key` estable
  (`APPOINTMENT_REMINDER:{appointment_id}:{recipient_id}:{offset_days}`), y el recálculo en
  reprogramación/cancelación es una actualización de filas existentes, no una regeneración.
- Impacto: `schedule_appointment_reminders`, `reschedule_appointment_reminders`,
  `cancel_appointment_reminders`.
- Archivos: `notifications/services.py`.

### ITD-008 — Alcance de auditoría de `LOGIN` fallido

- Problema: `record_event`/`safe_record_event` exigen un `actor` real (AH-086, invariante ya
  cerrada de Fase 3) — un intento de login con credenciales inválidas contra un correo que no
  existe no tiene ningún `User` real al que atribuir el evento.
- Decisión: auditar `LOGIN DENIED` únicamente cuando `form.get_user()` resuelve un usuario real
  (p. ej. contraseña correcta pero correo no verificado); un intento contra un correo inexistente
  o con contraseña incorrecta para un correo existente (donde Django nunca resuelve el usuario en
  el formulario) no genera `AuditEvent`.
- Justificación: no se relaja la invariante AH-086 ya cerrada de Fase 3 solo para cubrir este caso
  — hacerlo sería tratar el propio mecanismo de auditoría como negociable.
- Impacto: cobertura de auditoría de login parcial pero honesta; ver test
  `test_wrong_password_against_unknown_identity_is_not_audited`.
- Archivos: `accounts/views.py`.

### ITD-009 — Validación de "versión inexistente" sin CMS de documentos

- Problema: `phase-6-consent-domain.md` §6 exige "impedir aceptar una versión inexistente" sin
  definir de dónde sale el catálogo de versiones válidas.
- Decisión: registro mínimo a nivel de código (`CURRENT_POLICY_VERSIONS`), una única versión
  vigente aceptable por `policy_type`.
- Justificación: consent-domain.md §5 explícitamente excluye que Fase 6 decida contenido/versión
  jurídica de los documentos — un catálogo editable sería una funcionalidad no pedida por ninguna
  fuente superior (CLAUDE.md §14).
- Impacto: cambiar la versión vigente requiere un despliegue de código (a diferencia de las
  ventanas de recordatorio, que si son configurables sin desplegar — ver H-01 del audit report).
  Esto es una asimetría deliberada, no un descuido: la versión de un documento legal SÍ debería
  requerir una acción humana deliberada (publicar código nuevo), a diferencia de un parámetro
  puramente operativo como una ventana de recordatorio.
- Archivos: `accounts/services/consent.py`.

### ITD-010 — `_attempt_send` nunca reenvía un `Notification` ya `SENT`

- Problema: `_get_or_create_notification` ya deduplica la *fila*, pero
  `notify_appointment_*` llamaba a `_attempt_send` incondicionalmente sobre el resultado, incluso
  cuando `_get_or_create_notification` devolvía una fila ya existente y ya enviada — encontrado
  durante la propia revisión de código de esta implementación con un test que simulaba un segundo
  despacho manual del mismo evento.
- Decisión: `_attempt_send` retorna de inmediato sin reintentar transporte si
  `notification.status == SENT`.
- Justificación: `phase-6-notification-domain.md` §11 exige que "un mismo evento lógico no debe
  producir accidentalmente múltiples efectos" — no solo múltiples filas.
- Impacto: ningún test previo lo cubría explícitamente; se fortaleció antes de que fuera un bug en
  producción, no después.
- Archivos: `notifications/services.py`.

### ITD-011 — Valores concretos de reintentos y backoff (implementa PD-007)

- Problema: PD-007 exige "reintentos limitados + backoff" pero deja los valores concretos como
  decisión técnica.
- Decisión: `MAX_DELIVERY_ATTEMPTS = 5`; backoff exponencial `60s * 2^(attempt_count-1)`, tope
  `BACKOFF_MAX_SECONDS = 6h`.
- Justificación: escala actual del proyecto (volumen bajo, un solo proceso, sin infraestructura de
  colas) — un backoff de minutos-a-horas es suficiente para absorber una interrupción SMTP
  transitoria sin generar una tormenta de reintentos ni retrasar una notificación operativa por
  días. No representa una política funcional (no cambia destinatarios, contenido ni alcance).
- Impacto: una notificación agota sus reintentos en, como máximo,
  `60+120+240+480 = 900s (~15 min)` de la primera falla a la última, si cada intento vuelve a
  fallar de inmediato.
- Archivos: `notifications/services.py` (`MAX_DELIVERY_ATTEMPTS`, `BACKOFF_BASE_SECONDS`,
  `BACKOFF_MAX_SECONDS`, `_backoff_seconds`).

### ITD-012 — `SENDING_LEASE_TIMEOUT` para recuperar notificaciones huérfanas (implementa PD-007 / hallazgo 12.3)

- Problema: un proceso interrumpido entre marcar una fila `SENDING` y persistir el resultado real
  la deja bloqueada indefinidamente.
- Decisión: `SENDING_LEASE_TIMEOUT = 10 minutos`. `process_due_notifications` reclama cualquier
  fila `SENDING` cuyo `last_attempt_at` exceda ese lease: si su tipo es reintentable
  (`APPOINTMENT_*`), se reintenta como cualquier `FAILED`/`PENDING` vencido; si no
  (`REGISTRATION_INVITATION`/`EMAIL_VERIFICATION`/`PASSWORD_RECOVERY`, contenido de un solo uso no
  reconstruible), se cierra como `FAILED` con `reason_code=ORPHANED_NON_RETRYABLE_SENDING` sin
  reenviar contenido genérico incorrecto.
- Justificación: 10 minutos es varias veces el tiempo esperado de un envío SMTP normal (segundos),
  suficiente margen para no reclamar prematuramente una fila que en realidad sigue en curso en un
  proceso sano, sin dejar una fila huérfana bloqueada por horas.
- Impacto: ningún cron/servicio adicional — el propio `process_due_notifications` hace la
  recuperación en su ejecución normal.
- Archivos: `notifications/services.py` (`SENDING_LEASE_TIMEOUT`, `process_due_notifications`).

### ITD-013 — `SITE_BASE_URL` para enlaces en notificaciones (implementa PD-005)

- Problema: los correos deben incluir un enlace a TeCuidoApp (PD-005), pero se generan fuera de un
  request HTTP (dentro de un receiver de señal) — no hay `request.build_absolute_uri()` disponible.
- Decisión: nueva variable de entorno/`setting` `SITE_BASE_URL` (default
  `http://localhost:8000` en desarrollo), usada para construir
  `f"{SITE_BASE_URL}{reverse(...)}"`.
- Justificación: mismo patrón ya usado por el proyecto para otras variables de infraestructura
  (`EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`) — configuración por entorno, nunca hardcodeada.
- Impacto: debe configurarse `SITE_BASE_URL` con el dominio real en producción (ver §15/§17); sin
  configurar, los enlaces de desarrollo apuntan a `localhost:8000`, funcional en local pero no
  utilizable si se copia el correo fuera de esa máquina.
- Archivos: `TeCuidoApp/settings.py`, `.env.example`, `notifications/services.py`
  (`_appointment_url`).

### ITD-014 — Registro versión→URL para la referencia canónica de documentos legales (implementa PD-006)

- Problema: PD-006 exige poder responder "¿dónde estaba publicada esa versión?", incluso para una
  versión ya superada — no solo la vigente.
- Decisión: `settings.LEGAL_DOCUMENT_URLS = {policy_type: {version: url}}`, configurable por
  variable de entorno (`PRIVACY_NOTICE_URL`, `TERMS_AND_CONDITIONS_URL`), con una entrada por
  versión conocida (hoy solo `"1.0"` para cada tipo, igual que
  `consent.CURRENT_POLICY_VERSIONS`).
- Justificación: conservar el diccionario completo (no solo la versión vigente) es lo que permite
  que `acceptance_trace(...)` siga respondiendo correctamente para una aceptación histórica
  después de que se publique una versión nueva — sin esto, PD-006 quedaría satisfecho solo para la
  versión vigente, no para el historial completo que la propia decisión exige.
- Impacto: agregar una versión nueva requiere una entrada nueva en `LEGAL_DOCUMENT_URLS` **y** en
  `CURRENT_POLICY_VERSIONS` — ambas son decisiones de producto/legal (ITD-009), no técnicas.
- Archivos: `TeCuidoApp/settings.py`, `.env.example`, `accounts/services/consent.py`
  (`document_url`, `acceptance_trace`).

## Decisiones del propietario incorporadas

Las ocho decisiones fueron recibidas ya cerradas por el propietario (Prompt de corrección
post-implementación, 2026-09-21) y se incorporaron exactamente como fueron dadas — ninguna se
reinterpretó ni se volvió a presentar como pendiente.

- **PD-001** — `ADMIN_SENSITIVE_ACCESS` permanece definida en el catálogo de auditoría, sin
  operación emisora, sin inventarle una, sin eliminarla. Ver `phase-6-audit-domain.md` §3 y
  §19 (tabla) más abajo.
- **PD-002** — F6-D06 se interpreta como "se auditan los rechazos que alcanzan el boundary
  instrumentado y permiten identificar un actor"; fallos previos al boundary, rechazos del
  framework y casos sin actor resoluble quedan fuera, documentado explícitamente. No se rediseñó
  `AuditEvent` para aceptar actores inexistentes. Ver `phase-6-audit-domain.md` §4.
- **PD-003** — Recuperación de contraseña permanece en el flujo nativo de Django
  (`PasswordResetView`/`PasswordResetForm`); no se migra a `notifications`.
  `create_password_recovery_notification(...)` sigue definida, sin uso. Ver
  `phase-6-notification-domain.md` §3.
- **PD-004** — `ReminderWindow` es configurable con efecto hacia adelante únicamente; no se
  construyó reconciliación retroactiva, job masivo ni snapshot. Ver
  `phase-6-notification-data-model.md` §2.2.
- **PD-005** — Los correos de citas contienen información esencial (fecha/hora, médico,
  consultorio) + enlace a TeCuidoApp, nunca información clínica; se corrigió "Cita confirmada" →
  "Cita reservada". Ver `phase-6-notification-security-and-privacy.md` §1.
- **PD-006** — Aviso de Privacidad y Términos son documentos externos versionados; TeCuidoApp
  conserva usuario/documento/versión/fecha + referencia canónica por versión (incluidas versiones
  superadas), sin convertirse en gestor jurídico. Ver `phase-6-consent-domain.md` §1.
- **PD-007** — Reintentos limitados (`MAX_DELIVERY_ATTEMPTS=5`) con backoff exponencial
  (ITD-011) y recuperación de `SENDING` huérfano por lease timeout (ITD-012); sin estado nuevo —
  `FAILED` sirve como terminal, distinguido por `attempt_count`/`reason_code`. Ver
  `phase-6-notification-domain.md` §6 y `phase-6-notification-service-contracts.md` §4.
- **PD-008** — `audit` permanece como responsabilidad lógica transversal, físicamente
  `medical_records.AuditEvent`/`medical_records.services.audit`; no se creó una app `audit`, no
  se movió `AuditEvent`, no existe una segunda fuente de verdad. Ver `phase-6-audit-domain.md` §2
  (ya documentado desde la implementación inicial como M-02/ITD; el propietario ratifica esa
  misma decisión, no la cambia).

## 6. Hallazgos que requieren decisión del propietario

### PD-001 — `ADMIN_SENSITIVE_ACCESS` sin operación real que auditar

- Hallazgo: el catálogo base (`phase-6-audit-domain.md` §3, `requirements.md` §31) incluye
  "Acceso de administrador a información sensible" como acción auditable. No existe en el
  repositorio ninguna operación distinta de `MODIFY_PATIENT`/`CHANGE_PERMISSIONS`/`DISABLE_USER`
  que represente específicamente "un administrador consultó información sensible" (p. ej. no
  existe una pantalla de "ver expediente como administrador" — y no debería existir, dado que
  Fase 3/6 cierran que el rol administrativo no tiene bypass clínico).
- Evidencia: `grep` sobre `patients/`, `accounts/`, `medical_records/` no encontró ninguna vista
  administrativa de solo-lectura de datos sensibles distinta del CRUD ya auditado.
- Por qué no podía resolverse técnicamente: inventar un punto de auditoría para una acción sin
  operación correspondiente implicaría crear esa operación — eso era una decisión de alcance de
  producto, no una decisión técnica.
- Opciones presentadas: A — dejarlo definido sin conectar; B — definir una vista/consulta
  administrativa actual como "acceso a información sensible"; C — retirar la constante del
  catálogo.
- **Decisión del propietario: Alternativa A.** `AuditEvent.Action.ADMIN_SENSITIVE_ACCESS`
  permanece en el catálogo (migración ya aplicada), sin operación emisora, sin inventarle una y
  sin eliminarla. Podrá usarse cuando exista una operación real cuya semántica corresponda.
- Estado: **RESUELTO POR PROPIETARIO** (Alternativa A). Ver también
  `docs/design/phase-6-audit-domain.md` §3.

## Correcciones post-implementación

Hallazgos técnicos 12.1 a 12.9 del prompt de corrección — ninguno requirió una nueva decisión de
producto; todos se resolvieron técnicamente.

### Índice de commits (prompt 3/4, consolidación documental)

Ninguna corrección de esta lista queda pendiente — las 20 están implementadas, probadas y
commiteadas. Detalle completo (problema/causa/solución/tests) en la entrada narrativa de cada
`C-XXX` más abajo o en la sección de ronda correspondiente; esta tabla es solo el índice
commit-por-corrección que exige la consolidación documental.

| ID | Resumen | Commit(s) |
|---|---|---|
| C-001 | Django Admin del audit trail exigía `is_superuser`, no solo `is_staff` | `fd535e4` |
| C-002 | Cobertura de tests de auditoría de rechazos (PD-002) | `fd535e4` |
| C-003 | Recuperación de `SENDING` huérfano por lease timeout | `fd535e4` |
| C-004 | Límite de reintentos + backoff (`MAX_DELIVERY_ATTEMPTS`) | `fd535e4` |
| C-005 | Recordatorios `FAILED` incluidos en reprogramación/cancelación | `fd535e4` |
| C-006 | Edición de `Person` de un paciente vía Admin ahora audita `MODIFY_PATIENT` | `fd535e4` |
| C-007 | `send_mail` con 0 entregas ahora se trata como fallo | `fd535e4` |
| C-008 | Filtros `date_from`/`date_to` agregados a la UI del audit trail | `fd535e4` |
| C-009 | Pantalla de consentimiento con referencia canónica y fecha | `fd535e4` |
| C-010 | Contenido real de los correos de cita + asunto corregido | `fd535e4` |
| C-011 | Trazabilidad completa de consentimiento (`acceptance_trace`) | `fd535e4` |
| C-012 | `SENDING` huérfana en el máximo de intentos no se reclama de nuevo | `628e247` |
| C-013 | Fallo permanente no se vuelve a reclamar antes de agotar intentos | `628e247` |
| C-014 | Cobertura explícita por rol del acceso denegado al audit trail | `cb7d099` |
| C-015 | Tests de referencia de documento con `LEGAL_DOCUMENT_URLS` configurado | `cb7d099` |
| C-016 | Cobertura del email de cita modificada + no-bypass del enlace | `cb7d099` |
| C-017 | Precisión de PD-002 incorporada al Design Freeze §11/§12 | `46a16af` |
| C-018 | README.md/architecture.md corregidos ("implementada", no "siguiente") | `46a16af` |
| C-019 | Reprogramación de recordatorios ahora relee `ReminderWindow` vigente (PD-004) | código `cb8fe85`, tests `02e2738`, docs `38d22db` |
| C-020 | `patient_id` no numérico ya no rompe la UI del audit trail | código `aeb9403`, tests `daae3f9`, docs `592c356` |

**Commit final auditado de esta consolidación (prompt 3/4):** ver auto-referencia en
`docs/phases/phase-6-final-report.md` §5 (mismo patrón de auto-referencia trivial ya usado en
`79697e0`/`46a16af`/`a0793f0` — no confiar en un hash citado por adelantado; volver a ejecutar
`git rev-parse HEAD` en cualquier auditoría posterior).

### C-001 — Acceso inconsistente al audit trail vía Django Admin (hallazgo 12.1)

- Problema: `AuditEventAdmin` (Django Admin) solo dependía del gate genérico de `/admin/`
  (`is_staff=True`), mientras que `AuditEventListView` (API) y `AuditTrailView` (UI) exigían
  `is_superuser` vía `can_view_audit_log`. Cualquier usuario `is_staff=True` no administrador
  podía ver el audit trail completo por Django Admin.
- Causa: `AuditEventAdmin` nunca sobrescribió `has_view_permission`/`has_module_permission`;
  heredaba el permiso genérico de `ModelAdmin`, basado en permisos Django estándar
  (`is_staff` + permiso de modelo), no en la regla F6-D05.
- Solución: `has_module_permission`/`has_view_permission` ahora exigen explícitamente
  `request.user.is_superuser`, igual que `can_view_audit_log`.
- Archivos: `medical_records/admin.py`.
- Tests: `medical_records/tests/test_fase6_audit.py::AuditTrailAccessTests::
  test_django_admin_staff_without_superuser_cannot_see_audit_trail`,
  `::test_django_admin_superuser_can_see_audit_trail`.

### C-002 — Cobertura de auditoría de rechazos (hallazgo 12.2, aplica PD-002)

- Problema: la interpretación cerrada de F6-D06 (PD-002) no tenía cobertura de prueba explícita
  para "usuario inactivo" y "acceso administrativo no autorizado" en el contexto F6.
- Causa: cobertura insuficiente, no un defecto de código — los mecanismos subyacentes
  (`ModelBackend` para usuarios inactivos, `can_view_audit_log` para acceso no autorizado) ya
  funcionaban correctamente.
- Solución: se agregaron tests explícitos que demuestran ambos casos y que un rechazo nunca queda
  registrado como `SUCCESS`.
- Archivos: ninguno de producción — solo tests.
- Tests: `medical_records/tests/test_fase6_audit.py::RejectionAuditCoverageTests`.

### C-003 — Recuperación de `SENDING` huérfano (hallazgo 12.3, implementa PD-007)

- Problema: una fila marcada `SENDING` justo antes de un fallo del proceso (no del transporte)
  quedaba bloqueada indefinidamente — `process_due_notifications` no la volvía a considerar
  nunca, porque su filtro original solo miraba `PENDING`/`FAILED`.
- Causa: no existía ningún mecanismo de lease/timeout sobre el estado `SENDING`.
- Solución: `SENDING_LEASE_TIMEOUT` (ITD-012) — una fila `SENDING` con `last_attempt_at` vencido
  se reclama junto con las `PENDING`/`FAILED` vencidas; si su tipo no es reintentable
  (contenido de un solo uso), se cierra como `FAILED` sin reenviar.
- Archivos: `notifications/services.py` (`process_due_notifications`).
- Tests: `notifications/tests/test_services.py::RetryBackoffTests::
  test_orphaned_sending_retryable_notification_is_reclaimed`,
  `::test_orphaned_sending_non_retryable_notification_is_closed_without_resend`.

### C-004 — `FAILED` sin límite de reintentos (hallazgo 12.4, implementa PD-007)

- Problema: `process_due_notifications` reintentaba una fila `FAILED` indefinidamente, sin límite
  de intentos ni backoff — un fallo permanente (p. ej. dirección inválida) se reintentaría para
  siempre en cada ejecución del comando.
- Causa: `_attempt_send` no aplicaba ninguna política de reintentos — solo marcaba `FAILED` o
  `SENT` sin considerar `attempt_count`.
- Solución: `MAX_DELIVERY_ATTEMPTS=5` (ITD-011) con backoff exponencial; al agotar los intentos,
  la fila queda `FAILED` con `reason_code` prefijado `MAX_ATTEMPTS_EXCEEDED:` y
  `process_due_notifications` deja de reclamarla (`attempt_count__lt=MAX_DELIVERY_ATTEMPTS` en el
  filtro).
- Archivos: `notifications/services.py` (`_attempt_send`, `process_due_notifications`).
- Tests: `notifications/tests/test_services.py::RetryBackoffTests::
  test_failed_attempt_reschedules_with_backoff_not_immediate_retry`,
  `::test_notification_permanently_failed_after_max_attempts`,
  `::test_exhausted_notification_is_not_reclaimed_by_process_due_notifications`.

### C-005 — Recordatorios `FAILED` no recalculados en reprogramación/cancelación (hallazgo 12.5)

- Problema: `reschedule_appointment_reminders`/`cancel_appointment_reminders` solo consideraban
  recordatorios `PENDING`. Un recordatorio que había fallado una vez (`FAILED`, con reintentos
  restantes) y seguía siendo elegible para reintento no se recalculaba al reprogramar la cita, ni
  se cancelaba al cancelarla — podía terminar enviándose con la fecha vieja, o enviándose para una
  cita ya cancelada.
- Causa: el filtro de ambas funciones usaba `status=PENDING` exclusivamente, sin considerar que
  PD-007 introdujo `FAILED` como un estado también "vivo" mientras queden reintentos.
- Solución: ambas funciones ahora filtran
  `status__in=[PENDING, FAILED], attempt_count__lt=MAX_DELIVERY_ATTEMPTS`.
- Archivos: `notifications/services.py` (`reschedule_appointment_reminders`,
  `cancel_appointment_reminders`).
- Tests: `notifications/tests/test_services.py::RetryBackoffTests::
  test_reschedule_recomputes_failed_reminder_with_attempts_remaining`.

### C-006 — Edición de `Person` de un paciente no auditada como `MODIFY_PATIENT` (hallazgo 12.6)

- Problema: `PatientAdmin.save_model` era el único hook de `MODIFY_PATIENT`. Editar la `Person`
  vinculada a un paciente (nombre, teléfono, dirección) desde `PersonAdmin` — un camino real y
  disponible en Django Admin — modificaba información del paciente sin generar ningún
  `AuditEvent`.
- Causa: la relación `Patient.person` (OneToOne) no tenía ningún hook simétrico en
  `PersonAdmin`.
- Solución: `PersonAdmin.save_model` detecta si la `Person` editada tiene un `patient_profile`
  vinculado (`getattr(obj, "patient_profile", None)`) y, si lo tiene, emite `MODIFY_PATIENT` con
  `reason_code="PERSON_FIELDS"` para distinguirlo del camino directo por `PatientAdmin`.
- Archivos: `accounts/admin.py`.
- Tests: `medical_records/tests/test_fase6_audit.py::AdminModelAuditTests::
  test_modify_person_of_a_patient_via_admin_is_audited`.

### C-007 — Resultado real del transporte Email no validado (hallazgo 12.7)

- Problema: `EmailTransport.send` marcaba éxito con solo "`send_mail` no lanzó excepción" — un
  backend que "no falla" pero reporta 0 mensajes entregados se marcaría igualmente `SENT`.
- Causa: no se inspeccionaba el valor de retorno de `send_mail` (el número de mensajes
  efectivamente entregados).
- Solución: se captura el valor de retorno; `0` se trata como fallo
  (`reason_code=TRANSPORT_ZERO_DELIVERED`), sujeto a la misma política de reintentos/backoff que
  cualquier otro fallo de transporte.
- Archivos: `notifications/services.py` (`EmailTransport.send`).
- Tests: `notifications/tests/test_services.py::RetryBackoffTests::
  test_transport_zero_delivered_is_treated_as_failure`.

### C-008 — UI del audit trail sin los filtros de fecha del contrato (hallazgo 12.8)

- Problema: `phase-6-audit-api-contracts.md` §3 compromete `date_from`/`date_to` como filtros del
  audit trail. `AuditEventListView` (API) ya los soportaba; `AuditTrailView` (UI) no — una
  capacidad exclusivamente en la API, no en la UX, contra lo que exige el hallazgo.
- Causa: `AuditTrailView.get` nunca leía esos parámetros de `request.GET`.
- Solución: se agregan campos `date_from`/`date_to` (`<input type="date">`) al formulario de
  filtros, parseados por un helper `_parse_ui_date` (inicio/fin de día en la zona horaria activa)
  y pasados a `list_audit_events`.
- Archivos: `medical_records/views.py` (`AuditTrailView`, `_parse_ui_date`),
  `templates/medical_records/audit_trail.html`.
- Tests: `medical_records/tests/test_fase6_audit.py::AuditTrailAccessTests::
  test_ui_supports_date_range_filter_like_the_api`.

### C-009 — Pantalla de consentimiento sin referencia canónica ni fecha (hallazgo 12.9, aplica PD-006)

- Problema: antes de PD-006, la pantalla de consentimiento (`accounts/consent.html`) solo mostraba
  un booleano aceptado/pendiente — ni la referencia externa del documento ni cuándo se aceptó.
- Causa: `acceptance_status(...)` devolvía `{policy_type: bool}`, sin espacio para más datos.
- Solución: `acceptance_status(...)` ahora devuelve, por documento, `accepted`/`version`/
  `document_url`/`accepted_at`; la plantilla muestra el enlace "Leer el documento" (cuando hay
  URL configurada) y, si ya se aceptó, la fecha.
- Archivos: `accounts/services/consent.py`, `accounts/views.py` (`ConsentView._context`),
  `templates/accounts/consent.html`.
- Tests: `accounts/tests/test_consent.py::ConsentApiTests::
  test_status_endpoint_reflects_pending_and_accepted` (shape actualizado).

### C-010 — Contenido de correos de citas insuficiente (implementa PD-005)

- Problema: las plantillas originales eran texto genérico ("Tu cita fue reservada
  correctamente.") sin fecha/hora, médico, consultorio ni enlace — y el asunto "Cita confirmada"
  sugería un estado (`CONFIRMED`) que `Appointment` no tiene.
- Causa: `_render(...)` usaba un diccionario estático de `(asunto, mensaje)` por tipo de evento,
  sin consultar el recurso referenciado.
- Solución: para los cuatro eventos de cita, `_render` ahora recupera la `Appointment` referida
  (`resource_id`) y construye el mensaje con fecha/hora local (zona horaria de `Clinic`), médico,
  consultorio y un enlace (`_appointment_url`, ITD-013). Asunto corregido a "Cita reservada".
- Archivos: `notifications/services.py` (`_render`, `_appointment_essentials`,
  `_appointment_url`, `_APPOINTMENT_EVENT_COPY`).
- Tests: `notifications/tests/test_services.py::EmailContentTests` (3 tests: creada, cancelada,
  recordatorio).

### C-011 — Trazabilidad de consentimiento incompleta (implementa PD-006)

- Problema: `PolicyAcceptance` ya conservaba usuario/versión/fecha, pero no había forma de
  responder "¿dónde estaba publicada esa versión?" — la quinta pregunta que PD-006 exige poder
  responder.
- Causa: no existía ningún registro de referencia externa por versión.
- Solución: `settings.LEGAL_DOCUMENT_URLS` (ITD-014) + `consent.document_url(...)` +
  `consent.acceptance_trace(...)` (responde las cinco preguntas en una sola llamada), expuestos
  también en `acceptance_status(...)` para la UI/API.
- Archivos: `TeCuidoApp/settings.py`, `.env.example`, `accounts/services/consent.py`.
- Tests: `accounts/tests/test_consent.py::ConsentApiTests::
  test_acceptance_trace_answers_the_five_pd006_questions`,
  `::test_acceptance_trace_none_when_never_accepted`.

## 7. Desviaciones respecto a la documentación

Ninguna de las desviaciones listadas aquí es ya un hallazgo abierto — las tres están cerradas por
una decisión explícita del propietario (PD-003/PD-002/PD-001), no por una interpretación propia.

- **PD-003** (antes ITD-005): `create_password_recovery_notification` existe por contrato pero no
  está conectada — la recuperación de contraseña sigue el flujo nativo de Django, no el nuevo
  transporte. Confirmado como decisión final, no como algo pendiente de revisar. Ver §5/§6.
- **PD-002** (interpretación cerrada de F6-D06): cubierto de forma exhaustiva para las
  operaciones clínicas ya existentes de Fase 3 (sin cambios — ya emitían `DENIED`) y para `LOGIN`
  dentro del alcance acordado. No se auditan rechazos de `MODIFY_PATIENT`/`CHANGE_PERMISSIONS`/
  `DISABLE_USER` porque Django Admin nunca deja llegar un intento no autorizado hasta el código
  instrumentado (ver ITD-004) — el "rechazo" ya lo maneja el framework, con su propio mecanismo
  (403/redirect a login), sin generar un `AuditEvent`. Ver §6/C-002.
- **PD-001**: `ADMIN_SENSITIVE_ACCESS` definida sin conectar — desviación deliberada y
  permanente respecto a "todo el catálogo base debe estar conectado", no un pendiente.

## 8. Migraciones

| Migración | App | Contenido |
|---|---|---|
| `0001_initial.py` | notifications | `ReminderWindow`, `Notification` |
| `0002_seed_reminder_windows.py` | notifications | Datos semilla 15/10/5/1 días (`RunPython`, reversible) |
| `0006_alter_auditevent_action_and_more.py` | medical_records | +5 `Action`, solo choices |
| `0007_alter_auditevent_resource_type.py` | medical_records | +2 `ResourceType`, solo choices |
| `0004_policyacceptance.py` | accounts | `PolicyAcceptance` + `UNIQUE(user, policy_type, policy_version)` |

Sin migraciones nuevas en la ronda de corrección post-implementación: todos los cambios de PD-001
a PD-008 y de los hallazgos 12.1-12.9 son de comportamiento (servicios/admin/views/templates/
settings), no de esquema — confirmado con `makemigrations --check --dry-run` tras cada bloque de
corrección (ver §13).

## 9. Seguridad

Controles verificados:

- Autenticación requerida en todos los endpoints nuevos (`JsonApiView` local en cada app: 401 si
  `request.user.is_authenticated` es falso).
- `Cache-Control: no-store` en todas las respuestas JSON nuevas (`AuditEventListView`,
  `ConsentAcceptView`, `ConsentStatusView`).
- F6-D05 verificado en dos capas (API y UI): `can_view_audit_log` (solo `is_superuser`).
- **Hallazgo propio, corregido en esta misma implementación** (no en un audit report separado):
  `AuditEventListView.get` devolvía 200 con resultados vacíos para un `patient_id` inexistente
  **antes** de evaluar `can_view_audit_log` — un actor no autorizado podía obtener 200 (en vez del
  403 uniforme) simplemente enviando un `patient_id` inventado. Corregido moviendo la
  verificación de autorización al principio de la vista, antes de cualquier retorno temprano; test
  de regresión agregado (`test_non_administrator_is_denied_even_with_nonexistent_patient_id`).
- `ConsentAcceptView`/`ConsentStatusView` nunca aceptan `user`/`accepted_at` del cliente — ambos
  se determinan en servidor (verificado por test
  `test_accept_endpoint_ignores_client_supplied_user_and_timestamp`).
- Ningún log/mensaje de error nuevo incluye contenido clínico, secretos o stack traces
  (`EmailTransport.send` solo registra la dirección de destino y un `reason_code` seguro).
- `Notification` no tiene columna de cuerpo/contenido — nada que filtrar ahí por diseño.
- `AuditEvent` de `LOGIN`/`MODIFY_PATIENT`/`CHANGE_PERMISSIONS`/`DISABLE_USER` nunca almacena
  contraseñas, tokens ni permisos completos — solo `resource_id`/`reason_code` seguro.
- Usuarios inactivos: `_user_for_person_owner` (resolución de destinatarios) excluye
  explícitamente `user.is_active=False`.
- CSRF: ninguna vista nueva usa `@csrf_exempt`; los formularios server-rendered incluyen
  `{% csrf_token %}`.
- **Corrección post-implementación (C-001, hallazgo 12.1):** acceso al audit trail vía Django
  Admin restringido a `is_superuser` — antes bastaba `is_staff`. Ver §Correcciones.
- Revisión de `.env`: no está trackeado en git (`.gitignore`), no existe en el historial
  (`git log --all -- .env` vacío), y `.env.example` solo contiene placeholders — sin hallazgos de
  credenciales expuestas.

## 10. Auditoría

Catálogo conectado: `LOGIN` (éxito + rechazo con actor resoluble, PD-002/ITD-008),
`MODIFY_PATIENT` (vía `PatientAdmin` **y** `PersonAdmin` tras C-006), `CHANGE_PERMISSIONS`,
`DISABLE_USER` (vía `UserAdmin`, ITD-004). Catálogo ya existente de Fase 3/4 sin cambios de
comportamiento. `ADMIN_SENSITIVE_ACCESS` definida sin conectar — decisión final del propietario
(PD-001), no un hueco. Consulta restringida a Administrador (F6-D05), verificada por test en API,
UI **y Django Admin** (los tres puntos de acceso, tras C-001). Retención indefinida — ningún
comando/job de depuración se implementó (F6-D07).

## 11. Notificaciones

Email como único canal (F6-D01/F6-D02). Destinatarios resueltos en el momento de la intención,
nunca cacheados (`_appointment_recipients`). Contenido de cada correo de cita: información
esencial real (fecha/hora, médico, consultorio) + enlace a TeCuidoApp, nunca clínica (PD-005/
C-010). Reintentos limitados (máx. 5) con backoff exponencial y recuperación de `SENDING`
huérfano por lease timeout (PD-007/C-003/C-004, ITD-011/ITD-012) vía
`process_due_notifications`, con reclamo de filas de concurrencia segura
(`select_for_update(skip_locked=True)` en una transacción corta, separada del envío real — el
transporte nunca retiene locks). Resultado real del transporte validado, no solo ausencia de
excepción (C-007). Fallo de transporte nunca revierte la operación de negocio (verificado por
test con `mock` forzando una excepción del transporte). Sin opt-out (F6-D03, verificado
estructuralmente por test). Configuración de ventanas de recordatorio con efecto hacia adelante
únicamente, sin reconciliación retroactiva (PD-004).

## 12. Consentimientos

`PolicyAcceptance` con `UNIQUE(user, policy_type, policy_version)`; aceptar la misma versión dos
veces es idempotente (`get_or_create`); aceptar una versión no vigente se rechaza. Trazabilidad
completa por versión (quién/qué/versión/cuándo/dónde publicada), incluidas versiones ya
superadas, vía `document_url`/`acceptance_trace` (PD-006/C-011) — cierra las cinco preguntas que
la decisión exige poder responder. UI muestra referencia canónica y fecha de aceptación
(hallazgo 12.9/C-009). Solo Aviso de
Privacidad y Términos y Condiciones (F6-D04) — ningún consentimiento clínico introducido.

## 13. Testing

### Ronda de implementación inicial (2026-09-21, primera mitad de la sesión)

```text
python manage.py check                     -> System check identified no issues
python manage.py makemigrations --check    -> sin cambios pendientes tras cada bloque
python manage.py test accounts appointments care_requests   -> 333/333
python manage.py test notifications                          -> 14/14
python manage.py test accounts.tests.test_consent             -> 10/10
python manage.py test medical_records.tests.test_fase6_audit  -> 11/11
python manage.py test (notifications + test_consent +
                        test_fase6_audit, tras el hallazgo
                        de seguridad y ITD-010)                -> 35/35
python manage.py test (suite completa del proyecto)           -> 809/809, 552.49s
```

### Ronda de corrección post-implementación (2026-09-21, esta sesión)

```text
python manage.py check (tras cada corrección)                 -> System check identified no issues
python manage.py makemigrations --check --dry-run             -> No changes detected
python manage.py test notifications                            -> 24/24 (tras C-003/C-004/C-005/
                                                                   C-007/C-010, antes de agregar
                                                                   RetryBackoffTests/EmailContentTests)
python manage.py test notifications                            -> 24/24 (tras agregar
                                                                   RetryBackoffTests)
python manage.py test accounts.tests.test_consent               -> 12/12 (tras C-009/C-011, +2 tests)
python manage.py test medical_records.tests.test_fase6_audit    -> 17/17 (tras C-001/C-002/C-006/
                                                                   C-008, +6 tests)
python manage.py test notifications accounts.tests.test_consent
             medical_records.tests.test_fase6_audit             -> 53/53
python manage.py test (suite completa del proyecto)             -> 828/828, 547.21s. Tres
                                                                   tracebacks esperados en la
                                                                   salida (no son fallos):
                                                                   (1) "simulated outage" — mock
                                                                   preexistente de Fase 3,
                                                                   no relacionado con Fase 6;
                                                                   (2) "SMTP caído" y
                                                                   (3) "0 entregas" — los propios
                                                                   tests que fuerzan esas
                                                                   condiciones a propósito
                                                                   (§21 del Design Freeze, C-007).
python manage.py check (final)                                    -> System check identified no
                                                                      issues
python manage.py makemigrations --check --dry-run (final)         -> No changes detected
```

Casos cubiertos (acumulado, ambas rondas): F6-D01 (tres destinatarios), F6-D02 (recordatorios sin
médico, 4 ventanas, ventanas ya vencidas excluidas), F6-D03 (ausencia estructural de opt-out),
idempotencia/dedupe, paciente MINOR sin `User` (destinatario omitido sin error), fallo de
transporte no revierte la cita, cancelación cancela recordatorios pendientes y `FAILED` con
reintentos restantes (C-005), reprogramación recalcula `scheduled_for` (`PENDING` y `FAILED`,
C-005) y genera una notificación de modificación con `dedupe_key` distinto,
`process_due_notifications` omite un recordatorio cuya cita ya no es elegible o cuyo destinatario
perdió autorización, backoff tras fallo (C-004), agotamiento de reintentos y exclusión de
reclamo posterior (C-004), recuperación de `SENDING` huérfano reintentable y no reintentable
(C-003), resultado `0` del transporte tratado como fallo (C-007), contenido de correo con
información esencial/enlace/sin contenido clínico para los cuatro eventos de cita (C-010),
`LOGIN` auditado (éxito/rechazo con actor resoluble/rechazo sin actor resoluble), `MODIFY_PATIENT`
vía `PatientAdmin` **y** `PersonAdmin` (C-006), `DISABLE_USER`/`CHANGE_PERMISSIONS` vía Admin,
acceso al audit trail (admin permitido, no-admin denegado, incluyendo Django Admin con
`is_staff` sin `is_superuser`, C-001), filtro de fecha en la UI del audit trail (C-008), rechazos
de usuario inactivo y acceso no autorizado no registrados como éxito (C-002), consentimiento
(idempotencia, versión desconocida rechazada, endpoint nunca acepta `user`/`accepted_at` del
cliente, traza completa de las cinco preguntas de PD-006, C-011).

## 14. Problemas encontrados y resolución

- Bug propio: referencia rota (`RequestReason`, no `Appointment.CancellationReason`) en un test —
  corregido antes de ejecutar.
- Bug propio: `_get_or_create_notification`/`process_due_notifications` inicialmente sostenían
  locks de fila (`select_for_update`) durante el envío de red — corregido separando el reclamo
  (transacción corta) del envío real (fuera de cualquier transacción).
- Bug propio: dos líneas de código placeholder/basura dejadas accidentalmente en
  `patients/admin.py` y `medical_records/views.py` durante la redacción — detectadas y corregidas
  antes de ejecutar cualquier test.
- Bug propio (seguridad): ver §9 — orden de verificación de autorización en `AuditEventListView`.
- Bug propio en tests: `email_verified` no tiene `default=True` en `User.objects.create_user()`
  (solo en `create_superuser`) — un test de login fallaba por esa razón, no por el código de
  producción; corregido pasando `email_verified=True` explícitamente en el helper de test.
- Constraints de base de datos (`appointment_cancelled_requires_trace`,
  `responsiblepatientrelationship_inactive_requires_deactivation_info`) exigieron poblar más
  campos de los que mis tests inicialmente asumían al forzar transiciones de estado directamente
  — corregido completando los campos de traza requeridos.

### Ronda de corrección post-implementación

- Bug propio en tests: dos tests de backoff (`test_failed_attempt_reschedules_with_backoff_not_
  immediate_retry`, `test_notification_permanently_failed_after_max_attempts`) mockeaban el
  transporte *después* de que `_book()` ya hubiera enviado la notificación con éxito (backend de
  consola) — el guard `SENT` de ITD-010 hacía que el segundo intento simulado nunca se ejecutara.
  Corregido mockeando el transporte *antes* de `_book()`, para que el primer intento real ya
  falle.
- Bug propio en tests: `AuditTrailAccessTests.admin_user` tenía `is_superuser=True` pero no
  `is_staff=True` — Django Admin exige ambos para cualquier acceso a `/admin/`, así que el nuevo
  test `test_django_admin_superuser_can_see_audit_trail` fallaba con 302 (redirect a login), no
  por un defecto de `AuditEventAdmin`. Corregido agregando `is_staff=True` al fixture.
- Verificación de `.env`/secretos (§15 del prompt de corrección): sin hallazgos — ver §9.

## 15. Riesgos conocidos

- `process_due_notifications` depende de que operaciones configure un cron externo (ITD-006) —
  sin eso, los recordatorios se generan pero nunca se envían más allá del intento inmediato hecho
  en `notify_appointment_created`.
- Recuperación de contraseña queda fuera del nuevo transporte — decisión final del propietario
  (PD-003), no un riesgo a mitigar, pero significa que un fallo de ese flujo específico no queda
  registrado en `Notification` (sí en los logs propios de Django).
- `ADMIN_SENSITIVE_ACCESS` sin conectar — decisión final del propietario (PD-001).
- `SITE_BASE_URL` debe configurarse con el dominio real en producción (ITD-013) — sin
  configurar, los enlaces de los correos apuntarían a `localhost:8000`.
- `LEGAL_DOCUMENT_URLS` (`PRIVACY_NOTICE_URL`/`TERMS_AND_CONDITIONS_URL`) están vacíos por
  defecto — sin configurar, la UI de consentimiento no mostrará el enlace "Leer el documento"
  (se degrada correctamente: el resto de la pantalla sigue funcionando).
- El diagnóstico administrativo de `Notification` vía Django Admin es de solo lectura; no existe
  un endpoint JSON de diagnóstico de notificaciones más allá del admin (el contrato lo dejaba como
  opcional — "puede existir", `phase-6-notification-api-contracts.md` §2).
- Los valores de `MAX_DELIVERY_ATTEMPTS`/backoff/`SENDING_LEASE_TIMEOUT` (ITD-011/ITD-012) son
  una primera elección razonable para la escala actual, no medida contra tráfico real de
  producción — candidatos a ajustar con datos reales de operación.

## 16. Estado final

```text
PHASE 6 — IMPLEMENTED / READY FOR FINAL AUDIT
```

Las siete decisiones F6-D01 a F6-D07, más las ocho decisiones finales del propietario PD-001 a
PD-008, están implementadas, probadas y documentadas — ninguna quedó como pendiente abierta (ver
tabla de verificación más abajo). Los nueve hallazgos técnicos 12.1-12.9 del prompt de corrección
fueron corregidos con evidencia de test para cada uno.
No se declara `PHASE 6 — CLOSED`: esa declaración corresponde a una auditoría de cierre formal
independiente, no a quien implementó/corrigió el código — mismo criterio ya aplicado en el cierre
de Fase 5 de este proyecto (nunca autodeclarar cierre sin una verificación separada).

Regresión completa del proyecto: **828/828 tests, 547.21s, `check` y `makemigrations --check`
limpios** (ver §13 para el detalle de los tres tracebacks esperados, ninguno un fallo real).
Ningún archivo de Fases 1-5 fue tocado fuera de los puntos de enganche mínimos ya documentados en
§4 y ampliados en esta ronda por C-001 (`medical_records/admin.py`) y C-006
(`accounts/admin.py::PersonAdmin`).

> Nota (2026-09-22): este §16 es el snapshot histórico de la ronda de corrección que cerró esta
> sección. Una ronda posterior de 7 prompts secuenciales (ver "Ronda de refinamiento (Prompts 1-7
> secuenciales)" más abajo) corrigió C-012/C-013 y actualizó el estado a `PHASE 6 — READY FOR
> CLOSURE` (840/840 tests) — ese es el estado vigente, no el de este párrafo. Se conserva este
> texto sin alterar por trazabilidad, no por vigencia.

## 17. Recomendaciones posteriores

- Configurar `SITE_BASE_URL`, `PRIVACY_NOTICE_URL` y `TERMS_AND_CONDITIONS_URL` en el entorno de
  producción antes de operar Fase 6 (ITD-013/ITD-014) — sin esto, los enlaces de correo y la
  referencia canónica de consentimiento quedan incompletos, aunque el sistema sigue operando.
- Configurar el cron de `process_due_notifications` en el entorno de despliegue real.
- Si se decide auditar `ADMIN_SENSITIVE_ACCESS`, definir primero qué operación concreta lo
  amerita (PD-001) antes de conectar el hook.
- Revisar `MAX_DELIVERY_ATTEMPTS`/backoff/`SENDING_LEASE_TIMEOUT` (ITD-011/ITD-012) contra
  volumen real de producción una vez operando, y ajustar si corresponde (cambio puramente
  técnico, sin tocar política funcional).
- Evaluar, en una fase de hardening posterior, si vale la pena envolver
  `PasswordResetForm.send_mail` bajo el transporte de `notifications` para trazabilidad uniforme
  (PD-003) — no se recomienda hacerlo solo por consistencia estética; requeriría una nueva
  decisión del propietario, no es un cambio puramente técnico.

## Verificación de las ocho decisiones (PD-001 a PD-008)

| PD | Decisión | Código | Tests | Documentación | Estado |
|---|---|---|---|---|---|
| PD-001 | `ADMIN_SENSITIVE_ACCESS` sin uso | `AuditEvent.Action.ADMIN_SENSITIVE_ACCESS` definida, sin emisor | N/A (nada que probar — ausencia verificada por `grep`) | `phase-6-audit-domain.md` §3, este documento §6 | CONSISTENTE |
| PD-002 | Excepción de rechazos previos al boundary | Sin cambio de código — comportamiento ya correcto | `RejectionAuditCoverageTests`, `LoginAuditTests` | `phase-6-audit-domain.md` §4 | CONSISTENTE |
| PD-003 | Password Recovery nativo | `PasswordResetView`/`PasswordResetForm` sin modificar; `create_password_recovery_notification` sin invocar | Regresión de `accounts` (333/333 en ronda inicial, sin cambios en esta ronda) | `phase-6-notification-domain.md` §3 | CONSISTENTE |
| PD-004 | Configuración hacia adelante | **Corrección posterior (C-019):** esta fila afirmaba "comportamiento ya natural" — resultó falso; `reschedule_appointment_reminders` releía el offset desde el propio `dedupe_key` en vez de `ReminderWindow` vigente. Corregido, ver "Ronda de corrección funcional de recordatorios" más abajo | `ReminderWindowReconfigurationTests` (6 tests) | `phase-6-notification-data-model.md` §2.2 | CONSISTENTE |
| PD-005 | Email + enlace | `notifications/services.py::_render`/`_appointment_essentials`/`_appointment_url` | `EmailContentTests` (3 tests) | `phase-6-notification-security-and-privacy.md` §1 | CONSISTENTE |
| PD-006 | Documentos externos versionados | `accounts/services/consent.py::document_url`/`acceptance_trace`; `settings.LEGAL_DOCUMENT_URLS` | `test_acceptance_trace_answers_the_five_pd006_questions`, `test_acceptance_trace_none_when_never_accepted`, `test_status_endpoint_reflects_pending_and_accepted` | `phase-6-consent-domain.md` §1 | CONSISTENTE |
| PD-007 | Retries limitados + backoff | `MAX_DELIVERY_ATTEMPTS`, `_backoff_seconds`, `SENDING_LEASE_TIMEOUT`, `process_due_notifications` | `RetryBackoffTests` (7 tests) | `phase-6-notification-domain.md` §6, `phase-6-notification-service-contracts.md` §4 | CONSISTENTE |
| PD-008 | Reutilización de `AuditEvent` | Sin app `audit` nueva; `medical_records.AuditEvent`/`services.audit` únicos | Toda la suite de `medical_records.tests.test_fase6_audit` ejercita esta única fuente | `phase-6-audit-domain.md` §2 | CONSISTENTE |

Ninguna PD quedó en `PENDIENTE`, `PARCIAL`, `CONTRADICTORIO` ni `AUSENTE`.

## Control de alcance (§20 del prompt de corrección)

Confirmado fuera de Fase 6, sin cambios: WhatsApp, SMS, MFA/2FA, nuevas capacidades clínicas,
segunda infraestructura de auditoría, segunda fuente de verdad para `Appointment` (`grep` sobre
`notifications/`, `accounts/api.py`, `accounts/services/consent.py`, `medical_records/api.py` sin
resultados relevantes — ver evidencia en la respuesta final). No se reabrió ninguna Fase 1-5 más
allá de los puntos de enganche mínimos y ya documentados (§4, C-001, C-006).

---

# Ronda de refinamiento — 7 prompts secuenciales (2026-09-22)

Segunda ronda de corrección post-implementación, ejecutada como secuencia de 7 prompts (retry/
estados de notificaciones; auditoría y seguridad; consentimientos; emails; consolidación
documental; validación en navegador; validación final). Antes de cada prompt se releyó el estado
real del repositorio, `requirements.md`, `docs/architecture.md`,
`docs/phases/phase-6-design-freeze.md` y este mismo documento, confirmando que cada corrección
solicitada seguía siendo necesaria antes de tocar código.

## Nuevas decisiones técnicas

### ITD-015 — Clasificación de fallos permanentes vs. transitorios en el transporte

- Problema: Prompt 1 pide "diferenciar fallos transitorios y permanentes cuando sea técnicamente
  posible" sin inventar categorías de negocio nuevas.
- Decisión: `EmailTransport.send` valida el formato de la dirección con
  `django.core.validators.validate_email` **antes** de intentar el transporte (un formato
  inválido nunca se arregla con un reintento); además clasifica `smtplib.SMTPRecipientsRefused`/
  `django.core.mail.BadHeaderError` como permanentes (el servidor rechazó explícitamente al
  destinatario, o el encabezado es inválido) y cualquier otra excepción como transitoria.
  `TransportResult.is_permanent` propaga la clasificación; `_attempt_send` cierra un fallo
  permanente como `FAILED` terminal de inmediato (`reason_code` prefijado `PERMANENT:`), sin
  esperar a `MAX_DELIVERY_ATTEMPTS`.
- Impacto: `process_due_notifications` excluye explícitamente
  (`.exclude(reason_code__startswith="PERMANENT:")`) estas filas de cualquier reclamo futuro —
  bug encontrado y corregido en el mismo pase (ver C-012).
- Archivos: `notifications/services.py`.

## Nuevas correcciones

### C-012 — `SENDING` huérfana en `MAX_DELIVERY_ATTEMPTS` podía recibir un intento adicional (hallazgo explícito del Prompt 1, §1)

- Problema: la rama de reclamo de filas `SENDING` huérfanas en `process_due_notifications`
  filtraba por `last_attempt_at` vencido pero **no** por `attempt_count` — a diferencia de la
  rama `PENDING`/`FAILED`, que sí lo hacía. Una fila `SENDING` interrumpida justo después de su
  último intento permitido podía reclamarse y recibir un sexto envío real.
- Causa: asimetría entre las dos ramas del filtro `Q(...)` original, introducida en la
  implementación inicial de PD-007 (ronda anterior) y no cubierta por ningún test hasta este
  prompt.
- Solución: `due_ids` excluye explícitamente `SENDING` con `attempt_count >= MAX_DELIVERY_ATTEMPTS`;
  esas filas (junto con las `SENDING` de tipo no reintentable) se cierran directamente como
  `FAILED` con `reason_code=MAX_ATTEMPTS_EXCEEDED:ORPHANED_SENDING`, sin ningún intento de envío.
- Archivos: `notifications/services.py::process_due_notifications`.
- Tests: `test_orphaned_sending_at_max_attempts_is_not_reclaimed_for_another_attempt`.

### C-013 — Fallo permanente podía seguir reclamándose antes de agotar `MAX_DELIVERY_ATTEMPTS`

- Problema: al introducir ITD-015, un fallo marcado `PERMANENT:` con `attempt_count` todavía bajo
  seguía cumpliendo el filtro original (`attempt_count < MAX_DELIVERY_ATTEMPTS`) y volvía a
  reclamarse en la siguiente ejecución de `process_due_notifications` — contradiciendo la propia
  intención de "permanente" (cerrar de inmediato, sin reintentos).
- Causa: el filtro de reclamo no conocía la distinción permanente/transitorio recién introducida.
- Solución: `.exclude(reason_code__startswith="PERMANENT:")` en la consulta de reclamo.
- Archivos: `notifications/services.py::process_due_notifications`.
- Tests: `test_permanently_failed_notification_is_never_reclaimed`,
  `test_invalid_recipient_format_fails_permanently_without_waiting_for_max_attempts`.

### C-014 — Rol explícito en la cobertura de acceso al audit trail (Prompt 2)

- Problema: la cobertura previa de "no administrador denegado" solo probaba con un médico; el
  Prompt 2 exige casos explícitos de paciente, responsable, médico e inactivo por separado.
- Solución: tests nuevos por rol (paciente, responsable, usuario inactivo) contra API y UI.
- Archivos: solo tests — ningún código de producción cambió (ya era correcto).
- Tests: `medical_records/tests/test_fase6_audit.py::AuditTrailAccessTests::
  test_patient_is_denied_audit_trail`, `::test_responsible_is_denied_audit_trail`,
  `RejectionAuditCoverageTests::test_inactive_user_login_is_not_a_success_event`.

### C-015 — Referencia canónica de documento no probada cuando está configurada (Prompt 3)

- Problema: `document_url`/`acceptance_status` solo se habían probado con `LEGAL_DOCUMENT_URLS`
  vacío (comportamiento por defecto); faltaba evidencia de que el mecanismo funciona cuando el
  operador sí configura una URL real.
- Solución: tests con `override_settings(LEGAL_DOCUMENT_URLS=...)`.
- Archivos: solo tests.
- Tests: `accounts/tests/test_consent.py::ConsentDocumentReferenceTests` (3 tests).

### C-016 — Cobertura del evento "cita modificada" y del enlace del correo (Prompt 4)

- Problema: `EmailContentTests` cubría creada/cancelada/recordatorio pero no modificada; tampoco
  existía una verificación explícita de que el enlace del correo apunte a una vista realmente
  protegida por autorización (no una ruta nueva sin protección propia).
- Solución: tests nuevos.
- Archivos: solo tests.
- Tests: `notifications/tests/test_services.py::EmailContentTests::test_modified_email_content`,
  `::test_link_points_to_authorization_protected_view_no_bypass`.

### C-017 — Precisión de PD-002 en `phase-6-design-freeze.md` (Prompt 5)

- Problema: §11/§12 del Design Freeze seguían afirmando, sin matiz, que "todo rechazo... debe
  generar un `AuditEvent`" — una formulación más amplia que la excepción real ya implementada y
  cerrada por PD-002 (boundary instrumentado + actor identificable). El Prompt 5 exige
  explícitamente que "no debe existir una formulación normativa más amplia que contradiga la
  implementación aprobada".
- Causa: el Design Freeze nunca se actualizó cuando PD-002 se cerró en la ronda anterior — solo
  se actualizaron los documentos derivados (`phase-6-audit-domain.md`).
- Solución: nota de precisión añadida en ambas secciones, citando la excepción exacta y
  remitiendo a `phase-6-audit-domain.md` §4 y a este documento. No se reabre ni se debilita la
  regla general — se aclara su alcance ya cerrado.
- Archivos: `docs/phases/phase-6-design-freeze.md` §11/§12.

### C-018 — README.md y docs/architecture.md seguían diciendo "Fase 6 siguiente" (Prompt 5)

- Problema: estos dos documentos —nunca tocados en la ronda de corrección anterior— seguían
  describiendo Fase 6 como "⏭️ SIGUIENTE"/"la fase siguiente", contradiciendo el estado real
  (implementada) ya reflejado en toda la documentación específica de Fase 6.
- Solución: actualizados a "🔄 IMPLEMENTADA — pendiente de auditoría de cierre formal
  independiente", con referencia a este documento y a `phase-6-final-report.md`. No se declara
  `COMPLETADA`/`CLOSED` — esa declaración sigue reservada a la auditoría de cierre formal.
- Archivos: `README.md`, `docs/architecture.md` (banner superior, "Resumen de fases", "Fases
  futuras (histórico)").

## Evidencia de navegador (Prompt 6)

Ver `docs/phases/evidence/phase-6-browser-validation/README.md` — 8 capturas reales verificadas
(no simuladas ni `django.test.Client`): consentimiento (pendiente → aceptado), acceso al audit
trail por rol (paciente/médico/responsable denegados con 404 uniforme; administrador permitido
con datos reales; anónimo redirigido a login), filtro de fecha funcionando en vivo, y contenido
real de un correo "Cita reservada" impreso por el backend de consola. El documento de evidencia
también reporta con transparencia un incidente de la propia secuencia de automatización (sesión
no cerrada correctamente en dos intentos iniciales) y cómo se detectó y corrigió antes de aceptar
cualquier captura como válida.

## Regresión de esta ronda

```text
python manage.py check                                     -> System check identified no issues (0 silenced)
python manage.py makemigrations --check --dry-run           -> No changes detected
python manage.py test (suite completa del proyecto, -v 1)   -> Ran 840 tests in 563.110s — OK
                                                                 (828 -> 840; +12 sobre la ronda
                                                                 anterior: +6 notifications
                                                                 [C-012/C-013/C-016 y refuerzos],
                                                                 +3 medical_records [C-014],
                                                                 +3 accounts [C-015])
```

Las trazas de excepción que imprime la corrida completa (`simulated outage`, `SMTP caído`,
`Dirección de destino con formato inválido`, `reportó 0 entregas`) son de tests que simulan
deliberadamente esos fallos (mocks con `side_effect`) para verificar degradación segura —
`safe_record_event` y `EmailTransport`/`_attempt_send` las capturan y continúan; no son fallos
reales de la corrida, que terminó `OK` con `exit code 0`. Cero regresiones detectadas en Fases
1-5: la corrida ejecuta la suite completa del proyecto, no solo la de Fase 6.

## Verificación final de las ocho decisiones (Prompt 7)

| PD | Decisión | Código | Tests | Documentación | Estado |
|---|---|---|---|---|---|
| PD-001 | `ADMIN_SENSITIVE_ACCESS` sin uso | Sin cambios — sigue sin emisor, por diseño | N/A (ausencia verificada) | `phase-6-audit-domain.md` §3 | CONSISTENTE |
| PD-002 | Excepción de rechazos previos al boundary | Sin cambios de código — ya correcto | `LoginAuditTests`, `RejectionAuditCoverageTests` | `phase-6-audit-domain.md` §4 + **`phase-6-design-freeze.md` §11/§12 (C-017, cierra la formulación más amplia)** | CONSISTENTE |
| PD-003 | Password Recovery nativo | Sin cambios — `PasswordResetView` intacto | Regresión de `accounts` | `phase-6-notification-domain.md` §3 | CONSISTENTE |
| PD-004 | Configuración hacia adelante | **Corregido** (C-019 — ver "Ronda de corrección funcional de recordatorios" más abajo; la reprogramación no releía `ReminderWindow` vigente) | `ReminderSchedulingTests` + `ReminderWindowReconfigurationTests` (6 tests) | `phase-6-notification-data-model.md` §2.2 | CONSISTENTE |
| PD-005 | Email + enlace | Sin cambios de código — cobertura ampliada (C-016) | `EmailContentTests` (5 tests, los 4 eventos + no-bypass) | `phase-6-notification-security-and-privacy.md` §1 | CONSISTENTE |
| PD-006 | Documentos externos versionados | Sin cambios de código — cobertura ampliada (C-015) | `ConsentDocumentReferenceTests` + evidencia de navegador | `phase-6-consent-domain.md` §1 | CONSISTENTE |
| PD-007 | Retries limitados + backoff | **Corregido** (C-012/C-013, ITD-015) | `RetryBackoffTests` (11 tests) | `phase-6-notification-domain.md` §6, `phase-6-notification-service-contracts.md` §4 | CONSISTENTE |
| PD-008 | Reutilización de `AuditEvent` | Sin cambios — sigue siendo la única fuente | Toda `test_fase6_audit.py` | `phase-6-audit-domain.md` §2 | CONSISTENTE |

Ninguna PD quedó en `PENDIENTE`, `PARCIAL`, `CONTRADICTORIO` ni `AUSENTE`. No apareció ningún
`PD-009` — todos los hallazgos de esta ronda fueron técnicos, resueltos sin tocar alcance,
política ni ninguna de las ocho decisiones cerradas.

## Estado recomendado tras esta ronda

```text
PHASE 6 — READY FOR CLOSURE
```

No es una autodeclaración de `PHASE 6 — CLOSED` — sigue reservada a una auditoría de cierre
formal independiente (ver `docs/phases/phase-6-final-report.md`). Significa que, hasta donde esta
implementación puede verificar por sí misma: las 7 decisiones F6-D01..F6-D07 y las 8 PD-001..
PD-008 están implementadas, probadas y documentadas sin contradicciones; la regresión completa
pasa; existe evidencia de navegador real; y no quedan hallazgos técnicos abiertos de los 7 prompts
de esta ronda.

> Nota (2026-09-22): esta conclusión resultó incompleta — la ronda de corrección funcional
> siguiente (prompts 1/4 y 2/4, más abajo) encontró dos hallazgos reales adicionales (C-019,
> C-020) que esta ronda no cubrió. El estado vigente es `PHASE 6 — READY FOR FINAL AUDIT` (más
> conservador, no `READY FOR CLOSURE`), ver `docs/phases/phase-6-final-report.md` §8. Se conserva
> este texto sin alterar por trazabilidad, no por vigencia.

---

# Ronda de corrección funcional de recordatorios (prompt 1/4, 2026-09-22)

Una auditoría funcional posterior identificó una discrepancia real entre **PD-004** y la
implementación de `reschedule_appointment_reminders()`, no cubierta por la ronda de 7 prompts
anterior (esa ronda tocó `process_due_notifications` y el transporte, no la reconfiguración de
`ReminderWindow`).

## C-019 — `reschedule_appointment_reminders` no releía la configuración vigente de `ReminderWindow`

- **Problema:** al reprogramar una cita, la función recalculaba `scheduled_for` de cada
  recordatorio ya existente usando el `offset_days` incrustado en su propio `dedupe_key`
  (`APPOINTMENT_REMINDER:{appointment_id}:{user_id}:{offset_days}`), en vez de volver a
  consultar `ReminderWindow.objects.filter(is_active=True)`. Si la configuración de ventanas
  cambiaba entre la creación original de la cita y su reprogramación, la cita reprogramada
  conservaba offsets obsoletos en vez de adoptar la configuración vigente.
- **Causa:** el `dedupe_key` es (correctamente) estable para no duplicar filas — pero se estaba
  usando también como fuente de la configuración, cuando debía usarse solo como identidad de la
  fila. Eran dos responsabilidades distintas mezcladas en el mismo dato.
- **Solución:**
  1. Se calcula `active_offsets` desde `ReminderWindow.objects.filter(is_active=True)` al inicio
     de la función (la misma fuente de verdad que usa la creación original,
     `schedule_appointment_reminders`).
  2. Todo recordatorio `PENDING`/`FAILED` (con `attempt_count < MAX_DELIVERY_ATTEMPTS`) cuyo
     offset ya no está en `active_offsets` se cancela explícitamente
     (`reason_code="REMINDER_WINDOW_NO_LONGER_ACTIVE"`) en vez de recalcularse con una ventana
     obsoleta.
  3. Todo recordatorio cuyo offset sigue activo se recalcula contra la fecha vigente de la cita
     — comportamiento ya existente, sin cambios.
  4. Al final, se reutiliza `schedule_appointment_reminders(appointment)` (la misma función de
     creación original, no una segunda fuente de verdad) para materializar cualquier ventana
     activa nueva que la cita todavía no tuviera — respeta elegibilidad (offsets ya vencidos no
     se crean) e idempotencia (`dedupe_key` evita duplicar lo que el paso 2/3 ya dejó en su
     lugar).
  5. `SENT` y `SENDING` siguen completamente fuera del alcance de esta función — decisión ya
     cerrada en la ronda anterior (Prompt 1 de la corrección de 7 prompts), sin cambios: un
     recordatorio ya enviado nunca se reenvía, y `SENDING` es una ventana de milisegundos que se
     autocorrige en el propio envío.
  6. Una fila agotada (`attempt_count >= MAX_DELIVERY_ATTEMPTS`) sigue completamente fuera del
     alcance de la función (queda excluida del `queryset` de recorridos) — nunca se reactiva por
     un cambio de configuración ni por una reprogramación.
- **Restricciones respetadas:** no se creó reconciliación retroactiva global (solo se recalculan
  las filas de la cita efectivamente reprogramada, nunca todas las citas ya existentes); no se
  creó un nuevo scheduler ni una segunda fuente de verdad (se reutiliza `ReminderWindow` y
  `schedule_appointment_reminders`, ya existentes); PD-004 y PD-007 no se modificaron, solo se
  corrigió una implementación que no los cumplía correctamente.
- **Archivos:** `notifications/services.py` (`reschedule_appointment_reminders`,
  docstring de `schedule_appointment_reminders`).
- **Tests:** `notifications/tests/test_services.py::ReminderWindowReconfigurationTests` (6 tests,
  casos 1-6 del prompt de corrección — configuración por defecto, nueva cita con configuración
  cambiada, reprogramación que adopta la configuración cambiada, reprogramación repetida sin
  duplicar filas, interacción con `SENT`/`SENDING`/`FAILED`, y no reactivación de una fila
  agotada).

## Regresión de esta ronda

```text
python manage.py check                       -> System check identified no issues (0 silenced)
python manage.py makemigrations --check       -> No changes detected
python manage.py test notifications           -> 36/36 (30 -> 36; +6 de ReminderWindowReconfigurationTests)
python manage.py test appointments             -> 186/186 (sin regresión en Agenda)
```

No se tocó ningún archivo de `appointments/` — la corrección es exclusiva de
`notifications/services.py`; la suite de `appointments` se ejecutó solo para confirmar ausencia
de regresión en el consumidor de estas señales.

## Estado tras este prompt

Corrección completa e implementada y probada. Pendientes los prompts 2/4, 3/4 y 4/4 de esta
misma ronda (según se reciban) antes de volver a declarar un estado consolidado de Fase 6.

---

# Prompt 2/4 — evidencia browser/UI y consentimientos (2026-09-22)

Objetivo: completar evidencia real de navegador que faltaba (estados UI del audit trail,
consentimiento con documentos externos reales configurados, verificación adicional de enlaces de
notificación). Detalle completo de escenarios y capturas en
`docs/phases/evidence/phase-6-browser-validation/README.md` (sección "Ronda 2 — Prompt 2/4").

## C-020 — `patient_id` no numérico causaba un 500 no controlado en `AuditTrailView` (UI)

- **Problema:** al intentar generar la evidencia del estado "error de consulta" pedida por el
  prompt, se encontró un fallo real (no fabricado): `AuditTrailView.get` pasaba `patient_id` sin
  validar a `Patient.objects.filter(pk=patient_id)`. Un valor no numérico (`?patient_id=abc`)
  produce un `ValueError` que Django no captura, resultando en un 500 con traceback completo
  (entorno `DEBUG=True`) en una pantalla exclusiva de Administrador.
- **Causa:** el filtro de `patient_id` nunca tuvo la misma validación defensiva que ya tenían sus
  filtros hermanos en la misma vista (`_parse_ui_date` ignora silenciosamente una fecha
  inválida) ni la que ya tenía el API equivalente (`AuditEventListView._parse_int`,
  `medical_records/api.py`, responde con un `ApiError`/400 controlado). Inconsistencia entre UI y
  API para el mismo filtro sobre el mismo recurso.
- **Solución:** se envuelve `int(patient_id)` en `try/except (TypeError, ValueError)`, tratando
  un valor inválido igual que un `date_from`/`date_to` inválido — se ignora (no se aplica el
  filtro de paciente), el valor crudo se conserva en el formulario para que el usuario vea lo que
  escribió. Sin introducir una respuesta HTTP nueva ni una regla de validación nueva — solo
  alinea la UI con el criterio permisivo ya establecido en la misma vista.
- **Restricciones respetadas:** no se modificó el API (ya era correcto); no se introdujo
  funcionalidad nueva (§7 del prompt); PD-001..PD-008 sin cambios.
- **Archivos:** `medical_records/views.py::AuditTrailView.get`.
- **Tests:** `medical_records/tests/test_fase6_audit.py::AuditTrailAccessTests::
  test_ui_ignores_non_numeric_patient_id_instead_of_crashing`.
- **Evidencia browser:** captura del bug real (`09-audit-trail-error-patient-id-invalid-before-
  fix.jpg`, generada revirtiendo temporalmente el fix con `git stash` — nunca hubo una versión
  "rota a propósito" distinta del estado real pre-corrección) y de la corrección
  (`10-audit-trail-patient-id-invalid-after-fix.jpg`).

## Evidencia adicional generada (sin cambios de código)

- **Estado "empty" del audit trail:** filtro válido sin resultados —
  `11-audit-trail-empty.jpg`.
- **Estado "loading":** no existe un estado de carga distinguible que capturar — el audit trail
  es una vista Django server-rendered clásica sin capa JS/AJAX (documentado explícitamente en el
  README de evidencia en vez de fabricar un spinner que la aplicación no tiene).
- **Consentimiento con `LEGAL_DOCUMENT_URLS` real:** se configuraron
  `PRIVACY_NOTICE_URL`/`TERMS_AND_CONDITIONS_URL` en `.env` local (nunca commiteado) con URLs de
  prueba sobre `example.com` (dominio IANA reservado para documentación/pruebas), identificadas
  inequívocamente como entorno de validación. Se verificó con `read_page` que el `href` de cada
  enlace "Leer el documento" coincide exactamente con la URL configurada, y se completó el flujo
  de aceptación de "Términos y condiciones" (el Aviso de privacidad ya estaba aceptado desde la
  Ronda 1) — `12-consent-external-document-pending-terms.jpg`,
  `13-consent-external-document-both-accepted.jpg`.
- **Enlaces de notificación, verificación adicional en navegador real:** el enlace real de una
  notificación (`http://localhost:8000/agenda/citas/6/`) lleva a la vista correcta y protegida de
  Agenda para un usuario autorizado (200) y redirige a login sin filtrar datos para un anónimo
  (302) — `14-notification-link-appointment-detail-authorized.jpg`,
  `15-notification-link-anonymous-redirect-to-login.jpg`. Complementa (no reemplaza) la cobertura
  ya existente por test (`test_link_points_to_authorization_protected_view_no_bypass`).

## Regresión de este prompt

```text
python manage.py check                  -> System check identified no issues (0 silenced)
python manage.py makemigrations --check -> No changes detected
python manage.py test medical_records    -> 217/217 (216 -> 217; +1 de C-020)
```

## Estado tras este prompt

Corrección completa e implementada y probada; evidencia browser completa guardada y trazable al
commit de este prompt (ver `docs/phases/evidence/phase-6-browser-validation/README.md`,
"Ronda 2 — Prompt 2/4"). Pendientes los prompts 3/4 y 4/4 de esta misma ronda.

---

# Prompt 3/4 — consolidación documental y reporte final (2026-09-22)

Objetivo: alinear toda la documentación de Fase 6 con el estado real de código/tests, sin
declarar `PHASE 6 — CLOSED`. Cambios por documento:

- **`phase-6-design-freeze.md`:** se verificaron PD-002/PD-004/PD-005/PD-008 contra el contenido
  existente. PD-002 ya tenía su precisión (C-017, ronda anterior). PD-004/PD-005 no tenían
  ninguna afirmación que los contradijera (son decisiones técnicas correctamente delegadas a
  documentos derivados por el propio §28 del Design Freeze). Se encontró y corrigió una brecha
  real en PD-008: §8/§8.2 describían `notifications` y `audit` como dos apps Django separadas,
  sin ninguna precisión que explicara que la decisión final reutilizó `medical_records` — se
  agregó una nota de precisión en §8.2, mismo patrón que C-017.
- **`phase-6-documentation-index.md`:** nunca se había actualizado desde su redacción original
  como `DESIGN PACKAGE`. Se agregó una nota de estado de implementación (banner + §5) apuntando a
  `PHASE 6 — IMPLEMENTED / READY FOR FINAL AUDIT`, sin reescribir su función de navegación
  original.
- **`phase-6-implementation-summary.md` (este documento):** se agregó un índice consolidado de
  commits para las 20 correcciones (`C-001` a `C-020`, tabla al inicio de "Correcciones
  post-implementación") y se corrigieron dos afirmaciones que habían quedado desactualizadas y
  ahora eran falsas (la fila de PD-004 en la primera tabla de verificación, y el párrafo de §2
  que decía que el comportamiento de PD-004 "ya era natural" — ambas se referían al mismo hallazgo
  que C-019 demostró falso). Se agregó también una nota de vigencia sobre "Estado recomendado tras
  esta ronda" (7 prompts) para que no se confunda con el estado actual.
- **`phase-6-final-report.md`:** matriz F6-D01..F6-D07 corregida a la taxonomía exacta pedida
  (antes mezclaba lenguaje de PD-002/PD-006 en las descripciones); se agregó una sección
  independiente §3.1 con las ocho PD, sin mezclar ambas taxonomías; estado corregido de
  `READY FOR CLOSURE` a `PHASE 6 — READY FOR FINAL AUDIT` (más conservador, por los hallazgos de
  los prompts 1/4 y 2/4 de esta misma ronda); commit final vía auto-referencia (ver más abajo).

## Hallazgo de higiene de tests (no es una corrección de producción)

Al volver a ejecutar la suite completa (exigido por §7 del prompt — no confiar en el número
`840` histórico), la primera corrida reportó `847 tests, FAILED (failures=1)`:
`test_document_url_is_empty_string_when_unconfigured` fallaba porque el `.env` local configurado
en el Prompt 2/4 (`PRIVACY_NOTICE_URL`/`TERMS_AND_CONDITIONS_URL`, para la evidencia de
navegador) hace que `settings.LEGAL_DOCUMENT_URLS` ya no esté vacío en este entorno — el test
asumía implícitamente un entorno sin esas variables, en vez de forzar el estado "no configurado"
explícitamente. No es una regresión de código de producción: es un test no hermético que dependía
del entorno ambiente. Corregido agregando `@override_settings(LEGAL_DOCUMENT_URLS={})` — mismo
patrón ya usado por los tests hermanos de la misma clase.

- Archivos: `accounts/tests/test_consent.py` (solo tests).
- Sin corrección de producción — no se le asigna un ID `C-XXX` (no hubo problema en el código de
  la aplicación).

## Regresión final de este prompt

```text
python manage.py check                  -> System check identified no issues (0 silenced)
python manage.py makemigrations --check -> No changes detected
python manage.py test (suite completa)  -> Ran 847 tests in 569.631s — OK
                                            (840 -> 847; +6 C-019, +1 C-020; sin regresión)
```

Primera corrida: `847, FAILED (failures=1)` — `test_document_url_is_empty_string_when_
unconfigured` no era hermético (dependía de que el entorno no tuviera
`PRIVACY_NOTICE_URL`/`TERMS_AND_CONDITIONS_URL`, ahora configuradas en `.env` local por el
Prompt 2/4). Corregido con `@override_settings(LEGAL_DOCUMENT_URLS={})` explícito — sin
corrección de producción, ver sección anterior. Segunda corrida (arriba): limpia.

## Estado tras este prompt

```text
PHASE 6 — READY FOR FINAL AUDIT
```

Documentación consolidada, sin contradicciones conocidas entre `design-freeze`,
`documentation-index`, este documento y `final-report.md`. No se declara `PHASE 6 — CLOSED`.
Pendiente el prompt 4/4 (validación final) de esta misma ronda.

---

# Prompt 4/4 — validación final, git y release readiness (2026-09-22)

## Tabla final de validación de las ocho decisiones (PD-001..PD-008)

| ID | Decisión | Código | Tests | Evidencia | Documentación | Estado |
|---|---|---|---|---|---|---|
| PD-001 | `ADMIN_SENSITIVE_ACCESS` sin operación emisora, por diseño | `medical_records/models.py::AuditEvent.Action.ADMIN_SENSITIVE_ACCESS` (definida, sin emisor) | N/A — ausencia verificada por `grep` sin resultados de ningún emisor | — (ausencia estructural, no aplica evidencia browser) | `phase-6-audit-domain.md` §3 | CONSISTENTE |
| PD-002 | Rechazos auditables solo dentro del boundary instrumentado y con actor identificable | Sin cambio de código — `record_event`/`safe_record_event` ya exigían actor real (AH-086, Fase 3) | `LoginAuditTests`, `RejectionAuditCoverageTests` | — (mecanismo de servidor, no visible en captura de UI) | `phase-6-audit-domain.md` §4; precisión formal en `phase-6-design-freeze.md` §11/§12 (C-017) | CONSISTENTE |
| PD-003 | Recuperación de contraseña permanece en el flujo nativo de Django | Sin cambios — `PasswordResetView`/`PasswordResetForm` intactos; `create_password_recovery_notification` sin invocar | Regresión completa de `accounts` | — (fuera del alcance de la evidencia browser de Fase 6) | `phase-6-notification-domain.md` §3 | CONSISTENTE |
| PD-004 | `ReminderWindow` configurable hacia adelante; sin reconciliación retroactiva global | `notifications/services.py::reschedule_appointment_reminders` (**corregido**, C-019 — releía offset del `dedupe_key`, ahora consulta `ReminderWindow` vigente) | `ReminderWindowReconfigurationTests` (6 tests, casos 1-6 del prompt de corrección) | — (mecanismo temporal, no capturable en una sola captura de UI) | `phase-6-notification-data-model.md` §2.2; C-019 en este documento | CONSISTENTE |
| PD-005 | Correos de cita: información esencial + enlace, nunca contenido clínico | `notifications/services.py::_render`/`_appointment_essentials`/`_appointment_url` | `EmailContentTests` (5 tests: creada/modificada/cancelada/recordatorio + no-bypass del enlace) | `docs/phases/evidence/phase-6-browser-validation/README.md` Ronda 1 §5 (correo real por consola), Ronda 2 §8 (enlace verificado en navegador, capturas 14-15) | `phase-6-notification-security-and-privacy.md` §1 | CONSISTENTE |
| PD-006 | Aviso de Privacidad/Términos como documentos externos versionados, con referencia canónica trazable | `accounts/services/consent.py::document_url`/`acceptance_trace`; `settings.LEGAL_DOCUMENT_URLS` | `ConsentDocumentReferenceTests`, `test_acceptance_trace_answers_the_five_pd006_questions`, `test_acceptance_trace_none_when_never_accepted` | `docs/phases/evidence/phase-6-browser-validation/README.md` Ronda 1 §1 (capturas 01-02), Ronda 2 §7 (capturas 12-13, con `LEGAL_DOCUMENT_URLS` real configurado y `href` verificado) | `phase-6-consent-domain.md` §1 | CONSISTENTE |
| PD-007 | Reintentos limitados (`MAX_DELIVERY_ATTEMPTS=5`) con backoff exponencial; sin estado nuevo | `notifications/services.py` (`_attempt_send`, `process_due_notifications`, **corregido** C-012/C-013 — `SENDING` huérfana agotada y fallo permanente ya no se reclaman de nuevo) | `RetryBackoffTests` (15 tests) | — (mecanismo de fondo, no visible en UI) | `phase-6-notification-domain.md` §6, `phase-6-notification-service-contracts.md` §4 | CONSISTENTE |
| PD-008 | `audit` como responsabilidad lógica transversal — `medical_records.AuditEvent`, sin app `audit` separada | Sin app nueva; `medical_records.AuditEvent`/`medical_records.services.audit` únicos | Toda la suite `medical_records.tests.test_fase6_audit` (28 tests) | `docs/phases/evidence/phase-6-browser-validation/README.md` Ronda 1 §2/§3 (capturas 03-08), Ronda 2 §6 (capturas 09-11) | `phase-6-audit-domain.md` §2; precisión formal en `phase-6-design-freeze.md` §8.2 (esta ronda) | CONSISTENTE |

Las ocho terminan `CONSISTENTE`. Ninguna quedó `PENDIENTE`, `PARCIAL` ni `CONTRADICTORIA`. No se
registró ningún `PD-009` en esta ronda de 4 prompts — los dos hallazgos reales que surgieron
(C-019, C-020) fueron puramente técnicos y se resolvieron sin tocar ninguna de las ocho
decisiones ni el alcance de la fase.

## Suite completa y suites críticas (§1 del prompt 4/4)

```text
python manage.py check                  -> System check identified no issues (0 silenced)
python manage.py makemigrations --check -> No changes detected
python manage.py test (suite completa)  -> Ran 847 tests in 576.008s — OK
python manage.py test notifications     -> Ran 36 tests — OK
python manage.py test medical_records   -> Ran 217 tests — OK   (audit)
python manage.py test accounts          -> Ran 72 tests — OK    (incluye consent)
python manage.py test appointments      -> Ran 186 tests — OK   (agenda)
```

Ningún fallo. Las cuatro suites críticas suman 511 tests, todos incluidos también en los 847 de
la suite completa (no son una muestra aparte — se ejecutaron por separado únicamente para dar
visibilidad explícita por dominio, como pide el prompt).

## Regresión por fase (§2 del prompt 4/4)

| Fase | App(s) principal(es) | Resultado |
|---|---|---|
| Fase 1 — Fundaciones | `accounts`, `doctors`, `clinics`, `patients` | Incluidas en la suite completa (847/847) y en `accounts` (72/72) — sin fallos |
| Fase 2 — Agenda | `appointments` | 186/186 — sin fallos |
| Fase 3 — Gestión clínica | `medical_records` (encuentros clínicos) | Incluida en `medical_records` (217/217) — sin fallos |
| Fase 4 — Documentos | `clinical_documents`, `prescriptions`, `study_orders` | Incluidas en la suite completa — sin fallos |
| Fase 5 — CareRequest y operación | `care_requests` | Incluida en la suite completa — sin fallos |

No se encontró ningún fallo preexistente que documentar o clasificar — la suite completa
terminó `OK` sin excepciones no manejadas ajenas a los tres tracebacks esperados (tests que
simulan fallos deliberadamente: outage de base de datos, SMTP caído, formato de destinatario
inválido — ver detalle en §13 más abajo en este documento).

## Git, secretos y release artifact (§4/§5/§6 del prompt 4/4)

```text
git status --short --branch  -> ## main...origin/main [adelante 18]; solo .claude/settings.local.json modificado
git diff --cached            -> (vacío, nada staged sin commitear)
git rev-parse HEAD           -> ver auto-referencia del commit de este prompt
```

- `.claude/settings.local.json`: modificado localmente (config de plugins/permisos de la sesión,
  sin datos sensibles) pero **nunca commiteado** en ningún commit de Fase 6 de esta ni de
  ninguna ronda anterior — confirmado por `git diff --cached` vacío.
- Sin cambios de modo de archivo inesperados: `git diff --summary` de todos los commits de esta
  sesión muestra únicamente `create mode 100644` para archivos nuevos, ningún cambio de
  permisos sobre archivos existentes.
- `.env` nunca tracked (`git ls-files` sin resultados) y gitignorado (`.gitignore:19`); sin
  `__pycache__/`, `*.pyc` ni `private_media/` tracked.
- `git archive --format=zip HEAD` verificado (576 archivos): sin `.env`, `__pycache__/`, `*.pyc`
  ni `private_media/` — único archivo con nombre similar es `.env.example` (el template
  esperado, con placeholders/URLs de ejemplo, no secretos reales).

## Evidencia de navegador (§7 del prompt 4/4)

Verificado: `docs/phases/evidence/phase-6-browser-validation/README.md` está completo y
actualizado (15 capturas, dos rondas, cada una con su propio commit de referencia real —
`79697e0` Ronda 1, `592c356` Ronda 2, ninguno reutilizando un hash desactualizado). Cubre
consentimiento (con y sin `LEGAL_DOCUMENT_URLS` configurado), audit trail por rol y por estado UI
(éxito/denegado/empty/error), filtros, ausencia de opt-out, y enlaces de notificación sin bypass
de autorización — ver detalle completo en `docs/phases/phase-6-final-report.md` §5/§8.

## Estado final de esta ronda de 4 prompts

```text
PHASE 6 — READY FOR FINAL AUDIT
```

No se declara `PHASE 6 — CLOSED`. Los cuatro prompts de esta ronda están completos: corrección
funcional de recordatorios (1/4, C-019), evidencia browser/UI complementaria (2/4, C-020),
consolidación documental (3/4), y esta validación final (4/4). Riesgos restantes documentados en
`docs/phases/phase-6-final-report.md` §9 — ninguno bloquea este estado. No se registró ningún
`PD-009` en toda la ronda.

---

# Cierre formal — Prompt 1/3: consolidación documental (2026-09-22)

Primera de tres etapas del cierre formal (ver `docs/phases/phase-6-final-report.md` §10 para el
resumen completo). Objetivo: alinear toda la documentación con el estado real, sin cambios
funcionales, sin declarar `PHASE 6 — CLOSED` todavía.

## Verificación de PD-001..PD-008 contra el Design Freeze

Se releyó `docs/phases/phase-6-design-freeze.md` completo contra la redacción exacta exigida por
este prompt para cada PD. Resultado: PD-002 (§11/§12, precisión C-017) y PD-008 (§8.2, precisión
de la ronda de corrección funcional) ya tenían su precisión formal incorporada. PD-001, PD-003,
PD-004, PD-005, PD-006, PD-007 no tienen ninguna afirmación en el Design Freeze que los
contradiga — son decisiones correctamente delegadas a documentos derivados por el propio §28
("Decisiones técnicas pendientes de los documentos derivados"). **Ninguna de las ocho se
reabrió, amplió ni modificó** — se conservan exactamente como fueron cerradas.

## Alcance implementado, ITD, correcciones, pruebas, regresión, evidencia, migraciones y
## seguridad — referencia

Todo este contenido ya existe en las secciones correspondientes de este mismo documento (§2-§17,
"Ronda de refinamiento", "Ronda de corrección funcional de recordatorios", "Prompt 2/4", "Prompt
3/4", "Prompt 4/4" más arriba) — no se duplica aquí. Este prompt solo agrega el dato inequívoco
que faltaba: el commit final auditado.

## Final audited commit

```text
4f5e8c0ecb9a403fada16c8eded5d9bd56a1bed4
```

Auto-referencia trivial, mismo patrón ya usado en todo este documento — `79697e0`, `46a16af`,
`a0793f0`, `899dcc4`, `5a903ba`/`d94a94b` — no confiar en este hash citado, volver a ejecutar
`git rev-parse HEAD` en cualquier verificación posterior. **Este no es el commit definitivo de
cierre**: es el commit de la consolidación documental (prompt 1/3). El commit/tag de cierre
definitivo se crea en el prompt 2/3, después de la revalidación completa.

## Tag final

Todavía **no** se crea — pendiente del prompt 2/3, después de que la revalidación completa
confirme que no quedan hallazgos abiertos.

## Contradicciones encontradas

Ninguna contradicción **funcional**. Se registra, sin bloquear esta consolidación (no es una
contradicción funcional, es una cuestión de trazabilidad externa que no puedo verificar desde
este repositorio): la premisa de este prompt afirma que "la auditoría independiente... determinó
`PHASE 6 — IMPLEMENTED / READY FOR FINAL CLOSURE`", pero `git status --short --branch` muestra
`origin/main` 20+ commits detrás de `HEAD` — si esa auditoría corrió contra `origin/main` (el
único lugar accesible externamente, dado que el propietario aún no ha hecho `git push`), no pudo
haber evaluado ninguno de los commits de Fase 6. No es una discrepancia de código ni de
decisiones — se deja registrada para que el prompt 2/3 (revalidación) la confirme o la aclare.

## Discrepancias puramente documentales corregidas

- `phase-6-documentation-index.md`: describía `phase-6-final-report.md` como "plantilla de
  cierre" — ya no lo es, está consolidado. Corregido.
- `phase-6-documentation-index.md` y `phase-6-final-report.md`: ambos citaban el estado
  `READY FOR FINAL AUDIT` de la ronda anterior — actualizado a `PREPARED FOR FINAL VALIDATION`
  en ambos, consistente con que esta etapa todavía no declara `CLOSED`.

## Estado tras este prompt

```text
PHASE 6 — PREPARED FOR FINAL VALIDATION
```

Documentación consolidada. Tag: no creado. Commit de cierre definitivo: no creado. Pendiente el
prompt 2/3 (revalidación completa) y su confirmación posterior antes de declarar
`PHASE 6 — CLOSED`.

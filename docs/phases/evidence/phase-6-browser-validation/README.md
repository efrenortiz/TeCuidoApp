# Fase 6 — Evidencia de validación en navegador (Prompt 6 de la corrección post-implementación)

**Fecha:** 2026-09-22
**Herramienta:** Claude in Chrome (interacción real de navegador — no `django.test.Client`).
**Servidor:** `python manage.py runserver` local, `EMAIL_BACKEND` de consola.
**HEAD auditado:** `79697e0f590314847a3e8688ed45d08167cc0498` (más los cambios de código del
Prompt 1 de esta misma ronda, aplicados antes de esta validación).

Esta evidencia complementa, no sustituye, la suite de tests Django (§13 de
`docs/phases/phase-6-implementation-summary.md`). Cubre exactamente los escenarios exigidos por
el Prompt 6: consentimiento, audit trail por rol, filtros, y ausencia de opt-out.

## Seed usado

Script `seed_phase6_browser.py` (no versionado, solo de esta sesión) creó:

- `f6-admin@example.com` — Administrador (`is_superuser=True`).
- `f6-doctor@example.com` — Médico, con `DoctorClinic` en "Consultorio F6 Browser".
- `f6-patient@example.com` — Paciente adulto.
- `f6-responsible@example.com` — Responsable con `ResponsiblePatientRelationship.ACTIVE` hacia
  el paciente anterior.
- Una `Appointment` real (id 6) reservada por el paciente, generando de paso las tres
  notificaciones de "cita creada" — confirmadas por consola del `EMAIL_BACKEND` (ver §"Emails
  reales" más abajo), evidencia adicional no capturada en pantalla.

## Escenarios validados

### 1. Consentimiento (F6-D04 / PD-006)

| Paso | Actor | Resultado | Captura |
|---|---|---|---|
| Abrir "Aviso de privacidad y términos" | Paciente | Muestra ambos documentos, versión `1.0`, estado "Pendiente de aceptación", botón "Aceptar versión 1.0" por documento | `01-consent-pending.jpg` |
| Aceptar "Aviso de privacidad" | Paciente | Mensaje "Documento aceptado"; el Aviso pasa a "Aceptado el 22/09/2026 18:11"; Términos permanece "Pendiente" de forma independiente | `02-consent-accepted.jpg` |

Nota: `LEGAL_DOCUMENT_URLS` no está configurado en este entorno de desarrollo (`PRIVACY_NOTICE_URL`/
`TERMS_AND_CONDITIONS_URL` vacíos), así que el enlace "Leer el documento" no aparece — comportamiento
correcto y ya cubierto por test (`ConsentDocumentReferenceTests`), no un defecto de esta validación.

### 2. Audit trail — acceso por rol (F6-D05, hallazgo 12.1)

Cada fila se verificó confirmando primero el rol real en `/` (badge de rol visible) antes de
intentar `/clinica/auditoria/`, para no repetir el error de sesión encontrado durante esta misma
sesión (ver "Incidente" más abajo).

| Actor | Resultado esperado | Resultado real | Captura |
|---|---|---|---|
| Paciente | Denegado (404 uniforme, anti-enumeración) | 404, `Raised by: medical_records.views.AuditTrailView` | `03-patient-audit-trail-denied-404.jpg` |
| Médico | Denegado | 404 | `04-doctor-audit-trail-denied-404.jpg` |
| Administrador | Permitido | 200, tabla con 4 eventos reales (`LOGIN` de admin/médico/paciente + un evento histórico previo) | `05-admin-audit-trail-success.jpg` |
| Responsable | Denegado | 404 | `07-responsible-audit-trail-denied-404.jpg` |
| Anónimo (sin sesión) | Redirige a login | `302` → `/accounts/login/?next=/clinica/auditoria/` | `08-anonymous-redirect-to-login.jpg` |

Nota de verificación: las capturas `03`, `04` y `07` (paciente/médico/responsable denegados) son
**byte a byte idénticas** (`md5sum` coincide). Esto es esperado y no un residuo del incidente de
sesión descrito más abajo: el servidor corrió con `DJANGO_DEBUG=True`, así que las tres muestran
la página técnica genérica de Django 404 (método, URL, "Raised by", versión de Django) — sin
ningún dato de usuario/sesión. Mismo endpoint denegado + misma excepción ⇒ el mismo render en
los tres roles, lo cual además confirma positivamente que este 404 no filtra ninguna señal
distintiva por rol (propiedad anti-enumeración deseada). Se verificó el rol real en `/` antes de
cada una de las tres capturas, tal como en el resto del documento.

### 3. Filtros del audit trail (hallazgo 12.8)

| Filtro | Acción | Resultado | Captura |
|---|---|---|---|
| Fecha desde | `2026-09-22` | Oculta el evento histórico del 16/09/2026, conserva los 3 `LOGIN` del día | `06-admin-audit-trail-date-filter.jpg` |
| Acción | `Inicio de sesión` | Solo filas `LOGIN` (`?action=LOGIN` en la URL) — verificado, no se guardó captura adicional por ser una variación menor de la anterior | — |

### 4. Ausencia de opt-out (F6-D03)

La pantalla de consentimiento (`01`/`02`) y la pantalla de inicio (no capturada aparte) no
muestran ningún control de "notificaciones"/"preferencias"/"desactivar recordatorios" en ningún
rol. Consistente con la ausencia estructural ya verificada por
`notifications.tests.test_services.NoOptOutTests`.

### 5. Emails reales (evidencia complementaria, no pedida explícitamente pero generada por el seed)

La consola del servidor (`EMAIL_BACKEND` de consola) mostró el envío real, con contenido correcto,
de las tres notificaciones "cita creada" (paciente, responsable, médico) al crear la cita del seed
— asunto **"Cita reservada — TeCuidoApp"** (no "confirmada"), con fecha/hora/médico/consultorio y
el enlace `http://localhost:8000/agenda/citas/6/`. Ver `docs/phases/phase-6-implementation-summary.md`
§13 para la política de reintentos que gobierna este mismo transporte.

## Incidente durante la validación (transparencia)

Los primeros dos intentos de cambiar de sesión (paciente → médico, médico → administrador)
fallaron silenciosamente: `GET /accounts/logout/` no cierra sesión (Django exige `POST` desde
Django 5, devuelve error ante `GET`), y un envío de formulario cuyo clic no llegó a registrarse a
tiempo dejó la sesión anterior activa — la siguiente comprobación de "administrador denegado"
resultó ser, en realidad, una repetición del mismo actor anterior. Se detectó al verificar
explícitamente el rol en `/` antes de cada prueba subsiguiente, y se corrigió cerrando sesión
exclusivamente con el botón "Cerrar sesión" de la UI (que sí envía `POST`) y confirmando el nuevo
rol con una captura antes de repetir la prueba. Las capturas `03` a `08` de este documento
corresponden todas a sesiones verificadas de esta forma. Ningún hallazgo de producto se deriva de
este incidente — fue un problema de la secuencia de automatización, no del comportamiento de
TeCuidoApp.

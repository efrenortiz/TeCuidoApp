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

---

# Ronda 2 — Prompt 2/4 (evidencia UI/browser complementaria, 2026-09-22)

**Fecha:** 2026-09-22
**Herramienta:** Claude in Chrome (interacción real de navegador — no `django.test.Client`).
**Servidor:** `python manage.py runserver` local, `EMAIL_BACKEND` de consola,
`PRIVACY_NOTICE_URL`/`TERMS_AND_CONDITIONS_URL` configuradas en `.env` local (ver §3 abajo).
**Commit exacto validado:** `592c356e07cf863d5983fa4a51d00990016d5afc` (auto-referencia trivial,
mismo patrón ya usado en `79697e0`/`46a16af` — no confiar en este hash citado, volver a ejecutar
`git rev-parse HEAD` en cualquier auditoría posterior; no usar `79697e0` ni `38d22db`, ambos
anteriores a las correcciones de esta ronda: `38d22db` es el HEAD previo a C-020, el propio bug
documentado arriba se reprodujo y corrigió DESPUÉS de ese commit).

Esta ronda complementa, no repite, la evidencia de la Ronda 1 (arriba): estados UI pendientes
(empty/error) de la pantalla de audit trail, consentimiento con URLs canónicas reales
configuradas, y verificación adicional de los enlaces de notificación.

## 6. Estados UI del audit trail (§2 del prompt 2/4)

| Estado | Mecanismo de prueba controlado | Resultado | Captura |
|---|---|---|---|
| Empty | Filtro válido sin resultados (`date_from=2099-01-01&date_to=2099-01-02`) | 200, componente `_empty_state.html`: "No hay eventos de auditoría que coincidan con el filtro." | `11-audit-trail-empty.jpg` |
| Error (hallazgo real, antes de corregir) | `?patient_id=abc` (valor no numérico vía URL, sin modificar la app) | **500 no controlado** — `ValueError: Field 'id' expected a number but got 'abc'.`, `Raised during: medical_records.views.AuditTrailView` | `09-audit-trail-error-patient-id-invalid-before-fix.jpg` |
| Error (después de C-020) | Mismo `?patient_id=abc`, tras la corrección | 200 — el filtro inválido se ignora (mismo criterio permisivo que `date_from`/`date_to`), el valor crudo se conserva en el formulario, la consulta no se rompe | `10-audit-trail-patient-id-invalid-after-fix.jpg` |
| Loading | — | **No hay estado de carga distinguible que capturar**: esta pantalla es una vista Django server-rendered clásica, sin capa JS/AJAX (`templates/medical_records/audit_trail.html` es un `<form method="get">` con recarga completa de página, `templates/layouts/app_base.html` no carga ningún framework cliente). Esto es consistente con el principio arquitectónico de no construir infraestructura sin necesidad real (`CLAUDE.md` §12/§14) — ninguna decisión de F6-D05 pidió una capa AJAX. El único "loading" real es el indicador nativo de navegación del propio navegador, que en este entorno local se completa antes de que cualquier captura pueda distinguirlo de la página ya cargada; no se fabricó un spinner ni se modificó la app solo para producir una captura (instrucción explícita del prompt 2/4 §2). | — (no aplica) |

### C-020 — `patient_id` no numérico causaba un 500 no controlado en el audit trail (UI)

Al intentar generar la evidencia del estado "error" pedida por el prompt, se encontró un fallo
real, no fabricado: `AuditTrailView.get` pasaba `patient_id` sin validar a
`Patient.objects.filter(pk=patient_id)`, y Django propaga un `ValueError` sin capturar cuando el
valor no es convertible a entero — un administrador autenticado que escriba un ID no numérico
(o cualquier cliente que manipule la URL) recibe una página de error técnica en vez de un filtro
simplemente ignorado. El API equivalente (`AuditEventListView._parse_int`,
`medical_records/api.py`) ya validaba esto con un `ApiError` controlado (400) — la UI estaba
desalineada de su propio contrato hermano.

**Corrección:** se envuelve la conversión en `try/except (TypeError, ValueError)`, tratando un
`patient_id` inválido igual que un `date_from`/`date_to` inválido ya se trataba: se ignora
silenciosamente (mismo criterio ya documentado en `_parse_ui_date`, "filtro de UI opcional, no un
endpoint que deba validar estrictamente"), no se introduce una regla nueva ni una respuesta HTTP
nueva. No se tocó el API (ya era correcto). Ver `docs/phases/phase-6-implementation-summary.md`
para el detalle completo (problema/causa/solución/tests).

**Metodología:** el screenshot "antes" (`09-...`) se generó revirtiendo temporalmente el fix con
`git stash` (el archivo nunca había sido commiteado con el bug — el bug era el estado de partida
de esta ronda), capturando, y aplicando `git stash pop` para restaurar la corrección antes de
seguir. La app en ningún momento tuvo una versión "rota a propósito" distinta de su estado real
pre-corrección — no se fabricó un error que no existiera.

## 7. Consentimiento con documentos externos reales configurados (§3 del prompt 2/4)

A diferencia de la Ronda 1 (donde `LEGAL_DOCUMENT_URLS` estaba vacío por no estar configurado en
el entorno), esta ronda configuró en `.env` local (nunca commiteado, `.gitignore`):

```text
PRIVACY_NOTICE_URL=https://example.com/tecuido-entorno-de-validacion/aviso-de-privacidad-v1
TERMS_AND_CONDITIONS_URL=https://example.com/tecuido-entorno-de-validacion/terminos-y-condiciones-v1
```

`example.com` es el dominio reservado por IANA para documentación y pruebas (RFC 2606) — nunca
se interpretará como un documento legal real; la ruta además se autoidentifica como
"entorno-de-validacion". Mismo patrón ya documentado en `.env.example` del repositorio (no es una
convención nueva de esta ronda).

| Paso | Actor | Resultado | Captura |
|---|---|---|---|
| Abrir "Aviso de privacidad y términos" (usuario con Aviso ya aceptado, Términos pendiente) | Paciente (`f6-patient@example.com`) | Ambos documentos muestran tipo, versión (`v1.0`) y enlace real **"Leer el documento"**; verificado con `read_page` que el `href` de cada enlace coincide exactamente con la URL configurada arriba | `12-consent-external-document-pending-terms.jpg` |
| Aceptar "Términos y condiciones" v1.0 | Paciente | "Documento aceptado"; ambos documentos quedan "Aceptado", cada uno con su propia fecha/hora — el enlace "Leer el documento" se conserva visible también después de aceptar | `13-consent-external-document-both-accepted.jpg` |

Esto cierra la brecha explícita señalada por el prompt 2/4 §3: la evidencia anterior no podía
demostrar "documento mostrado / versión visible / enlace disponible" porque el entorno no tenía
URLs configuradas — ahora sí, con una URL de prueba inequívocamente identificada como tal.

## 8. Enlaces de notificación — vista correcta, sin bypass (§4 del prompt 2/4)

Las cuatro plantillas de notificación (creada/modificada/cancelada/recordatorio) comparten la
misma función `_appointment_url(appointment)` (`notifications/services.py`) — ya verificado por
`test_link_points_to_authorization_protected_view_no_bypass` (Django test client). Esta ronda
añade la verificación equivalente en navegador real, sobre el mismo enlace
(`http://localhost:8000/agenda/citas/6/`) que las notificaciones de la cita del seed
efectivamente contienen (confirmado por consola del `EMAIL_BACKEND`, Ronda 1 §5):

| Actor | Resultado | Captura |
|---|---|---|
| Paciente autenticado (dueño de la cita) | 200 — vista real de detalle de cita (`appointments:appointment_detail`), sin contenido clínico, con acciones "Reprogramar"/"Cancelar cita" | `14-notification-link-appointment-detail-authorized.jpg` |
| Anónimo (sesión cerrada, mismo enlace exacto) | `302` → `/accounts/login/?next=/agenda/citas/6/` — ni el ID de la cita ni ningún dato se filtra antes del login | `15-notification-link-anonymous-redirect-to-login.jpg` |

Confirma que el enlace de las notificaciones lleva a la pantalla ya protegida de Agenda
(`LoginRequiredMixin` + autorización por objeto), no a una ruta nueva sin protección propia —
ninguna URL "de un solo uso" ni token de bypass, tal como exige `phase-6-notification-
security-and-privacy.md`.

## Regresión ejecutada tras la corrección de esta ronda

```text
python manage.py check                        -> System check identified no issues (0 silenced)
python manage.py makemigrations --check        -> No changes detected
python manage.py test medical_records          -> ver commit de esta ronda / implementation-summary.md
```

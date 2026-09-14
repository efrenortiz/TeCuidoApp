# Informe final — Fase 3: Gestión clínica

Fecha: 2026-09-11

## Resumen ejecutivo

Fase 3 se implementó en 8 etapas incrementales (ETAPA 0 a ETAPA 7), cada una validada contra
`docs/phases/phase-3-prompt_programacion.md` antes de avanzar a la siguiente, con regresión
obligatoria de Fase 2 después de cada etapa que tocara `appointments`, permisos compartidos o
navegación relevante. Las 8 etapas cerraron con su Gate en verde. La suite completa del proyecto
(`python manage.py test`) pasa **528/528** (526/526 al cierre de la auditoría de hallazgos
HIGH/CRITICAL, más 2 tests agregados en la corrección del hallazgo `AuditEvent.actor_id` —
ver sección dedicada más abajo), sin migraciones pendientes y sin hallazgos de seguridad
abiertos sin documentar.

La única limitación de evidencia señalada al cierre de ETAPA 7 —ausencia de una validación real
de navegador, porque la extensión Claude-in-Chrome no estaba disponible durante la construcción—
se resolvió en una **sesión de cierre posterior** (2026-09-11): se ejecutó una validación real de
navegador (Chromium real vía Playwright, no test client de Django) contra el servidor de
desarrollo, cubriendo el flujo clínico completo de extremo a extremo. Resultado: **17/17
verificaciones OK**, con capturas de pantalla y registro paso a paso conservados en
`docs/phases/evidence/phase-3-browser-validation-2026-09-11/`. Ver detalle en ETAPA 7 y en la
sección "Validación real de navegador — cierre" más abajo.

Adicionalmente, se ejecutó una **auditoría técnica independiente de hallazgos HIGH/CRITICAL**
(2026-09-11), que verificó con evidencia (no por afirmación) cada hallazgo histórico y buscó
activamente hallazgos nuevos. Resultado: **0 CRITICAL y 0 HIGH abiertos que bloqueen el cierre**.
La auditoría encontró y corrigió un defecto real no reportado previamente (dos endpoints de la
API devolvían 500 en vez de 404 para un id inexistente) y confirmó que el único hallazgo con
exposición técnica residual (los endpoints legacy de Fase 2, ya documentados en ADR-020) no
bloquea el cierre según el criterio de release ya aprobado del propio proyecto. Ver sección
"Auditoría final de hallazgos HIGH/CRITICAL" más abajo para el detalle completo, incluida la
justificación de por qué ese hallazgo no bloquea pese a no estar eliminado del código.

```
FASE 3 — IMPLEMENTADA
```

---

## ETAPA 0 — Baseline y diagnóstico

**Implementado:** inspección del repositorio, apps existentes, modelos relevantes, patrón de
servicios/API/tests de Fase 2 (`appointments`), y ejecución del baseline (`check`,
`makemigrations --check`, `test`) antes de escribir código nuevo.

**Decisiones aplicadas:** ninguna decisión de diseño propia — etapa puramente de diagnóstico.

**Resultado de pruebas:** baseline de Fase 1/2 verde antes de iniciar Fase 3 (sin fallos
preexistentes que ocultar o heredar).

**Gate 0:** CLOSED — arquitectura de Agenda, patrón de servicios/API/tests y puntos de
integración quedaron identificados antes de tocar código.

---

## ETAPA 1 — App `medical_records` y modelo base

**Implementado:**
- App `medical_records` creada y registrada en `INSTALLED_APPS`.
- Modelos `ClinicalEncounter` (`Appointment 1 ─── 0..1 ClinicalEncounter`, estados únicamente
  `IN_PROGRESS`/`COMPLETED`, cinco campos clínicos obligatorios + seis opcionales, timestamps) y
  `MedicalRecord` (`Patient 1 ─── 1 MedicalRecord` conceptual, seis campos longitudinales).
- Constraints de integridad a nivel de PostgreSQL (`CheckConstraint` de estado, de
  `completed_at`↔estado, de orden temporal `started_at≥created_at`/`completed_at≥started_at`, de
  positividad de peso/talla) y unicidad (`appointment`, `patient`).
- `medical_records/admin.py`, migración `0001_initial`.
- `medical_records/tests/test_models.py` (27 tests).

**Decisiones aplicadas:**
- Contradicción documental resuelta: `clinical-encounter-rules.md` R-008 trataba `patient`/`clinic`
  como columnas de `ClinicalEncounter`, pero el modelo físico ratificado (`clinical-data-model.md`
  §25.2) solo define `appointment`/`doctor`. Se implementaron `patient`/`clinic` como **propiedades
  derivadas de solo lectura** de `appointment` — satisface R-008 por construcción, sin una segunda
  fuente editable de verdad.
- Defecto de diseño real detectado y corregido: `created_at` con `auto_now_add=True` calcula su
  propio `now()` en el INSERT, independiente de `started_at` capturado antes por el servicio —
  podía violar el CHECK `started_at ≥ created_at` por pura carrera de microsegundos incluso en
  flujo normal. Se cambió a `DateTimeField()` explícito; el servicio (ETAPA 2) captura un único
  `now` y lo asigna a ambos campos.

**Resultado de pruebas:** 27/27 en `test_models.py`; `check`/`makemigrations --check` limpios.

**Gate 1:** CLOSED.

---

## ETAPA 2 — Domain Services

**Implementado:**
- `medical_records/services/exceptions.py` — taxonomía completa de 14 excepciones de dominio.
- `medical_records/services/permissions.py` — autorización object-level reutilizando
  `appointments.services.permissions.is_assigned_doctor` y
  `patients.services.permissions.doctor_has_active_relationship`/`responsible_has_active_relationship`
  (ADR-008: sin lógica duplicada).
- `medical_records/services/encounter.py` — `start_encounter`, `save_encounter`,
  `complete_encounter`, `get_encounter`, reutilizando `appointments.services.appointment
  .start_appointment()`/`complete_appointment()` dentro de transacciones anidadas propias.
- `medical_records/services/record.py` — `get_or_create_for_patient`, `get_medical_record`,
  `update_medical_record`.
- Validación de contenido clínico real (R-050–R-057): normalización, rechazo de placeholders
  case-insensitive, sin evaluación de calidad médica ni longitud mínima.
- `medical_records/tests/test_services.py` (50 tests).

**Decisiones aplicadas:**
- Resolución de nomenclatura (no arquitectónica): `clinical-service-contracts.md` SC-065 menciona
  "EncounterImmutable" en prosa, ausente de la taxonomía cerrada §19; SC-136
  (`EncounterAlreadyCompleted`) describe exactamente ese caso — se usó ese nombre, ya definitivo.
- `get_or_create_for_patient(actor=None)` se invoca internamente desde `start_encounter` (ya
  autorizado vía P-027, sin exigir relación — P-031) en vez de re-autorizar con la política de
  lectura longitudinal (P-013), que sí exige relación activa y bloquearía la primera consulta.
- `can_access_patient_record` NO reutiliza `patients.services.permissions.can_view_patient`: esa
  función concede acceso incondicional a `is_superuser` (ADR-004, alcance global Fase 1/2), lo que
  contradice P-008/038/042 (acceso clínico ≠ acceso administrativo; sin bypass genérico).

**Resultado de pruebas:** 51/51 en `test_services.py` (número final, tras las adiciones de ETAPA 4/6);
regresión Fase 2 332/332.

**Gate 2:** CLOSED.

---

## ETAPA 3 — Concurrencia e integridad transaccional

**Implementado:** `medical_records/tests/test_concurrency.py` (8 tests, `TransactionTestCase` +
`threading.Barrier`, mismo patrón que Fase 2): dos `start_encounter` concurrentes (idempotencia
real), backstop de unicidad de BD ante creación directa concurrente, dos `complete_encounter`
concurrentes (contenido idéntico y distinto), `save_encounter` concurrente (campos distintos y
mismo campo — last-write-wins sin corrupción), `save` vs `complete` concurrentes, guardado
inmediatamente posterior a un cierre ya confirmado.

**Decisiones aplicadas:** ninguna decisión nueva — se confirmó empíricamente (carreras reales, no
solo secuenciales) que `select_for_update()` + unicidad de BD bastan para las invariantes de
Gate 3, sin mecanismo adicional (Redis/Celery/locks distribuidos).

**Resultado de pruebas:** 8/8, ejecutado 3 veces consecutivas sin flakiness; regresión Fase 2
332/332.

**Gate 3:** CLOSED — nunca persistió `ClinicalEncounter COMPLETED` + `Appointment IN_CONSULTATION`,
ni `Appointment IN_CONSULTATION` + `ClinicalEncounter` inexistente.

---

## ETAPA 4 — API

**Implementado:**
- `medical_records/api.py` — vistas planas `django.views.View` + `JsonResponse` (mismo patrón que
  `appointments/api.py`, sin DRF), 7 endpoints: iniciar consulta, consultar/guardar/completar
  encuentro, consultar/actualizar expediente, historial paginado.
- Mapeo de campos español↔inglés según la tabla cerrada de `clinical-api-contracts.md` §25 (D-002).
- Traducción centralizada de errores de dominio → HTTP según la tabla de mapeo §19.
- `medical_records/tests/test_api.py` (39 tests).

**Decisiones aplicadas:**
- Corrección de un defecto real de ETAPA 2: `update_medical_record` creaba el expediente
  implícitamente (`get_or_create`); `API-095` (cerrado) exige que el PATCH nunca lo cree. Se
  corrigió para exigir el expediente ya existente (`ClinicalRecordNotFound` → 404 si no existe).
- Se agregó `list_encounters_for_patient` (`ClinicalHistoryService`, SC-093-098) — ETAPA 2 no lo
  incluyó pese a que `GET /patients/{id}/encounters/` (API-081) lo requiere.
- `IncompleteClinicalContent`/`ClinicalContentPlaceholder` se enriquecieron para transportar la
  lista completa de campos afectados (API-103 exige `details.fields` como lista).
- `MedicalRecord` expone sus 6 campos longitudinales con nombres internos (inglés): a diferencia de
  `ClinicalEncounter`, no existe tabla de mapeo cerrada para estos campos.

**Resultado de pruebas:** 39/39 en `test_api.py`; medical_records 125/125 acumulado; regresión
Fase 2 332/332.

**Gate 4:** CLOSED.

---

## ETAPA 5 — UX/UI y pantallas

**Implementado:**
- `appointments/appointment_detail.html` extendido con botones condicionales por estado ("Iniciar
  consulta"/"Continuar consulta"/"Ver consulta"), sin recrear una agenda paralela (SCREEN-016).
- `EncounterDetailView` (una sola vista/plantilla para IN_PROGRESS editable, COMPLETED de solo
  lectura y detalle histórico, branched por `can_edit`), `EncounterSaveView`, `EncounterCompleteView`
  (confirmación vía `<dialog>` reutilizando el componente ya existente en Fase 1, sin exigir un
  Guardar previo — SCREEN-071).
- `MedicalRecordView` con las tres secciones cerradas por SCREEN-088 (Resumen clínico / Datos
  longitudinales / Historial), nunca fusionadas; resumen nunca etiquetado "diagnóstico actual".
- `PatientEncounterHistoryView`, paginado, orden más reciente→más antiguo.
- `medical_records/tests/test_ui.py` (32 tests).

**Decisiones aplicadas:**
- "Iniciar consulta"/"Finalizar consulta" de Fase 2 dejaron de ser el camino expuesto en la UI —
  sustituidos por el flujo clínico atómico. Los endpoints de Fase 2 en sí no se modificaron (ver
  ADR-020, ETAPA 7).
- El botón "Ver consulta" se restringe a actores clínicos (doctor/paciente/responsable),
  excluyendo administradores (SCREEN-117/120 — ser admin no activa modo UX clínico).
- Sin JavaScript en ninguna pantalla clínica — todos los flujos se resuelven con submits de
  formulario planos y re-render server-side.

**Resultado de pruebas:** 32/32 en `test_ui.py`; medical_records 157/157 acumulado; regresión
Fase 2 332/332.

**Gate 5:** CLOSED — validado mediante 32 tests automatizados (equivalente a la validación manual
exigida: inicio, captura, guardado, interrupción, reanudación, completion, pantalla bloqueada,
lectura histórica, permisos visibles y efectivos).

---

## ETAPA 6 — Auditoría, seguridad y endurecimiento

**Implementado:**
- `AuditEvent` (entidad de auditoría separada — AH-011, cerrado) + `medical_records/services
  /audit.py` (`record_event` para mutaciones dentro de la misma transacción — AH-088;
  `safe_record_event` para lecturas, nunca bloquea la operación — AH-089).
- Auditoría cableada en los 8 puntos de servicio: `START_ENCOUNTER`, `SAVE_ENCOUNTER`,
  `COMPLETE_ENCOUNTER` (éxito y denegado — AH-021/022/023, cerradas), `CREATE_MEDICAL_RECORD`,
  `UPDATE_MEDICAL_RECORD`, `READ_CLINICAL_ENCOUNTER`, `READ_MEDICAL_RECORD`,
  `READ_CLINICAL_HISTORY`.
- `list_audit_events`/`can_view_audit_log` — lectura restringida al Administrador (P-041/AH-107,
  cerradas); `AuditEventAdmin` registrado sin permisos de alta/edición/borrado (AH-082/083,
  append-only).
- `medical_records/tests/test_audit.py` (23 tests).

**Decisiones aplicadas:**
- Bug real corregido: escribir el evento `DENIED` dentro del mismo `transaction.atomic()` que el
  `raise` inmediatamente posterior lo habría descartado por el propio rollback. Se movió a un
  `try/except` fuera del `atomic()`. Verificado con un test que falló antes de la corrección.
- Segundo bug real corregido: `safe_record_event` necesitaba su propio `transaction.atomic()`
  (savepoint) — sin él, un `IntegrityError` al auditar dejaba la conexión Postgres en "current
  transaction is aborted" para el resto de la transacción ambiente, rompiendo la lectura clínica
  que ese helper existe para proteger. Detectado forzando una falla real (actor nulo), no simulada.
- Se omiten `request_id`/`metadata` del esquema conceptual de AH-011 — sin necesidad real de
  correlación multi-evento en el alcance mínimo de F3.

**Resultado de pruebas:** 23/23 en `test_audit.py`; medical_records 180/180 acumulado; regresión
Fase 2 332/332.

**Gate 6:** CLOSED — evidencia de operaciones auditadas, accesos no autorizados rechazados **y**
registrados, ausencia de IDOR, ausencia de documentos públicos (Fase 3 no implementa archivos),
ausencia de información clínica en logs/errores (verificado por grep y por test).

---

## ETAPA 7 — Suite de pruebas y cierre

**Implementado:**
- `medical_records/tests/test_smoke.py` — smoke suite de Fase 3 (§38), 1 test end-to-end vía HTTP
  real cubriendo los 9 puntos exigidos: login de médico, cita elegible, inicio, guardado parcial,
  completion válido, lectura de expediente, historial, acceso denegado a paciente ajeno, edición
  post-completion rechazada.
- `medical_records/tests/test_security.py` (11 tests) — CSRF, ausencia de secretos/SQL en errores,
  caché privada, payloads que intentan cambiar `patient_id`/`doctor_id`/`status`/timestamps.
- `Cache-Control: no-store` (API) y `never_cache` (UI) en toda respuesta clínica — cierra
  TS-103/158, brecha real detectada en el barrido final que ninguna etapa anterior cubría.
- `ADR-020` — decisión arquitectónica explícita sobre el hallazgo pendiente desde ETAPA 5/6 (los
  endpoints legacy de Fase 2 `appointment_start`/`appointment_complete` siguen alcanzables
  directamente sin pasar por la atomicidad clínica).
- Verificación cruzada completa contra las 47 secciones de `phase-3-testing-strategy.md`.

**Decisiones aplicadas:**
- El hallazgo de los endpoints legacy se resolvió **documentando** la decisión (ADR-020), no
  modificando código: la alternativa (que `appointments` importe `medical_records` para verificar
  la existencia de un `ClinicalEncounter`) invertiría la dependencia unidireccional de ADR-008 sin
  justificación proporcional a un caso de uso marginal (requiere una solicitud HTTP directa, no
  alcanzable desde ninguna pantalla de la aplicación, y exige seguir siendo el médico asignado).
- Evidencia de "smoke browser" (§42, punto 6): durante la construcción de ETAPA 7, el entorno de
  esa sesión no tuvo la extensión Claude-in-Chrome conectada, así que no fue posible una captura
  de navegador real en ese momento. Se documentó la limitación explícitamente en vez de fabricar
  evidencia, apoyándose en la evidencia equivalente disponible (smoke HTTP end-to-end + 32 tests
  de UI que renderizan y verifican el HTML real).
  **Actualización (sesión de cierre, 2026-09-11):** esa limitación quedó resuelta. Se instaló
  Playwright de forma ad-hoc (no es una dependencia del proyecto; no se agregó a
  `requirements.txt`) y se ejecutó una validación real con Chromium headless contra el servidor
  de desarrollo, cubriendo login, cita elegible, inicio, captura de los cinco campos, guardado
  parcial con verificación de persistencia tras recarga, interrupción/reanudación, completion,
  inmutabilidad (intento real de edición post-completion rechazado por el servidor), historial,
  detalle histórico y seguridad clínica (acceso denegado a paciente ajeno, sin fuga de datos).
  Resultado: 17/17 verificaciones OK. Evidencia completa (7 capturas de pantalla + registro
  JSON paso a paso + metadatos de entorno/usuarios/alcance) en
  `docs/phases/evidence/phase-3-browser-validation-2026-09-11/`. Los dos hallazgos que aparecieron
  en la primera corrida del script de validación se investigaron antes de tocar cualquier archivo
  de la aplicación y resultaron ser suposiciones incorrectas del script (no defectos): el label de
  `Appointment.Status.COMPLETED` es "Atendida" (Fase 2, ya cerrado), distinto de
  `ClinicalEncounter.Status.COMPLETED` ("Completada"); y el acceso al expediente por el médico
  exige una `DoctorPatientRelationship` activa incluso siendo el médico asignado de la cita
  (P-009/P-010, ya cerrado y probado desde ETAPA 2) — se corrigió el script de validación, no la
  aplicación. Detalle completo, incluida la nota sobre la página técnica 404 de `DEBUG=True` (no
  bloqueante — no expone datos clínicos), en el `README.md` de la carpeta de evidencia.

**Resultado de pruebas:**
- `python manage.py check` → sin problemas.
- `python manage.py makemigrations --check --dry-run` → sin cambios pendientes.
- `python manage.py test` (suite completa del proyecto) → **526/526, OK**.
- `medical_records.tests.test_concurrency` ejecutado 3 veces consecutivas → estable (TS-151).
- Regresión Fase 2 (`appointments patients accounts doctors clinics`) → 332/332.
- Validación real de navegador (sesión de cierre, 2026-09-11) → **17/17 verificaciones OK** — ver
  sección dedicada más abajo.
- Re-confirmación final tras la validación de navegador: `check`, `makemigrations --check` y
  `python manage.py test` completos vueltos a ejecutar — sin cambios de código de aplicación entre
  una corrida y otra, resultado idéntico (526/526, tras el fix de H-07 — ver auditoría de hallazgos).

**Gate 7:** CLOSED.

---

## Validación real de navegador — cierre

- **Ejecutada:** sí, en sesión de cierre separada de la construcción de ETAPA 7.
- **Fecha:** 2026-09-11.
- **Entorno:** servidor de desarrollo local (`manage.py runserver`), base de datos de desarrollo
  local (no producción), Chromium real headless vía Playwright (instalación ad-hoc, no forma
  parte de las dependencias del proyecto).
- **Alcance:** flujo clínico completo de extremo a extremo — login de médico, contexto de Agenda,
  inicio de consulta (con verificación de idempotencia), captura y guardado parcial de los cinco
  campos obligatorios, persistencia tras recarga de página, interrupción y reanudación,
  completion, inmutabilidad post-completion (intento real de edición rechazado por el servidor),
  historial y detalle histórico, y seguridad clínica (acceso denegado a un paciente ajeno, tanto
  al expediente como a la URL directa del encuentro, sin fuga de datos clínicos).
- **Resultado:** 17/17 verificaciones OK, 0 fallos en la corrida final registrada.
- **Ubicación de la evidencia:** `docs/phases/evidence/phase-3-browser-validation-2026-09-11/`
  (7 capturas de pantalla, `validation-log.json` con el registro paso a paso, y `README.md` con
  metadatos completos — fecha/hora, entorno, usuarios/rol de prueba, URL inicial, resultado por
  bloque, y la investigación de los dos hallazgos iniciales que resultaron ser del script de
  validación, no de la aplicación).
- Los flujos críticos (inicio atómico, guardado parcial persistente, completion atómico,
  inmutabilidad, historial, y rechazo de acceso no autorizado) fueron **observados directamente**
  en un navegador real, no solo inferidos de tests automatizados.

```
PHASE 3 — READY TO CLOSE
```

---

## Desglose final de `medical_records` (196 tests)

| Suite | Tests |
|---|---:|
| `test_models.py` | 27 |
| `test_services.py` | 51 |
| `test_concurrency.py` | 8 |
| `test_api.py` | 41 |
| `test_ui.py` | 32 |
| `test_audit.py` | 25 |
| `test_security.py` | 11 |
| `test_smoke.py` | 1 |
| **Total** | **196** |

(2 tests adicionales respecto al cierre original de ETAPA 7: agregados en la auditoría de
hallazgos HIGH/CRITICAL del 2026-09-11 — ver sección siguiente. 2 tests adicionales más,
en `test_audit.py`, agregados en la corrección del hallazgo `AuditEvent.actor_id` del mismo
día — ver "Corrección — `AuditEvent.actor_id` NULL en `READ_CLINICAL_ENCOUNTER`" más abajo.)

---

## Auditoría final de hallazgos HIGH/CRITICAL — 2026-09-11

Auditoría técnica independiente posterior al cierre de ETAPA 7, con el objetivo explícito de
verificar (no asumir) que no quedan hallazgos HIGH/CRITICAL abiertos. Metodología: revisión línea
por línea del código actual de `medical_records` (modelos, servicios, permisos, API, vistas,
auditoría), cruce contra los 19 ADRs y los 13 documentos de diseño clínico, y verificación en vivo
(no solo lectura de código) de cada hallazgo histórico y de dos escenarios de riesgo
adicionales identificados de forma independiente.

### Hallazgos históricos — estado verificado

| ID | Hallazgo | Severidad | Estado reportado | Estado verificado | Evidencia |
|---|---|---|---|---|---|
| H-01 | `created_at` con `auto_now_add` podía violar `started_at≥created_at` por carrera de microsegundos | HIGH | RESOLVED (ETAPA 1) | **RESOLVED** | `models.py`: `created_at` es `DateTimeField()` sin `auto_now_add`; `encounter.py` asigna un único `now` a ambos campos |
| H-02 | `update_medical_record` creaba el expediente implícitamente (violaba API-095) | HIGH | RESOLVED (ETAPA 4) | **RESOLVED** | `record.py`: usa `.filter().first()` + `ClinicalRecordNotFound`; test `test_update_before_lazy_creation_is_404` pasa |
| H-03 | Evento de auditoría `DENIED` se perdía por el rollback de la misma transacción que audita | HIGH | RESOLVED (ETAPA 6) | **RESOLVED** | Los tres `except ClinicalNotAuthorized` de `encounter.py` están fuera del `transaction.atomic()`; test `test_denied_start_is_audited_and_survives_the_rollback` pasa |
| H-04 | `safe_record_event` podía dejar la conexión Postgres en "transaction aborted" | HIGH | RESOLVED (ETAPA 6) | **RESOLVED** | `audit.py`: `safe_record_event` usa su propio `transaction.atomic()` (savepoint); test `test_safe_record_event_never_raises` pasa |
| H-05 | Ausencia de `Cache-Control` en respuestas clínicas (TS-103/158, categoría "Alta" en la matriz de riesgo propia del proyecto) | HIGH | RESOLVED (ETAPA 7) | **RESOLVED** | `api.py` (`Cache-Control: no-store`), `views.py` (`@never_cache`); tests dedicados pasan |
| H-06 | Los endpoints legacy de Fase 2 (`start_appointment`/`complete_appointment`) permiten `Appointment COMPLETED` sin `ClinicalEncounter`, alcanzables por HTTP directo | HIGH | RESOLVED vía ADR-020 (documentado) | **PARTIALLY RESOLVED** — ver análisis detallado abajo | Reproducido en vivo en esta auditoría (script ad-hoc, no test unitario): tras el bypass, `Appointment.status=COMPLETED` con `ClinicalEncounter` inexistente de forma permanente; `start_encounter` posterior falla con `EncounterNotStartable` |

### Hallazgo nuevo, encontrado en esta auditoría

| ID | Hallazgo | Severidad | Estado al encontrarlo | Estado verificado | Evidencia |
|---|---|---|---|---|---|
| H-07 | `PATCH /api/v1/clinical/encounters/{id}/` y `POST /api/v1/clinical/encounters/{id}/complete/` devolvían **500** (no 404) para un `id` inexistente — viola TS-155 explícitamente ("Un ID inexistente no debe convertirse en un error 500 ni revelar información interna") | HIGH | OPEN (no reportado previamente, sin cobertura de test) | **RESOLVED en esta sesión** | Reproducido en vivo: traceback `ClinicalEncounter.DoesNotExist` sin capturar → 500, antes del fix. Corregido en `medical_records/services/encounter.py` (`save_encounter`/`complete_encounter`): se captura `ClinicalEncounter.DoesNotExist` y se traduce a `ClinicalNotFound` (mismo patrón ya usado en `get_encounter`/`start_encounter`). Confirmado en vivo tras el fix: 404 `CLINICAL_RESOURCE_NOT_FOUND`. Tests nuevos `test_save_on_nonexistent_encounter_returns_404_not_500` y `test_complete_on_nonexistent_encounter_returns_404_not_500` agregados y pasando. |

### Decisión detallada — H-06 (el único hallazgo con exposición técnica residual)

```text
ID: H-06
Severidad: HIGH
Descripción: appointments.services.appointment.start_appointment()/complete_appointment()
  (Fase 2, sin modificar) permanecen alcanzables directamente vía HTTP y no verifican la
  existencia de un ClinicalEncounter. Un médico ya asignado a la cita (mismo actor que la UI
  clínica ya autoriza) puede, mediante una solicitud HTTP directa fuera de cualquier pantalla de
  la aplicación, transicionar Appointment SCHEDULED→IN_CONSULTATION→COMPLETED sin que exista
  nunca un ClinicalEncounter para esa cita. Verificado en vivo: una vez ocurre el bypass, el
  flujo clínico normal queda permanentemente bloqueado para esa cita (start_encounter falla con
  EncounterNotStartable), por lo que no hay manera posterior de generar la documentación clínica
  para esa consulta.
Origen: identificado durante ETAPA 5 (construcción original), documentado en ADR-020
  (2026-09-11, Accepted) y confirmado con reproducción en vivo durante esta auditoría.
¿Está realmente resuelto?: NO en el sentido de "eliminado del código" — SÍ en el sentido de
  "evaluado, documentado como decisión arquitectónica explícita y mitigado en la única superficie
  de uso real (la UI, que ya no ofrece ningún camino hacia estas funciones desde ETAPA 5)".
Evidencia: appointments/services/appointment.py sin modificar (confirmado por git diff — 0
  cambios); reproducción en vivo de esta auditoría (script ad-hoc, no incluido en el repositorio);
  ADR-020 (docs/adr/ADR-020-legacy-agenda-transition-endpoints.md).
Impacto: no permite acceso no autorizado (exige ser el médico ya asignado a esa cita específica);
  no corrompe ni viola ningún constraint de base de datos (Appointment 1 ─── 0..1 ClinicalEncounter
  admite explícitamente 0); no expone datos clínicos de terceros; el efecto real es la ausencia
  de documentación clínica para una consulta marcada como atendida — un problema de completitud
  de proceso, no de integridad de datos ni de autorización.
Bloquea cierre de Fase 3: NO — según el criterio de release ya vigente y aprobado del propio
  proyecto (phase-3-testing-strategy.md §41): "regresión conocida de Agenda **sin** decisión
  explícita documentada" bloquea el cierre; con decisión documentada (ADR-020, con alternativas
  evaluadas y rechazadas por razones arquitectónicas concretas — preservar la dependencia
  unidireccional de ADR-008), el criterio no bloquea. Esta auditoría no downgradea ni oculta el
  hallazgo: se reporta con su severidad real (HIGH) y su exposición técnica residual explícita;
  la razón de que no bloquee el cierre es una regla de negocio que el propio proyecto ya adoptó
  antes de esta auditoría, no un juicio nuevo para facilitar el cierre.
```

### Decisión detallada — H-07 (único hallazgo nuevo)

```text
ID: H-07
Severidad: HIGH
Descripción: dos endpoints de la API JSON clínica devolvían 500 Internal Server Error (con
  traceback completo cuando DEBUG=True) para un encounter_id inexistente, en vez del 404
  documentado y ya usado consistentemente en el resto de la API.
Origen: defecto no detectado en ETAPA 4 (API) ni en ninguna etapa posterior — ausencia de
  cobertura de test para este caso específico en los dos endpoints afectados (sí existía para
  el GET, pero no para PATCH/complete).
¿Está realmente resuelto?: SI.
Evidencia: reproducción en vivo antes y después del fix (ver tabla arriba); 526/526 tests del
  proyecto completo pasan tras el fix; 2 tests de regresión nuevos añadidos; regresión de Fase 2
  (332/332) y concurrencia (8/8 × 3 corridas) reconfirmadas sin cambios tras el fix.
Impacto: sin el fix, un id inexistente en estos dos endpoints exponía información interna
  (traceback) si DEBUG=True quedaba activo accidentalmente, y en cualquier caso violaba
  TS-155 y el contrato de errores uniforme de la API (API-099).
Bloquea cierre de Fase 3: NO (ya corregido, verificado, y cubierto por tests permanentes).
```

### Resultado de la auditoría

```
AUDITORÍA FINAL DE HALLAZGOS

CRITICAL abiertos: 0
HIGH abiertos: 0
MEDIUM abiertos: 0
LOW abiertos: 0

Hallazgos HIGH/CRITICAL históricos:
RESUELTOS: 5
NO VERIFICADOS: 0
ABIERTOS: 0
(+1 PARCIALMENTE RESUELTO — H-06, documentado en ADR-020 y no bloqueante, ver detalle arriba)

Nuevos HIGH/CRITICAL detectados: 1 (H-07 — resuelto en esta misma sesión, con fix, evidencia
  en vivo y tests de regresión permanentes)

Resultado:
PASS

¿Cumple el criterio para cierre de Fase 3?
SI

PHASE 3 — NO OPEN HIGH/CRITICAL FINDINGS
```

### Evidencia de verificación de esta auditoría (no solo afirmación)

- `python manage.py check` → sin problemas (ejecutado tras el fix de H-07).
- `python manage.py makemigrations --check --dry-run` → sin cambios pendientes.
- `python manage.py test` (suite completa del proyecto) → **526/526, OK** (524 previos + 2 tests
  de regresión nuevos para H-07: `test_save_on_nonexistent_encounter_returns_404_not_500`,
  `test_complete_on_nonexistent_encounter_returns_404_not_500`).
- `medical_records.tests.test_concurrency` → 8/8, ejecutado 3 veces consecutivas tras el fix, sin
  flakiness (el archivo modificado, `encounter.py`, es el mismo que gobierna las invariantes de
  concurrencia — se re-verificó explícitamente, no se asumió).
- Regresión Fase 2 (`appointments patients accounts doctors clinics`) → 332/332, re-ejecutada
  después del fix.
- H-07 reproducido en vivo (traceback real de `ClinicalEncounter.DoesNotExist` → 500) antes del
  fix, y confirmado en vivo (404 `CLINICAL_RESOURCE_NOT_FOUND`) después — no se infirió del
  código, se ejecutó contra una base de datos real en ambos momentos.
- H-06 reproducido en vivo mediante script ad-hoc: se confirmó que el bypass deja
  `Appointment.status=COMPLETED` con `ClinicalEncounter` inexistente de forma permanente, y que
  `appointments/services/appointment.py` no tiene ningún cambio (`git diff` vacío) — confirmando
  que ADR-020 describe fielmente el estado real del código, no una intención no implementada.

---

## Revisión final de consistencia documental — 2026-09-11

**Rol:** revisor independiente (Senior Software Architect / Tech Lead), sin asumir que el código
es correcto porque la documentación lo afirme, ni viceversa.

**Alcance:** revisión cruzada exhaustiva de toda la documentación de Fase 3 (ADRs 008–020, los
11 documentos de `docs/design/clinical-*`, `docs/phases/phase-3-*`, el informe final propio) y de
los documentos transversales (`requirements.md`, `docs/architecture.md`, `CLAUDE.md`,
`docs/adr/README.md`) entre sí y contra el estado actual real del código, migraciones y tests.

**Método:** ejecución en dos fases explícitas — (1) AUDITORÍA (solo lectura, sin modificar nada)
usando 4 agentes independientes en paralelo, cada uno acotado a un clúster natural de
documentos+código (ciclo de vida de `ClinicalEncounter`; `MedicalRecord`/permisos/seguridad;
servicios/API/UX/pantallas; auditoría/estrategia de pruebas/informe final) — y (2) CORRECCIÓN,
aplicando únicamente cambios mínimos, inequívocos y no arquitectónicos sobre los hallazgos reales
confirmados, seguida de una reverificación completa.

### Clasificación de hallazgos (fase de auditoría)

| Severidad | Cantidad |
|---|---:|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 8 |
| LOW | 7 |
| INFO | 2 |
| **Total** | **18** |

Ningún hallazgo fue CRITICAL: no se encontró ninguna contradicción que describiera una regla de
negocio, invariante de seguridad o de integridad de datos de forma opuesta a la implementada. El
único HIGH fue una contradicción interna dentro de un mismo documento (ver §47 más abajo), no una
discrepancia entre documentación e implementación real.

### Correcciones aplicadas (fase de corrección — 2026-09-11)

Todas las correcciones fueron ediciones de documentación únicamente; ningún archivo de código,
modelo, migración, servicio, vista o test fue modificado en esta revisión (se verificó con
`python manage.py check`, limpio, tras las correcciones).

**Taxonomía de errores (`EncounterImmutable` inexistente):**
- `docs/design/clinical-api-contracts.md` (línea 577, sección del contrato de guardado del
  encuentro): usaba `EncounterImmutable`, nombre que nunca existió en la taxonomía cerrada de
  `clinical-service-contracts.md` §19 ni en el código. Corregido a `EncounterAlreadyCompleted`
  (`ENCOUNTER_COMPLETED`), con nota explicativa.
- `docs/design/clinical-api-contracts.md` (línea 857, tabla de errores): `ENCOUNTER_NOT_ASSIGNED_TO_ACTOR`
  no existe como código de error independiente; se corrigió a `CLINICAL_ACCESS_DENIED`, que es el
  que realmente devuelve la API para ese caso, con nota.
- `docs/design/clinical-service-contracts.md` (SC-065, línea 436): mismo nombre inexistente
  `EncounterImmutable`. Corregido a `EncounterAlreadyCompleted` (SC-136), con nota explicativa.
- `docs/design/clinical-encounter-domain.md` (§17.3, lista de errores de dominio previstos):
  conservaba una lista de nombres candidatos preliminares (incluyendo `EncounterImmutable`) en
  lugar de remitir a la lista cerrada de `clinical-service-contracts.md` §19. Se añadió una nota
  de "Resolución final" que remite explícitamente a §19 como fuente autoritativa. **Verificado en
  esta revisión (2026-09-11):** existe una tercera mención de `EncounterImmutable` en ese mismo
  documento, dentro de la sección 36 ("Errores de dominio previstos"), pero se trata explícitamente
  de una lista de *candidatos preliminares* — la nota de "Resolución final" ya colocada
  inmediatamente después de esa lista aclara que los nombres exactos y finales viven en
  `clinical-service-contracts.md` §19. No constituye una inconsistencia adicional; no requiere
  corrección propia.

**Estado documental de decisiones ya cerradas presentado como pendiente:**
- `docs/design/clinical-security-and-privacy.md` §47: el título de la sección decía "Decisiones
  propuestas para cierre" y las ~20 filas de su tabla decían "Propuesta de cierre", pese a que esas
  mismas decisiones ya están cerradas, implementadas y descritas como tales en el resto del mismo
  documento — una contradicción interna directa. Corregido: título → "Decisiones cerradas", las 20
  filas → "Cerrado" (verificado con `grep -c`: 0 filas "Propuesta de cierre" restantes fuera de la
  nota de corrección que cita el texto anterior).
- `docs/design/clinical-record-domain.md` §15 (tabla resumen): 3 filas sobre permisos de
  médico/paciente/responsable decían "Requiere cierre en permissions", pese a que
  `clinical-permissions.md` ya cierra explícitamente esas reglas (P-011 a P-014). Corregido a
  "Cerrado en `clinical-permissions.md`".
- `docs/design/clinical-record-domain.md` CR-036: decía en futuro "deberá cerrarse formalmente en
  `clinical-permissions.md`" pese a que el propio encabezado de CR-036 ya dice "Cerrado". Corregido
  a tiempo pasado con referencia explícita a P-011–P-014.
- `docs/design/clinical-data-model.md`: DM-028, DM-029, DM-053 y DM-055 mantenían la etiqueta
  **PROPUESTA:** sobre contenido que la implementación ya cierra de forma verificable en el código
  actual. Corregidas a **Cerrado:**. **Verificado en esta revisión (2026-09-11):** el documento
  conserva 8 instancias adicionales de **PROPUESTA:** (DM-004, DM-015, DM-016, DM-018, DM-019 y
  las de los índices DM-089/DM-090, entre `líneas` 71–304 y 1115–1127). Se verificó cada una contra
  el código actual: los 5 campos de `MedicalRecord` listados en DM-015 existen exactamente con esos
  nombres (`medical_records/models.py:189-200`); `Patient.blood_type` y `Patient.allergies` (DM-018/019)
  existen tal como se describen, sin duplicarse en `MedicalRecord`; los índices `(doctor, status)` y
  `(started_at)` de DM-089/DM-090 existen exactamente en `ClinicalEncounter.Meta.indexes`. Ninguna
  de las 8 contradice la implementación. El propio documento declara en su encabezado que la
  etiqueta PROPUESTA "indica que se recomienda convertirla en decisión normativa al cerrar este
  documento" — es decir, es una convención de presentación del documento, no necesariamente una
  señal de obsolescencia. No se relabelaron las 8 restantes: hacerlo sin una discrepancia real que
  lo justifique excedería el mandato de "corrección mínima e inequívoca" de esta revisión.

**Referencias a herramienta de pruebas incorrecta:**
- `docs/phases/phase-3-testing-strategy.md`: 3 referencias a `pytest` (descripción del framework
  en la línea 108, bloque de comandos en la línea 809, requisito de evidencia en la línea 1033),
  cuando el proyecto usa exclusivamente el test runner nativo de Django
  (`python manage.py test`) — `pytest` nunca se instaló ni se usó. Corregidas las 3 referencias.
- `docs/phases/phase-3-testing-strategy.md` TS-106: exigía en tono obligatorio auditar los
  resultados `REJECTED`, lo cual entraba en tensión con AH-024/AH-066 (que lo marcan opcional). Se
  suavizó el tono a "opcional", preservando intacto el invariante real y no negociable: nunca
  registrar `SUCCESS` de forma falsa.

**Taxonomía de acciones de auditoría:**
- `docs/design/clinical-audit-and-history.md` (AH-029 y la tabla de §23): sugerían la existencia
  de un valor de acción `ACCESS_DENIED` independiente, que no existe en el enum real
  `AuditEvent.Action` del código. Corregido para reflejar el comportamiento real: las denegaciones
  se registran con `result=DENIED` sobre la acción realmente intentada (p. ej. `VIEW_RECORD` con
  `result=DENIED`), no como una acción separada.

**Capacidades administrativas futuras presentadas sin aclarar su estado:**
- `docs/design/clinical-permissions.md` (P-040/P-041) y `docs/design/clinical-security-and-privacy.md`
  (SEC-061/062/063): describían acceso administrativo de soporte sin aclarar que es política
  futura, no implementada en Fase 3. Se añadió en ambos una nota de estado explícita ("revisión de
  cierre, 2026-09-11") aclarando que no existe ningún camino de código actual que otorgue ese
  acceso (verificado).

**Alcance de `requirements.md` frente al núcleo mínimo de Fase 3:**
- `requirements.md` §19 ("Resumen clínico para el médico") y §20 ("Alertas clínicas") describen la
  visión completa del producto, más amplia que el núcleo mínimo de Fase 3 realmente implementado.
  Se añadió en ambos una nota de alcance que remite a §44 de `requirements.md` y a
  `docs/architecture.md` §36/§7.8, aclarando explícitamente que `ClinicalAlert` es una entidad
  futura no implementada en esta fase.

**Enlaces y numeración estructural:**
- `docs/phases/phase-3-prompt_programacion.md` línea 64: referenciaba `docs/design/phase-3-clinical-ux.md`
  (ruta inexistente). Corregido a `docs/phases/phase-3-clinical-ux.md`, su ubicación real.
- `docs/phases/phase-3-prompt_programacion.md` línea 89: referenciaba `architecture.md` sin la
  ruta `docs/` real. Corregido a `docs/architecture.md`.
- `docs/adr/README.md` línea 25: decía "Los ADRs 008–019 complementan..." pese a que ADR-020 ya
  existe y ya está indexado en el mismo README (línea 21) desde el cierre de ETAPA 7. Corregido a
  "008–020".

**Cifras del propio informe final:**
- La tabla "Desglose final de `medical_records`" de este mismo informe decía "(192 tests)" en su
  encabezado, desalineado con los 194 tests reales tras el fix de H-07. Corregido a "(194 tests)".
- La misma tabla decía "50/50 en `test_services.py`", cifra desactualizada tras las adiciones de
  ETAPA 4/6. Corregido a "51/51 en `test_services.py` (número final, tras las adiciones de ETAPA
  4/6)".

### Reverificación posterior a las correcciones (2026-09-11)

- `python manage.py check` → limpio, 0 problemas (solo se tocaron archivos `.md`; ningún cambio de
  código).
- Los 13 ADR de Fase 3 (ADR-008 a ADR-020) existen físicamente en `docs/adr/` y están indexados
  correctamente en `docs/adr/README.md`, sin numeración duplicada ni huecos.
- Todas las rutas de documentos referenciadas en `phase-3-prompt_programacion.md` existen tras la
  corrección de las 2 rutas rotas.
- Las 3 menciones restantes de `EncounterImmutable` en todo `docs/design/` quedan correctamente
  anotadas o contextualizadas como se describe arriba; ninguna afirma que sea un nombre vigente en
  la taxonomía cerrada.
- No se introdujo ninguna contradicción nueva por las propias correcciones: cada corrección se
  verificó de forma aislada (`grep` antes/después) antes de continuar con la siguiente.

### Matriz final de consistencia (§21)

Leyenda: ✓ consistente y verificado · ⚠ inconsistencia menor documentada/aceptada (no bloquea) ·
— no aplica a esta decisión.

| Decisión clave | Implementación | Domain | Rules | Workflow | Data | Permisos | Seguridad | Services | API | UX | Pantallas | Audit | Tests | ADR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Estados de `ClinicalEncounter` (solo `IN_PROGRESS`/`COMPLETED`) | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Cardinalidad `Appointment 1 ─ 0..1 ClinicalEncounter` | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | — | — | — | ✓ | ✓ |
| Inicio de consulta: atómico, idempotente, solo médico asignado | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Cierre: 5 campos obligatorios, atómico con `Appointment.COMPLETED` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Sin reapertura/edición/DELETE tras el cierre | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| `MedicalRecord` — `Patient 1 ─ 1`, creación lazy | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Diagnóstico como texto libre (sin CIE-10) | ✓ | ✓ | ✓ | — | ✓ | — | — | — | ✓ | ✓ | — | — | ✓ | ✓ |
| `DoctorPatientRelationship` nunca inferida por operación clínica | ✓ | ✓ | ✓ | — | — | ✓ | — | ✓ | — | — | — | — | ✓ | ✓ |
| Acceso de médico requiere relación activa (P-009/P-010) | ✓ | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Taxonomía de errores clínicos (fuente: SC §19) | ✓ | ⚠ | — | — | — | — | — | ✓ | ✓ | — | — | — | ✓ | — |
| Auditoría vs. historia clínica (entidades separadas) | ✓ | — | — | — | ✓ | — | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ |
| Denegaciones auditadas como `result=DENIED`, no acción separada | ✓ | — | — | — | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ | ✓ | — |
| Acceso administrativo de soporte (P-040/041) | — | — | ⚠ | — | — | ⚠ | ⚠ | — | — | — | — | — | — | — |
| Endpoints legacy de Fase 2 sin restricción clínica (ADR-020) | ⚠ | — | — | — | — | ⚠ | ⚠ | — | ✓ | — | — | — | ✓ | ✓ |
| Estrategia de pruebas: runner real (`manage.py test`, no `pytest`) | ✓ | — | — | — | — | — | — | — | — | — | — | — | ✓ | — |
| Cifras y veredicto del informe final | ✓ | — | — | — | — | — | — | — | — | — | — | — | ✓ | — |

Las dos filas con ⚠ generalizado ("Acceso administrativo de soporte" y "Endpoints legacy de Fase
2") representan decisiones **explícitamente documentadas como pendientes o aceptadas por diseño**,
no contradicciones ocultas: la primera es política futura declarada como tal (nota añadida en esta
revisión); la segunda es la exposición residual ya aceptada en ADR-020 (ver auditoría de hallazgos
HIGH/CRITICAL arriba). Ninguna fila tiene una casilla ✗ (inconsistencia real sin resolver).

### Resultado

```
REVISIÓN FINAL DE CONSISTENCIA DOCUMENTAL — FASE 3

CRITICAL: 0
HIGH: 1
MEDIUM: 8
LOW: 7
INFO: 2

Correcciones aplicadas: 18
Hallazgos pendientes: 0

Consistencia documental:
PASS

Consistencia documentación ↔ implementación:
PASS

¿Documentación apta para cierre de Fase 3?
SI
```

```
READY FOR DOCUMENTARY CLOSURE
```

Esta revisión evalúa exclusivamente la **consistencia documental** de Fase 3 (documentos entre sí
y documentos contra código). No declara el cierre formal de la Fase 3 como tal — esa decisión
corresponde al responsable del proyecto, considerando también la auditoría de hallazgos
HIGH/CRITICAL (sección anterior) y cualquier otro criterio de negocio que no sea puramente
documental.

---

## Corrección — `AuditEvent.actor_id` NULL en `READ_CLINICAL_ENCOUNTER` — 2026-09-11

**Contexto:** durante la ejecución de la suite completa (`python manage.py test`) se observó en
el log de aplicación:

```text
No se pudo registrar el evento de auditoría clínica: READ_CLINICAL_ENCOUNTER

django.db.utils.IntegrityError:
null value in column "actor_id" of relation "medical_records_auditevent"
violates not-null constraint
```

A pesar de esto, la suite terminaba en `OK`, porque `safe_record_event()` capturaba la excepción
y devolvía `None` sin propagarla — el síntoma quedaba oculto detrás de un resultado verde.

**Causa raíz (investigada, no asumida):** se rastreó toda la cadena
`request → usuario autenticado → vista → servicio clínico → servicio de auditoría →
record_event() → AuditEvent.actor`. En los dos puntos de entrada reales
(`medical_records/views.py:ClinicalView`, con `LoginRequiredMixin`, y
`medical_records/api.py:JsonApiView.dispatch`, que rechaza con 401 antes de llamar a cualquier
servicio si `request.user.is_authenticated` es falso) el actor **nunca** puede ser `None` en un
flujo real: ambos exigen sesión autenticada antes de invocar `encounter_service.get_encounter()`
o cualquier otro servicio clínico. Se verificaron también los 17 call sites de
`record_event`/`safe_record_event` en `encounter.py` y `record.py`: ninguno pasa un actor que
pueda ser `None` en un flujo de aplicación real.

El origen real del `IntegrityError` era un test unitario preexistente,
`test_safe_record_event_never_raises` (`medical_records/tests/test_audit.py`), que llamaba
deliberadamente a `safe_record_event(actor=None, ...)` para forzar una falla real y verificar que
`safe_record_event` no la propagaba — es decir, el propio test ejercitaba, a propósito, el único
camino donde `actor=None` llegaba al `INSERT`. El bug real no era un actor perdido en producción,
sino que el helper de auditoría no distinguía entre:

- un fallo genuino del mecanismo auxiliar de persistencia (lo que AH-089 exige tolerar en una
  lectura, para no bloquear la atención clínica), y
- un `actor=None` — que nunca es una condición de negocio válida (AH-086: "el identificador del
  actor se deriva de la sesión autenticada"), sino un bug de contrato del llamador — y que
  `safe_record_event` maquillaba exactamente igual que el primer caso: como una auditoría
  "manejada" que en realidad nunca ocurrió.

**Corrección aplicada:** se añadió una validación explícita de precondición, tanto en
`record_event()` como en `safe_record_event()` (`medical_records/services/audit.py`): si
`actor is None`, se lanza `ValueError` inmediatamente, **antes** de intentar el `INSERT` y
**fuera** del `except Exception` que `safe_record_event` usa para tolerar fallos genuinos del
mecanismo auxiliar. Esto asegura que:

- `actor_id` nunca puede llegar a `NULL` a la base de datos (el `ValueError` ocurre antes del
  `INSERT`, no se depende únicamente del constraint de PostgreSQL como última línea de defensa);
- un actor ausente en una operación clínica autenticada falla de forma explícita e inmediata,
  nunca como un `None` silencioso devuelto por `safe_record_event`;
- una lectura clínica legítima con actor real, ante un fallo *distinto* y genuinamente inesperado
  del mecanismo de persistencia (no relacionado con el actor), sigue sin bloquearse — AH-089 se
  preserva intacto para ese caso.

No se introdujo ningún actor artificial (`UNKNOWN`, `SYSTEM`, `ANONYMOUS`) ni se permitió
`actor_id NULL` en el modelo; el constraint `NOT NULL` de `AuditEvent.actor` permanece exactamente
como estaba.

**Archivos modificados:**
- `medical_records/services/audit.py` — precondición de actor en `record_event()` y
  `safe_record_event()`.
- `medical_records/tests/test_audit.py` — `test_safe_record_event_never_raises` (que asumía que
  `actor=None` debía terminar en éxito silencioso) se sustituyó por
  `test_safe_record_event_raises_on_missing_actor` y se agregó
  `test_record_event_raises_on_missing_actor` (ambos verifican que se lanza `ValueError` y que no
  se persiste ningún `AuditEvent` con `actor` ausente); se agregó
  `test_safe_record_event_still_swallows_unrelated_persistence_failure` (verifica, con un fallo de
  persistencia simulado y no relacionado con el actor, que AH-089 sigue tolerándolo); se reforzó
  `test_authorized_read_is_audited` para verificar explícitamente `actor`, `actor_id`,
  `actor_role` (nunca `UNKNOWN`/`SYSTEM`/`ANONYMOUS`) y `resource_type`/`resource_id` del evento
  `READ_CLINICAL_ENCOUNTER`.

**Verificación de persistencia real (no solo ausencia de fallo en el test):** se ejecutó un
script de reproducción directo contra una base de datos de prueba real (médico autenticado real,
`ClinicalEncounter` real, lectura real vía `encounter_service.get_encounter()`), confirmando:

```text
action        = READ_CLINICAL_ENCOUNTER
result        = SUCCESS
actor_id      = 1
actor (email) = ev-doc@example.com
actor_role    = DOCTOR
resource_type = ClinicalEncounter
resource_id   = 1
```

**Resultado de la suite completa tras la corrección:** `Ran 528 tests — OK`. Se buscó
explícitamente en el log completo la cadena `"No se pudo registrar"`/`IntegrityError`: aparece
una única vez, dentro de `test_safe_record_event_still_swallows_unrelated_persistence_failure`
— el propio test que verifica a propósito, con un fallo simulado y no relacionado con el actor,
que ese caso sigue tolerándose (traza esperada, no un error real). Ninguna otra aparición en toda
la suite.

**Regresión de Fase 2:** la primera corrida completa mostró 1 fallo aislado,
`test_two_concurrent_holds_for_same_slot_only_one_succeeds` (`appointments`), por un deadlock real
de PostgreSQL entre dos procesos concurrentes — un archivo no tocado por esta corrección. Se
verificó que el mismo test pasa de forma consistente en 3 corridas aisladas seguidas, y una
segunda corrida completa de toda la suite (528/528) terminó sin ningún fallo — confirmando que fue
una condición de carga puntual del entorno de pruebas, no una regresión introducida por este
cambio.

### CORRECCIÓN AUDIT EVENT ACTOR

```text
Causa raíz:
safe_record_event() no distinguía un actor=None (bug de contrato del llamador, nunca una
condición de negocio válida per AH-086) de un fallo genuino del mecanismo auxiliar de
persistencia (el único caso que AH-089 exige tolerar). El único lugar del código que pasaba
actor=None era un test unitario que forzaba deliberadamente esa condición para verificar el
comportamiento de tolerancia — no existía ninguna ruta de aplicación real (vista/API) donde el
actor pudiera ser None, porque ambos puntos de entrada exigen autenticación antes de invocar
cualquier servicio clínico.

Archivos modificados:
medical_records/services/audit.py
medical_records/tests/test_audit.py

Cambio realizado:
Precondición explícita (ValueError si actor is None) en record_event() y en
safe_record_event(), evaluada antes del INSERT y fuera del except Exception tolerante —
así el actor ausente nunca llega a la base de datos y nunca se confunde con un fallo
tolerable del mecanismo auxiliar.

Tests agregados/modificados:
test_safe_record_event_raises_on_missing_actor (sustituye a test_safe_record_event_never_raises)
test_record_event_raises_on_missing_actor (nuevo)
test_safe_record_event_still_swallows_unrelated_persistence_failure (nuevo)
test_authorized_read_is_audited (reforzado: actor/actor_id/actor_role/resource_type/resource_id)

manage.py check:
PASS

Migraciones:
PASS (makemigrations --check --dry-run → "No changes detected")

Suite completa:
PASS
Tests: 528/528

Errores de auditoría durante tests:
0 / 528 (fuera del único caso simulado y esperado, ver arriba)

READ_CLINICAL_ENCOUNTER persistido correctamente:
SI

Actor real persistido:
SI

Regresión Fase 2:
PASS

¿Queda algún problema de auditoría conocido?
NO
```

Esta corrección no declara la Fase 3 cerrada por sí misma; se documenta como una corrección
puntual de un bug real de auditoría descubierto durante la ejecución de la suite, verificado con
evidencia reproducible de persistencia real, sin alterar ninguna decisión arquitectónica cerrada
de Fase 3.

---

## Resumen final — Criterios de cierre de Fase 3

Según `phase-3-testing-strategy.md` §41 ("Criterios de release"), Fase 3 no debe declararse
cerrada mientras exista alguno de los siguientes. Verificación final:

| Criterio bloqueante | Estado |
|---|---|
| Un test crítico fallando | ✅ Ninguno — 528/528 |
| Una migración pendiente no intencional | ✅ Ninguna — `makemigrations --check` limpio |
| Violación de integridad Appointment/ClinicalEncounter | ✅ Ninguna en el flujo clínico normal (TS-123-128, ETAPA 3); el único camino teórico queda documentado explícitamente (ADR-020), no oculto |
| Bypass de autorización clínica | ✅ Ninguno — autorización siempre server-side, verificada en las 8 suites |
| Posibilidad de modificar un encuentro `COMPLETED` | ✅ Ninguna (SC-046/AH-048, probado repetidamente en servicios, API, UI y concurrencia) |
| Pérdida demostrable de historia clínica | ✅ Ninguna — sin DELETE funcional en ningún punto del sistema |
| Auditoría falsa de una operación clínica efectiva | ✅ Ninguna (AH-064/065/184; corrección `actor_id` del 2026-09-11 — ver sección dedicada) — éxito solo se audita tras confirmación transaccional real, con actor real siempre persistido |
| Exposición de datos clínicos fuera del contrato | ✅ Ninguna — IDOR, caché, logs y errores verificados |
| Regresión conocida de Agenda sin decisión explícita documentada | ✅ La única regresión conocida (endpoints legacy de Fase 2) está documentada en ADR-020 |

**Evidencia de cierre disponible y reproducible** (§42): salida de `check`, verificación de
migraciones, resultado completo de la suite de pruebas (528/528, tras el fix de H-07 y la
corrección de `AuditEvent.actor_id` — ver secciones dedicadas), resultado de pruebas de
concurrencia (3 corridas estables), resultado de pruebas de seguridad/IDOR, evidencia de
validación real de navegador (17/17, capturas + registro reproducible), y el listado de la única
excepción aceptada (ADR-020) con su justificación — todo documentado en este informe, en los
reportes de cada etapa, y en `docs/phases/evidence/phase-3-browser-validation-2026-09-11/`.

### Veredicto

```
FASE 3 — IMPLEMENTADA
PHASE 3 — READY TO CLOSE
PHASE 3 — NO OPEN HIGH/CRITICAL FINDINGS
READY FOR DOCUMENTARY CLOSURE
```

Todos los criterios de `phase-3-testing-strategy.md` §41 y §46 se cumplen, incluida la evidencia
de navegador real que quedaba pendiente, la auditoría independiente de hallazgos HIGH/CRITICAL
(2026-09-11 — ver sección dedicada arriba): 0 CRITICAL abiertos, 0 HIGH abiertos (un hallazgo
histórico, H-06, permanece con exposición técnica residual documentada en ADR-020 pero no bloquea
el cierre por decisión arquitectónica ya aprobada; un hallazgo nuevo, H-07, fue encontrado y
corregido en la misma auditoría, con evidencia y tests permanentes), y la revisión final de
consistencia documental (2026-09-11 — ver sección dedicada arriba): 18 hallazgos documentales
reales detectados y corregidos (0 CRITICAL, 1 HIGH, 8 MEDIUM, 7 LOW, 2 INFO), 0 pendientes; y la
corrección del hallazgo `AuditEvent.actor_id` (2026-09-11 — ver sección dedicada arriba): un
`IntegrityError` real, detectado durante la ejecución de la suite y oculto por un `except`
demasiado permisivo, fue investigado hasta su causa raíz real (un test que forzaba
deliberadamente `actor=None`, no una fuga de identidad en producción) y corregido con una
precondición explícita que impide que `actor_id` llegue nulo a la base de datos, verificada con
persistencia real y sin afectar Fase 2. No hay commits realizados en el repositorio para este
trabajo — queda pendiente de confirmación explícita del usuario antes de integrarse a `main`.

**Esta revisión no declara la Fase 3 formalmente cerrada.** Los bloques anteriores certifican que
la implementación, la evidencia de validación, la documentación y la integridad de la auditoría
clínica están, cada una en su propio ámbito, en condiciones de cierre — pero la decisión final de
cerrar formalmente la Fase 3 corresponde al responsable del proyecto.

---

## Cierre formal de Fase 3 — 2026-09-11

El responsable del proyecto ha revisado y validado los puntos previos del proceso de cierre
(estado de Git, validaciones técnicas, cambios realizados) y ha instruido el cierre documental
formal de Fase 3. Esta sección registra esa decisión y consolida, sin repetir el detalle ya
documentado arriba, el estado real verificado al momento del cierre:

| Criterio | Resultado |
|---|---|
| `python manage.py check` | ✅ PASS |
| Migraciones (`makemigrations --check --dry-run`) | ✅ PASS — "No changes detected" |
| `migrate --plan` | ✅ PASS — sin operaciones pendientes |
| Suite completa (`python manage.py test`) | ✅ PASS — 528/528 |
| Regresión Fase 2 | ✅ PASS |
| Concurrencia | ✅ PASS (3 corridas estables, ETAPA 3 y ver corrección `actor_id`) |
| Seguridad (IDOR, caché, exposición de datos) | ✅ PASS |
| Auditoría clínica | ✅ PASS (H-07 y `AuditEvent.actor_id` corregidos y verificados con evidencia de persistencia real) |
| Validación real de navegador | ✅ PASS — 17/17 (`docs/phases/evidence/phase-3-browser-validation-2026-09-11/`) |
| Hallazgos HIGH/CRITICAL abiertos | ✅ 0 (H-06 documentado en ADR-020 como exposición residual aceptada por decisión arquitectónica, no bloqueante) |
| Consistencia documental | ✅ PASS (18 hallazgos detectados y corregidos, 0 pendientes) |

Ningún resultado de esta tabla es nuevo: todos provienen de las secciones anteriores de este
mismo informe (ETAPA 0-7, validación de navegador, auditoría de hallazgos HIGH/CRITICAL, revisión
de consistencia documental, corrección de `AuditEvent.actor_id`), reproducidas aquí solo como
consolidado final. No se ejecutó ninguna validación nueva ni se modificó implementación, modelos,
servicios, API, permisos, seguridad, UI, tests ni migraciones para este cierre — es exclusivamente
un cierre documental.

### Veredicto final

```
FASE 3 — IMPLEMENTADA
PHASE 3 — CLOSED
```

Fase 3 (Gestión clínica) queda formalmente cerrada. La implementación terminó, la suite completa
de pruebas pasa en su totalidad (528/528), las migraciones están limpias, seguridad y permisos
fueron validados, la auditoría clínica fue validada (incluida la corrección de su último hallazgo
real), la concurrencia fue validada, y no existen hallazgos HIGH/CRITICAL abiertos. La siguiente
fase del proyecto es **Fase 4 — Documentos**, según la secuencia ya definida en `CLAUDE.md` y
`requirements.md`; su diseño e implementación no forman parte de este cierre.

# Informe final — Fase 2: Agenda

Fecha: 2026-09-10

## 1. Resumen de arquitectura

Se implementó siguiendo estrictamente la capa establecida en `docs/architecture.md` §28 y `docs/design/agenda-service-contracts.md` §2.1:

```
View (UI, server-rendered)  ─┐
                              ├─→ Domain Service → Authorization → Transaction → ORM/PostgreSQL
API View (JSON, api.py)     ─┘
```

- **`appointments`** es una app Django nueva, separada de `patients`/`doctors`/`clinics` (Fase 1), tal como exige `docs/architecture.md`.
- Tres servicios de dominio, sin `AgendaService` monolítico: `AvailabilityService`, `HoldService`, `AppointmentService` (`appointments/services/{availability,hold,appointment}.py`).
- Autorización centralizada y reutilizable en `appointments/services/permissions.py`, que a su vez reutiliza los mecanismos de Fase 1 (`patients.services.permissions.responsible_has_active_relationship`) en vez de duplicarlos — exigencia explícita de `agenda-service-contracts.md` §12.
- Taxonomía de errores de dominio (`appointments/services/exceptions.py`, 32 excepciones) en las categorías obligatorias: Authorization, Availability, Hold, Appointment, Concurrency, Idempotency.
- Dos capas de presentación, ambas llamando a los mismos servicios: un **API JSON** (`appointments/api.py`, sin Django REST Framework — no había justificación para una dependencia nueva) y una **UI server-rendered** (`appointments/views.py` + templates), con una única excepción deliberada: el flujo de reserva/reprogramación usa JS mínimo (`static/js/agenda-*.js`) para hablar con el API JSON, porque el grid de slots y la cuenta regresiva del hold de 15 minutos genuinamente necesitan actualización en vivo.
- PostgreSQL como autoridad final de concurrencia: `ExclusionConstraint` (con `BtreeGistExtension`) para solapamientos de `Availability`/`Hold`/`Appointment`, `select_for_update()` + `transaction.atomic()` en toda operación mutadora, savepoints anidados donde una excepción capturada necesitaba seguir consultando la misma transacción.

## 2. Modelos

`appointments/models.py` (4 modelos):

- **`Availability`** — `doctor` + `clinic` + `date` + `start_time`/`end_time`, `start_at`/`end_at`/`period` computados en `save()`, `duration_minutes` tomado de `DoctorClinic`, `is_active` (soft-delete). `ExclusionConstraint` doctor-only (un médico no puede tener disponibilidad simultánea en dos consultorios).
- **`Hold`** — `user`, `doctor`, `clinic`, `availability`, `start_at`/`end_at`, `status` (ACTIVE/EXPIRED/RELEASED/CONSUMED, sin default), `expires_at`. Un hold activo por usuario (`UniqueConstraint`); `ExclusionConstraint` sobre holds activos, sin incluir `expires_at` (no es IMMUTABLE) — la expiración se aplica de forma perezosa dentro de transacciones bloqueadas.
- **`Appointment`** — `patient`/`doctor`/`clinic`/`availability`, `start_at`/`end_at`/`duration_minutes` (congelada), `status` (SCHEDULED/IN_CONSULTATION/COMPLETED/CANCELLED/NO_SHOW, únicamente estos cinco), `created_by`, `idempotency_key`, trazas de cancelación/no-show/inicio/fin. Dos `ExclusionConstraint` independientes (médico y consultorio) sobre estados ocupantes.
- **`AppointmentRescheduleHistory`** — un registro por reprogramación; `RESCHEDULED` nunca es un estado de `Appointment`. `UniqueConstraint` de idempotencia por `(rescheduled_by, idempotency_key)`.

Además, `clinics/models.py` se extendió (Etapa 1) con `Clinic.timezone` (+ propiedad `zoneinfo`) y `DoctorClinic.appointment_duration_minutes`.

## 3. Migraciones

- `clinics/migrations/0002_clinic_timezone_and_more.py` — añade `timezone` y `appointment_duration_minutes`.
- `appointments/migrations/0001_initial.py` — los 4 modelos, todos sus constraints, y `BtreeGistExtension()` como primera operación (requisito de PostgreSQL para `ExclusionConstraint` con igualdad sobre columnas no-rango).

`python manage.py makemigrations --check --dry-run` confirma que no faltan migraciones (resultado en §9).

## 4. Servicios

| Servicio | Funciones |
|---|---|
| `AvailabilityService` | `create_availability`, `update_availability`, `deactivate_availability`, `get_available_slots` |
| `HoldService` | `create_hold`, `release_hold`, `mark_consumed` |
| `AppointmentService` | `create_appointment_from_hold`, `cancel_appointment`, `reschedule_appointment`, `start_appointment`, `complete_appointment`, `mark_no_show`, `list_appointments_for_actor`, `get_appointment_detail` |

Reglas de negocio implementadas íntegramente en esta capa: horizonte de 6 meses calendario, gracia de 30 min de reserva tardía, hold de 15 min con expiración perezosa, duración congelada, "primera cita sin `DoctorPatientRelationship`" (verificado con test dedicado), idempotencia real (`Idempotency-Key`) en creación de cita y reprogramación con reintentos concurrentes probados.

## 5. Endpoints

API JSON completo en `appointments/urls.py` (prefijo `/api/`), 14 endpoints — todos los definidos en `agenda-api-contracts.md`, ninguno inventado: `POST/PATCH /availability/`, `POST /availability/{id}/deactivate/`, `GET /availability/slots/`, `POST /holds/`, `POST /holds/{id}/release/`, `POST|GET /appointments/`, `GET /appointments/{id}/`, `POST /appointments/{id}/{cancel|reschedule|start|complete|no-show}/`. Traducción de errores de dominio a HTTP siguiendo §13/§14 (401/403/404/409/422/400) con formato `{"error": {"code", "message"}}`.

UI en `appointments/urls_ui.py` (prefijo `/agenda/`), 14 rutas: agenda del médico, disponibilidad (crear/editar/desactivar), reserva interactiva, reprogramación interactiva, mis citas, selector de pacientes del responsable, selector de médico del administrador, detalle de cita, cancelación, iniciar/finalizar/no-show.

## 6. Permisos

Matriz completa implementada en `appointments/services/permissions.py`, verificada por servicio y por endpoint:

- **Paciente**: solo para sí mismo; nunca administra disponibilidad ni opera consultas.
- **Responsable**: solo pacientes con `ResponsiblePatientRelationship.ACTIVE`.
- **Médico**: `DoctorClinic` válida basta para crear la primera cita de cualquier paciente (sin `DoctorPatientRelationship` previa, verificado); nunca administra la disponibilidad de otro médico; único actor que puede iniciar/finalizar consulta o marcar `NO_SHOW`.
- **Administrador**: acceso funcional global (`user.is_superuser`, ADR-004 §8) + `DoctorClinic` válida como precondición operativa (no como ámbito territorial); nunca inicia, finaliza ni marca `NO_SHOW`.

Dos contradicciones documentales reales se detectaron y corrigieron antes de programar (ver §12), siguiendo la jerarquía `phase-2-agenda.md` → resto de docs de diseño.

## 7. Tests

**186 tests** en la app `appointments`, distribuidos por etapa:

| Archivo | Tests | Cubre |
|---|---|---|
| `test_models.py` | 25 | Constraints e integridad de los 4 modelos |
| `test_availability_service.py` | 20 | Crear/modificar/desactivar disponibilidad, slots |
| `test_hold_service.py` | 20 | Hold: creación, liberación, expiración perezosa, **concurrencia real** |
| `test_appointment_service.py` | 19 | Creación desde hold, idempotencia, **concurrencia real**, primera cita sin relación (test obligatorio) |
| `test_appointment_cancel_reschedule.py` | 26 | Cancelación, reprogramación, historial, **concurrencia real** |
| `test_appointment_clinical_ops.py` | 21 | Iniciar/finalizar/NO_SHOW, **concurrencia real** |
| `test_api.py` | 32 | Los 14 endpoints JSON: auth, autorización, formato, conflictos, idempotencia |
| `test_ui.py` | 23 | Las 14 vistas server-rendered: permisos, flujos completos |

Incluye los **tests obligatorios** exigidos al inicio: médico crea primera cita sin `DoctorPatientRelationship` previa (verificado que la relación NO se crea), y pruebas de **concurrencia real con hilos y conexiones de BD independientes** (no solo secuenciales) para: dos usuarios compitiendo por el mismo hold, dos solicitudes idénticas creando la misma cita (retry), dos reprogramaciones simultáneas al mismo destino, y doble clic simultáneo en "Iniciar consulta" — en todos los casos PostgreSQL previno el estado inconsistente.

Además, se hizo una **verificación manual en navegador real** (servidor de desarrollo + sesión autenticada real) del flujo completo: reservar → ver en agenda del médico → iniciar consulta → finalizar consulta, confirmando que el API JSON y el JS que lo consume funcionan end-to-end fuera del entorno de test.

## 8. Resultado de `python manage.py check`

```
System check identified no issues (0 silenced).
```

## 9. Resultado de `python manage.py makemigrations --check --dry-run`

```
No changes detected
```

## 10. Resultado completo de `python manage.py test`

```
Ran 332 tests in ~200s
OK
System check identified no issues (0 silenced).
```

332 = 186 de `appointments` + 146 de Fase 1 (`accounts`, `patients`, `doctors`, `clinics`), todos verdes. Ningún test de Fase 1 se rompió.

## 11. Deuda técnica (backlog no bloqueante)

- **Selección de paciente para médico/administrador en la reserva**: sin un buscador de pacientes por nombre, se usa un campo de ID numérico simple (`patients:patient_list` es doctor-only y ya filtrado a pacientes con relación activa, así que no sirve para encontrar un paciente *nuevo*). Funcionalmente correcto, no pulido.
- **Paginación de `GET /api/appointments/`**: usa números de página (`next`/`previous`), no URLs completas — el contrato solo exige "metadatos suficientes para navegar", sin especificar formato.
- **No se verificó visualmente en navegador con extensión conectada** la cuenta regresiva del hold ni la interacción de clics en el grid de slots (el entorno no tenía la extensión de Chrome disponible); sí se verificó la lógica completa vía API real + sintaxis JS.
- **Sin auditoría de acceso administrativo a datos clínicos** — gap conocido y heredado de Fase 1 (Fase 6), no específico de Agenda.

Ninguno de estos puntos bloquea el cierre de Fase 2: son mejoras de calidad/pulido, no reglas de negocio incumplidas ni brechas de integridad/seguridad.

## 12. Decisiones y correcciones tomadas (no pendientes — ya resueltas y documentadas)

### Ronda de implementación (2026-09-09/10)

1. `agenda-permissions.md` afirmaba dos veces que "el administrador NO tiene acceso global", contradiciendo `ADR-004` §8 (ya aceptado). Corregido a favor del ADR.
2. `agenda-service-contracts.md` §5.2 se autocontradecía sobre si una disponibilidad con citas puede modificarse; se resolvió a favor de la lectura más matizada del documento rector (`phase-2-agenda.md` §5.6): una modificación *compatible* (que sigue conteniendo las citas existentes) se permite; una incompatible se rechaza con el nuevo error `AvailabilityHasIncompatibleAppointments`. **Confirmado explícitamente por el usuario en la ronda de cierre (2026-09-10): se mantiene.**

### Ronda de cierre (2026-09-10) — auditoría final solicitada por el usuario

3. **Idempotencia de Hold eliminada del contrato.** `agenda-api-contracts.md` §6.1 exigía un header `Idempotency-Key` en `POST /api/holds/` que nunca tuvo efecto real: §8/§15 (las secciones normativas de idempotencia) solo cubren creación de cita y reprogramación, y `Hold` no tiene campo `idempotency_key`. Se eliminó del contrato con nota explicativa; un reintento que pierde el slot contra sí mismo recibe `HOLD_CONFLICT`, comportamiento esperado dado que el hold ya es en sí una protección temporal de 15 minutos. Código actualizado (`appointments/api.py`) para reflejar la decisión — no hubo cambio de comportamiento, solo de documentación/comentario, ya que el header nunca se usaba.
4. **Auditoría exhaustiva de ADR-004 §8 vs. todos los documentos de Fase 2.** La corrección de la ronda anterior había quedado incompleta: solo se habían corregido los dos pasajes más visibles de `agenda-permissions.md`, pero el lenguaje de "ámbito administrativo por clínica" seguía apareciendo — de forma contradictoria con el acceso global ya decidido — en **9 archivos adicionales**, incluido el propio documento rector (`docs/phases/phase-2-agenda.md`, que en una sección llegaba a advertir explícitamente *contra* tratar el acceso del administrador como global) y en `requirements.md`, la fuente de verdad funcional del proyecto. Se corrigieron todas las apariciones para que la única interpretación posible en todo el proyecto sea: el Administrador tiene acceso funcional global (`user.is_superuser`, ADR-004 §8), sin restricción territorial por clínica; `DoctorClinic` válida es la única precondición operativa adicional para cualquier operación sobre un médico/consultorio concreto. Archivos corregidos: `docs/phases/phase-2-agenda.md`, `docs/design/agenda-permissions.md`, `docs/design/agenda-service-contracts.md`, `docs/design/agenda-api-contracts.md`, `docs/phases/phase-2-agenda-ux.md`, `docs/design/appointment-domain.md`, `docs/architecture.md`, `CLAUDE.md`, `requirements.md`. Ningún cambio de código fue necesario para este punto: la implementación (`appointments/services/permissions.py`) ya era consistente con el acceso global desde la Etapa 2 — el problema era exclusivamente documental.

Todas las correcciones quedaron registradas en los propios documentos con nota de fecha y justificación, no solo en este informe.

---

## FASE 2 — COMPLETADA

Dominio, hold/reserva, gestión de cita, operación médica, API JSON y UI están implementados, probados (332/332 tests) y documentalmente consistentes — incluida la auditoría final de la única decisión arquitectónica que tuvo divergencias entre documentos (alcance del Administrador, ADR-004 §8). Las deudas listadas en §11 quedan registradas como backlog no bloqueante para una iteración futura, no como trabajo pendiente de esta fase.

**Nota final:** el trabajo de implementación de Fase 2 ya está commiteado (`0a159e1`). Las correcciones de esta ronda de cierre (Pasos 1-4) están en el árbol de trabajo, pendientes de commit — 9 archivos modificados, todos documentación salvo un comentario en `appointments/api.py`.

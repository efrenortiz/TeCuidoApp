# ADR-020 — Fase 2's Direct Appointment Transition Endpoints Remain Unrestricted

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Arquitectura / Frontera Agenda-Clínica

## 1. Contexto

`appointments.services.appointment.start_appointment()` y `complete_appointment()` (y sus vistas UI `AppointmentStartView`/`AppointmentCompleteView`, Fase 2) transicionan `Appointment` `SCHEDULED → IN_CONSULTATION` y `IN_CONSULTATION → COMPLETED` de forma independiente, sin crear ni exigir un `ClinicalEncounter`.

Fase 3 (ADR-009/ADR-010) estableció que el flujo clínico normal transiciona `Appointment` y `ClinicalEncounter` de forma atómica, a través de `medical_records.services.encounter.start_encounter()`/`complete_encounter()`, que internamente reutilizan las funciones de Fase 2 dentro de su propia transacción.

Al implementar la UI de Fase 3 (Etapa 5), se descubrió que las vistas/URLs originales de Fase 2 siguen siendo alcanzables directamente y, si se invocan así, producen exactamente la combinación que ADR-009/010 buscan evitar en el flujo clínico normal: una `Appointment` `IN_CONSULTATION` sin `ClinicalEncounter`, o `COMPLETED` sin haber cerrado un encuentro clínico.

## 2. Restricción arquitectónica que impide la solución "obvia"

La solución más directa —que `start_appointment()`/`complete_appointment()` verifiquen la existencia de un `ClinicalEncounter` antes de proceder— exigiría que `appointments` importara `medical_records`, invirtiendo la dependencia unidireccional fijada por ADR-008 (`medical_records` depende de `appointments`, nunca al revés). Esa inversión es un cambio arquitectónico mayor, no una corrección de alcance de Fase 3, y no se toma aquí.

## 3. Decisión

Las vistas y servicios originales de Fase 2 (`start_appointment`, `complete_appointment`, `AppointmentStartView`, `AppointmentCompleteView`) permanecen sin modificar y siguen siendo operaciones de Agenda legítimas y autosuficientes:

- Autorización: sin cambios — siguen exigiendo `is_assigned_doctor`, exactamente igual que antes de Fase 3.
- No se agrega ninguna dependencia de `appointments` hacia `medical_records`.
- La UI de Fase 3 (`templates/appointments/appointment_detail.html`) ya NO enlaza a estas vistas para iniciar/completar consultas — el único camino expuesto al usuario es el flujo clínico (`medical_records`), que sí garantiza la atomicidad Appointment+ClinicalEncounter.
- Los tests de Fase 2 que ejercitan estas vistas directamente (`appointments/tests/test_ui.py::test_start_complete_no_show_actions`) se mantienen intactos como verificación de que Agenda sigue funcionando de forma independiente.

## 4. Consecuencias aceptadas

- Es técnicamente posible, mediante una solicitud HTTP directa (no a través de ninguna pantalla de la aplicación), transicionar una `Appointment` a `IN_CONSULTATION` o `COMPLETED` sin que exista un `ClinicalEncounter` correspondiente. Quien lo haga debe ser, en todo caso, el médico asignado — no es un bypass de autorización, es un bypass del flujo clínico recomendado.
- Esta posibilidad queda documentada como una **regresión conocida y aceptada explícitamente**, según el criterio de cierre de `phase-3-testing-strategy.md` §41 ("regresión conocida de Agenda sin decisión explícita documentada" bloquea el cierre; **con** decisión documentada, no lo hace).

## 5. Alternativas rechazadas

- **Invertir la dependencia de apps** (que `appointments` importe `medical_records`): rechazada por romper ADR-008 sin justificación suficiente para un caso de uso marginal.
- **Duplicar la lógica de transición dentro de `medical_records` y deprecar las funciones de Fase 2**: rechazada por "no reescribas Fase 2" (regla explícita del prompt de programación de Fase 3) y por introducir dos implementaciones del mismo efecto de negocio (SC-001/SC-008, evitar duplicación).
- **Eliminar las URLs/vistas de Fase 2**: rechazada — rompería `appointments/tests/test_ui.py` y cualquier integración futura que legítimamente necesite operar Agenda sin el módulo clínico activo.

## 6. Evolución futura

Si una fase posterior determina que este bypass representa un riesgo operativo real (no solo teórico), la solución preferida es un mecanismo explícito de bajo acoplamiento — por ejemplo, un hook/registro que `appointments` exponga y que `medical_records` complete en su `AppServiceConfig.ready()`, sin que `appointments` importe `medical_records` directamente. No se implementa en Fase 3 por no tener una necesidad real demostrada (CLAUDE.md §12/§14 — evitar sobreingeniería, no construir infraestructura sin necesidad).

## 7. Relación

Complementa ADR-008 y ADR-009; no los modifica.

## 8. Estado

**Accepted.**

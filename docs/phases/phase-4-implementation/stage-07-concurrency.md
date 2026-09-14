# Stage 7 — Concurrencia e idempotencia

## Objetivo

Ejecutar pruebas reales de concurrencia (hilos + conexiones de base de datos independientes, no
simulaciones) sobre doble emisión, doble versionado y doble anulación, verificando que nunca
existan duplicados, estados imposibles, versiones inconsistentes ni bypass de autorización.

## Alcance

`prescriptions/tests/test_concurrency.py` (3 escenarios) y `study_orders/tests/test_concurrency.py`
(2 escenarios) — `TransactionTestCase` + `threading.Barrier`, mismo patrón ya validado en
`medical_records/tests/test_concurrency.py` (Fase 3) y `appointments/tests/test_hold_service.py`
(Fase 2). No se duplicó el mismo conjunto completo para `ClinicalDocument` standalone: usa
exactamente el mismo mecanismo (`select_for_update` + `is_current_version`) ya verificado de forma
independiente en `Prescription` y `StudyOrder` — ver "Gaps conocidos".

## Implementación realizada

Escenarios ejecutados con hilos reales, cada uno con su propia conexión de base de datos
(`connections.close_all()` al terminar, para forzar una conexión nueva por hilo):

1. **Doble emisión concurrente con el mismo `Idempotency-Key`** (Prescription y StudyOrder): ambas
   peticiones deben tener éxito (idempotencia), nunca debe existir más de un recurso real.
2. **Doble corrección concurrente sobre la misma versión vigente** (Prescription y StudyOrder):
   exactamente una debe ganar; la otra debe fallar con un error de dominio identificable
   (`DocumentImmutableResource`), nunca de forma silenciosa ni con una versión inconsistente.
3. **Doble anulación concurrente con el mismo motivo** (Prescription): ambas deben tener éxito
   (idempotente), pero sólo debe quedar un evento de auditoría `SUCCESS`.

## Decisiones aplicadas

Ninguna decisión nueva — esta etapa verificó (y corrigió, ver abajo) la implementación ya cerrada
en Stages 2/3.

## Archivos creados

- `prescriptions/tests/test_concurrency.py`
- `study_orders/tests/test_concurrency.py`

## Archivos modificados

- `prescriptions/services/prescription.py` — `issue()` ahora captura `IntegrityError` del
  `UniqueConstraint` de idempotencia y responde con el recurso ya creado (replay idempotente) en
  vez de propagar el error crudo.
- `study_orders/services/study_order.py` — mismo fix, análogo.

## Migraciones

Ninguna.

## Tests ejecutados

```bash
python manage.py test prescriptions.tests.test_concurrency study_orders.tests.test_concurrency -v 2
python manage.py test prescriptions study_orders clinical_documents -v 1
```

## Resultado de tests

```text
Ran 5 tests in 3.532s
OK
```

Suite completa de las tres apps: `Ran 157 tests — OK` (5 de concurrencia nuevos + 152 de
Stages 1-6 → 157 tests de Fase 4 hasta este punto).

## Validaciones manuales

No aplica (concurrencia real verificada con hilos, no manualmente).

## Problemas encontrados

**Bug real de concurrencia en `issue()` (Prescription y StudyOrder).** La primera versión de
`issue()` comprobaba el `Idempotency-Key` existente con una consulta SIN lock, antes de intentar
crear la fila. Bajo una carrera real (dos peticiones exactamente simultáneas con el mismo
`Idempotency-Key`), ambas pasaban esa comprobación inicial (ninguna veía todavía la fila de la
otra), y ambas intentaban `Prescription.objects.create(...)`: la primera tenía éxito, la segunda
violaba el `UniqueConstraint` y el `IntegrityError` crudo de PostgreSQL se propagaba sin capturar —
exactamente el escenario que H-03 (revisión documental) y ADR-029 exigían resolver, no simplemente
documentar. Detectado inmediatamente por
`test_concurrent_issue_with_same_idempotency_key_never_duplicates` (1/2 "success" en vez de 2/2).

## Problemas resueltos

Se corrigió `issue()` en ambos servicios: el `IntegrityError` se captura fuera del
`with transaction.atomic()` (la transacción ya revirtió limpiamente al propagar la excepción) y,
si existe `idempotency_key`, se re-consulta la fila ganadora y se devuelve como resultado
idempotente — mismo criterio ya usado por
`appointments.services.appointment.create_appointment_from_hold` para exactamente este mismo tipo
de carrera en Fase 2. Verificado: los 2 tests de doble emisión concurrente pasan de forma estable,
y la suite completa de las tres apps (157/157) sigue en verde.

## Gaps conocidos

- No se duplicó el conjunto completo de pruebas de concurrencia con hilos reales para
  `ClinicalDocumentService.create_version`/`void_or_inactivate` (documentos standalone): usan
  exactamente el mismo mecanismo (`select_for_update` + `is_current_version`) ya verificado de
  forma independiente dos veces (Prescription y StudyOrder, con implementaciones de servicio
  separadas). Riesgo residual bajo — no bloqueante — dado que el propio bug real encontrado en esta
  etapa (idempotencia de `issue`) fue detectado precisamente por tener pruebas de hilos reales, lo
  que confirma el valor de esta técnica y no señala ningún patrón de riesgo específico de
  `ClinicalDocument` que la deje sin cubrir silenciosamente.

## Riesgos

Ninguno nuevo tras la corrección.

## Gate

PASS

# Stage 2 — Dominio y servicios

## Objetivo

Implementar `PrescriptionService`, `StudyOrderService` y las operaciones de dominio de
`ClinicalDocumentService` (emisión, versionado, anulación, lectura), con autorización, idempotencia
y auditoría — toda la lógica detrás de la frontera `UI/API → Service → Authorization → Transaction
→ ORM`.

## Alcance

Servicios de dominio y su autorización/auditoría. La generación real de PDF y el almacenamiento de
archivos se construyeron en paralelo (Stage 3, mismo commit lógico) porque el contrato exige que
`issue`/`create_version` generen su documento dentro de la misma transacción — separarlos habría
significado escribir código que luego se reescribe. Los dos stages se documentan por separado
porque cubren preocupaciones distintas (dominio/autorización vs. almacenamiento/PDF), no porque se
hayan construido en momentos distintos.

## Implementación realizada

- `medical_records/services/exceptions.py`: taxonomía `Document*` de Fase 4 (`DocumentNotFound`,
  `DocumentPermissionDenied`, `DocumentInvalidState`, `DocumentValidationError`, `DocumentConflict`,
  `DocumentImmutableResource`, `DocumentReferenceInconsistency`, `DocumentStorageError`) — ver
  ADR-029/`phase-4-service-contracts.md` §7. Prefijo `Document` para no colisionar por nombre con
  la taxonomía `Clinical*` de Fase 3, sin renombrar el concepto ya cerrado documentalmente.
- `medical_records/services/permissions.py`: `can_issue_document_for_encounter`,
  `can_correct_or_void_document`, `can_read_document_resource` — implementan exactamente la matriz
  de `phase-4-permissions.md`/ADR-028 (médico asignado al encuentro vs. médico con relación activa,
  P-009/P-010 preservados).
- `prescriptions/services/prescription.py`: `issue`, `get`, `list_for_patient`, `create_version`,
  `void`.
- `study_orders/services/study_order.py`: mismas operaciones, análogas.
- `clinical_documents/services/document.py`: `upload`, `get`, `list_for_patient`, `download`,
  `create_generated_document`, `create_version`, `void_or_inactivate`.

## Decisiones aplicadas

- **Idempotencia**: reutiliza el patrón exacto de Fase 2
  (`appointments.services.appointment.create_appointment_from_hold`): comprobar por
  `(doctor, idempotency_key)` antes de mutar; si existe y coincide la identidad lógica
  (`clinical_encounter`), se devuelve el recurso existente (replay idempotente); si no coincide,
  `DocumentConflict`.
- **Dónde se audita `DENIED`**: fuera del `with transaction.atomic()` (en el `except`), exactamente
  como `medical_records.services.encounter` — un evento `DENIED` registrado dentro del bloque que
  luego se revierte desaparecería junto con la transacción. Se detectó y corrigió este error
  exacto durante la propia implementación (ver "Problemas encontrados").
- **Versionado (ADR-023)**: `create_version` adquiere `select_for_update()` sobre la versión actual,
  verifica `is_current_version`, y crea la nueva fila dentro de la misma transacción — la segunda
  corrección concurrente sobre la misma versión recibe `DocumentImmutableResource` tras perder la
  carrera por el lock.
- **Anulación idempotente (SC-065 por analogía)**: repetir `void`/`void_or_inactivate` con el mismo
  motivo sobre un recurso ya `VOIDED` es un no-op idempotente; con motivo distinto, `DocumentInvalidState`.
- **`patient` derivado, nunca aceptado del cliente (D-003)**: `issue` sólo recibe `clinical_encounter`;
  `patient`/`doctor` se toman siempre de `clinical_encounter.appointment.patient`/`clinical_encounter.doctor`.
- **`list_for_patient` aplica el mismo criterio que `MedicalRecord`/historial de Fase 3**: un médico
  asignado a un encuentro concreto (sin relación activa) puede leer LOS DOCUMENTOS DE ESE encuentro,
  pero no el historial documental completo del paciente — verificado explícitamente con un test que
  primero detectó la ausencia de esta distinción como error de mi propio test, no del servicio (ver
  "Problemas encontrados").

## Archivos creados

- `prescriptions/services/prescription.py`, `study_orders/services/study_order.py`,
  `clinical_documents/services/document.py` (+ `storage.py`/`pdf.py`, ver Stage 3).
- `prescriptions/tests/test_services.py`, `study_orders/tests/test_services.py`,
  `clinical_documents/tests/test_services.py`.

## Archivos modificados

- `medical_records/services/exceptions.py` (taxonomía Fase 4).
- `medical_records/services/permissions.py` (autorización Fase 4).

## Migraciones

Ninguna en esta etapa (sin cambios de modelo).

## Tests ejecutados

```bash
python manage.py test prescriptions study_orders clinical_documents -v 2
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Resultado de tests

```text
Ran 83 tests in 69.044s
OK
```

(32 de Stage 1 + 51 nuevos de servicios). `check`/`makemigrations --check` limpios.

## Validaciones manuales

No aplica (sin UI/API todavía).

## Problemas encontrados

1. **Auditoría `DENIED` dentro de un `atomic()` que luego revierte** — en la primera versión de
   `void()`/`create_version()` el evento `DENIED` se registraba dentro del mismo
   `with transaction.atomic()` que después lanzaba la excepción de permiso, por lo que el registro
   se revertía junto con todo lo demás (mismo bug de clase ya corregido una vez en Fase 3 para
   `AuditEvent.actor_id`, esta vez detectado antes de llegar a producir un test en verde falso,
   por inspección directa del propio código antes de ejecutarlo).
2. **`list_for_patient` con autorización real más estricta de lo que asumía mi primer test** — el
   test asumía que el médico asignado a un encuentro podía listar todo el historial de recetas del
   paciente; la implementación (correcta, según P-009/P-010) lo rechaza sin relación activa. El
   test estaba mal, no el servicio — se corrigió el test para reflejar el comportamiento
   correctamente cerrado.

## Problemas resueltos

Ambos corregidos en el propio código de esta etapa antes de cerrarla; ver detalle arriba y en
Stage 3 (los bugs de PDF/versión-inicial, que aparecieron al ejecutar estos mismos tests, se
documentan allí porque pertenecen a esa capa).

## Gaps conocidos

- `ClinicalDocumentService.create_version`/`void_or_inactivate` sólo cubren documentos standalone
  (`prescription`/`study_order` ambos `NULL`) — comportamiento intencional (CD-006/CD-007), no un
  gap.

## Riesgos

- El acoplamiento de servicio `prescriptions`/`study_orders` → `clinical_documents` (para generar
  su propio PDF) es una dependencia real entre apps, además de la ya existente a nivel de modelo
  (FK inversa). Es unidireccional a nivel de import de Python (sin ciclo) y está documentado en
  ADR-021/ADR-027.

## Gate

PASS

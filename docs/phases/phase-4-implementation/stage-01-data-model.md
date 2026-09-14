# Stage 1 — Apps y modelo de datos

## Objetivo

Crear las tres apps Django de Fase 4 y su modelo de datos (entidades, relaciones, constraints,
índices), extender `AuditEvent` con las acciones/recursos documentales, sin implementar todavía
servicios ni UI.

## Alcance

Modelos, migraciones, admin básico y tests de modelo/constraints. No incluye lógica de negocio,
storage, PDF, API ni UI.

## Implementación realizada

- Tres apps nuevas: `prescriptions`, `study_orders`, `clinical_documents`, registradas en
  `INSTALLED_APPS`.
- `prescriptions.Prescription`/`PrescriptionItem` (ADR-022/023): `patient`/`doctor`/`clinical_encounter`
  FKs directas (patient se deriva siempre en el servicio, nunca se acepta independiente — se
  aplicará en Stage 2), `status` (`ISSUED`/`VOIDED`), `version_number`/`previous_version`/
  `is_current_version` (ADR-023), `idempotency_key` (mismo patrón que `appointments.Appointment`).
- `study_orders.StudyOrder`/`StudyOrderItem`: análogo, más `study_type`
  (`LABORATORY`/`IMAGING`/`HISTOPATHOLOGY`/`OTHER`).
- `clinical_documents.ClinicalDocument` (ADR-024/025): `patient` obligatorio; `appointment`/
  `clinical_encounter`/`prescription`/`study_order` opcionales; `status` nullable, sólo
  significativo cuando no hay respaldo de `Prescription`/`StudyOrder` (D-002); `document_type`/
  `origin`; metadatos de archivo (`storage_key` único, `mime_type`, `size_bytes`,
  `original_filename`); versionado propio (`version_number`/`previous_version`/`is_current_version`)
  sólo para el caso standalone.
- `medical_records.AuditEvent` extendido (sin tocar su esquema existente de Fase 3): nuevas
  `Action` (`ISSUE_PRESCRIPTION`, `ISSUE_STUDY_ORDER`, `VOID_PRESCRIPTION`, `VOID_STUDY_ORDER`,
  `UPLOAD_CLINICAL_DOCUMENT`, `GENERATE_CLINICAL_DOCUMENT`, `READ_CLINICAL_DOCUMENT`,
  `DOWNLOAD_CLINICAL_DOCUMENT`, `CREATE_DOCUMENT_VERSION`, `VOID_CLINICAL_DOCUMENT`), nuevos
  `ResourceType` (`Prescription`, `StudyOrder`, `ClinicalDocument`), y tres nuevas FK opcionales
  (`prescription`, `study_order`, `clinical_document`) — mismo mecanismo de auditoría de Fase 3, sin
  modelo paralelo (ADR-021).
- `medical_records/testing.py`: fixtures compartidas (`ClinicalEncounterFixture`) para los tests de
  las tres apps nuevas, evitando duplicar el fixture de médico/paciente/cita/encuentro ya usado en
  `medical_records/tests/*.py`.
- Admin básico registrado para las tres entidades (mismo nivel que `ClinicalEncounter`/
  `MedicalRecord` en Fase 3 — sin restricciones especiales de permisos de admin en esta etapa).

## Decisiones aplicadas

- `patient` se mantiene como FK directa en `Prescription`/`StudyOrder` (no solo derivable vía
  `clinical_encounter`) — mismo patrón de denormalización ya usado por `AuditEvent` en Fase 3
  (D-003, ver `clinical-documents-data-model.md`). La validez de este valor se protegerá en el
  servicio (Stage 2), nunca aceptando `patient` como parámetro independiente del cliente.
- Versionado por fila nueva con `is_current_version` explícito (ADR-023) — sin columna de
  "cadena/raíz"; la protección de concurrencia se implementará vía `select_for_update` en el
  servicio (Stage 2).
- Un único `ClinicalDocument` `GENERATED` por `Prescription`/`StudyOrder` (constraint parcial), en
  vez de permitir múltiples PDFs por versión.
- `previous_version` como `OneToOneField` (no `ForeignKey`): expresa a nivel de esquema que una
  versión anterior nunca puede tener dos sucesoras (más fuerte que un `ForeignKey` + verificación
  manual, sin necesitar un constraint adicional).

## Archivos creados

- `prescriptions/` (app completa: `models.py`, `admin.py`, `apps.py`, `migrations/0001_initial.py`,
  `services/__init__.py`, `tests/__init__.py`, `tests/test_models.py`).
- `study_orders/` (misma estructura).
- `clinical_documents/` (misma estructura, migraciones `0001_initial.py`…`0004_*.py` — ver nota en
  "Problemas encontrados").
- `medical_records/testing.py`.

## Archivos modificados

- `TeCuidoApp/settings.py` (`INSTALLED_APPS`).
- `medical_records/models.py` (`AuditEvent.Action`/`ResourceType` extendidos, 3 FKs nuevas).
- `medical_records/migrations/0003_auditevent_clinical_document.py`,
  `0004_auditevent_prescription.py`, `0005_auditevent_study_order_alter_auditevent_action_and_more.py`
  (generadas por `makemigrations`, no escritas a mano).

## Migraciones

```text
$ python manage.py makemigrations prescriptions study_orders clinical_documents medical_records
```

Django dividió `clinical_documents` en varias migraciones (`0001`…`0003`) para resolver la
dependencia cruzada entre apps (`clinical_documents` → `prescriptions`/`study_orders`, y
`medical_records.AuditEvent` → las tres apps nuevas) — no es un ciclo real a nivel de grafo de
migraciones (cada migración depende de una migración *anterior* de la otra app, nunca de una
posterior), y `migrate` las aplicó todas sin error.

```text
$ python manage.py migrate
... (8 migraciones nuevas aplicadas — ver detalle en el log de la sesión)
$ python manage.py check
System check identified no issues (0 silenced).
$ python manage.py makemigrations --check --dry-run
No changes detected
```

## Tests ejecutados

```bash
python manage.py test prescriptions study_orders clinical_documents -v 2
python manage.py test   # regresión completa
```

## Resultado de tests

```text
Ran 32 tests in 26.296s
OK
```

Regresión completa: `Ran 560 tests` (528 previos + 32 nuevos) — 1 fallo aislado en
`appointments.tests.test_hold_service.HoldConcurrencyTests.test_two_concurrent_holds_for_same_slot_only_one_succeeds`
por un deadlock real de PostgreSQL bajo la carga completa de la suite (mismo patrón ya observado y
documentado en sesiones anteriores de Fase 3 — no relacionado con ningún archivo tocado en esta
etapa). Verificado: pasa 3/3 en tres corridas aisladas inmediatamente después. Se considera un
flake de entorno, no una regresión; se reconfirmará en la regresión final de Stage 8.

## Validaciones manuales

No aplica en esta etapa (sin UI/API todavía).

## Problemas encontrados

Un `CheckConstraint` mal escrito en `ClinicalDocument`
(`clinicaldocument_status_matches_backing`) no rechazaba `status=NULL` en un documento standalone
(sin `prescription`/`study_order`) porque `status IN (...)` con `status` `NULL` evalúa a
desconocido en SQL, y PostgreSQL no rechaza una fila cuando un `CHECK` evalúa a `NULL`/desconocido
— sólo la rechaza cuando evalúa explícitamente a `FALSE`. El test
`test_standalone_document_without_status_is_rejected` lo detectó de inmediato.

## Problemas resueltos

Se agregó `Q(status__isnull=False)` explícito a la rama del constraint que exige `status` en el
caso standalone, forzando que `NULL` evalúe a `FALSE` en vez de a desconocido. Verificado con el
mismo test, ahora en verde, y con una migración adicional (`clinical_documents/migrations/0004_*.py`).

## Gaps conocidos

Ninguno bloqueante para esta etapa.

## Riesgos

- El deadlock de Fase 2 en `test_hold_service.py` bajo carga completa de la suite es un riesgo de
  entorno conocido (no de Fase 4); se seguirá vigilando en cada regresión completa posterior.
- Los tests de constraint dependen de `IntegrityError` a nivel de PostgreSQL, no de validación de
  formulario — esto es intencional (defensa en profundidad), pero significa que el servicio (Stage 2)
  deberá traducir esas excepciones a los errores de dominio de Fase 4 (`ValidationError`/`InvalidState`)
  antes de que lleguen a la API.

## Gate

PASS

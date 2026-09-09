# TeCuido — Fixtures Fase 1

## Orden de carga

Ejecutar desde la carpeta que contiene `manage.py`:

```bash
python manage.py loaddata tecuido_fase1/01_groups.json
python manage.py loaddata tecuido_fase1/02_catalogs.json
python manage.py loaddata tecuido_fase1/03_users.json
python manage.py loaddata tecuido_fase1/04_persons.json
python manage.py loaddata tecuido_fase1/05_doctors.json
python manage.py loaddata tecuido_fase1/06_patients.json
python manage.py loaddata tecuido_fase1/07_responsibles.json
python manage.py loaddata tecuido_fase1/08_clinics.json
python manage.py loaddata tecuido_fase1/09_relationships.json
```

## Usuarios de prueba

- admin@tecuido.test / Admin.TC2026!
- dra.carmen.hernandez@gmail.com / TeCuido2026!
- dr.martinez@tecuido.test / TeCuido2026!
- ana.paciente@tecuido.test / Patient.TC2026!
- maria.paciente@tecuido.test / Patient.TC2026!
- carlos.paciente@tecuido.test / Patient.TC2026!
- patricia.responsable@tecuido.test / Responsible.TC2026!

Carmen Hernandez Vega:
- email: dra.carmen.hernandez@gmail.com
- teléfono: 3316038923
- perfil: Doctor

Los valores Sex, RelationType y Invitation.Status están implementados como TextChoices en
los modelos revisados, por lo que `02_catalogs.json` queda vacío intencionalmente (`[]`,
JSON válido). `loaddata` emite `RuntimeWarning: No fixture data found for '02_catalogs'.
Installed 0 object(s)` al cargarlo — es el comportamiento esperado de Django ante un fixture
vacío a propósito, no un error; no requiere corrección.

No se incluye Invitation: `token_hash` debe proceder de un token seguro generado por el flujo
de invitación, no de un valor estático de fixture.


## Corrección de timestamps
Los fixtures fueron corregidos para incluir los campos `created_at` y `updated_at` obligatorios en los modelos correspondientes de Fase 1.
Esto evita errores `NotNullViolation` al cargar datos en PostgreSQL.

## Corrección de esquema (2026-09-08, ADR-007 §3.8 addendum)
Los fixtures quedaron desactualizados respecto al esquema real en dos puntos y fueron
corregidos:

- `06_patients.json`: se agregó `regime` (`MINOR`/`ADULT`) a cada `patients.patient` — el
  campo no tiene `default`, así que omitirlo hace fallar `loaddata` con `IntegrityError`.
  Ana, María y Carlos (con `User` propio) quedaron en `ADULT`; el paciente menor de prueba
  (sin `User`) quedó en `MINOR`.
- `09_relationships.json`: los dos `patients.responsiblepatientrelationship` usaban
  `is_active`, un campo que ya no existe (se reemplazó por `status` — ver ADR-007 §3.7).
  Se corrigieron a `"status": "ACTIVE"`.

Verificado cargando las 9 fixtures en orden contra una base de pruebas limpia (migraciones
actuales aplicadas) y revirtiendo la transacción — carga sin errores.

## Corrección de contradicción: backfill de `regime` por edad (Caso 7, 2026-09-09)
`patients/migrations/0004_patient_regime_and_relationship_deactivation.py` calculaba
originalmente `Patient.regime` a partir de `Person.birth_date` para las filas ya existentes
(`backfill_patient_regime`, vía `RunPython`). Eso contradecía la política ya decidida
(`Person.birth_date` determina solo la edad cronológica; `Patient.regime` cambia únicamente
por transición explícita de un médico) — con edad como criterio, un paciente cronológicamente
adulto pero todavía `MINOR` se habría "graduado" a `ADULT` sin que ningún médico ejecutara la
transición, y sin desactivar sus `ResponsiblePatientRelationship` activas.

Se eliminó el backfill por completo: `regime` es obligatorio, sin `default` de campo, y la
migración no calcula ningún valor — cada `Patient` debe declarar `regime` explícitamente al
crearse (`register_minor_patient` pasa `MINOR`; `accept_invitation` pasa `ADULT`). Fase 1 no
tiene datos de producción que preservar, así que esto es seguro: la migración solo corre
contra un esquema recién creado, antes de cargar cualquier fixture.

Se agregó además el escenario canónico que demuestra la política (Patient PK 5 / Person PK 8):
19 años cronológicos, `regime = MINOR`, responsable `ACTIVE`, médico tratante `ACTIVE` — ver
`00_MANIFEST.json` → `scenario_details`.

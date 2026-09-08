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
los modelos revisados, por lo que `02_catalogs.json` queda vacío intencionalmente.

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

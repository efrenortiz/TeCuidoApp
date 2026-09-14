# Stage 4 — API

## Objetivo

Exponer los servicios de dominio como API JSON siguiendo exactamente
`docs/design/phase-4-api-contracts.md` — sin inventar endpoints.

## Alcance

Vistas HTTP delgadas (Django views + `JsonResponse`), URLs, y su traducción de errores de dominio
a HTTP. Sin UI de navegador (Stage 5).

## Implementación realizada

- `clinical_documents/api_common.py`: infraestructura HTTP compartida (`DocumentJsonApiView`,
  mapeo de errores, parsing de body) — las tres apps de Fase 4 comparten la MISMA taxonomía de
  errores (ADR-029), a diferencia de `medical_records`/`appointments`, que no la comparten y por
  eso mantienen su propio `JsonApiView` independiente.
- `prescriptions/api.py` + `prescriptions/urls.py`:
  - `POST /api/v1/clinical/prescriptions/`
  - `GET  /api/v1/clinical/prescriptions/<id>/`
  - `POST /api/v1/clinical/prescriptions/<id>/versions/`
  - `POST /api/v1/clinical/prescriptions/<id>/void/`
- `study_orders/api.py` + `study_orders/urls.py`: mismos cuatro endpoints, análogos
  (`study-orders/`).
- `clinical_documents/api.py` + `clinical_documents/urls.py`:
  - `POST /api/v1/clinical/documents/` (`multipart/form-data`)
  - `GET  /api/v1/clinical/documents/<id>/`
  - `GET  /api/v1/clinical/documents/?patient=<id>&type=<type>&from=<date>&to=<date>`
  - `GET  /api/v1/clinical/documents/<id>/download/`
- `TeCuidoApp/urls.py`: las tres apps montadas bajo el mismo prefijo `api/v1/clinical/` ya
  existente (verificado sin colisión de rutas contra `medical_records.urls`).

## Decisiones aplicadas

- **Mapeo error↔HTTP** (M-01 de la revisión documental, ya cerrado): `NotFound→404`,
  `PermissionDenied→403`, `ValidationError→400`, `InvalidState→409`, `Conflict→409`,
  `ImmutableResource→409`, `ReferenceInconsistency→422`, `StorageError→503`.
- **201 vs. 200 en emisión**: igual que `EncounterStartView` de Fase 3 — la vista comprueba SI ya
  existía un recurso con esa `(doctor, idempotency_key)` ANTES de llamar al servicio, sólo para
  elegir el código HTTP; la corrección real (no duplicar) la garantiza el servicio bajo lock.
- **IDOR**: `get`/`download` nunca distinguen "no existe" de "no autorizado" — ambos devuelven 404
  con el mismo código `CLINICAL_RESOURCE_NOT_FOUND` (mismo criterio que Fase 3, P-041/SC-068).
- **Descarga**: `FileResponse` + `Content-Disposition` vía
  `django.utils.http.content_disposition_header` (Django 6.1) — nunca interpola el nombre del
  cliente directamente en el header a mano (previene inyección de cabeceras).
- **No se expone `storage_key`** en ninguna respuesta JSON (verificado con test dedicado).

## Archivos creados

- `clinical_documents/api_common.py`, `clinical_documents/api.py`, `clinical_documents/urls.py`.
- `prescriptions/api.py`, `prescriptions/urls.py`.
- `study_orders/api.py`, `study_orders/urls.py`.
- `prescriptions/tests/test_api.py`, `study_orders/tests/test_api.py`,
  `clinical_documents/tests/test_api.py`.

## Archivos modificados

- `TeCuidoApp/urls.py` (3 nuevos `include()`).

## Migraciones

Ninguna.

## Tests ejecutados

```bash
python manage.py test prescriptions study_orders clinical_documents -v 2
python manage.py test   # regresión completa
```

## Resultado de tests

```text
Ran 30 tests in 24.135s
OK
```

(30 tests de API nuevos, sumados a los 83 de Stages 1-3 → 113 tests de Fase 4 hasta este punto).

## Validaciones manuales

No aplica todavía (ver Stage 5 — navegador).

## Problemas encontrados

Ninguno nuevo en esta etapa — la implementación de la API no reveló defectos adicionales de los
servicios (ya endurecidos en Stage 2/3).

## Problemas resueltos

No aplica.

## Gaps conocidos

Ninguno.

## Riesgos

- La carga de archivos (`multipart/form-data`) lee el archivo completo en memoria
  (`uploaded.read()`) antes de validar tamaño — para el límite actual (10 MB) es aceptable; un
  límite mayor futuro debería revisar esto (usar `chunks()` con corte temprano) — no bloqueante
  para Fase 4.

## Gate

PASS

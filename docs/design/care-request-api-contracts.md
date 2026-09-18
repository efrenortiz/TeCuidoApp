# Fase 5 — Contrato API de `CareRequest`

**Estado:** diseño técnico cerrado
**Fecha de referencia:** 2026-09-15

## 1. Principios

La API de CareRequest reutiliza el patrón existente del proyecto:

- vistas Django planas;
- `JsonResponse`;
- autenticación por sesión;
- sin DRF;
- mapeo de excepciones de dominio a respuesta HTTP mediante el patrón `_ERROR_MAP`/`JsonApiView` ya existente.

No se introduce una dependencia nueva.

## 2. Endpoint

```http
POST /api/v1/care-requests/
```

El prefijo puede ajustarse por nomenclatura durante la implementación sin modificar el diseño del dominio.

## 3. Autenticación

Requiere una sesión autenticada.

Una solicitud no autenticada devuelve el error de autenticación siguiendo la convención existente del proyecto.

## 4. Headers

Opcional:

```http
Idempotency-Key: <string>
```

Cuando está presente, la clave pertenece exclusivamente al namespace de `CareRequest`.

## 5. Cuerpo de la petición — `multipart/form-data` siempre (corrección — 2026-09-17; exigencia técnica añadida 2026-09-18)

**Reemplaza la versión anterior de esta sección**, que describía un cuerpo JSON. Verificado
contra el código real (`care_requests/api.py::CareRequestCreateView.post`): la vista lee
`request.POST`/`request.FILES`, nunca el cuerpo crudo de la petición — el endpoint **no acepta
`application/json`**.

**Corrección 2026-09-18 — multipart es una exigencia técnica, no una descripción incompleta:**
la intención existente (`static/js/care-request.js::submitCareRequest`, único cliente real,
siempre construye un `FormData` y nunca envía JSON) deja claro que `multipart/form-data` es el
único formato válido, no uno tolerado entre varios. Antes de esta corrección, la vista no lo
exigía explícitamente: `request.POST` también se puebla con `application/x-www-form-urlencoded`
(Django lo parsea igual), así que ese formato se aceptaba "por accidente" aunque nunca fue la
intención, y `application/json` fallaba con un `400` engañoso ("`doctor_id` es obligatorio", sin
mencionar la causa real: el cuerpo nunca se interpretó). Ahora `CareRequestCreateView.post`
valida `request.content_type` al inicio y rechaza cualquier valor que no comience con
`multipart/form-data` mediante un `ApiError` (`400`) con un mensaje explícito sobre el
`Content-Type` recibido — antes de tocar `request.POST`/`request.FILES`.

```http
POST /api/v1/care-requests/
Content-Type: multipart/form-data; boundary=...
```

Se usa `multipart/form-data` **siempre**, con o sin adjuntos — mismo criterio que
`clinical_documents.api.ClinicalDocumentListCreateView` (Fase 4): un único formato de entrada,
en vez de aceptar JSON cuando no hay archivos y multipart solo cuando los hay. Esto evita un
segundo endpoint o una rama de parseo condicional en la vista.

### Campos (form fields, no claves JSON)

| Campo (form field) | Obligatorio | Regla |
|---|---:|---|
| `doctor_id` | Sí | Médico solicitado |
| `clinic_id` | Sí | Consultorio/contexto de Agenda |
| `start` | Sí | Inicio del slot seleccionado (ISO 8601) |
| `end` | Sí | Fin del slot seleccionado (ISO 8601); debe ser estrictamente posterior a `start` — ver §6.1 |
| `motivo` | Sí | Texto libre; rechazado si está vacío o es solo espacios en blanco tras normalizar (§6.2) |
| `padecimiento` | No | Texto libre; ausente/`""` |
| `descripcion` | No | Texto libre; ausente/`""` |
| `patient_id` | Condicional | Necesario cuando un responsable solicita por un paciente |
| `attachments` | No | Archivo(s); puede repetirse el campo hasta 5 veces — ver §8 |

## 6. Fechas

`start` y `end` utilizan ISO 8601 y el mismo parsing aplicado por las APIs existentes de Agenda.

Los valores proceden del slot generado por `get_available_slots()`.

La API no calcula duración ni deriva `end` desde `start`.

### 6.1 `start_at < end_at` — validación de servicio antes de la constraint (corrección — 2026-09-17)

El modelo mantiene `CheckConstraint(start_at__lt=end_at)` como defensa en profundidad — sin
cambios. Pero `start_at == end_at` o `start_at > end_at` se rechazan ahora en
`CareRequestService.create()` **antes** de intentar persistir, con `CareRequestValidationError`
(`400 VALIDATION_ERROR`). Antes de esta corrección no existía esa validación de servicio: un
intervalo inválido llegaba sin control hasta el `INSERT`, y el `IntegrityError` crudo de
PostgreSQL (incluyendo el `DETAIL` con los valores de la fila, potencialmente `motivo`) se
propagaba sin traducir — un `500` con información interna, no un `400` controlado.

### 6.2 `motivo` — nunca vacío ni solo espacios en blanco

Ya corregido en la ronda de hardening previa (`phase-5-final-report.md` §30): el servicio
normaliza (`.strip()`) y rechaza `motivo` vacío o de solo espacios en blanco de forma
independiente del frontend. Se documenta aquí porque es parte del contrato de entrada de este
endpoint, no solo del servicio.

## 7. Actor y paciente

El servidor determina el actor desde `request.user`.

### Actor paciente

El paciente se deriva del actor. No se acepta que un `patient_id` distinto sustituya al paciente autenticado.

### Actor responsable

`patient_id` identifica al paciente objetivo y debe corresponder a una relación responsable-paciente válida y `ACTIVE`.

## 8. Archivos

La solicitud es siempre `multipart/form-data` (§5) — no solo "cuando existen adjuntos" (esa
condición ya no aplica: el mismo formato se usa con o sin archivos). Los adjuntos, cuando
existen, se transportan en el campo `attachments` junto con los demás campos de texto en la
misma petición.

Límites:

- máximo 5 archivos por CareRequest;
- tipos PDF/JPEG/PNG;
- tamaño máximo por archivo = límite vigente de Fase 4.

No existe límite acumulado independiente en Fase 5.

## 9. Respuesta exitosa

```http
201 Created
```

```json
{
  "care_request_id": 501,
  "status": "CONVERTIDA",
  "appointment_id": 900,
  "clinical_document_ids": [12, 13]
}
```

El resultado corresponde a `CareRequestResult`.

## 10. Replay idempotente

El replay exitoso utiliza la misma respuesta `201 Created`, siguiendo la convención existente de Agenda donde la vista no distingue el caso de creación nueva del replay del servicio.

El replay no consume rate limit adicional y no vuelve a crear la Appointment.

### 10.1 Identidad lógica de la solicitud (corrección — 2026-09-17, adjuntos corregidos 2026-09-18)

Un mismo `(created_by, idempotency_key)` solo produce replay si la nueva solicitud coincide, además de en paciente/médico/consultorio/intervalo, en `motivo`, `padecimiento`, `descripcion` y el contenido exacto de los adjuntos (mismo nombre original, mismo tamaño en bytes **y mismo contenido byte a byte**, en orden de envío). Ver `care-request-service-contracts.md` §7.1 para la regla completa y la razón de cada campo.

**Corrección 2026-09-18:** la versión anterior de esta sección solo exigía nombre + tamaño para los adjuntos, lo que permitía que dos archivos distintos con el mismo nombre y la misma longitud en bytes (pero contenido diferente) se trataran incorrectamente como el mismo adjunto. La comparación ahora incluye el contenido byte a byte — leído únicamente cuando nombre y tamaño ya coinciden, sin I/O adicional en el caso común.

Cualquier divergencia en esos campos con la misma clave devuelve `409 Idempotency Conflict` (`CARE_REQUEST_CONFLICT`), nunca un replay silencioso del resultado original.

### 10.2 Solicitud inválida con clave existente

Una solicitud estructuralmente inválida (`motivo` vacío/solo espacios, `start_at >= end_at`) siempre devuelve `400 VALIDATION_ERROR`, incluso si su `Idempotency-Key` ya está asociada a una `CareRequest` comprometida — la validación de entrada se evalúa antes que cualquier comparación de idempotencia (`care-request-service-contracts.md` §3.1.1). No se interpreta como replay ni como `409`.

## 11. Errores

El mapeo debe reutilizar el mecanismo existente del proyecto.

| Situación | HTTP conceptual | Código lógico |
|---|---:|---|
| Sesión no autenticada | 401 | `NOT_AUTHENTICATED` |
| Datos inválidos | 400 | código de validación existente |
| No autorizado | 403 | código de autorización existente |
| Idempotency-Key reutilizada con datos diferentes | 409 | `CARE_REQUEST_CONFLICT` |
| Slot/Hold/Appointment rechazado por Agenda | 409 | código de conflicto/error de Agenda correspondiente |
| Límite de creación alcanzado | 429 | `RATE_LIMITED` |
| Archivo/tipo/límite no válido | 400 | código existente de validación de ClinicalDocument |
| Intervalo inválido (`start_at >= end_at`) | 400 | `VALIDATION_ERROR` (`CareRequestValidationError`) — §6.1 |
| `motivo` vacío o solo espacios en blanco | 400 | `VALIDATION_ERROR` (`CareRequestValidationError`) — §6.2 |
| `Content-Type` distinto de `multipart/form-data` | 400 | `BAD_REQUEST` (`ApiError`) — §5 |
| Excepción no anticipada (bug, fallo de infraestructura) | 500 | ver §11.1 (corregido 2026-09-18) |

No se crean códigos duplicados si existe ya uno equivalente.

### 11.1 Errores no anticipados — corrección 2026-09-18 (captura acotada por la política de no-cache)

**Reemplaza la conclusión anterior de esta sección**, que decía que `CareRequestJsonApiView.
dispatch` no tenía cláusula `except Exception` alguna, igual que `appointments.api.JsonApiView`
y `clinical_documents.api_common.DocumentJsonApiView`. Eso seguía siendo cierto para la
seguridad de contenido (ningún dato interno se exponía), pero dejaba un problema distinto: la
política de no-cache (§12.1) exige `Cache-Control: no-store` en **toda** respuesta, y un `500`
que escapa sin pasar por `dispatch` nunca recibe ese header (el `500` por defecto de Django no
lo agrega).

`dispatch` ahora tiene una cláusula `except Exception` **acotada exclusivamente a este
propósito** — no a "manejar errores inesperados" en general:

- Con `DEBUG=True` (desarrollo): se re-lanza la excepción tal cual (`raise`), preservando la
  página de depuración de Django exactamente como en cualquier otra vista del proyecto. Ningún
  desarrollador pierde el traceback local.
- Con `DEBUG=False` (producción, el único caso que ve un cliente real): se devuelve un `500`
  genérico y fijo (`INTERNAL_ERROR`, `"Ocurrió un error inesperado."`) con `Cache-Control:
  no-store` — mismo principio de "sin internals" que ya regía (§12.1), ahora también con el
  header de caché correcto.

`appointments.api.JsonApiView`/`clinical_documents.api_common.DocumentJsonApiView` **no se
modificaron** — siguen sin captura genérica, porque ninguna de las dos tenía (ni tiene) el
mismo requisito explícito de no-cache verificado como una brecha real en esta ronda. Esta es
una divergencia deliberada y documentada de `CareRequest` respecto a ese patrón, no un cambio
silencioso de arquitectura.

## 12. Semántica transaccional de errores

Un error de Agenda no crea una CareRequest persistente.

Un error de adjuntos produce rollback de la BD y activa compensación física de los archivos creados durante la ejecución.

## 12.1 Datos sensibles fuera de responses y logs (corrección — 2026-09-17)

Ninguna respuesta de error incluye `motivo`, `padecimiento`, `descripcion`, contenido de
archivos, rutas de almacenamiento privado, secretos ni tracebacks. Los mensajes de error son
genéricos (`_ERROR_MAP`, mensajes fijos) — nunca interpolan el valor enviado por el cliente.
Verificado: ningún mensaje de `_ERROR_MAP` ni de `ApiError` en `care_requests/api.py` incluye
un valor de campo de la petición; los únicos valores interpolados son nombres de campo
literales (p. ej. `"'{field}' es obligatorio."`), nunca su contenido.

## 12.2 `Cache-Control: no-store` en toda respuesta (corrección — 2026-09-18)

**Hallazgo:** antes de esta corrección, `CareRequestJsonApiView.dispatch` solo asignaba
`Cache-Control: no-store` en la ruta de éxito — las tres cláusulas `except` (`ApiError`,
`ValueError`, `(CareRequestError, AgendaError, DocumentError)`) hacían `return` directamente
dentro del bloque `except`, sin pasar por esa línea. Toda respuesta de error (400, 403, 404,
409, 422, 429) quedaba sin el header, contradiciendo la política clínica de no-cache.

**Corrección:** cada rama ahora asigna a una variable local `response` en vez de retornar
directamente; una única línea `response["Cache-Control"] = "no-store"` al final de `dispatch`
cubre uniformemente el éxito y las cuatro rutas de error (incluida la nueva rama `except
Exception` de §11.1). El caso `401` (fuera del `try`, evaluado antes de cualquier lógica) se
ajustó de la misma forma.

Cobertura verificada con un test por código de estado representativo: 201 (éxito), 400, 401,
403, 409, 429, 500.

## 13. No existen endpoints adicionales de Fase 5 para

- editar CareRequest;
- cancelar CareRequest;
- aprobar/revisar CareRequest;
- convertir manualmente;
- check-in/waiting room.

## 14. Dependencias

La API de CareRequest llama a `CareRequestService`. La capa HTTP no debe crear Hold, Appointment o ClinicalDocument directamente.

```text
HTTP
 ↓
CareRequestService
 ↓
Agenda / ClinicalDocument
```

## 15. Cliente HTTP (`static/js/care-request.js`) — rechazo de red (corrección — 2026-09-18)

`apiFetchJson()`/`apiFetchForm()` usan `fetch()`, cuya promesa se **rechaza** (no resuelve con
un status HTTP) ante un fallo de red real — sin conexión, DNS, CORS, servidor inalcanzable —,
a diferencia de cualquier 4xx/5xx, que sí resuelve normalmente. Antes de esta corrección, ese
rechazo no se manejaba: se propagaba sin capturar hasta `searchSlots`/`submitCareRequest`, que
solo tienen `.then()`/`.finally()` — el usuario no veía ningún mensaje de error, y quedaba un
"unhandled promise rejection" en la consola del navegador.

Ambas funciones ahora usan la forma de dos argumentos de `.then(onFulfilled, onRejected)`, con
`networkErrorResult()` como `onRejected`: convierte el rechazo en un resultado **resuelto**,
con la misma forma `{ok: false, status: 0, body: {error: {code, message}}}` que ya usan ambos
callers para un error HTTP normal — sin cambiar la firma pública de `apiFetchJson`/
`apiFetchForm` ni el código de `searchSlots`/`submitCareRequest`. El mensaje mostrado es fijo y
genérico ("No se pudo conectar con el servidor..."), nunca expone el objeto de error real de
`fetch()`. El botón de confirmar (`confirmBtn.disabled`) se restaura igual que ante cualquier
otro error, vía el mismo `.finally()` ya existente — sin reintento automático, sin doble envío.

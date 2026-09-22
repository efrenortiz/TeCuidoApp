# Fase 6 — Consent Domain

**Fuente normativa:** `docs/phases/phase-6-design-freeze.md` v1.1
**Estado:** Diseño técnico derivado — **implementado** (ver
`docs/phases/phase-6-implementation-summary.md`, PD-006).

## 1. Alcance

Fase 6 implementa exclusivamente el registro técnico de aceptación de documentos de plataforma:

- Aviso de Privacidad;
- Términos y Condiciones.

No se incluyen consentimientos clínicos específicos.

**PD-006 (decisión final del propietario):** el Aviso de Privacidad y los Términos son documentos
canónicos **externos y versionados** — TeCuidoApp no los gestiona como contenido propio, ni se
convierte en gestor jurídico completo. Solo conserva la evidencia de aceptación y una referencia
estable hacia dónde estaba publicada cada versión (`settings.LEGAL_DOCUMENT_URLS`,
`accounts.services.consent.document_url`), de modo que pueda responderse en todo momento:

```text
¿Qué documento aceptó?      -> policy_type
¿Qué versión?                -> policy_version
¿Cuándo?                     -> accepted_at
¿Quién lo aceptó?            -> user
¿Dónde estaba publicada?     -> document_url(policy_type, policy_version)
```

`accounts.services.consent.acceptance_trace(...)` responde las cinco preguntas en una sola
llamada. La referencia se conserva **por versión**, no solo para la vigente: una aceptación
histórica de una versión ya superada sigue siendo trazable a su publicación original.

## 2. Unidad conceptual

```text
User
  ↓ accepts
Document / Policy version
  ↓
Acceptance record
```

## 3. Datos mínimos

Cada aceptación debe poder demostrar:

- usuario;
- documento aceptado;
- versión;
- fecha/hora de aceptación.

## 4. Inmutabilidad lógica

Una aceptación histórica no se edita para “transformarla” en otra versión.

Una nueva versión requiere un nuevo registro de aceptación cuando corresponda al comportamiento definido por la plataforma.

## 5. No inferir obligaciones legales

Este dominio registra la aceptación técnica. No decide qué documento es jurídicamente obligatorio, qué texto debe contener ni qué obligaciones regulatorias aplican.

## 6. Versionado

La versión es una referencia estable al documento presentado al usuario. La implementación debe impedir aceptar una versión inexistente.

## 7. Privacidad

No almacenar como parte del registro la totalidad del documento si el sistema puede referenciar una versión publicada estable.

## 8. Modelo físico mínimo (cierra M-01)

Entidad `PolicyAcceptance` (o nombre equivalente que siga la convención del proyecto):

| Campo | Propósito |
|---|---|
| id | Identificador interno |
| user | Usuario que acepta (FK a `accounts.User`, `PROTECT`) |
| policy_type | `PRIVACY_NOTICE` \| `TERMS_AND_CONDITIONS` |
| policy_version | Versión del documento aceptado |
| accepted_at | Fecha/hora asignada por el servidor |

Restricción de integridad: `UNIQUE(user, policy_type, policy_version)`.

Esta restricción resuelve la condicional dejada abierta en
`phase-6-consent-service-contracts.md` §4 ("si el dominio establece unicidad"): **sí la
establece**. Aceptar de nuevo la misma combinación (`user`, `policy_type`, `policy_version`) no
crea una segunda fila — la primera aceptación es la que cuenta, y la operación es idempotente sin
error. Aceptar una `policy_version` distinta de la misma `policy_type` sí crea una fila nueva —
nunca sobrescribe ni elimina la aceptación anterior (§4, inmutabilidad lógica).

No se crea una tabla separada por cada tipo de documento: `policy_type` es la discriminación
suficiente sobre una única tabla, siguiendo el mismo principio de núcleo mínimo ya aplicado en
`MedicalRecord` (Fase 3) y en `Notification`
(`phase-6-notification-data-model.md` §2.1).

## 9. Exposición HTTP mínima (cierra M-01)

No se define un documento de contrato API separado para esta fase: la aceptación se expone
mediante un único par de endpoints mínimos, siguiendo el patrón JSON ya usado por el resto del
proyecto (sin DRF, mismo estilo que `phase-6-notification-api-contracts.md` y
`phase-6-audit-api-contracts.md`):

```text
POST /.../consent/accept/    body: { policy_type, policy_version }
GET  /.../consent/status/    respuesta: aceptaciones vigentes del usuario autenticado
```

El path exacto debe seguir el namespace/convención ya existente del proyecto; este documento fija
la semántica, no una URL obligatoria. El cliente nunca puede enviar `user` ni `accepted_at` —
ambos se determinan en servidor. Aceptar una `policy_version` inexistente se rechaza (ver
`phase-6-consent-service-contracts.md` §6). El endpoint de aceptación requiere autenticación; no
expone contenido de otros usuarios.

# Fase 5 — Permisos de `CareRequest`

**Estado:** diseño técnico cerrado
**Fecha de referencia:** 2026-09-15

## 1. Principios

La autorización de `CareRequest` sigue ADR-004:

- autenticación obligatoria;
- permisos funcionales + autorización por objeto;
- validación server-side;
- deny by default;
- nunca confiar en IDs, URLs o controles de frontend;
- relaciones inactivas no conceden acceso operativo.

No se crea una política de autorización paralela.

## 2. Actor de la creación

La creación requiere un usuario autenticado.

El actor puede ser:

- paciente autenticado que solicita para sí mismo;
- responsable autenticado que solicita para un paciente con relación `ACTIVE`.

No se acepta que el cliente decida arbitrariamente `created_by`.

`created_by` siempre corresponde al usuario autenticado.

## 3. Regla paciente

Cuando el actor es el propio paciente:

```text
patient = actor's patient profile
created_by = actor
responsible = NULL
```

El cliente no puede sustituir el paciente por otro ID.

## 4. Regla responsable

Cuando el actor es un responsable:

```text
patient = paciente objetivo
created_by = actor
responsible = responsible profile
```

Debe existir una `ResponsiblePatientRelationship` válida y `ACTIVE` entre responsable y paciente.

La relación se valida en servidor, no en frontend.

## 5. Médico y consultorio

La creación debe utilizar un médico y consultorio válidos para el actor según las reglas ya definidas por Agenda.

CareRequestService no duplica validaciones de `DoctorClinic` ni disponibilidad; las delega a Agenda.

## 6. Consulta de una CareRequest

El acceso de lectura de una CareRequest debe verificar autorización por objeto, conforme a las relaciones reales del dominio.

El mero conocimiento del ID no concede acceso.

La implementación debe evitar asumir que todos los médicos pueden consultar todas las solicitudes o que todos los responsables pueden consultar todos los pacientes.

La política concreta debe respetar las relaciones vigentes de Fase 1 y ADR-004.

### 6.1 Acceso administrativo (`/admin/`) — auditoría diferida a Fase 6

El Administrador (superusuario) puede consultar cualquier `CareRequest` vía `CareRequestAdmin` (solo lectura, sin `add`/`change`/`delete`) — consistente con su acceso global según ADR-004 §8. Ese mismo acceso, cuando toca `motivo`/`padecimiento`/`descripcion`, debería quedar auditado por `requirements.md` §62/ADR-004 §26. Esa auditoría **no se implementa en Fase 5** — ver `care-request-security-and-privacy.md` §14 para la decisión completa, la evidencia revisada y el riesgo aceptado (no nuevo, ya presente en todo `ModelAdmin` clínico del proyecto).

## 7. Edición

Fase 5 no contempla una operación independiente de edición de CareRequest.

Por tanto no existe una matriz de permisos para `update`.

## 8. Cancelación

No existe permiso `cancel CareRequest`.

La cancelación corresponde al ciclo de vida de `Appointment`.

## 9. Conversión

La conversión no es una acción manual separada de un rol.

Es parte de la misma operación iniciada por el actor autorizado:

```text
crear CareRequest
 ↓
Agenda
 ↓
Appointment
 ↓
CONVERTIDA
```

No existe un permiso independiente “convertir CareRequest”.

## 10. Archivos

Los archivos se rigen por la autorización de `ClinicalDocument` de Fase 4 además de la autorización de la operación CareRequest.

No se crean permisos de almacenamiento paralelos.

## 11. Matriz funcional

| Operación | Paciente | Responsable | Médico | Administrador |
|---|---:|---:|---:|---:|
| Crear para sí | ✅ | — | No definido por requisito F5 | No definido por requisito F5 |
| Crear por paciente relacionado | — | ✅ si relación `ACTIVE` | — | No definido por requisito F5 |
| Leer propia/relacionada | Según autorización por objeto | Según autorización por objeto | Según autorización por objeto | Según permisos globales existentes |
| Editar CareRequest | ❌ | ❌ | ❌ | ❌ |
| Cancelar CareRequest | ❌ | ❌ | ❌ | ❌ |
| Convertir manualmente | ❌ | ❌ | ❌ | ❌ |

Las celdas que no están definidas como una nueva capacidad funcional de Fase 5 no deben transformarse en permisos nuevos sin un requisito que lo justifique.

## 12. Seguridad de la autorización

Toda autorización debe ocurrir antes de devolver o modificar información protegida.

El frontend puede ocultar acciones, pero nunca constituye la frontera de seguridad.

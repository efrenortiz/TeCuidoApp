# Fase 6 — Audit Domain

**Fuente normativa:** `docs/phases/phase-6-design-freeze.md` v1.1
**Estado:** Diseño técnico derivado — **implementado** (ver
`docs/phases/phase-6-implementation-summary.md` para el estado de código, tests y las decisiones
finales del propietario PD-001/PD-002/PD-008 que confirman/precisan este documento).

## 1. Propósito

Definir la auditoría transversal de TeCuidoApp usando el `AuditEvent` ya existente, ampliando su capacidad solo donde Fase 6 lo justifique.

## 2. Source of truth

No se crea un segundo modelo o tabla de audit log.

La capacidad física existente de `medical_records.AuditEvent` se reutiliza como fuente de verdad
para **todas** las acciones del catálogo base (§3), incluidas las que no son clínicas (`LOGIN`,
`MODIFY_PATIENT`, `CHANGE_PERMISSIONS`, `DISABLE_USER`, `ADMIN_SENSITIVE_ACCESS`).

**Decisión de dirección de dependencia (cierra M-02):** esto implica que apps ajenas al dominio
clínico (`accounts`, `patients`, herramientas administrativas) deberán importar
`medical_records.services.audit` para registrar esas acciones — invirtiendo el sentido habitual de
dependencia entre fases (una fase temprana no suele depender de una fase posterior). Es una
excepción consciente y documentada, no un acoplamiento accidental: se prefiere frente a crear una
segunda tabla de auditoría (prohibido por §24 de `phase-6-design-freeze.md`, "nueva fuente de
verdad paralela para auditoría") o una nueva app `audit` sin necesidad demostrada (contrario al
principio de infraestructura mínima de §18.1/§22 del Design Freeze). **No se crea una app Django
`audit` en esta primera versión de Fase 6.**

Si en el futuro este acoplamiento se vuelve un problema real y medible, la alternativa es
introducir una app `audit` delgada que actúe solo como frontera de servicio (nunca como segunda
tabla) e importe `medical_records.services.audit` internamente, de modo que ninguna otra app
dependa directamente de `medical_records`. Esa migración no está justificada hoy y no se
implementa en esta fase.

## 3. Catálogo base

El catálogo técnico debe cubrir al menos las operaciones ya identificadas por la arquitectura:

```text
LOGIN
READ_MEDICAL_RECORD
READ_CLINICAL_HISTORY
READ_CLINICAL_ENCOUNTER
START_ENCOUNTER
SAVE_ENCOUNTER
COMPLETE_ENCOUNTER
CREATE_MEDICAL_RECORD
UPDATE_MEDICAL_RECORD
ISSUE_PRESCRIPTION
ISSUE_STUDY_ORDER
UPLOAD_CLINICAL_DOCUMENT
GENERATE_CLINICAL_DOCUMENT
READ_CLINICAL_DOCUMENT
DOWNLOAD_CLINICAL_DOCUMENT
MODIFY_PATIENT
CHANGE_PERMISSIONS
DISABLE_USER
ADMIN_SENSITIVE_ACCESS
```

La nomenclatura física debe reutilizar `AuditEvent.Action` donde ya exista y agregar únicamente acciones faltantes necesarias para F6.

**PD-001 (decisión final del propietario):** las cuatro acciones no clínicas están conectadas a
un punto de entrada real (`LOGIN` vía `accounts.views.AuditedLoginView`;
`MODIFY_PATIENT`/`CHANGE_PERMISSIONS`/`DISABLE_USER` vía Django Admin,
`patients.admin.PatientAdmin`/`accounts.admin.PersonAdmin`/`accounts.admin.UserAdmin`).
`ADMIN_SENSITIVE_ACCESS` permanece **definida en el catálogo pero sin operación emisora
actual** — no existe en el repositorio ninguna operación administrativa distinta de las tres ya
conectadas que represente específicamente "acceso a información sensible". No se inventa una
operación para darle uso, no se elimina del catálogo y no se le asigna artificialmente una acción
que ya tiene su propio significado (p. ej. no se reutiliza para `MODIFY_PATIENT`). Podrá
conectarse cuando exista una operación real cuya semántica corresponda.

## 4. Rechazos

Todo intento rechazado que corresponda a una operación del catálogo base debe generar un `AuditEvent` con resultado de rechazo/denegación apropiado.

Ejemplo:

```text
Intento de lectura clínica sin autorización
        ↓
Authorization rejects
        ↓
AuditEvent(action=READ_..., result=DENIED)
```

**PD-002 (decisión final del propietario — interpretación cerrada de F6-D06):**

> Se auditan los rechazos de operaciones sensibles que alcanzan el boundary instrumentado de
> TeCuidoApp y permiten identificar un actor.

Quedan explícitamente fuera de esta política, sin que ello constituya un incumplimiento de F6-D06:

- fallos previos al boundary de auditoría (p. ej. un `500` de infraestructura antes de que el
  código de dominio se ejecute);
- rechazos del framework que ocurren antes de la instrumentación propia de TeCuidoApp;
- casos en los que no puede resolverse un `User` real al que atribuir el evento — `record_event`/
  `safe_record_event` exigen un actor real (AH-086, invariante cerrada de Fase 3) y no se
  rediseña `AuditEvent` para aceptar un actor inexistente solo para cubrir esta política.

Ejemplo concreto ya implementado: un intento de login con contraseña incorrecta contra un correo
que no existe en el sistema nunca resuelve un `User`, así que no genera `AuditEvent` — pero un
intento con contraseña correcta rechazado por correo no verificado sí lo genera (`DENIED`), porque
ahí el actor ya es resoluble. Ver
`medical_records/tests/test_fase6_audit.py::LoginAuditTests` para la evidencia de ambos casos.

## 5. Éxitos y errores

Un evento de éxito debe representar una operación efectivamente realizada.

Si una operación hace rollback, no debe quedar un evento de éxito persistido como si la operación hubiera ocurrido.

## 6. Actor

El actor debe ser el usuario autenticado real, nunca un valor suministrado por el cliente.

El rol observado puede conservarse como snapshot histórico.

## 7. Información sensible

No almacenar contenido clínico, secrets, cuerpos completos de request ni stack traces en `AuditEvent`.

## 8. Lectura

Solo Administradores autorizados pueden consultar el audit trail.

Médicos, pacientes y responsables no obtienen acceso al log técnico por el hecho de tener acceso a otros datos.

**Corrección post-implementación (hallazgo 12.1):** esta regla debe cumplirse en **los tres**
puntos de acceso reales, no solo en la API/UI propias de TeCuidoApp:

```text
AuditEventListView (API)   -> can_view_audit_log (is_superuser)
AuditTrailView (UI)        -> can_view_audit_log (is_superuser)
Django Admin (/admin/...)  -> antes: cualquier is_staff=True
                               ahora: is_superuser (AuditEventAdmin.has_view_permission/
                               has_module_permission)
```

Antes de la corrección, `AuditEventAdmin` solo dependía del gate genérico de `/admin/`
(`is_staff`), lo que permitía a cualquier usuario `is_staff=True` no administrador ver el audit
trail completo vía Django Admin — inconsistente con la política ya aplicada en API/UI. Corregido
en `medical_records/admin.py`; cobertura en
`medical_records/tests/test_fase6_audit.py::AuditTrailAccessTests`.

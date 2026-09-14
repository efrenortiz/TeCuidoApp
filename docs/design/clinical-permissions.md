# TeCuidoApp — Fase 3: Clinical Permissions

**Documento:** `clinical-permissions.md`  
**Fase:** 3 — Clinical Care  
**Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11)  
**Propósito:** definir la política de autorización para expediente clínico, encuentros clínicos y futuros componentes clínicos.

---

## 1. Propósito y alcance

Este documento cierra las reglas de autorización clínica que quedaron deliberadamente abiertas en `phase-3-clinical-encounter.md`, `clinical-encounter-domain.md` y `clinical-record-domain.md`.

Su objetivo es establecer una política única, simple y consistente para responder:

1. quién puede acceder a información clínica;
2. quién puede crear, modificar o completar un `ClinicalEncounter`;
3. qué relación con el paciente habilita lectura histórica;
4. qué diferencia existe entre acceso funcional de Agenda y acceso clínico;
5. cómo se comporta la autorización durante la transición de menor a adulto;
6. qué operaciones requieren auditoría;
7. qué ocurre ante ausencia, revocación o cambio de relaciones.

No redefine la autenticación, ni duplica `Patient`, `Doctor`, `Responsible`, `DoctorPatientRelationship`, `ResponsiblePatientRelationship` o `DoctorClinic`.

---

# 2. Fuentes de verdad y jerarquía de políticas

La autorización clínica se apoya en:

- identidad/autenticación de `User`;
- rol funcional;
- identidad de `Patient`, `Doctor` o `Responsible`;
- relaciones de dominio ya existentes;
- estado del recurso clínico;
- reglas específicas de la operación.

La jerarquía conceptual es:

```text
Autenticación
    ↓
Rol / permiso funcional
    ↓
Permiso sobre objeto
    ↓
Relación de dominio
    ↓
Regla específica de operación
    ↓
Auditoría cuando corresponda
```

La política global continúa siendo **deny by default**.

---

# 3. Principios de autorización

## P-001 — Deny by default

Una operación clínica debe rechazarse si no existe una regla explícita que la autorice.

## P-002 — La autenticación no concede acceso clínico

Estar autenticado no equivale a poder consultar expedientes o encuentros.

## P-003 — El rol no sustituye la autorización sobre objeto

Ser `DOCTOR`, `RESPONSIBLE`, `PATIENT` o `ADMINISTRATOR` no concede por sí solo acceso a cualquier paciente.

## P-004 — La UI no constituye una barrera de seguridad

Ocultar botones, rutas o menús nunca sustituye la validación en servidor.

## P-005 — La autorización debe ejecutarse en servidor

Toda lectura o modificación clínica protegida debe pasar por una comprobación de autorización en backend.

## P-006 — No confiar en IDs enviados por el cliente

Un `patient_id`, `encounter_id` o `medical_record_id` proporcionado por el cliente debe verificarse contra el contexto autorizado del usuario.

## P-007 — Un permiso funcional no concede acceso global

Tener permiso para “ver expediente” no significa poder ver cualquier expediente.

## P-008 — El acceso clínico y el acceso administrativo son distintos

El acceso administrativo global de Fase 2 no se interpreta automáticamente como autorización clínica irrestricta.

---

# 4. Matriz principal de acceso clínico

La siguiente matriz es la política base de Fase 3.

| Actor | Ver propio perfil clínico | Ver expediente de otro paciente | Ver encuentro clínico | Crear encuentro | Editar encuentro abierto | Completar encuentro | Eliminar clínicos |
|---|---:|---:|---:|---:|---:|---:|---:|
| Paciente | Sí, propio | No | Sí, propio, según política de datos del portal | No | No | No | No |
| Responsable activo | No, salvo datos propios | Sí, pacientes autorizados y dentro del alcance definido | Sí, pacientes autorizados y dentro del alcance definido | No | No | No | No |
| Médico asignado | No aplica | Sí, si existe autorización clínica | Sí | Sí | Sí | Sí | No |
| Otro médico con relación activa | No aplica | Sí | Sí, lectura | No | No | No | No |
| Médico sin relación clínica autorizante | No aplica | No | No | Sólo puede atender si Agenda autoriza iniciar una cita válida | No salvo que sea el asignado | No | No |
| Administrador | No aplica | Acceso excepcional de soporte, bajo permiso específico y auditoría | Acceso excepcional de soporte, bajo permiso específico y auditoría | No | No | No | No |

**Nota importante:** la capacidad de un médico para crear/iniciar la **primera consulta válida** de un paciente puede existir sin `DoctorPatientRelationship` previa, porque Agenda permite la primera cita mediante `DoctorClinic`. Eso no convierte automáticamente al médico en lector histórico irrestricto ni crea la relación médico-paciente.

---

# 5. Política propuesta para otros médicos

## P-009 — Relación médico-paciente como autorización histórica

Para lectura clínica histórica de un paciente por un médico distinto del médico asignado al encuentro actual, la fuente normal de autorización será una `DoctorPatientRelationship` vigente y autorizante.

La razón es mantener separadas dos ideas:

```text
DoctorClinic
    → permite operar en la Agenda / contexto clínico

DoctorPatientRelationship
    → expresa relación clínica longitudinal autorizante
```

## P-010 — Una cita aislada no crea acceso histórico permanente

La existencia de una `Appointment` o de un `ClinicalEncounter` no activa automáticamente una relación longitudinal de lectura.

Por tanto:

```text
Appointment existente
      ≠
acceso histórico permanente
```

## P-011 — Médico asignado sí puede leer su encuentro

El médico asignado a un `ClinicalEncounter` puede acceder a su contenido mientras la operación sea compatible con su estado.

## P-012 — Médico asignado puede continuar un encuentro abierto

Si el encuentro permanece `IN_PROGRESS`, únicamente el médico asignado puede retomarlo y modificarlo.

## P-013 — Otro médico puede leer encuentro histórico con autorización longitudinal

Un médico con `DoctorPatientRelationship` activa y autorizante puede leer información clínica histórica del paciente, incluida información contenida en encuentros completados, sin adquirir capacidad de edición.

## P-014 — Otro médico no puede modificar por tener lectura

La lectura nunca implica:

```text
edit
complete
reopen
change doctor
```

## P-015 — Relación revocada elimina el acceso longitudinal ordinario

Cuando la `DoctorPatientRelationship` deja de estar activa, el médico deja de tener acceso longitudinal ordinario al expediente bajo esa relación.

Los accesos excepcionales posteriores requieren una regla explícita de soporte, emergencia o autoridad, documentada y auditada.

## P-016 — La relación se consulta en el momento del acceso

No se recomienda materializar permisos clínicos históricos en una tabla de ACL duplicada durante Fase 3.

El servicio debe evaluar la relación vigente al solicitar el recurso.

---

# 6. Paciente

## P-017 — El paciente puede consultar su propia información clínica permitida

**Cerrado (auditoría de cierre, 2026-09-11) — Decisión D-004, ver `clinical-record-domain.md` CR-034:**

El paciente adulto puede leer, de cada `ClinicalEncounter` propio en estado `COMPLETED`: los cinco campos obligatorios completos (`reason_for_visit`, `present_illness`, `physical_exam`, `assessment`, `plan`), los metadatos del encuentro (fecha, médico, consultorio, duración) y los campos opcionales presentes. Un encuentro `IN_PROGRESS` no es visible para el paciente.

Esta es la regla definitiva de campos visibles — no queda pendiente de ninguna decisión de producto posterior.

## P-018 — El paciente no puede modificar la nota médica

El paciente no puede crear, editar, completar ni eliminar un `ClinicalEncounter`.

## P-019 — El paciente no puede editar el expediente clínico estructural

La información clínica profesional permanece bajo las reglas clínicas del sistema.

Una futura funcionalidad para que el paciente aporte antecedentes o datos declarativos debe ser modelada como información aportada por paciente, no como edición silenciosa de una nota médica.

## P-020 — Protección contra IDOR

Cambiar el identificador de paciente o encuentro en la URL/API no puede conceder acceso a otro registro.

---

# 7. Responsable

## P-021 — El responsable depende de relación activa

El acceso del responsable deriva de `ResponsiblePatientRelationship` con estado `ACTIVE`.

## P-022 — El responsable no obtiene acceso por parentesco declarado

Un nombre, teléfono, correo o dato personal no constituye por sí solo una autorización.

## P-023 — El responsable puede leer sólo pacientes autorizados

El servicio debe comprobar la relación antes de devolver contexto clínico.

**Cerrado (auditoría de cierre, 2026-09-11) — Decisión D-004:** cuando el acceso está autorizado (`ResponsiblePatientRelationship.ACTIVE`), el responsable ve exactamente lo mismo que P-017 concede al paciente sobre sí mismo — los cinco campos obligatorios completos de cada encuentro `COMPLETED` del paciente autorizado, metadatos y campos opcionales presentes. No existe un filtrado adicional específico para el responsable más allá de la propia autorización de acceso a ese paciente.

## P-024 — El responsable no puede editar la nota médica

Aunque pueda consultar información clínica permitida, el responsable no puede editar ni completar encuentros.

## P-025 — Cambio a adulto

Al pasar el paciente de `MINOR` a `ADULT`, la autorización del responsable no se conserva automáticamente como autorización clínica del adulto.

La relación administrativa puede mantenerse para fines históricos o administrativos según sus propias reglas, pero el acceso clínico del responsable debe revalidarse bajo la política aplicable al adulto.

## P-026 — El cambio de régimen no duplica expediente

La transición menor → adulto mantiene el mismo `MedicalRecord`; lo que cambia son las reglas de autorización.

---

# 8. Médico asignado

## P-027 — Sólo el médico asignado inicia el encuentro

La operación `start` de un `ClinicalEncounter` requiere que el actor coincida con `Appointment.doctor`.

## P-028 — Sólo el médico asignado modifica el encuentro abierto

Mientras `ClinicalEncounter.status = IN_PROGRESS`, únicamente `ClinicalEncounter.doctor` puede guardar cambios clínicos.

## P-029 — Sólo el médico asignado completa

La transición a `COMPLETED` requiere al médico asignado.

## P-030 — El médico asignado no puede cambiar la identidad estructural

Incluso estando autorizado para editar, no puede cambiar:

- paciente;
- cita de origen;
- médico asignado;
- clínica de origen.

## P-031 — El médico asignado no necesita `DoctorPatientRelationship` para la primera consulta

La ausencia de relación previa no impide la atención inicial si Agenda ya autorizó una cita válida.

## P-032 — Crear la consulta no crea relación permanente

`start()` no debe crear, activar, modificar ni inferir `DoctorPatientRelationship`.

---

# 9. Médico no asignado

## P-033 — No puede editar un encuentro abierto

Tener relación longitudinal con el paciente no da capacidad de edición sobre un encuentro que pertenece a otro médico.

## P-034 — No puede completar un encuentro ajeno

No puede ejecutar la transición final de un encuentro que no tiene asignado.

## P-035 — Puede leer cuando exista autorización longitudinal

Su permiso normal es de lectura cuando `DoctorPatientRelationship` activa lo autoriza.

## P-036 — No puede apropiarse de un encuentro

No existe operación clínica F3 para transferir un `ClinicalEncounter` abierto entre médicos.

## P-037 — La consulta compartida futura será una evolución

Si más adelante se requiere coatención, segundo médico, interconsulta o sustitución, deberá crearse un modelo y autorización específicos. F3 no interpreta automáticamente una relación de lectura como coautoría.

---

# 10. Administrador

## P-038 — Acceso global administrativo no equivale a acceso clínico ordinario

El administrador conserva el acceso funcional global establecido por ADR-004, pero no obtiene por ese solo hecho capacidad para editar o completar consultas clínicas.

## P-039 — No puede iniciar, completar ni editar ClinicalEncounter por su rol administrativo

Estas acciones siguen siendo exclusivas del médico asignado.

## P-040 — Acceso administrativo de soporte debe ser explícito

Cuando una tarea operativa requiera acceder a información clínica sensible, el sistema debe invocar una capacidad administrativa específica, no un bypass genérico.

**Nota de estado (revisión de cierre, 2026-09-11):** esta capacidad queda definida aquí como requisito de política para cuando exista, pero **no se implementa en Fase 3**. Ningún endpoint, vista o servicio actual concede acceso administrativo de soporte al expediente o al contenido clínico — `medical_records/services/permissions.py` documenta explícitamente que ninguna función de autorización clínica consulta `is_superuser` (P-038/P-042). Un administrador que necesite este acceso hoy no tiene ningún camino, auditado o no, para obtenerlo.

## P-041 — Acceso administrativo clínico debe auditarse

Todo acceso de soporte a expediente o contenido clínico debe generar evento de auditoría — aplicable cuando la capacidad de P-040 se implemente; ver la nota de estado ahí.

**Cerrado (auditoría de cierre, 2026-09-11):** el `AuditLog` generado por estos eventos (y por el resto de eventos definidos en `clinical-audit-and-history.md`) solo puede ser **leído por el Administrador** (`user.is_superuser`). Ningún otro actor —incluido el médico asignado, el paciente o el responsable— tiene acceso de lectura al registro de auditoría; su visibilidad de la actividad clínica se limita al propio contenido clínico (encuentros, expediente) definido en las secciones anteriores de este documento, nunca al log técnico de accesos.

## P-042 — No debe existir endpoint “admin bypass” genérico

No se permitirá un patrón equivalente a:

```python
if user.is_superuser:
    return all_clinical_data
```

sin aplicar una política concreta y registrable.

## P-043 — Superusuario no puede reabrir una consulta completada

La auditoría o soporte no convierten una operación administrativa en capacidad de modificar historia clínica cerrada.

---

# 11. ClinicalEncounter — permisos por estado

## P-044 — Antes de iniciar

No existe `ClinicalEncounter` que pueda editarse.

La operación relevante es `start`, controlada por Agenda y por la identidad del médico asignado.

## P-045 — `IN_PROGRESS`

Permisos:

| Operación | Actor |
|---|---|
| Leer | Médico asignado; otros médicos autorizados según política de lectura |
| Guardar | Médico asignado |
| Completar | Médico asignado |
| Cancelar | Nadie desde dominio clínico |
| Eliminar | Nadie |
| Cambiar paciente | Nadie |
| Cambiar médico | Nadie |

## P-046 — `COMPLETED`

Permisos:

| Operación | Actor |
|---|---|
| Leer | Actores clínicamente autorizados |
| Editar | Nadie en F3 |
| Completar nuevamente | Nadie |
| Reabrir | Nadie |
| Eliminar | Nadie |

## P-047 — La lectura no depende de editable

Un actor puede tener permiso de lectura aunque nunca pueda modificar el encuentro.

---

# 12. MedicalRecord — permisos

## P-048 — El expediente pertenece al paciente

El `MedicalRecord` representa la continuidad clínica del paciente y no pertenece funcionalmente a un médico o clínica.

## P-049 — El expediente no es propiedad del médico

El médico puede participar en la atención y tener permisos clínicos, pero no es propietario exclusivo del expediente.

## P-050 — Un médico no puede reasignar expediente

Ningún médico puede mover un `MedicalRecord` a otro paciente.

## P-051 — Lectura del expediente

La lectura se autoriza sobre el paciente y sus componentes clínicos mediante la matriz de actores y relaciones.

## P-052 — Edición de datos longitudinales

Los campos propios de `MedicalRecord` pueden tener permisos específicos distintos a la lectura de encuentros.

En F3 se recomienda que la edición de información longitudinal profesional quede reservada a actores clínicos autorizados, con reglas de servicio específicas.

## P-053 — El expediente no puede editarse mediante un encuentro cerrado

Completar una consulta no concede permiso posterior para modificar cualquier dato longitudinal del expediente.

---

# 13. Operaciones de lectura

## P-054 — Lista de pacientes

Una lista de pacientes debe construirse desde un queryset autorizado; nunca devolver todos y filtrar en frontend.

## P-055 — Detalle de paciente

La vista/API de paciente debe comprobar permiso sobre ese paciente antes de incluir información clínica.

## P-056 — Historial clínico

El historial sólo se devuelve después de validar el permiso sobre el paciente y el alcance clínico del actor.

## P-057 — Encuentro individual

La consulta de un `ClinicalEncounter` debe verificar autorización antes de serializar campos clínicos.

## P-058 — Endpoints secundarios

Descargas, exportaciones, documentos, impresiones, adjuntos y búsquedas clínicas deben reutilizar el mismo servicio/política de autorización.

## P-059 — No existen endpoints públicos de expediente

No se permite exponer información clínica mediante URLs públicas, tokens previsibles o identificadores sin validación de permisos.

---

# 14. Operaciones de escritura

## P-060 — La escritura requiere autorización explícita

Toda escritura clínica debe verificar:

```text
actor
+
operation
+
resource
+
resource state
```

## P-061 — No existe escritura masiva por rol

Un endpoint como `POST /clinical-records/bulk-update/` no forma parte de F3 salvo una futura especificación explícita.

## P-062 — Save y Complete reutilizan autorización común

`save()` y `complete()` deben compartir la comprobación de actor asignado y estado, evitando reglas divergentes.

---

# 15. Primera consulta sin relación previa

## P-063 — Primera consulta permitida

Si Agenda tiene:

```text
Appointment.SCHEDULED
DoctorClinic válida
Doctor asignado
```

el médico puede iniciar la consulta aunque no exista `DoctorPatientRelationship` activa previa.

## P-064 — La primera consulta no concede retrospectivamente lectura histórica ilimitada

El acceso a consultas anteriores queda sometido a la relación y política aplicables a su fecha/estado según F3.

## P-065 — El primer encuentro no muta autorización

Crear `ClinicalEncounter` no produce cambios en:

- `DoctorPatientRelationship`;
- `ResponsiblePatientRelationship`;
- roles;
- permisos globales.

---

# 16. Revocación y cambios de relación

## P-066 — Revocación futura

La revocación de una relación debe afectar los nuevos accesos que dependan de ella.

## P-067 — No revocar historia ya registrada

Revocar una relación no elimina encuentros ni expediente.

## P-068 — El cambio de relación no cambia la autoría histórica

Un nuevo médico autorizado para leer no se convierte en autor de encuentros anteriores.

## P-069 — El médico antiguo no conserva acceso indefinido por cache

Las capas de aplicación no deben convertir un permiso revocado en acceso persistente indefinido.

---

# 17. Menor → adulto

## P-070 — El `MedicalRecord` continúa siendo el mismo

No se crea un expediente nuevo al cumplir 18 años.

## P-071 — Se recalcula autorización según régimen actual

El servicio debe usar el estado actual del paciente para determinar si el actor puede acceder.

## P-072 — El responsable no hereda automáticamente acceso de adulto

La autorización basada en responsabilidad sobre un menor no debe interpretarse como autorización clínica perpetua después de la mayoría de edad.

## P-073 — El adulto pasa a controlar su propio acceso de paciente

A partir del cambio de régimen, la política de paciente adulto se convierte en la referencia principal para su acceso de portal.

## P-074 — Historia previa no se separa

El paciente adulto conserva acceso a su historial conforme a las reglas de privacidad aplicables; no se fragmenta el expediente por edad.

---

# 18. Emergencia / soporte excepcional

F3 no implementa un modelo clínico especial de “break glass” como permiso ordinario.

## P-075 — No usar emergencia como bypass genérico

Una eventual autorización de emergencia deberá ser una capacidad explícita, temporal, justificada y auditada.

## P-076 — No se activa automáticamente en F3

F3 no presume que cualquier médico puede romper el control de acceso simplemente declarando una emergencia desde la UI.

## P-077 — Evolución futura

Si se requiere acceso de emergencia, deberá documentarse mediante ADR/decisión de producto y pruebas específicas.

---

# 19. Auditoría de acceso

## P-078 — Lectura clínica sensible debe poder auditarse

Los accesos al expediente y a componentes clínicos sensibles deben ser auditables.

## P-079 — Registrar actor y contexto

Como mínimo, el evento de auditoría deberá poder identificar:

- actor;
- paciente/contexto clínico;
- recurso accedido;
- operación;
- fecha y hora;
- resultado cuando el mecanismo de auditoría lo soporte.

## P-080 — Denegaciones sensibles pueden auditarse

Se recomienda registrar denegaciones relevantes que indiquen un intento de acceso indebido, sin convertir cada validación técnica rutinaria en ruido de auditoría.

## P-081 — Auditoría separada del dominio clínico

`AuditLog` no forma parte de `MedicalRecord` ni `ClinicalEncounter`.

---

# 20. Protección frente a acceso directo

## P-082 — URLs directas

Una URL válida no sustituye una autorización válida.

## P-083 — API directa

Llamar directamente al endpoint sin UI debe producir exactamente la misma decisión de autorización que la interfaz.

## P-084 — Enumeración de IDs

El sistema debe evitar que un usuario aprenda si existe un recurso clínico ajeno simplemente probando IDs.

## P-085 — Querysets autorizados

Cuando sea técnicamente apropiado, las consultas deben partir del conjunto de objetos autorizados para reducir riesgo de fugas accidentales.

---

# 21. Separación con Agenda

## P-086 — Agenda y clínica tienen permisos distintos

Tener permiso para crear/reprogramar una cita no equivale a poder leer o editar la consulta clínica.

## P-087 — Tener `DoctorClinic` no equivale a acceso histórico completo

`DoctorClinic` es suficiente para las operaciones de Agenda que Fase 2 definió para el médico y para habilitar la primera atención; no sustituye la autorización longitudinal clínica.

## P-088 — `IN_CONSULTATION` no es permiso por sí mismo

El estado de Appointment identifica una transición operativa, pero el servicio clínico debe validar nuevamente al actor.

---

# 22. Separación con DoctorPatientRelationship

## P-089 — La relación es una fuente de autorización, no la identidad del encuentro

`ClinicalEncounter` continúa perteneciendo a su `Appointment`.

## P-090 — La relación no controla la autoría histórica

Una relación posterior no cambia quién fue el médico que realizó una consulta anterior.

## P-091 — La relación no se crea automáticamente

Ni `Appointment` ni `ClinicalEncounter` la crean como efecto secundario.

---

# 23. Servicios de autorización recomendados

La implementación puede centralizar las reglas en funciones/servicios conceptuales como:

```text
can_view_patient(user, patient)
can_view_medical_record(user, patient)
can_view_encounter(user, encounter)
can_edit_encounter(user, encounter)
can_complete_encounter(user, encounter)
can_view_history(user, patient)
```

No es obligatorio que esos nombres sean definitivos, pero sí debe existir un único lugar de autoridad por regla para evitar copiar condiciones en múltiples vistas.

---

# 24. Regla de separación entre lectura y escritura

La política recomendada es:

```text
READ  ≠ WRITE

WRITE ⊂ READ
```

Es decir, quien puede escribir necesariamente debe poder leer el recurso necesario para esa operación, pero quien puede leer no necesariamente puede escribir.

Ejemplo:

```text
Doctor asignado
    READ + WRITE

Otro médico autorizado
    READ

Responsable autorizado
    READ

Paciente
    READ propio
```

---

# 25. Errores mínimos de autorización

La capa de dominio/servicio deberá poder distinguir al menos conceptualmente:

- `AuthenticationRequired`
- `PermissionDenied`
- `ObjectNotFoundOrNotAccessible`
- `RelationshipRequired`
- `RelationshipInactive`
- `ClinicalNotAuthorized` (corregido en la auditoría de cierre, 2026-09-11, para usar el nombre definitivo de `clinical-service-contracts.md` SC-132 — cubre, entre otros casos, un médico no asignado que intenta modificar el encuentro)
- `EncounterAlreadyCompleted`
- `ClinicalWriteForbidden`
- `AdministrativeClinicalAccessRequired`

La API podrá traducir estos errores según su contrato HTTP sin duplicar la regla clínica.

---

# 26. Invariantes de seguridad

## I-P-001

Un paciente nunca puede consultar el expediente de otro paciente por modificar un identificador.

## I-P-002

Un responsable sólo puede acceder a pacientes autorizados mediante su relación vigente.

## I-P-003

Un médico no asignado nunca puede modificar ni completar un encuentro abierto.

## I-P-004

Una relación `DoctorPatientRelationship` no se crea automáticamente por atender al paciente.

## I-P-005

Tener `DoctorClinic` no implica acceso histórico ilimitado al expediente.

## I-P-006

Un encuentro completado no puede editarse mediante permisos ordinarios.

## I-P-007

El administrador no puede utilizar su rol para iniciar o completar consultas.

## I-P-008

El acceso clínico sensible debe poder ser auditado.

## I-P-009

La revocación de una relación no elimina historia clínica.

## I-P-010

La transición menor → adulto mantiene el expediente y modifica las reglas de autorización aplicables.

## I-P-011

La UI no puede ampliar permisos efectivos.

## I-P-012

Todo endpoint clínico debe respetar la misma política que la interfaz.

---

# 27. Casos explícitos de autorización

| Caso | Resultado |
|---|---|
| Paciente consulta su propio historial | Permitido |
| Paciente cambia `patient_id` al de otro paciente | Denegado |
| Responsable ACTIVE consulta paciente autorizado | Permitido, según alcance de datos |
| Responsable sin relación consulta paciente ajeno | Denegado |
| Médico asignado inicia cita válida | Permitido |
| Médico asignado guarda `IN_PROGRESS` | Permitido |
| Médico asignado completa con requisitos válidos | Permitido |
| Otro médico con `DoctorPatientRelationship` activa consulta historial | Permitido en lectura |
| Otro médico con relación intenta editar encuentro ajeno abierto | Denegado |
| Médico sin relación intenta leer historial sin otra autorización | Denegado |
| Médico sin relación inicia primera consulta permitida por Agenda | Permitido |
| Primera consulta crea automáticamente relación médico-paciente | No |
| Administrador intenta iniciar consulta | Denegado |
| Administrador intenta completar consulta | Denegado |
| Administrador realiza consulta clínica de soporte autorizada | Permitido sólo mediante capacidad específica y auditada |
| Encuentro `COMPLETED` intenta editarse | Denegado |
| Responsable pierde autorización antes de una nueva consulta | Nuevo acceso denegado |
| Paciente cumple 18 años | Mismo expediente, nueva evaluación de autorización |

---

# 28. Decisiones propuestas para cierre

Las siguientes decisiones se consideran las más consistentes con lo trabajado hasta ahora:

1. **La lectura histórica de otro médico se basa normalmente en `DoctorPatientRelationship` activa.**
2. **La primera atención puede ocurrir sin esa relación**, porque Agenda la habilita mediante `DoctorClinic` y cita válida.
3. **Esa primera atención no crea automáticamente la relación.**
4. **El médico asignado conserva el privilegio exclusivo de escritura sobre el encuentro abierto.**
5. **La lectura no implica escritura.**
6. **El administrador tiene acceso funcional global, pero no bypass clínico genérico.**
7. **Acceso administrativo a clínica sensible, cuando exista una razón legítima, debe ser explícito y auditado.**
8. **La transición menor → adulto conserva el expediente y cambia la política de autorización aplicable.**
9. **No se crea en F3 una ACL duplicada; las relaciones del dominio son la fuente normal de autorización.**
10. **El acceso de emergencia tipo break-glass queda fuera de F3.**

---

# 29. Fuera de alcance de este documento

No se implementa aquí:

- consentimiento clínico electrónico avanzado;
- autorización por episodio asistencial compleja;
- break-glass de emergencia;
- coatención de varios médicos;
- sustitución formal de médico;
- delegación temporal de permisos;
- permisos por especialidad;
- permisos por campo clínico;
- acceso de aseguradoras;
- acceso de laboratorios externos;
- interoperabilidad externa de expedientes;
- anonimización clínica;
- rectificación formal/versionado de historia cerrada.

Cada uno requerirá una decisión específica antes de entrar al modelo.

---

# 30. Criterios de aceptación

El documento se considera cerrado para implementación cuando se verifique que:

- paciente sólo ve lo propio;
- responsable sólo ve pacientes autorizados;
- médico asignado puede iniciar, guardar y completar;
- otro médico autorizado puede leer sin editar;
- médico no autorizado no puede leer por URL/API;
- `DoctorClinic` no se usa como sustituto de autorización longitudinal;
- administrador no puede iniciar/completar consultas;
- acceso administrativo sensible tiene ruta explícita y auditable;
- encuentro completado permanece inmutable;
- la transición menor → adulto no duplica expediente;
- ninguna operación clínica modifica automáticamente `DoctorPatientRelationship`.

---

# 31. Relación con los documentos siguientes

Este documento alimentará directamente:

- `clinical-security-and-privacy.md`
- `clinical-service-contracts.md`
- `clinical-api-contracts.md`
- `phase-3-clinical-ux.md`
- `clinical-audit-and-history.md`
- `phase-3-testing-strategy.md`

Especialmente, la API y los servicios deberán implementar esta política sin copiar reglas divergentes en cada endpoint.

---

# 32. Resumen ejecutivo

La política de Fase 3 debe mantenerse simple:

```text
PATIENT
  → own clinical information

RESPONSIBLE ACTIVE
  → authorized patients

DOCTOR ASSIGNED
  → read + write + complete current encounter

OTHER DOCTOR WITH ACTIVE RELATION
  → read clinical history

DOCTOR WITHOUT LONGITUDINAL RELATION
  → may attend first valid appointment when Agenda authorizes it,
    but does not automatically gain historical access

ADMINISTRATOR
  → global application access,
    but no clinical editing/completion bypass
```

La regla estructural más importante es:

> **Agenda determina quién puede iniciar una atención válida; la autorización clínica determina quién puede leer o modificar la información clínica.**

Y una segunda regla evita una fuente importante de inconsistencias:

> **Atender a un paciente y mantener una relación médico-paciente son decisiones independientes.**

# TeCuidoApp — Fase 3: Clinical Audit and History

**Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11)  
**Propósito:** definir la trazabilidad de operaciones clínicas y la preservación del historial clínico.  
**Dependencias:** `phase-3-clinical-encounter.md`, `clinical-encounter-rules.md`, `clinical-encounter-domain.md`, `clinical-record-domain.md`, `clinical-data-model.md`, `clinical-permissions.md`, `clinical-security-and-privacy.md`, `clinical-service-contracts.md`, `clinical-api-contracts.md`.  
**Regla general:** este documento no redefine autorización, dominio ni API; los complementa con reglas de auditoría e historia.

---

## 1. Propósito

Fase 3 necesita dos mecanismos distintos pero relacionados:

1. **Historial clínico:** la información clínica que debe permanecer disponible como registro asistencial histórico.
2. **Auditoría:** evidencia técnica de las operaciones relevantes realizadas sobre información clínica.

No deben confundirse. El historial responde **qué información clínica quedó registrada**. La auditoría responde **quién realizó qué operación, sobre qué recurso, cuándo y con qué resultado**.

El diseño propuesto mantiene ambos conceptos separados, simples y verificables.

---

## 2. Fuentes y jerarquía

### 2.1 Fuentes inmediatas

La fuente funcional principal son las decisiones cerradas de Fase 3 sobre `ClinicalEncounter` y `MedicalRecord`.

### 2.2 Fases anteriores

Las reglas de Agenda, identidad, relaciones médico-paciente, permisos y seguridad continúan vigentes salvo contradicción explícita.

### 2.3 Regla de contradicción

Cuando una regla histórica sea incompatible con una decisión específica y posterior de Fase 3, prevalece la decisión específica de Fase 3.

### 2.4 Alcance temporal

Este documento define la solución mínima necesaria para Fase 3. No pretende resolver desde ahora retención legal avanzada, firma electrónica avanzada, expediente interoperable, versionado clínico completo ni SIEM empresarial.

---

# 3. Principios rectores

## AH-001 — Historial y auditoría son conceptos distintos

Nunca se utilizará el log de auditoría como sustituto del expediente clínico.

## AH-002 — La historia clínica es longitudinal

La historia se conserva a través del tiempo y no se reemplaza por el estado más reciente.

## AH-003 — Los encuentros completados forman parte del historial

Un `ClinicalEncounter` en `COMPLETED` constituye una pieza histórica de atención.

## AH-004 — Un encuentro en progreso no es todavía historia cerrada

Un encuentro `IN_PROGRESS` puede consultarse por quienes tengan autorización, pero no se presenta como registro clínico final.

## AH-005 — No borrar historia clínicamente relevante

No existe borrado funcional de encuentros completados ni sustitución silenciosa de contenido histórico.

## AH-006 — La auditoría también es histórica

Los eventos de auditoría deben ser append-only desde la perspectiva funcional: se agregan eventos y no se corrigen mediante edición silenciosa.

## AH-007 — Auditar operaciones relevantes, no cada clic

Se auditan acciones de seguridad y negocio con valor probatorio o de trazabilidad; no interacciones visuales sin impacto.

## AH-008 — El actor es el usuario autenticado

La identidad del actor se deriva del contexto autenticado del servidor y nunca de un campo enviado por el cliente.

## AH-009 — Registrar resultado

Un evento relevante debe indicar si la operación terminó exitosamente, fue rechazada por autorización/regla o falló técnicamente cuando sea útil para seguridad y diagnóstico.

## AH-010 — No registrar secretos

La auditoría no almacena contraseñas, tokens, cookies de sesión ni secretos equivalentes.

---

# 4. Modelo conceptual de auditoría

## AH-011 — Entidad `AuditEvent`

Se propone una entidad técnica de auditoría separada de los modelos clínicos.

Campos conceptuales mínimos:

- `id` — identificador único.
- `occurred_at` — instante del evento.
- `actor_user_id` — usuario autenticado que ejecutó la acción, cuando exista.
- `actor_role` — rol relevante observado al momento del evento, cuando aplique.
- `action` — acción normalizada.
- `resource_type` — tipo lógico del recurso.
- `resource_id` — identificador del recurso afectado, cuando exista.
- `patient_id` — paciente clínico relacionado, cuando exista y sea necesario para búsqueda/seguridad.
- `appointment_id` — cita relacionada, cuando exista.
- `clinical_encounter_id` — encuentro relacionado, cuando exista.
- `result` — éxito, rechazo funcional, rechazo de autorización o fallo técnico según catálogo interno.
- `reason_code` — código interno de resultado/rechazo cuando aplique.
- `request_id` — identificador técnico para correlación, si está disponible.
- `metadata` limitada y controlada para contexto no sensible.

## AH-012 — No duplicar el contenido clínico

`AuditEvent` no copia el cuerpo completo de `ClinicalEncounter`, `MedicalRecord`, documentos, recetas o estudios.

## AH-013 — Referencias, no snapshots

La auditoría referencia recursos clínicos mediante sus identificadores. No se convierte en una segunda base de datos clínica.

## AH-014 — `resource_type` explícito

El tipo del recurso se registra explícitamente para evitar ambigüedad al interpretar `resource_id`.

## AH-015 — Identidad del paciente como contexto

Cuando la operación tenga contexto de paciente, `patient_id` puede registrarse como índice de trazabilidad, pero no sustituye `resource_id`.

## AH-016 — Correlación técnica

`request_id` se utilizará para correlacionar una petición con varios eventos derivados de una misma operación.

## AH-017 — No usar IP como identidad

La dirección IP, cuando se registre, es un dato técnico complementario y nunca sustituye a `actor_user_id`.

## AH-018 — No guardar User-Agent completo por defecto

No se propone conservar cadenas técnicas extensas sin necesidad. El diseño inicial prioriza actor, operación, recurso y resultado.

---

# 5. Catálogo mínimo de acciones auditables

## AH-019 — Acciones de autenticación

En el ámbito clínico, serán auditables cuando existan mecanismos para ello:

- inicio de sesión exitoso;
- inicio de sesión rechazado por credenciales;
- cierre de sesión explícito;
- recuperación/cambio de credenciales con impacto de seguridad;
- invalidación administrativa de sesión, si existe.

## AH-020 — Acceso de lectura clínica

Debe auditarse la consulta de información clínica sensible cuando la operación permita reconstruir quién accedió a ella.

## AH-021 — Inicio de consulta

Registrar `START_ENCOUNTER` para todo inicio efectivo o intento relevante según la política de resultados.

## AH-022 — Guardado de consulta

Registrar `SAVE_ENCOUNTER` cuando exista persistencia exitosa de contenido clínico.

## AH-023 — Finalización de consulta

Registrar `COMPLETE_ENCOUNTER` cuando la transición a `COMPLETED` sea efectiva.

## AH-024 — Rechazo de finalización

Un intento de completar rechazado por campos obligatorios, estado o autorización puede registrarse con resultado de rechazo cuando aporte valor de trazabilidad.

## AH-025 — Lectura de expediente

Registrar `READ_MEDICAL_RECORD` para accesos clínicos al expediente cuando la arquitectura de auditoría esté disponible.

## AH-026 — Lectura de historial

Registrar `READ_CLINICAL_HISTORY` para consultas longitudinales de historia clínica.

## AH-027 — Modificación de expediente

Toda actualización legítima de campos longitudinales del `MedicalRecord` debe generar un evento `UPDATE_MEDICAL_RECORD`.

## AH-028 — Creación de expediente

La creación efectiva de `MedicalRecord` genera `CREATE_MEDICAL_RECORD`.

## AH-029 — Acceso denegado

Los accesos clínicos denegados por autorización pueden generar un evento de auditoría con recurso y razón general, sin almacenar contenido clínico. **Corrección de consistencia (revisión de cierre, 2026-09-11):** la implementación no usa un valor de `action` separado (`ACCESS_DENIED`) — registra la misma `action` de negocio que se intentó (p. ej. `START_ENCOUNTER`, `READ_MEDICAL_RECORD`) con `result = DENIED`. Este diseño conserva qué operación se intentó, información que un valor `ACCESS_DENIED` genérico perdería; se documenta aquí como el comportamiento definitivo.

## AH-030 — Exportación

Las exportaciones clínicas, cuando existan, deben tener evento de auditoría propio. La exportación no forma parte del núcleo mínimo de Fase 3.

## AH-031 — Documentos

Carga, lectura, descarga o eliminación lógica de documentos clínicos, cuando estén implementados, tendrán acciones de auditoría específicas.

---

# 6. Propuesta de resultados

## AH-032 — `SUCCESS`

La operación produjo el efecto de negocio previsto.

## AH-033 — `DENIED`

La operación fue rechazada por autorización.

## AH-034 — `REJECTED`

La operación llegó a una capa de negocio válida pero no cumplió una regla funcional.

## AH-035 — `ERROR`

La operación no pudo completarse debido a una falla técnica inesperada.

## AH-036 — No auditar excepciones internas completas

El evento de auditoría almacena un código seguro, no stack traces ni mensajes internos sensibles.

---

# 7. Qué debe quedar en el historial clínico

## AH-037 — Encuentros completados

Cada `ClinicalEncounter` `COMPLETED` permanece disponible como parte del historial del paciente.

## AH-038 — Orden cronológico

El historial se presenta en orden clínico temporal, preferentemente por `started_at` descendente para consultas recientes primero.

## AH-039 — Preservar fecha del evento

La fecha clínica no debe sustituirse por `updated_at` para reconstruir cuándo ocurrió la atención.

## AH-040 — `started_at` es fecha clínica primaria del encuentro

La atención se ubica históricamente mediante `started_at`.

## AH-041 — `completed_at` indica cierre

`completed_at` permite conocer cuándo se cerró la nota, pero no sustituye a `started_at`.

## AH-042 — `updated_at` no reordena la historia clínica

Un guardado de un encuentro abierto modifica `updated_at`, pero no cambia el momento clínico original.

## AH-043 — Guardados parciales no crean encuentros adicionales

No se generan múltiples registros históricos por cada guardado.

## AH-044 — Un encuentro es una unidad histórica

Los sucesivos guardados de un mismo `ClinicalEncounter` pertenecen al mismo registro.

## AH-045 — `SCHEDULED` no pertenece a historia clínica

Una cita programada sin atención iniciada pertenece a Agenda, no al historial clínico.

## AH-046 — `CANCELLED` no pertenece a historia clínica

Una cita cancelada no genera `ClinicalEncounter`.

## AH-047 — `NO_SHOW` no pertenece a historia clínica

Una inasistencia no genera `ClinicalEncounter`.

---

# 8. Inmutabilidad del historial

## AH-048 — `COMPLETED` es histórico e inmutable

Una vez completado, el encuentro no puede editarse desde la aplicación.

## AH-049 — No reapertura

No existe transición `COMPLETED → IN_PROGRESS` en Fase 3.

## AH-050 — No modificación silenciosa

No se actualiza un encuentro completado para corregir un error sin un mecanismo explícito futuro.

## AH-051 — No eliminación funcional

No existe endpoint ni acción de UI para eliminar un encuentro clínico.

## AH-052 — No reemplazo total

No se permite sustituir todo el contenido histórico de un encuentro por un objeto nuevo conservando el mismo significado.

## AH-053 — Antecedentes longitudinales son distintos

La modificación de un campo longitudinal del `MedicalRecord` no modifica retrospectivamente encuentros históricos.

## AH-054 — Resumen no es historia

El resumen clínico puede cambiar por derivación de información vigente, sin alterar el contenido histórico de los encuentros.

---

# 9. Corrección de errores históricos

## AH-055 — Fase 3 no implementa enmiendas

No se implementa todavía un sistema de correcciones/amendments versionadas.

## AH-056 — No editar por acceso administrativo

El rol administrativo no habilita una vía genérica para cambiar contenido histórico.

## AH-057 — Preparación futura

Una futura capacidad de enmienda deberá crear evidencia explícita, preservar el original y registrar actor, motivo, fecha y nuevo estado.

## AH-058 — No usar auditoría para corregir historia

Agregar un `AuditEvent` no corrige el contenido del expediente. Son mecanismos distintos.

---

# 10. Auditoría de ClinicalEncounter

## AH-059 — Evento de inicio

Crear evento después de que la transacción de inicio sea efectiva.

## AH-060 — No auditar como éxito un inicio fallido

Un intento que no modifica Agenda ni crea encuentro no puede registrarse como `START_ENCOUNTER / SUCCESS`.

## AH-061 — Inicio idempotente

Cuando un segundo inicio idempotente reconoce el encuentro ya existente, puede registrarse como evento técnico de operación repetida, pero no debe crear una segunda atención histórica.

## AH-062 — Guardado exitoso

El evento `SAVE_ENCOUNTER / SUCCESS` representa un guardado efectivamente persistido.

## AH-063 — Guardado fallido

Un guardado que falla antes de commit no debe registrarse como cambio clínico exitoso.

## AH-064 — Compleción atómica

El evento `COMPLETE_ENCOUNTER / SUCCESS` sólo se registra después de que `ClinicalEncounter → COMPLETED` y `Appointment → COMPLETED` hayan quedado confirmados.

## AH-065 — No auditar cierre parcial como éxito

Si la transacción de cierre falla, no existe evento de éxito.

## AH-066 — Rechazo por contenido

El intento de completar con placeholders o campos obligatorios vacíos puede generar un evento `REJECTED` con código general, sin almacenar el contenido rechazado.

## AH-067 — Lectura

Las lecturas de encuentros completados deben ser auditables conforme a la política de acceso clínico.

## AH-068 — Concurrencia

Una operación perdedora en concurrencia no se registra como modificación exitosa.

---

# 11. Auditoría de MedicalRecord

## AH-069 — Creación

La creación del expediente debe quedar vinculada al paciente y, si ocurre con el primer encuentro, correlacionada con esa operación.

## AH-070 — Actualización

Cada modificación persistida de campos longitudinales relevantes debe generar evento.

## AH-071 — No registrar campos completos

El evento debe identificar la operación, pero no duplicar los valores clínicos completos del expediente.

## AH-072 — Lectura longitudinal

Las consultas que devuelvan historial clínico sensible deben ser trazables.

## AH-073 — Acceso por paciente

La lectura del propio expediente por el paciente puede auditarse de la misma forma que cualquier lectura clínica sensible.

## AH-074 — Acceso por responsable

La lectura por responsable debe auditarse y reflejar la identidad del actor real.

## AH-075 — Acceso por médico

La lectura por médico debe auditarse, distinguiendo cuando sea posible entre acceso contextual a una atención y acceso longitudinal.

## AH-076 — Acceso administrativo

El acceso de soporte o excepcional debe producir auditoría reforzada y razón de acceso cuando dicha modalidad exista.

---

# 12. Separación de acceso y auditoría

## AH-077 — Auditar no concede permisos

Crear un evento de auditoría nunca autoriza la operación.

## AH-078 — Denegación no expone información clínica

Un evento de acceso denegado debe contener sólo información mínima necesaria para trazabilidad.

## AH-079 — Evitar enumeración

La respuesta API frente a recursos no autorizados continuará siguiendo la política de seguridad; el mecanismo interno de auditoría no debe revelar al cliente si el recurso existe cuando la política de seguridad requiera respuesta uniforme.

## AH-080 — No registrar secretos del request

Los cuerpos de solicitud no se copian al log de auditoría.

## AH-081 — No registrar tokens

Nunca registrar Authorization headers, refresh tokens, cookies de sesión ni equivalentes.

---

# 13. Integridad técnica del AuditEvent

## AH-082 — Append-only funcional

No habrá edición desde UI o API del evento de auditoría.

## AH-083 — No DELETE funcional

No habrá borrado de eventos de auditoría desde la aplicación.

## AH-084 — Timestamp del servidor

`occurred_at` debe asignarse en servidor.

## AH-085 — Orden no depende del cliente

Los clientes no pueden enviar el timestamp del evento como fuente de verdad.

## AH-086 — Actor no viene del body

El identificador del actor se deriva de la sesión autenticada.

## AH-087 — Recurso derivado del contexto

Siempre que sea posible, el tipo e identificador del recurso se derivan del objeto autorizado que la operación realmente tocó.

## AH-088 — Fallo de auditoría y operación clínica

Para operaciones clínicas críticas, se propone que la auditoría de éxito sea parte del mismo límite transaccional cuando sea técnicamente viable. Si la infraestructura futura impide esa atomicidad, deberá existir una estrategia explícita de recuperación; no se ignoran silenciosamente fallos de auditoría.

## AH-089 — No bloquear toda lectura clínica por auditoría no disponible

La política final deberá equilibrar continuidad asistencial y trazabilidad; Fase 3 prioriza no perder operaciones clínicas legítimas por un mecanismo auxiliar, salvo que una regulación aplicable exija lo contrario.

---

# 14. Retención y conservación

## AH-090 — Conservación de historia

Los registros clínicos completados se conservan mientras formen parte del historial del paciente y según las obligaciones de retención aplicables al despliegue.

## AH-091 — Fase 3 no fija un plazo legal universal

No se inventa un periodo de retención legal dentro de este documento.

## AH-092 — Auditoría no se elimina con el recurso

Un evento de auditoría no debe desaparecer simplemente porque un recurso clínico deje de estar activo o visible funcionalmente.

## AH-093 — Menor → adulto

El cambio de régimen no genera una nueva historia ni reinicia la auditoría del paciente.

## AH-094 — Cambio de médico

Cambiar de médico no modifica la historia previa ni reescribe sus autores históricos.

## AH-095 — Cambio de clínica

Cambiar de clínica no mueve ni reatribuye silenciosamente el historial histórico.

---

# 15. Identidad histórica del autor

## AH-096 — Autor del encuentro

El `doctor` del `ClinicalEncounter` permanece como autor clínico del encuentro.

## AH-097 — No reatribución

No se cambia retrospectivamente el doctor de un encuentro completado para adaptarlo a cambios de relación futura.

## AH-098 — Auditoría conserva actor operativo

`actor_user_id` registra quién realizó la operación; puede coincidir o no conceptualmente con el autor clínico, especialmente para lecturas y acciones administrativas.

## AH-099 — No inferir actor desde doctor

No se debe asumir que todo evento sobre un encuentro fue realizado por el médico que figura en el encuentro.

## AH-100 — Lectura y autoría son distintas

Leer un encuentro no convierte al lector en participante ni autor de la atención.

---

# 16. Historial visible al usuario

## AH-101 — Historia ordenada y legible

La UI debe presentar los eventos clínicos en orden temporal y con separación clara entre encuentro abierto y encuentro completado.

## AH-102 — Mostrar estado clínico

Cada encuentro debe mostrar `IN_PROGRESS` o `COMPLETED` cuando el actor tenga permiso para verlo.

## AH-103 — Mostrar médico autor

El historial debe mostrar el médico asociado al encuentro conforme a las políticas de acceso.

## AH-104 — Mostrar fechas clínicas

La UI debe mostrar como mínimo fecha de atención y, para el detalle, las fechas relevantes disponibles.

## AH-105 — No mostrar auditoría técnica al paciente por defecto

La consola técnica de auditoría no forma parte del historial clínico estándar del paciente.

## AH-106 — Separación de historia y actividad técnica

No se mezclan `SAVE_ENCOUNTER`, `READ_MEDICAL_RECORD` u otros eventos técnicos con la narrativa clínica.

---

# 17. Consulta de auditoría

## AH-107 — Acceso restringido

**Cerrado (auditoría de cierre, 2026-09-11):** la consulta de `AuditEvent` está restringida al Administrador (`user.is_superuser`) — ver `clinical-permissions.md` P-041, que fija esto como regla normativa. Ningún otro actor, incluido el médico asignado, tiene acceso de lectura al log de auditoría; no se expondrá como historial clínico normal.

## AH-108 — Sin endpoint público general

No existirá un endpoint genérico que permita a cualquier actor consultar auditoría por `patient_id`.

## AH-109 — Soporte administrativo explícito

Las herramientas de auditoría para soporte deben contar con un permiso operativo explícito.

## AH-110 — Motivo para acceso excepcional

Una futura función de acceso administrativo excepcional deberá registrar motivo y actor.

## AH-111 — Filtros mínimos

Las consultas internas deberán poder filtrar por actor, acción, recurso y rango temporal cuando se necesite investigar un evento.

## AH-112 — Paginación

Las consultas de auditoría se paginan para evitar cargas masivas.

## AH-113 — No alterar filtros por seguridad

La aplicación debe aplicar autorización antes de ejecutar consultas de auditoría.

---

# 18. Historial clínico y rendimiento

## AH-114 — No cargar toda la historia siempre

Las pantallas deben obtener el historial por páginas.

## AH-115 — Encuentro individual bajo demanda

El detalle completo de un encuentro se consulta cuando el usuario lo solicita o cuando la pantalla lo necesita explícitamente.

## AH-116 — Resumen separado

El resumen clínico del expediente se obtiene sin reconstruir toda la historia si no es necesario.

## AH-117 — Índices de soporte

El modelo de datos debe soportar consultas por paciente y fecha clínica mediante índices apropiados.

## AH-118 — Auditoría indexable

`AuditEvent` deberá poder consultar eficientemente por `occurred_at`, actor y recurso, sin requerir escaneo completo.

---

# 19. Concurrencia y trazabilidad

## AH-119 — Un único resultado de verdad

Sólo las transacciones efectivamente confirmadas generan eventos de éxito.

## AH-120 — Save vs complete

Si un `save_encounter` y un `complete_encounter` compiten, la auditoría debe reflejar únicamente las transacciones que realmente hicieron commit.

## AH-121 — Complete vs complete

Dos intentos simultáneos de completar no pueden producir dos cierres exitosos.

## AH-122 — Complete vs lectura

Una lectura concurrente puede observar el estado que la transacción ya haya confirmado según el nivel de aislamiento; el evento de auditoría representa únicamente operaciones confirmadas.

## AH-123 — Idempotencia

Repetir una petición idempotente no debe crear múltiples objetos clínicos históricos.

---

# 20. Privacidad de los datos de auditoría

## AH-124 — AuditEvent también es sensible

La auditoría de acceso clínico puede revelar qué paciente o recurso fue consultado y, por tanto, debe protegerse.

## AH-125 — Menor cantidad de datos

Sólo se almacenan los metadatos necesarios para trazabilidad.

## AH-126 — No contenido clínico completo

Nunca se registra como metadata el motivo, padecimiento, exploración, diagnóstico o plan completos salvo necesidad explícita y futura aprobada.

## AH-127 — No parámetros indiscriminados

No se registran todos los query parameters ni formularios completos de forma genérica.

## AH-128 — No logs de aplicación como historia

Los logs técnicos de Django, servidor o infraestructura no sustituyen `AuditEvent`.

---

# 21. Errores y fallos

## AH-129 — Fallo antes de mutación

Si una operación falla antes de persistir cambios clínicos, el historial clínico no cambia.

## AH-130 — Error después de mutación no confirmada

No debe quedar una falsa señal de éxito en auditoría.

## AH-131 — Error parcial

Las operaciones críticas deben ser atómicas para evitar una auditoría que describa un estado que nunca existió.

## AH-132 — Correlación

`request_id` puede agrupar eventos de una misma solicitud sin copiar datos sensibles.

---

# 22. Propuesta de esquema mínimo

```text
AuditEvent
---------
id
occurred_at
actor_user_id -> User
actor_role
action
resource_type
resource_id
patient_id -> Patient (nullable)
appointment_id -> Appointment (nullable)
clinical_encounter_id -> ClinicalEncounter (nullable)
result
reason_code (nullable)
request_id (nullable)
metadata (nullable / controlled)
```

## AH-133 — Metadata controlada

Aunque el sistema pueda técnicamente soportar JSON para metadata de auditoría, sólo se permitirán claves explícitamente aprobadas. No es un mecanismo para guardar datos clínicos arbitrarios.

## AH-134 — Relaciones opcionales

No todas las acciones necesitan todas las referencias. Por ejemplo, un evento de autenticación puede no tener paciente.

## AH-135 — No FK polimórnea obligatoria

`resource_type + resource_id` se mantiene como referencia lógica para flexibilidad, mientras las FK específicas se usan cuando aporten integridad real y sean conocidas.

---

# 23. Política de auditoría por operación

| Operación | Resultado clínico | Auditoría propuesta |
|---|---|---|
| Iniciar consulta | crea encuentro / cambia Appointment | `START_ENCOUNTER` |
| Inicio repetido idempotente | sin nuevo encuentro | evento técnico opcional / no nuevo histórico |
| Guardar parcial | actualiza encuentro abierto | `SAVE_ENCOUNTER` |
| Completar | cierre atómico | `COMPLETE_ENCOUNTER` |
| Leer encuentro | sin mutación | `READ_CLINICAL_ENCOUNTER` |
| Leer expediente | sin mutación | `READ_MEDICAL_RECORD` |
| Leer historial | sin mutación | `READ_CLINICAL_HISTORY` |
| Actualizar expediente | mutación longitudinal | `UPDATE_MEDICAL_RECORD` |
| Crear expediente | crea registro por paciente | `CREATE_MEDICAL_RECORD` |
| Acceso denegado | sin mutación | la `action` de la operación intentada, con `result = DENIED` (no un valor `ACCESS_DENIED` separado — ver AH-029) |
| Exportar | fuera del núcleo F3 | acción futura específica |

---

# 24. Diferencia entre cambios clínicos y cambios técnicos

## AH-136 — Cambio clínico

Es una modificación de información que forma parte del estado asistencial, como guardar los campos de un encuentro abierto o actualizar antecedentes longitudinales.

## AH-137 — Cambio de sistema

Es una acción administrativa/técnica como iniciar sesión, consultar datos o realizar una petición.

## AH-138 — Ambos pueden auditarse

La auditoría puede incluir tanto cambios clínicos como accesos sin modificación.

## AH-139 — No todo cambio técnico afecta historia

Leer una historia no altera el historial clínico.

---

# 25. Reglas para futuras correcciones

## AH-140 — Enmienda explícita futura

Si una fase futura permite corregir un registro completado, deberá preservar el original y crear una nueva evidencia de corrección.

## AH-141 — Motivo obligatorio futuro

Las correcciones históricas futuras deberán requerir motivo.

## AH-142 — Actor explícito futuro

Toda enmienda futura deberá identificar al actor autenticado que la realizó.

## AH-143 — Auditoría de enmienda

Toda enmienda futura generará uno o más eventos de auditoría específicos.

---

# 26. Reglas para documentos clínicos futuros

## AH-144 — Documento separado

Los documentos clínicos no se incrustan en `AuditEvent`.

## AH-145 — Descarga auditable

La descarga o visualización de un documento clínico debe ser auditable cuando la función exista.

## AH-146 — Eliminación lógica futura

Si un documento se elimina lógicamente, la auditoría debe conservar evidencia del acto.

---

# 27. Lo que no se debe hacer

## AH-147 — No usar `updated_at` como auditoría

Los timestamps del dominio indican estado temporal del recurso; no sustituyen una bitácora de quién hizo qué.

## AH-148 — No usar `created_by` improvisado

No se agregarán campos de actor a todos los modelos solamente para evitar crear auditoría estructurada.

## AH-149 — No crear snapshots JSON de cada consulta

No se generará una copia completa del encuentro en cada guardado.

## AH-150 — No duplicar historial

No existirán simultáneamente un expediente textual duplicado y los encuentros como fuentes paralelas de verdad.

## AH-151 — No auditar cada input visual

Cambiar de pestaña, mover el foco o escribir una letra no genera eventos de auditoría.

## AH-152 — No borrar logs para ocultar accesos

No habrá funcionalidad clínica para eliminar eventos.

---

# 28. Política propuesta de implementación F3

## AH-153 — Servicio central

La creación de eventos de auditoría deberá estar centralizada en un componente/servicio reutilizable y no dispersa en cada vista.

## AH-154 — Después de autorización

El contexto del actor y el resultado de autorización deben conocerse antes de emitir el evento correspondiente.

## AH-155 — Dentro del caso de uso

La auditoría de una mutación clínica debe estar asociada al caso de uso del servicio, no al ORM genérico.

## AH-156 — No signals para semántica clínica

No utilizar señales de Django para decidir por sí mismas qué representa una acción clínica.

## AH-157 — ORM como soporte

La persistencia del evento es una preocupación técnica; el significado de la acción lo determina el servicio de aplicación.

---

# 29. Política de consulta del historial

## AH-158 — Historia por paciente

La unidad natural de navegación histórica es el paciente autorizado.

## AH-159 — No historia por doctor

La historia no pertenece al médico y no se filtra como “consultas de este médico” salvo que la UI lo solicite como filtro autorizado.

## AH-160 — No historia por clínica como propiedad

La clínica es contexto asistencial, no propietaria del expediente.

## AH-161 — Filtro temporal

La historia debe soportar filtros por periodo cuando la pantalla los necesite.

## AH-162 — Paginación estable

La paginación debe usar un orden determinista, por ejemplo fecha clínica descendente e identificador como desempate.

---

# 30. Política de accesos excepcionales

## AH-163 — No romper `deny by default`

Una necesidad de soporte no justifica un bypass universal.

## AH-164 — Break-glass futuro

Un mecanismo de emergencia, si alguna fase futura lo requiere, deberá ser explícito, temporal, altamente auditable y separado de los permisos normales.

## AH-165 — No implementar break-glass en F3

Fase 3 no necesita un mecanismo de emergencia genérico.

---

# 31. Integración con permisos

## AH-166 — Permisos determinan acceso

`clinical-permissions.md` sigue siendo la fuente de verdad para decidir si una lectura o escritura está autorizada.

## AH-167 — Auditoría registra decisión

`clinical-audit-and-history.md` registra el resultado de la operación; no redefine quién puede hacerla.

## AH-168 — Médico asignado

Las operaciones sobre un encuentro abierto realizadas por su médico asignado deben quedar auditadas.

## AH-169 — Otro médico

La lectura longitudinal autorizada por `DoctorPatientRelationship` debe quedar auditada.

## AH-170 — Paciente

La lectura propia puede quedar auditada; la capacidad de modificar la nota clínica continúa prohibida.

## AH-171 — Responsable

Las lecturas autorizadas por relación activa deben quedar auditadas.

## AH-172 — Administrador

Los accesos administrativos extraordinarios deben generar evidencia reforzada.

---

# 32. Checklist de cierre

## AH-173 — Identidad del actor

Toda acción clínica relevante puede atribuirse al usuario autenticado.

## AH-174 — Identidad del recurso

Toda acción relevante identifica el recurso afectado cuando aplica.

## AH-175 — Momento del evento

El tiempo se asigna en servidor.

## AH-176 — Resultado

El evento distingue éxito y rechazo/fallo de manera estable.

## AH-177 — No secretos

No hay secretos en auditoría.

## AH-178 — No contenido clínico duplicado

La auditoría no funciona como copia del expediente.

## AH-179 — Historial inmutable

Los encuentros completados permanecen intactos.

## AH-180 — Sin reapertura

La historia no puede reabrirse mediante una operación escondida.

## AH-181 — Acceso al historial protegido

La consulta longitudinal sigue las reglas de autorización.

## AH-182 — Auditoría protegida

La auditoría tiene permisos propios.

## AH-183 — Paginación

Historia y auditoría no requieren cargas ilimitadas.

## AH-184 — Integridad transaccional

Los eventos de éxito de operaciones críticas reflejan sólo estados confirmados.

---

# 33. Decisiones cerradas propuestas

| ID | Decisión | Estado |
|---|---|---|
| AH-001 | Historia y auditoría son distintos | CERRADA |
| AH-005 | No borrar historia clínicamente relevante | CERRADA |
| AH-011 | `AuditEvent` separado | CERRADA |
| AH-021 | Auditar inicio de consulta | CERRADA |
| AH-022 | Auditar guardados persistidos | CERRADA |
| AH-023 | Auditar compleción | CERRADA |
| AH-037 | `COMPLETED` forma parte de historia | CERRADA |
| AH-048 | Encuentro completado inmutable | CERRADA |
| AH-055 | Sin amendments en F3 | CERRADA |
| AH-064 | Auditar completion sólo después del commit | CERRADA |
| AH-082 | AuditEvent append-only | CERRADA |
| AH-101 | Historia separada visualmente de actividad técnica | CERRADA |
| AH-107 | Auditoría con permisos propios | CERRADA |
| AH-124 | AuditEvent es información sensible | CERRADA |
| AH-165 | Sin break-glass en F3 | CERRADA |

---

# 34. Fuera de alcance de Fase 3

Queda expresamente fuera:

- versionado completo de notas clínicas;
- mecanismo de amendment formal;
- firma electrónica avanzada;
- sellado criptográfico o blockchain de auditoría;
- SIEM empresarial;
- exportación clínica avanzada;
- interoperabilidad HL7/FHIR;
- retención legal universal configurable;
- break-glass de emergencia;
- expediente de múltiples organizaciones con políticas federadas;
- auditoría de cada evento de frontend;
- analítica clínica derivada de los logs.

---

# 35. Invariantes de alto nivel

**I-AH-001.** Un encuentro `COMPLETED` forma parte de la historia clínica del paciente.  
**I-AH-002.** Un encuentro `COMPLETED` no puede modificarse funcionalmente.  
**I-AH-003.** Un encuentro `COMPLETED` no puede reabrirse.  
**I-AH-004.** Un `AuditEvent` no modifica por sí mismo ningún recurso clínico.  
**I-AH-005.** Un evento de éxito clínico representa una operación efectivamente confirmada.  
**I-AH-006.** La identidad del actor proviene del contexto autenticado del servidor.  
**I-AH-007.** La auditoría no almacena secretos.  
**I-AH-008.** La auditoría no sustituye al historial clínico.  
**I-AH-009.** La historia no depende del médico actual del paciente.  
**I-AH-010.** Una cita `CANCELLED` o `NO_SHOW` no crea historial clínico.  
**I-AH-011.** Leer la historia no concede derecho de edición.  
**I-AH-012.** Auditar una operación no autoriza la operación.  

---

# 36. Criterios de aceptación

### AC-AH-001 — Historia

Un encuentro completado aparece una sola vez en el historial y conserva su identidad y fecha clínica.

### AC-AH-002 — Inmutabilidad

Una petición normal de modificación contra un encuentro completado es rechazada.

### AC-AH-003 — Auditoría de inicio

Un inicio exitoso produce un evento de auditoría correspondiente.

### AC-AH-004 — Auditoría de guardado

Un guardado exitoso produce un evento; un fallo no se registra como éxito.

### AC-AH-005 — Auditoría de cierre

La finalización produce un evento sólo cuando ambas transiciones de cierre han sido confirmadas.

### AC-AH-006 — Lectura

Las lecturas clínicas relevantes pueden atribuirse al actor autenticado.

### AC-AH-007 — Privacidad

Los eventos no contienen la nota clínica completa ni secretos de sesión.

### AC-AH-008 — Concurrencia

Dos cierres concurrentes no producen dos cierres exitosos ni dos versiones de historia.

### AC-AH-009 — Permisos

Un actor sin autorización no obtiene historia clínica y su acceso no crea un bypass de seguridad.

### AC-AH-010 — Integridad histórica

Cambios posteriores de médico, clínica o relación médico-paciente no modifican retrospectivamente la autoría de encuentros completados.

---

# 37. Próximos documentos relacionados

Este documento queda como referencia de trazabilidad para:

1. `phase-3-testing-strategy.md`
2. ADRs de auditoría e historial
3. implementación de `AuditEvent`
4. pruebas de acceso y seguridad

La siguiente capa no debe crear nuevos conceptos clínicos sin contrastarlos con este documento y con las decisiones ya cerradas de Fase 3.

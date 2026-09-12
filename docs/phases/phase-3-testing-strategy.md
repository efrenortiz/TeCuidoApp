# TeCuidoApp — Fase 3: Clinical Testing Strategy

## 1. Propósito y alcance

Este documento define la estrategia de pruebas para Fase 3 del dominio clínico de TeCuidoApp.

La estrategia verifica que el comportamiento implementado sea consistente con:

- `phase-3-clinical-encounter.md`
- `clinical-encounter-workflow.md`
- `clinical-encounter-rules.md`
- `clinical-encounter-domain.md`
- `clinical-record-domain.md`
- `clinical-data-model.md`
- `clinical-permissions.md`
- `clinical-security-and-privacy.md`
- `clinical-service-contracts.md`
- `clinical-api-contracts.md`
- `phase-3-clinical-ux.md`
- `clinical-screens.md`
- `clinical-audit-and-history.md`

Fase 3 no se considera terminada porque "funciona en el navegador". La salida requiere evidencia suficiente en dominio, base de datos, permisos, servicios, API, UI, concurrencia, seguridad y auditoría.

## 2. Objetivos

La estrategia tiene seis objetivos principales:

1. demostrar que un Appointment elegible puede originar exactamente un ClinicalEncounter;
2. demostrar que el encuentro puede guardarse parcialmente y completarse de forma atómica;
3. demostrar que el expediente conserva historia clínica sin corrupción ni duplicación;
4. demostrar que los permisos no pueden saltarse mediante URLs, IDs o llamadas directas;
5. demostrar que operaciones concurrentes no generan estados imposibles;
6. demostrar que la trazabilidad clínica y de seguridad es verificable.

## 3. Principios de prueba

### TS-001 — Probar comportamiento observable

Cada regla relevante debe verificarse mediante una prueba que observe resultado, estado o efecto persistido.

### TS-002 — El dominio es fuente de verdad

La prueba debe privilegiar invariantes del dominio sobre detalles accidentales de implementación.

### TS-003 — La UI no es evidencia suficiente

Una prueba de navegador exitosa no sustituye pruebas de servicio, base de datos y autorización.

### TS-004 — Seguridad desde el servidor

Toda autorización clínica debe probarse contra el endpoint o servicio protegido, no solo contra la visibilidad de botones.

### TS-005 — Concurrencia explícita

Las operaciones de inicio y cierre requieren pruebas concurrentes; una secuencia lineal de tests no demuestra integridad bajo carrera.

### TS-006 — No probar solamente el happy path

Cada operación crítica debe tener casos nominales, inválidos, no autorizados, concurrentes y de repetición cuando aplique.

### TS-007 — Tests deterministas

Los tests no deben depender de reloj real, orden accidental entre tests, datos compartidos ni sleeps arbitrarios.

### TS-008 — Datos clínicos mínimos realistas

Los fixtures deben usar contenido clínico sintético suficientemente realista para atravesar validaciones de contenido, sin utilizar datos personales reales.

### TS-009 — Sin snapshots masivos innecesarios

No se utilizarán snapshots de páginas completas cuando una aserción semántica sea suficiente.

### TS-010 — Fallos aislados

Cada test debe limpiar sus cambios y poder ejecutarse de forma aislada.

## 4. Pirámide de pruebas

### Nivel 1 — Unitarias de dominio

Prueban reglas puras, normalización, validación de contenido, transición de estados y construcción de errores.

### Nivel 2 — Servicios y transacciones

Prueban permisos efectivos, atomicidad, persistencia, idempotencia y concurrencia sobre la base de datos real de pruebas.

### Nivel 3 — API

Prueban contratos HTTP, serialización, autenticación, autorización, códigos de estado y errores.

### Nivel 4 — Integración

Prueban interacción entre Agenda, pacientes, médicos, clínicas, expediente y auditoría.

### Nivel 5 — UI / navegador

Prueban navegación, visibilidad contextual, formularios, feedback, errores y flujo nominal.

### Nivel 6 — seguridad

Prueban bypass de permisos, IDOR, exposición de datos y efectos no autorizados.

## 5. Herramientas y convenciones

### TS-011 — Framework principal

Se utilizará el framework de pruebas ya establecido por el proyecto: `python manage.py test` (Django test utilities/`TestCase`/`TransactionTestCase`). **Corrección de consistencia (revisión de cierre, 2026-09-11):** una redacción anterior mencionaba `pytest` como alternativa preferente; el proyecto no usa `pytest` en ninguna fase (no está en `requirements.txt`, no existe `pytest.ini`/`conftest.py`) — el runner real y único es el de Django, ya usado consistentemente desde Fase 1.

### TS-012 — Base de datos de pruebas

Los tests de persistencia deben ejecutarse sobre la misma familia de base de datos soportada por producción, particularmente PostgreSQL cuando se prueben constraints, locking o comportamiento transaccional específico.

### TS-013 — Fixtures reutilizables

Crear fixtures para usuario paciente, responsable, médico, clínica, `DoctorClinic`, Appointment elegible y Appointment en estados finales.

### TS-014 — Builders de datos clínicos

Se recomienda un builder pequeño para generar encuentros con los cinco campos obligatorios y variantes opcionales.

### TS-015 — Identificadores no predecibles en tests de seguridad

Los tests de autorización deben usar IDs válidos de otros pacientes para demostrar que conocer un ID no concede acceso.

## 6. Matriz de ambientes

| Ambiente | Propósito | Base de datos | Datos reales |
|---|---|---|---|
| Unit | Reglas puras | No necesaria | Prohibidos |
| Integration | Servicios/ORM | PostgreSQL de test | Prohibidos |
| API | Contratos HTTP | PostgreSQL de test | Prohibidos |
| Browser | UX/UI | PostgreSQL de test | Prohibidos |
| Security | Bypass/IDOR | PostgreSQL de test | Prohibidos |

## 7. Testabilidad del dominio

### TS-016 — Reglas deterministas

Las reglas que no requieren I/O deben poder probarse sin levantar toda la aplicación.

### TS-017 — Tiempo inyectable cuando sea necesario

Las pruebas de timestamps deben poder controlar el instante de prueba sin depender de delays reales.

### TS-018 — Identidad explícita

Los servicios deben recibir el actor de forma determinista, de modo que los tests puedan variar paciente, responsable, médico y administrador.

### TS-019 — Errores de dominio estables

Los tests deben asertar tipos/códigos de error estables y no mensajes accidentales cuando el contrato así lo permita.

## 8. Fixtures mínimos

### TS-020 — Paciente A

Paciente con identidad válida y sin encuentros previos.

### TS-021 — Paciente B

Paciente distinto para pruebas de aislamiento e IDOR.

### TS-022 — Médico asignado

Médico con relación válida con clínica y Appointment elegible.

### TS-023 — Médico no asignado

Médico válido en la clínica, pero no asignado a la cita probada.

### TS-024 — Médico con relación histórica

Médico con `DoctorPatientRelationship` activa o histórica según el caso, para demostrar independencia respecto a Appointment.

### TS-025 — Responsable autorizado

Responsable con `ResponsiblePatientRelationship.ACTIVE`.

### TS-026 — Responsable no autorizado

Responsable sin relación activa con el paciente objetivo.

### TS-027 — Administrador

Usuario con `is_superuser=True` y, cuando corresponda, condición operacional `DoctorClinic`.

### TS-028 — Appointment elegible

Appointment `SCHEDULED`, médico asignado y paciente presente según el flujo.

### TS-029 — Appointment IN_CONSULTATION

Appointment iniciado y ligado a un ClinicalEncounter `IN_PROGRESS`.

### TS-030 — Appointment COMPLETED

Appointment terminado y ligado a ClinicalEncounter `COMPLETED`.

### TS-031 — Appointment CANCELLED

Debe utilizarse para verificar ausencia de ClinicalEncounter.

### TS-032 — Appointment NO_SHOW

Debe utilizarse para verificar ausencia de ClinicalEncounter.

## 9. Datos clínicos sintéticos

### TS-033 — Fixture válido mínimo

Debe contener contenido real en los cinco campos requeridos.

### TS-034 — Fixture de campo vacío

Debe probar `null`, cadena vacía y espacios según el contrato de cada campo.

### TS-035 — Fixture de placeholder

Debe incluir `N/A`, `No aplica`, equivalentes y variantes de mayúsculas/espacios.

### TS-036 — Texto corto válido

Debe demostrarse que no existe un mínimo arbitrario de caracteres cuando el contenido es clínicamente válido.

### TS-037 — Diagnóstico libre

Debe probarse texto libre sin obligación de catálogo CIE-10.

## 10. Cobertura por regla de ClinicalEncounter

### TS-038 — Una cita origina como máximo un encuentro

Verificar unicidad con una operación nominal y una segunda operación repetida.

### TS-039 — Appointment obligatorio

Intentar crear encuentro sin Appointment mediante el nivel apropiado y verificar rechazo.

### TS-040 — Solo médico asignado puede iniciar

Un médico no asignado debe recibir rechazo y no debe producir mutación.

### TS-041 — Presencia del paciente

Cuando la regla de Agenda lo requiera, probar inicio con condición de presencia válida e inválida.

### TS-042 — CANCELLED no inicia

Verificar rechazo y ausencia de encuentro.

### TS-043 — NO_SHOW no inicia

Verificar rechazo y ausencia de encuentro.

### TS-044 — IN_CONSULTATION no se cancela

Probar que las acciones de cancelación/NO_SHOW no son válidas después de inicio.

### TS-045 — Inicio atómico

Forzar fallo en uno de los lados de la operación y verificar que no quede estado parcial.

### TS-046 — Doble inicio idempotente

Enviar dos solicitudes equivalentes y demostrar que existe un solo encuentro.

### TS-047 — Doble inicio concurrente

Ejecutar dos transacciones concurrentes y verificar un único registro y un único estado final consistente.

### TS-048 — Guardado parcial

Guardar con uno o más campos faltantes y comprobar persistencia.

### TS-049 — Guardado exitoso actualiza updated_at

Verificar que `updated_at` cambia en un guardado efectivo.

### TS-050 — Guardado fallido no destruye última versión

Provocar un fallo y verificar que permanece el último contenido válido persistido.

### TS-051 — Interrupción no autocierra

Simular salida o pausa y verificar `IN_PROGRESS`.

### TS-052 — Reanudación

Volver a abrir un encuentro `IN_PROGRESS` y verificar que conserva identidad y datos.

### TS-053 — Múltiples encuentros abiertos

Un mismo médico debe poder mantener encuentros abiertos de distintas citas válidas.

### TS-054 — Completar con cinco campos válidos

Verificar transición a `COMPLETED`.

### TS-055 — Completar con campo requerido ausente

Verificar rechazo y conservación de `IN_PROGRESS`.

### TS-056 — Completar con placeholder

Verificar rechazo de contenido inválido.

### TS-057 — Completar guarda cambios finales

Enviar cambios junto con la acción de completar y verificar que quedan persistidos antes del cierre.

### TS-058 — Cierre atómico

Forzar error durante el cierre y verificar que Appointment y Encounter no quedan en estados distintos.

### TS-059 — Doble completar

**Corrección de consistencia (auditoría de cierre, 2026-09-11) — Decisión D-001:** el comportamiento ya no es "idempotente o error", sino exclusivamente idempotente, para eliminar la contradicción que existía entre `clinical-service-contracts.md` (SC-065, ya corregido) y `clinical-api-contracts.md` (API-067).

Ejecutar completar dos veces sobre el mismo encuentro y verificar que la segunda solicitud (sin contenido distinto) devuelve el mismo resultado exitoso que la primera (200 OK, mismo encuentro `COMPLETED`), sin re-ejecutar el cierre ni alterar `completed_at`. Verificar además que una segunda solicitud que sí envía contenido distinto es rechazada con `EncounterImmutable`.

### TS-060 — Modificación después de COMPLETED

Verificar rechazo absoluto.

### TS-061 — Reapertura prohibida

Intentar pasar `COMPLETED → IN_PROGRESS` y verificar rechazo.

### TS-062 — Delete prohibido

Intentar eliminación funcional y verificar que no existe operación permitida.

## 11. Pruebas de timestamps

### TS-063 — created_at

Debe corresponder al momento de creación persistida del encuentro.

### TS-064 — started_at

Debe establecerse al inicio y no modificarse en guardados posteriores.

### TS-065 — updated_at

Debe reflejar el último guardado exitoso.

### TS-066 — completed_at

Debe quedar `NULL` mientras está `IN_PROGRESS` y establecerse al completar.

### TS-067 — Orden temporal

Verificar `created_at ≤ started_at ≤ completed_at` cuando aplique.

### TS-068 — No alterar timestamps manualmente

Campos controlados por servidor no deben aceptar valores arbitrarios desde API.

## 12. MedicalRecord

### TS-069 — Un expediente por paciente

Verificar unicidad de `Patient 1 ─── 1 MedicalRecord`.

### TS-070 — Creación lazy

Un paciente puede no tener expediente hasta la primera operación clínica que lo requiera.

### TS-071 — Creación idempotente

Solicitudes concurrentes o repetidas no deben producir expedientes duplicados.

### TS-072 — Atomicidad con primer encuentro

Cuando el contrato lo indique, la creación necesaria del expediente debe formar parte de la misma transacción del inicio clínico.

### TS-073 — No reasignación

Un expediente no puede pasar de un paciente a otro.

### TS-074 — Identidad canónica

Verificar que la identidad personal procede de `Patient` y no de copias persistidas.

### TS-075 — Historial ordenado

Verificar que encounters completados aparecen en orden clínico esperado.

### TS-076 — No existe current encounter persistido

El sistema no debe crear un campo duplicado para indicar el encuentro "actual".

## 13. Antecedentes longitudinales

### TS-077 — Edición explícita de antecedentes

Modificar un dato longitudinal autorizado y verificar persistencia.

### TS-078 — No confundir antecedentes con historia

Una modificación actual no debe reescribir contenido histórico de un encuentro completado.

### TS-079 — Alergias

Las alergias deben probarse como dato longitudinal separado de `ClinicalAlert` cuando corresponda.

### TS-080 — Medicamentos actuales vs recetas históricas

Modificar medicamentos actuales no debe alterar recetas históricas.

### TS-081 — Estudios actuales vs resultados históricos

La visualización debe distinguir orden/resultado/histórico sin sobrescribir encuentros.

## 14. Permisos clínicos

### TS-082 — Paciente lee solo lo propio

Intentar acceder a expediente de otro paciente y verificar `403` o error contractual equivalente, no filtrado accidental.

### TS-083 — Responsable solo con relación activa

Probar responsable autorizado y no autorizado.

### TS-084 — Médico asignado modifica encuentro abierto

Debe poder leer y modificar su encuentro `IN_PROGRESS`.

### TS-085 — Médico no asignado no modifica encuentro

Debe rechazarse cualquier mutación aun cuando esté en la misma clínica.

### TS-086 — Médico con relación longitudinal puede leer según contrato

Verificar lectura histórica cuando exista `DoctorPatientRelationship` válida.

### TS-086a — Médico sin relación ni asignación no puede leer (obligatorio)

**Añadido en la auditoría de cierre (2026-09-11):** era el único caso negativo de lectura no cubierto explícitamente por esta estrategia — TS-085 solo cubre modificación, no lectura. Dado que la fuga de lectura no autorizada es el riesgo más severo de un sistema de expedientes clínicos, este test es obligatorio.

Un médico sin `DoctorPatientRelationship` activa con el paciente y que no es el médico asignado a ninguna `Appointment`/`ClinicalEncounter` de ese paciente intenta leer su expediente/historial → debe rechazarse (código de no-divulgación de `clinical-permissions.md`/`clinical-security-and-privacy.md`), sin revelar si el expediente existe.

### TS-087 — Appointment aislada no crea DoctorPatientRelationship

Después del primer encuentro verificar que no apareció ni se activó automáticamente una relación.

### TS-088 — Administrador

Verificar alcance administrativo conforme al contrato, sin elevarlo a capacidad de modificación clínica prohibida.

### TS-089 — Indirect object reference

Sustituir IDs por IDs de otro paciente en URLs, payloads y endpoints secundarios.

### TS-090 — Permiso en endpoint directo

Llamar al endpoint sin pasar por UI y verificar que la autorización sigue aplicada.

## 15. API

### TS-091 — Contrato de inicio

Probar request válida, request repetida, estado inválido, actor inválido y paciente inexistente.

### TS-092 — Contrato de lectura

Verificar shape estable y ausencia de campos no autorizados.

### TS-093 — Contrato de guardado

Verificar partial update, campos desconocidos, timestamps protegidos y estado `IN_PROGRESS`.

### TS-094 — Contrato de completar

Verificar persistencia final, validación y transición atómica.

### TS-095 — Contrato de expediente

Verificar lectura autorizada y orden del histórico.

### TS-096 — Errores HTTP

Los códigos deben distinguir autenticación, autorización, validación y conflicto/estado sin filtrar excepciones internas.

### TS-097 — No CRUD genérico

No deben existir endpoints que permitan borrar o mutar directamente recursos clínicos fuera de los contratos explícitos.

## 16. Seguridad

### TS-098 — Usuario anónimo

No debe leer ni modificar información clínica.

### TS-099 — Session fixation / auth boundary

Verificar que un usuario autenticado no puede reutilizar privilegios de otra identidad mediante manipulación del request.

### TS-100 — CSRF

Para operaciones web mutantes protegidas por sesión, verificar la protección requerida por el stack.

### TS-101 — No datos clínicos en logs normales

Provocar errores de API y verificar que no se registren bodies clínicos completos en logs operativos ordinarios.

### TS-102 — No secretos en errores

Verificar que tracebacks o configuraciones sensibles no lleguen a respuestas.

### TS-103 — Caché privada

Las respuestas clínicas no deben quedar disponibles para un usuario diferente por caché compartida.

### TS-104 — Documentos privados

Cuando existan documentos, probar acceso por URL directa sin autorización.

## 17. Auditoría

### TS-105 — Inicio exitoso auditado

Debe existir evento de auditoría para la acción definida como auditable.

### TS-106 — Inicio fallido

Un evento explícito de rechazo/error es opcional (`clinical-audit-and-history.md` AH-024/AH-066 — "puede generar"); lo obligatorio y ya verificado es que un intento fallido **nunca** se registre como `START_ENCOUNTER`/`SUCCESS` — sin falsear un éxito.

### TS-107 — Inicio idempotente

La segunda solicitud no debe fabricar un falso segundo evento clínico; el evento técnico debe seguir la política de auditoría.

### TS-108 — Guardado exitoso auditado

Probar que la operación relevante queda trazable.

### TS-109 — Compleción atómica auditada

Debe existir un evento representativo del cierre efectivo y no de un cierre parcial.

### TS-110 — Acceso de lectura auditado

Leer expediente/historial cuando corresponda y verificar el evento.

### TS-111 — Acceso denegado auditado

Verificar trazabilidad del rechazo sin almacenar innecesariamente contenido clínico.

### TS-112 — Auditoría inmutable

Intentar modificar o borrar un `AuditEvent` desde las rutas funcionales prohibidas.

## 18. UI / navegador

### TS-113 — Agenda muestra iniciar cuando corresponde

La acción debe aparecer para el médico correcto y cita elegible.

### TS-114 — Agenda no reemplaza autorización

Ocultar la acción no debe ser el único mecanismo; los tests de API deben cubrirlo.

### TS-115 — Identidad inequívoca del paciente

La pantalla de consulta debe mostrar suficiente contexto para evitar confusión.

### TS-116 — Cinco campos visibles

Todos los campos mínimos deben aparecer de forma comprensible.

### TS-117 — Guardar no completar

Después de guardar, el encuentro sigue `IN_PROGRESS`.

### TS-118 — Indicador de persistencia

Debe existir feedback claro de último guardado exitoso y de fallo.

### TS-119 — Validación visible

Los errores de campos obligatorios deben ser localizables y accionables.

### TS-120 — Completion

La acción de completar debe requerir explicitud y reflejar el estado final.

### TS-121 — Pantalla completada bloqueada

Después de `COMPLETED` no deben aparecer controles de edición clínica.

### TS-122 — Reanudar encuentro

Un encuentro `IN_PROGRESS` debe poder retomarse conforme a permisos.

## 19. Concurrencia

### TS-123 — Inicio concurrente

Dos actores o requests que compiten por el mismo Appointment no deben producir doble ClinicalEncounter.

### TS-124 — Guardado concurrente

Verificar la política elegida para dos guardados sobre el mismo encuentro.

### TS-125 — Guardar vs completar

Probar carrera entre save y complete; el resultado debe respetar el estado final contractual.

### TS-126 — Completar vs completar

Dos completions concurrentes no deben generar estados imposibles ni dos cierres efectivos incompatibles.

### TS-127 — Request después del cierre

Una mutación que llegue después de `COMPLETED` debe ser rechazada.

### TS-128 — Appointment y Encounter consistentes

No debe existir combinación persistente inválida entre ambos estados.

## 20. Integridad de base de datos

### TS-129 — Constraint de unicidad

Verificar unicidad de Appointment por ClinicalEncounter a nivel de DB.

### TS-130 — Foreign keys

Eliminar o desconectar entidades referenciadas debe fallar o comportarse conforme al contrato; no dejar huérfanos clínicos.

### TS-131 — Campos obligatorios de esquema

Las columnas indispensables deben tener constraints adecuados.

### TS-132 — Índices críticos

Verificar que existan índices para búsquedas de historial y resolución por Appointment/Paciente conforme al diseño.

### TS-133 — Integridad no depende solo de ORM

Un test debe intentar violar una regla a bajo nivel cuando sea razonable y verificar que PostgreSQL la impide.

## 21. Pruebas de regresión con Fase 2

### TS-134 — Agenda nominal no clínica

Todos los tests existentes de Agenda deben seguir pasando.

### TS-135 — Cancelación previa al inicio

Una cita `SCHEDULED` debe seguir pudiendo cancelarse cuando las reglas de Agenda lo permiten.

### TS-136 — NO_SHOW previo al inicio

Debe permanecer disponible antes de `IN_CONSULTATION` conforme al contrato de Agenda.

### TS-137 — Confirmación de cita

Las reglas previas de confirmación no deben alterarse por Fase 3.

### TS-138 — Availability

Disponibilidad, holds y reservas deben conservar su comportamiento.

### TS-139 — Permisos Fase 2

Las reglas de paciente, responsable, médico y administrador de Agenda deben permanecer intactas salvo la transición explícita a consulta.

## 22. Casos negativos prioritarios

| Caso | Resultado esperado |
|---|---|
| Médico no asignado inicia | Rechazo |
| Appointment CANCELLED inicia | Rechazo |
| Appointment NO_SHOW inicia | Rechazo |
| Segundo inicio | Idempotencia / mismo encuentro |
| Completar con datos vacíos | Rechazo |
| Completar con placeholder | Rechazo |
| Editar COMPLETED | Rechazo |
| Reabrir COMPLETED | Rechazo |
| Otro médico modifica | Rechazo |
| Otro paciente accede | Rechazo |
| Payload cambia patient_id | Rechazo |
| Payload cambia doctor_id | Rechazo |
| Payload cambia timestamps | Ignorado o rechazado |
| DELETE clínico | No disponible |
| Carrera start/start | Un solo encuentro |
| Carrera save/complete | Estado consistente |
| Carrera complete/complete | Un solo cierre efectivo |

## 23. Contrato de pruebas por servicio

### 23.1 `start_encounter`

Debe probar:

- autenticación;
- actor médico;
- asignación;
- estado `SCHEDULED`;
- presencia cuando corresponda;
- ausencia de encuentro previo;
- creación transaccional;
- idempotencia;
- concurrencia;
- auditoría.

### 23.2 `save_encounter`

Debe probar:

- encuentro existente;
- estado `IN_PROGRESS`;
- médico autorizado;
- partial update;
- normalización;
- persistencia;
- `updated_at`;
- concurrencia;
- auditoría.

### 23.3 `complete_encounter`

Debe probar:

- cinco mínimos;
- validación de placeholders;
- guardado final;
- atomicidad;
- timestamps;
- transición Appointment;
- inmutabilidad;
- auditoría.

### 23.4 `MedicalRecordService`

Debe probar:

- resolución del paciente;
- creación lazy;
- unicidad;
- lectura autorizada;
- actualización longitudinal;
- separación de historia.

## 24. Pruebas de contratos de API

Cada endpoint debe tener como mínimo una tabla de casos con:

| Dimensión | Caso |
|---|---|
| Auth | Anónimo |
| Auth | Usuario autenticado |
| Role | Rol correcto |
| Role | Rol incorrecto |
| Scope | Paciente propio |
| Scope | Paciente ajeno |
| State | Estado esperado |
| State | Estado inválido |
| Payload | Válido |
| Payload | Faltante |
| Payload | Placeholder |
| Payload | Campo desconocido |
| Race | Repetición |
| Error | Respuesta estable |

## 25. Property-based / invariant testing

No es obligatorio introducir property-based testing como dependencia nueva de Fase 3. Cuando resulte conveniente, pueden expresarse invariantes con generación de estados simples.

### TS-140 — Nunca dos encuentros para la misma cita

Para cualquier secuencia válida de starts repetidos, el conteo final debe ser 0 o 1, nunca mayor que 1.

### TS-141 — COMPLETED nunca regresa a IN_PROGRESS

Para cualquier secuencia de comandos válida e inválida, una vez completado el encuentro, ninguna mutación funcional permitida debe revertirlo.

### TS-142 — Historia no desaparece

Guardar/editar antecedentes actuales no debe eliminar encuentros históricos.

## 26. Pruebas de migraciones

### TS-143 — Migraciones limpias

Aplicar todas las migraciones sobre una base vacía.

### TS-144 — Migraciones reproducibles

Ejecutar la cadena completa en orden y verificar esquema final esperado.

### TS-145 — No migraciones pendientes

`makemigrations --check` debe no reportar cambios pendientes cuando el código esté cerrado.

### TS-146 — Constraints e índices

Verificar que las migraciones creen efectivamente los constraints e índices documentados.

## 27. Calidad estática y checks

Antes de cerrar Fase 3 deben ejecutarse, como mínimo:

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

Cuando existan checks o linters del proyecto, deben ejecutarse además sin introducir herramientas nuevas únicamente por esta fase.

## 28. Estrategia de transacciones

Los tests transaccionales deben distinguir claramente entre:

- rollback del servicio;
- integrity error de PostgreSQL;
- conflicto de estado;
- autorización previa a la transacción.

### TS-147 — Rollback completo

Un fallo dentro de una operación clínica no debe dejar una parte de la transacción persistida.

### TS-148 — No confundir rollback con compensación

Fase 3 debe preferir una sola transacción atómica cuando el contrato así lo requiere, en lugar de dos operaciones con compensación manual.

## 29. Estrategia de concurrencia real

Las pruebas de carrera deben usar barreras/sincronización determinista, no `sleep(1)` como mecanismo principal.

### TS-149 — Dos workers

Crear dos workers que intenten ejecutar simultáneamente la misma operación crítica.

### TS-150 — Verificación posterior

La aserción debe hacerse después de que ambas transacciones concluyan y sobre la base de datos, no sobre respuestas aisladas solamente.

### TS-151 — Repetibilidad

Los tests de concurrencia deben ejecutarse varias veces durante validación de release para reducir riesgo de carreras intermitentes.

## 30. Seguridad contra IDOR

### TS-152 — Encounter de otro paciente

Cambiar únicamente el identificador del encuentro en una URL o request debe producir rechazo.

### TS-153 — Record de otro paciente

Cambiar únicamente el identificador del expediente debe producir rechazo.

### TS-154 — Appointment ajeno

Intentar iniciar consulta sobre una cita de otro paciente debe producir rechazo.

### TS-155 — ID no existente

Un ID inexistente no debe convertirse en un error 500 ni revelar información interna.

## 31. Pruebas de privacidad

### TS-156 — Minimización de payload

La API debe devolver solamente la información necesaria para la vista autorizada.

### TS-157 — No exposición en mensajes

Errores de permisos deben evitar revelar existencia de recursos no autorizados cuando el contrato así lo exige.

### TS-158 — Back button / cache

Volver a una pantalla clínica después de logout o cambio de usuario no debe mostrar datos privados mediante caché cliente/servidor inapropiada.

### TS-159 — Descargas privadas

Recursos documentales protegidos deben negar acceso directo a actores no autorizados.

## 32. UX y accesibilidad

### TS-160 — Navegación con teclado

Las acciones primarias y campos deben poder operarse con teclado.

### TS-161 — Etiquetas asociadas

Los campos clínicos deben tener labels accesibles.

### TS-162 — Errores comprensibles

Los mensajes deben explicar qué corregir sin exponer detalles internos.

### TS-163 — Estado no solo por color

`IN_PROGRESS` y `COMPLETED` deben diferenciarse mediante texto/semántica además de color.

### TS-164 — Responsive

Las pantallas clínicas deben seguir siendo utilizables en el rango soportado por el proyecto.

## 33. Pruebas de regresión de permisos

Cada cambio en permisos debe ejecutar nuevamente:

- pruebas de paciente;
- responsable;
- médico asignado;
- médico no asignado;
- administrador;
- aislamiento entre pacientes;
- acceso por API;
- acceso por UI.

## 34. Matriz de cobertura de riesgos

| Riesgo | Pruebas principales | Prioridad |
|---|---|---|
| Doble ClinicalEncounter | TS-046, TS-047, TS-123 | Crítica |
| Cierre inconsistente | TS-058, TS-126, TS-128 | Crítica |
| Edición post-completion | TS-060, TS-061 | Crítica |
| Acceso indebido | TS-082–090, TS-152–155 | Crítica |
| Pérdida de historia | TS-073, TS-075, TS-078, TS-142 | Crítica |
| Exposición de datos | TS-101–104, TS-156–159 | Alta |
| Auditoría falsa | TS-105–112 | Alta |
| Regresión Agenda | TS-134–139 | Alta |
| UX incorrecta | TS-113–122 | Media |

## 35. Criterio de cobertura

La cobertura numérica de líneas no será el único gate.

Fase 3 debe alcanzar cobertura de comportamiento en todas las reglas clasificadas como:

- `CRITICAL`: 100% de casos contractuales e invariantes relevantes;
- `HIGH`: casos nominales y negativos completos;
- `MEDIUM`: casos nominales principales y errores representativos;
- `LOW`: cubierta por smoke/integración cuando corresponda.

No se recomienda fijar un único porcentaje global como sustituto de cobertura semántica.

## 36. Datos y privacidad en tests

### TS-165 — Sin PHI real

No introducir datos clínicos reales en fixtures, snapshots, logs o artefactos de CI.

### TS-166 — Datos sintéticos consistentes

Los fixtures sintéticos deben parecer plausibles sin representar a una persona real.

### TS-167 — Limpieza de artefactos

Los reportes y capturas de navegador no deben contener información clínica de usuarios reales.

## 37. CI y pipeline

El pipeline recomendado para una rama clínica es:

1. checks y lint existentes;
2. tests unitarios;
3. tests de servicios/transacciones;
4. tests de API;
5. pruebas de seguridad;
6. pruebas de UI/browser;
7. migraciones/checks finales.

Un fallo en cualquiera de las pruebas críticas bloquea el cierre.

## 38. Smoke suite de Fase 3

Debe existir una suite rápida que cubra como mínimo:

1. login de médico;
2. Appointment elegible;
3. inicio;
4. guardado parcial;
5. completion válido;
6. lectura de expediente;
7. historial del encuentro;
8. acceso denegado para paciente ajeno;
9. edición post-completion rechazada.

## 39. Suite de regresión completa

Antes del release de Fase 3 deben ejecutarse todos los tests existentes de Fase 1 y Fase 2 junto con la suite completa de Fase 3.

La referencia histórica del cierre de Fase 2 es el baseline; cualquier reducción de cobertura funcional debe explicarse como cambio intencional y documentarse.

## 40. Pruebas manuales de aceptación

La verificación manual no reemplaza automatización, pero debe cubrir el recorrido clínico real:

### Flujo nominal

Agenda → Iniciar consulta → Capturar mínimos → Guardar → salir/interrumpir → retomar → completar → consultar historial.

### Flujo negativo

Intentar completar con campos vacíos → placeholder → usuario no autorizado → acceso a otro paciente → intentar modificar completada.

### Flujo de recuperación

Fallo de guardado → verificar último estado persistido → reintentar.

### Flujo concurrente

Dos solicitudes simultáneas de inicio y dos de completion.

## 41. Criterios de release

Fase 3 no debe declararse cerrada mientras exista alguno de los siguientes:

- un test crítico fallando;
- una migración pendiente no intencional;
- una violación de integridad Appointment/ClinicalEncounter;
- un bypass de autorización clínica;
- posibilidad de modificar un encuentro `COMPLETED`;
- pérdida demostrable de historia clínica;
- auditoría falsa de una operación clínica efectiva;
- exposición de datos clínicos fuera del contrato;
- regresión conocida de Agenda sin decisión explícita documentada.

## 42. Evidencia requerida para cierre

La evidencia de cierre debe incluir:

1. salida de `manage.py check`;
2. verificación de migraciones;
3. resultado completo de `python manage.py test`;
4. resultado de pruebas de concurrencia;
5. resultado de pruebas de seguridad/IDOR;
6. evidencia de smoke browser;
7. listado de cualquier excepción aceptada y su justificación.

## 43. Reglas de mantenimiento de tests

### TS-168 — Tests reflejan contratos

Cuando cambie un contrato, deben cambiar primero los tests que expresan ese contrato y después la implementación.

### TS-169 — No testear implementación accidental

Evitar aserciones sobre nombres internos, consultas ORM específicas o estructuras HTML accidentales si no forman parte del contrato.

### TS-170 — Tests claros

Cada test debe expresar una regla única o una interacción coherente.

### TS-171 — Sin tests duplicados innecesarios

La cobertura debe repartirse por nivel para evitar mantener la misma lógica en demasiadas capas.

## 44. Qué queda fuera de Fase 3

No son gates de esta fase salvo que algún requisito previo los active explícitamente:

- CIE-10;
- catálogos diagnósticos;
- recomendaciones clínicas automáticas;
- IA diagnóstica;
- módulos específicos de ginecología/obstetricia;
- prescripción avanzada;
- resultados de estudios avanzados;
- interoperabilidad externa;
- firma digital avanzada;
- enmiendas/versionado de encuentros completados;
- historia clínica distribuida entre organizaciones.

## 45. Invariantes finales de la estrategia

### I-TEST-001

Una Appointment elegible produce cero o un ClinicalEncounter, nunca más de uno.

### I-TEST-002

`COMPLETED` es terminal.

### I-TEST-003

Todo ClinicalEncounter válido referencia una Appointment existente.

### I-TEST-004

Todo ClinicalEncounter completado tiene los cinco campos mínimos con contenido clínico real.

### I-TEST-005

No existe modificación no autorizada de información clínica.

### I-TEST-006

La finalización no deja Appointment y ClinicalEncounter en estados incompatibles.

### I-TEST-007

Un guardado exitoso actualiza `updated_at`.

### I-TEST-008

Un fallo no destruye la última versión persistida.

### I-TEST-009

El expediente de un paciente no se reasigna a otro paciente.

### I-TEST-010

Los encuentros históricos no desaparecen al modificar información longitudinal actual.

### I-TEST-011

Una acción clínica relevante genera la trazabilidad de auditoría definida por contrato.

### I-TEST-012

Conocer un identificador no autorizado nunca concede acceso al recurso.

## 46. Criterios de aceptación finales

La estrategia se considera satisfecha cuando:

- existe suite automatizada para todas las reglas críticas;
- las carreras críticas fueron verificadas con concurrencia real;
- API, servicio y UI comparten el mismo comportamiento contractual;
- las pruebas de seguridad comprueban acceso a objetos de terceros;
- Agenda de Fase 2 conserva sus resultados;
- no existen errores críticos conocidos;
- la evidencia de release está disponible y reproducible.

## 47. Siguiente documento

Con esta estrategia cerrada, el siguiente paso documental corresponde a los **ADRs de Fase 3**, donde se deben registrar como decisiones arquitectónicas formales las reglas que puedan requerir revisión histórica independiente de los contratos funcionales.

---

## Anexo A — Catálogo resumido de suites

| Suite | Contenido | Ejecución |
|---|---|---|
| `clinical_domain` | Invariantes y estados | Cada cambio |
| `clinical_services` | Servicios/transacciones | Cada cambio |
| `clinical_api` | Contratos HTTP | Cada cambio |
| `clinical_permissions` | Autorización/IDOR | Cada cambio sensible |
| `clinical_security` | Seguridad/privacidad | Cada cambio sensible |
| `clinical_audit` | Trazabilidad | Cada cambio clínico |
| `clinical_browser` | Flujo UX | CI/release según costo |
| `regression_phase2` | Agenda existente | Cada PR relevante |
| `clinical_concurrency` | carreras críticas | CI/release |
| `migrations` | esquema/constraints | Cada migración |

## Anexo B — Prioridad recomendada de implementación de tests

### P0 — Antes de cualquier UI clínica

Implementar primero:

- inicio atómico;
- doble inicio;
- guardado parcial;
- completion atómico;
- bloqueo post-completion;
- permisos de médico asignado;
- IDOR;
- integridad DB;
- expediente único.

### P1 — Antes de release funcional

Añadir:

- interrupción/reanudación;
- historial;
- auditoría;
- API completa;
- regresión de Agenda;
- smoke browser.

### P2 — Antes del cierre formal

Añadir:

- pruebas concurrentes repetibles;
- privacidad/caché/documentos;
- accesibilidad;
- evidencia completa de release.

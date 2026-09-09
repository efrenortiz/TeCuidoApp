# ADR-006 — Database Integrity and Transactions

**Estado:** Accepted  
**Fecha:** 2026-09-01  
**Decisores:** Equipo de desarrollo  
**Área:** Persistencia / PostgreSQL / Integridad / Concurrencia

---

# 1. Contexto

TeCuidoApp utilizará **PostgreSQL** como base de datos principal.

El dominio contiene relaciones críticas entre entidades, entre ellas:

```text
User
Person
Doctor
Patient
Responsible
Clinic
Invitation
```

y posteriormente:

```text
Appointment
CareRequest
MedicalEncounter
Prescription
StudyOrder
ClinicalDocument
AuditLog
```

La especificación establece que el modelo de datos debe priorizar:

- integridad referencial;
- claridad;
- facilidad de consulta;
- historial;
- seguridad.

También existen operaciones que deben mantener consistencia entre múltiples entidades.

Por ejemplo, aceptar una invitación puede implicar:

```text
User
Person
Patient
DoctorPatientRelationship
Invitation
```

y posteriormente existirán operaciones aún más sensibles, como (Fase 2, `docs/phases/phase-2-agenda.md`):

```text
crear un hold temporal sobre un horario
crear una cita directamente (sin confirmación posterior — la reserva se cierra en la misma
  operación que la crea)
reprogramar o cancelar una cita
```

La especificación establece explícitamente que el sistema debe utilizar mecanismos apropiados de concurrencia y transacciones de base de datos para evitar dobles reservaciones.

Por ello, la integridad de la información no debe depender únicamente del código de aplicación.

---

# 2. Problema

Una aplicación puede contener validaciones correctas en Python y aun así terminar con datos inconsistentes bajo determinadas circunstancias.

Ejemplo:

```text
Request A:
crear relación Doctor-Patient

Request B:
crear la misma relación simultáneamente
```

O:

```text
Request A:
aceptar invitación

Request B:
aceptar la misma invitación al mismo tiempo
```

También pueden producirse inconsistencias si una operación falla parcialmente:

```text
crear User
   ↓
crear Person
   ↓
ERROR
   ↓
Patient nunca se crea
```

Sin una estrategia de transacciones e integridad de base de datos, podrían quedar registros huérfanos o estados parciales.

La arquitectura debe establecer qué garantías proporciona PostgreSQL y cuáles corresponden a Django.

---

# 3. Decisión

TeCuidoApp utilizará una estrategia de **integridad en múltiples niveles**:

```text
Application Rules
        +
Django Validation
        +
Database Constraints
        +
Transactions
        +
Concurrency Control
```

PostgreSQL será considerado la última línea de defensa para la integridad estructural de los datos.

La aplicación no debe confiar exclusivamente en validaciones realizadas en Python.

---

# 4. Principio de integridad

Las reglas importantes deben imponerse en el nivel más apropiado.

Conceptualmente:

```text
Business rule
     ↓
Application validation
     ↓
Database constraint
     ↓
Transactional boundary
```

No todas las reglas deben convertirse en constraints SQL.

Sin embargo, toda regla que pueda expresarse como una restricción estructural debe evaluarse para implementarse también en PostgreSQL.

---

# 5. Integridad referencial

Las relaciones entre entidades utilizarán Foreign Keys de Django/PostgreSQL.

Ejemplos:

```text id="8xg4ym"
Patient → Person
Doctor → Person
Responsible → Person
DoctorPatientRelationship → Doctor
DoctorPatientRelationship → Patient
ResponsiblePatientRelationship → Responsible
ResponsiblePatientRelationship → Patient
DoctorClinic → Doctor
DoctorClinic → Clinic
Invitation → Doctor
```

No se deben utilizar identificadores sueltos en texto para representar relaciones estructurales.

---

# 6. Foreign Keys como regla de dominio

Cuando dos entidades tengan una relación estructural permanente, debe utilizarse una foreign key.

Ejemplo:

```python id="j5n7gt"
doctor = models.ForeignKey(
    "doctors.Doctor",
    on_delete=models.PROTECT,
)
```

La estrategia exacta de `on_delete` dependerá del significado de la relación.

No utilizar:

```python id="m1d0va"
doctor_id = models.IntegerField()
```

para relaciones que deberían ser foreign keys.

---

# 7. Estrategia `on_delete`

La elección de `on_delete` debe representar una decisión de negocio.

No utilizar `CASCADE` por defecto simplemente por conveniencia.

Debe evaluarse:

### `CASCADE`

Cuando la eliminación del padre realmente implique que el hijo deje de existir y esto sea seguro.

### `PROTECT`

Cuando la existencia del hijo deba impedir la eliminación del padre.

### `SET_NULL`

Cuando la relación pueda quedar vacía sin comprometer integridad y el negocio permita conservar el registro.

### Baja lógica

Cuando la entidad deba permanecer disponible por razones históricas o de trazabilidad.

Para información clínica y registros históricos se deberá priorizar la preservación sobre la eliminación destructiva.

---

# 8. Constraints únicos

Las reglas de unicidad críticas deben respaldarse con constraints de base de datos.

Ejemplo:

```text
User.email = UNIQUE
```

No depender exclusivamente de:

```python
form.is_valid()
```

o:

```python
serializer.is_valid()
```

porque dos requests concurrentes podrían pasar la validación antes de insertar.

---

# 9. Constraints compuestos

Cuando una relación de negocio deba ser única por combinación de campos, se utilizarán constraints compuestos.

Ejemplo conceptual:

```text
Doctor + Patient
```

si la relación correspondiente debe ser única.

Otro ejemplo futuro:

```text
Doctor + Clinic + date/time slot
```

cuando las reglas de agenda lo requieran.

La decisión concreta de cada constraint deberá derivarse del modelo de dominio.

---

# 10. Check Constraints

Cuando una regla pueda expresarse de manera segura como una restricción sobre valores almacenados, se considerará un `CheckConstraint`.

Ejemplo conceptual:

```text
expires_at > created_at
```

o:

```text
start_time < end_time
```

Esto proporciona una segunda protección además de la validación de aplicación.

No deben utilizarse check constraints para reglas que dependan de múltiples tablas si PostgreSQL no puede garantizarlas mediante ese mecanismo.

---

# 11. Índices

Los campos utilizados frecuentemente para:

- búsquedas;
- foreign keys;
- filtros;
- ordenamientos;
- restricciones;

deben evaluarse para crear índices adecuados.

No se deben agregar índices indiscriminadamente.

Cada índice debe aportar un beneficio razonable y considerar el costo de escritura y almacenamiento.

---

# 12. Transacciones

Las operaciones que modifiquen varias entidades de forma que deban considerarse una única operación de negocio deben ejecutarse dentro de una transacción.

En Django se utilizará:

```python id="o7u5vc"
transaction.atomic()
```

cuando corresponda.

Ejemplo:

```text
BEGIN
    crear User
    crear Person
    crear Patient
    crear DoctorPatientRelationship
    marcar Invitation como USED
COMMIT
```

Si cualquiera de esas operaciones falla:

```text
ROLLBACK
```

---

# 13. Regla de atomicidad

No debe existir una operación de negocio que pueda dejar deliberadamente un estado parcial cuando sus pasos deban considerarse inseparables.

Ejemplo incorrecto:

```text
User creado
Person creada
Patient creado
Invitation permanece PENDING
```

si el proceso de registro se considera una sola operación.

La definición del límite transaccional debe responder al caso de uso.

---

# 14. Servicios transaccionales

Cuando una operación involucre múltiples modelos o apps, la transacción deberá ubicarse preferentemente en el servicio que coordina el caso de uso.

Ejemplo:

```text
AcceptInvitationService
        ↓
transaction.atomic()
        ↓
User
Person
Patient
DoctorPatientRelationship
Invitation
```

Esto mantiene la lógica transaccional fuera de views y reduce el riesgo de que cada consumidor implemente el flujo de forma distinta.

---

# 15. Transacciones y excepciones

Una transacción no debe ocultar errores.

La implementación debe:

- detectar fallos;
- propagar excepciones apropiadamente;
- permitir rollback;
- devolver una respuesta funcional adecuada.

No utilizar:

```python
try:
    ...
except Exception:
    pass
```

para evitar que un error rompa una transacción.

---

# 16. Integridad vs Validación

Debe diferenciarse:

### Validación

Determina si los datos son aceptables antes de ejecutar una operación.

### Constraint

Impone una regla estructural en la base.

### Transaction

Garantiza que múltiples cambios ocurran como una unidad.

Ejemplo:

```text
Email único
    ↓
Unique Constraint

Registro válido
    ↓
Application Validation

Crear User + Person + Patient
    ↓
Atomic Transaction
```

Estos mecanismos se complementan; ninguno sustituye completamente a los otros.

---

# 17. Concurrencia

La arquitectura debe considerar concurrencia desde el diseño.

No debe asumirse:

```text
"dos requests no llegarán al mismo tiempo"
```

Las operaciones sensibles deben analizarse bajo escenarios concurrentes.

Especialmente:

- consumo de invitaciones;
- creación de relaciones únicas;
- futuras reservas;
- bloqueos temporales;
- cambios de estado.

---

# 18. Estrategia para concurrencia

Cuando una operación dependa del estado actual de una fila, la implementación deberá evaluar mecanismos como:

```python id="1m0x1m"
select_for_update()
```

dentro de una transacción.

Debe utilizarse únicamente cuando la operación lo requiera y con comprensión del nivel de aislamiento y el comportamiento de PostgreSQL.

No utilizar locking indiscriminadamente.

---

# 19. Invitaciones

La aceptación de una invitación es un caso de uso que requiere especial cuidado.

Conceptualmente:

```text
BEGIN
    lock Invitation
    validate state
    validate expiration
    create User
    create Person
    create Patient
    create DoctorPatientRelationship
    mark Invitation USED
COMMIT
```

Esto protege contra múltiples solicitudes concurrentes que intenten consumir la misma invitación.

Esta decisión complementa `ADR-003-invitation-security.md`.

---

# 20. Unicidad e idempotencia

Cuando sea razonablemente posible, las operaciones críticas deberán diseñarse para resistir reintentos.

Ejemplo:

```text
Request
   ↓
timeout
   ↓
client retries
```

La implementación debe evitar que un retry produzca duplicados cuando la operación originalmente sí llegó a ejecutarse.

La solución concreta podrá apoyarse en:

- constraints únicos;
- estados;
- identificadores de idempotencia;
- transacciones;

cuando el caso de uso lo justifique.

No se implementará una capa genérica de idempotencia para todo el sistema sin requerimiento.

---

# 21. Estados y transiciones

Cuando una entidad tenga estados, las transiciones importantes deben protegerse.

Ejemplo (Fase 2, `docs/phases/phase-2-agenda.md` §8/§15 — estado real, no un placeholder):

```text
Appointment
   SCHEDULED
       ↓
  IN_CONSULTATION
       ↓
   COMPLETED

  SCHEDULED → CANCELLED   (terminal)
  SCHEDULED → NO_SHOW     (terminal)
```

Estos son los únicos cinco estados de `Appointment` — no existen `PENDING`, `CONFIRMED` ni
`IN_PROGRESS`; ninguna transición ocurre por el solo paso del tiempo, siempre requiere la
acción humana autorizada correspondiente.

No debe permitirse que dos requests realicen simultáneamente transiciones incompatibles.

La estrategia concreta de locking o actualización condicional se definirá cuando se implemente la entidad.

---

# 22. Soft Delete

La baja lógica no debe utilizarse como una excusa para ignorar la integridad.

Una entidad desactivada puede seguir siendo referenciada históricamente.

Ejemplo:

```text
Doctor
is_active = false
      ↑
      │
Historical MedicalEncounter
```

El registro histórico debe mantenerse aunque el médico ya no esté activo.

Esto es consistente con el requisito de conservar información clínica histórica y evitar eliminación física rutinaria.

---

# 23. Historial clínico

Las futuras entidades clínicas deben diseñarse para preservar hechos históricos.

No utilizar una estructura donde actualizar un dato actual destruya el valor histórico anterior.

Ejemplo incorrecto:

```text
Patient.current_diagnosis
```

como sustituto de un historial de diagnósticos.

Correcto conceptualmente:

```text
MedicalEncounter
    ↓
Diagnosis at that moment
```

El mismo principio aplica a:

- tratamientos;
- recetas;
- estudios;
- evolución;
- documentos emitidos.

La especificación establece que consultas, diagnósticos, tratamientos y documentos deben conservar trazabilidad histórica.

---

# 24. Integridad de documentos

Cuando se implementen documentos clínicos, la eliminación física deberá evaluarse cuidadosamente.

Una referencia a un documento clínico histórico no debe romperse por una operación administrativa ordinaria.

Las reglas concretas de retención serán definidas posteriormente.

---

# 25. Errores de integridad

La aplicación debe manejar adecuadamente errores provenientes de PostgreSQL.

Ejemplos:

- `IntegrityError`;
- unique constraint violation;
- foreign key violation;
- check constraint violation.

No se deben convertir silenciosamente en respuestas exitosas.

El usuario debe recibir una respuesta funcional adecuada y el sistema debe mantener consistencia.

---

# 26. Race Conditions

Toda operación con patrón:

```text
check
then
write
```

debe evaluarse por posibles race conditions.

Ejemplo inseguro:

```python id="z2z8h7"
if not Invitation.objects.filter(...).exists():
    Invitation.objects.create(...)
```

Dos requests podrían pasar el `exists()` simultáneamente.

Cuando la unicidad sea una regla, la base de datos debe reforzarla.

---

# 27. "Check then act"

El patrón:

```text
CHECK
  ↓
ACT
```

no garantiza seguridad bajo concurrencia.

Preferir:

```text
TRANSACTION
   +
LOCK / CONSTRAINT / CONDITIONAL UPDATE
```

según la naturaleza de la operación.

La solución exacta debe ser específica al caso de uso.

---

# 28. Nivel de aislamiento

PostgreSQL utilizará su configuración transaccional estándar salvo que exista una necesidad documentada para modificarla.

No elevar el isolation level globalmente para solucionar un problema local.

Cuando aparezca un problema de concurrencia:

1. identificar la condición;
2. determinar qué garantía necesita el caso de uso;
3. utilizar el mecanismo mínimo necesario;
4. documentar la decisión cuando tenga impacto arquitectónico.

---

# 29. Deadlocks

La aplicación debe considerar la posibilidad de deadlocks al utilizar locking.

Cuando una operación requiera múltiples locks, se debe mantener un orden consistente de adquisición cuando sea posible.

Ejemplo:

```text
Invitation
   ↓
Patient
   ↓
Relationship
```

debe seguir el mismo orden en los workflows equivalentes.

No utilizar locks sin analizar su interacción con otras transacciones.

---

# 30. Performance

Las transacciones deben mantenerse tan pequeñas como sea razonablemente posible.

Evitar mantener una transacción abierta durante:

- llamadas HTTP externas;
- envío de emails;
- procesamiento pesado;
- generación de archivos;
- operaciones lentas que no necesitan formar parte de la transacción.

Ejemplo:

```text
BAD

BEGIN
   create data
   send email
   call external service
   COMMIT
```

Preferir:

```text
BEGIN
   create data
   COMMIT

send email
```

cuando el comportamiento del negocio lo permita.

---

# 31. Email y transacciones

Las operaciones de persistencia no deben depender innecesariamente de que un email externo pueda enviarse inmediatamente.

Ejemplo:

```text
crear Invitation
COMMIT
      ↓
enviar email
```

Cuando posteriormente se implemente Celery/outbox u otro mecanismo, deberá definirse la estrategia de consistencia correspondiente.

No se implementará infraestructura de mensajería avanzada en esta fase sin una necesidad real.

---

# 32. PostgreSQL como fuente de integridad

La base de datos será considerada autoridad para:

- foreign keys;
- uniqueness;
- check constraints;
- atomicidad transaccional;
- consistencia estructural.

La aplicación será responsable de:

- reglas funcionales;
- autorización;
- workflows;
- validaciones de negocio;
- presentación de errores.

---

# 33. Migraciones

Todo cambio estructural debe realizarse mediante migraciones Django.

Nunca modificar manualmente el esquema de producción como mecanismo normal.

Cada migración debe ser:

- versionada;
- reproducible;
- revisable;
- compatible con el estado esperado del proyecto.

Antes de finalizar una modificación de modelos, ejecutar:

```bash
python manage.py makemigrations
python manage.py migrate
```

y verificar que la base pueda construirse correctamente.

---

# 34. Migraciones y datos existentes

Cuando una modificación requiera transformar datos existentes, no asumir que una migración estructural simple es suficiente.

Debe evaluarse si se requiere:

- schema migration;
- data migration;
- transición progresiva.

Las migraciones destructivas deben revisarse especialmente.

---

# 35. Backward Compatibility

Las nuevas migraciones deben evitar romper silenciosamente funcionalidades existentes.

Cuando una modificación estructural pueda afectar código desplegado en distintas versiones, deberá evaluarse una estrategia compatible de transición.

La necesidad concreta dependerá del modelo de despliegue del proyecto.

---

# 36. Testing de integridad

Los tests deben verificar tanto comportamiento de aplicación como integridad de base de datos.

Ejemplos:

- email duplicado;
- foreign key inválida;
- relación duplicada;
- estado inválido;
- transacción revertida;
- operación parcialmente fallida;
- invitación consumida concurrentemente.

---

# 37. Testing de concurrencia

Las funcionalidades sensibles deberán contar con pruebas de concurrencia cuando exista un riesgo real.

No es necesario crear pruebas complejas para cada modelo.

Prioridades:

```text
Fase 1
- Invitation consumption

Fase 2
- Appointment booking
- Temporary slot locking
- Conflict prevention
```

La especificación exige explícitamente proteger la reserva contra dobles reservaciones.

---

# 38. Bloqueo temporal de 15 minutos (Hold) — decidido en Fase 2

Política funcional completa en `docs/phases/phase-2-agenda.md` §7 (aprobada 2026-09-09); este
ADR fija solo el principio de integridad, no repite la política.

`Hold` protege `Doctor + Clinic + Slot` durante 15 minutos como máximo, no se renueva, y un
usuario solo puede tener un hold activo a la vez. El escenario a proteger:

```text
User A selects slot
        ↓
temporary lock (Hold)

User B selects same slot
        ↓
DENIED
```

El hold es un mecanismo técnico, no un estado de `Appointment` (§21) — no sustituye la
protección de concurrencia de la base de datos: la creación definitiva de la cita siempre
revalida el slot dentro de la misma transacción que la confirma.

La solución debe apoyarse en PostgreSQL y transacciones, no exclusivamente en memoria o
lógica del frontend. El diseño detallado de la implementación (tabla, constraint o mecanismo
de expiración) se define al construir `appointments`, no aquí.

---

# 39. Doble reserva y exclusión de horarios — decidido en Fase 2

Política funcional completa en `docs/phases/phase-2-agenda.md` §5.7, §6, §21 (aprobada
2026-09-09).

El sistema debe impedir:

```text
Appointment A
09:00–10:00
Doctor X
Clinic Y

Appointment B
09:00–10:00
Doctor X
Clinic Y
```

Una cita ocupa simultáneamente al médico y al consultorio durante toda su duración; no puede
existir otra cita incompatible para ninguno de los dos en ese lapso. La implementación
concreta debe considerar:

- constraints aplicables (p. ej. `ExclusionConstraint` de PostgreSQL sobre médico/consultorio
  y rango de tiempo, si el diseño técnico lo determina así);
- transacciones;
- locking (`select_for_update` u equivalente);
- consultas concurrentes;
- estrategia de intervalos de tiempo.

Si dos operaciones concurrentes compiten por el mismo horario, solo una puede resultar
exitosa; la otra debe recibir un error de negocio de horario no disponible, nunca un estado
inconsistente.

---

# 40. Reglas de diseño para nuevos modelos

Antes de agregar un modelo nuevo, evaluar:

### Relaciones

¿Qué entidades debe referenciar?

### Unicidad

¿Qué combinaciones deben ser únicas?

### Estado

¿Qué estados son válidos?

### Eliminación

¿Debe permitirse eliminar físicamente?

### Historial

¿La información necesita conservar versiones o eventos?

### Concurrencia

¿Dos requests pueden modificarla simultáneamente?

### Índices

¿Cómo será consultada?

---

# 41. Alternativas consideradas

## Alternativa A — Integridad únicamente en Python/Django

**Decisión:** Rejected.

Motivo:

No protege adecuadamente contra ciertas condiciones de concurrencia ni garantiza integridad cuando múltiples procesos interactúan simultáneamente con la base.

---

## Alternativa B — Integridad únicamente mediante PostgreSQL

**Decisión:** Rejected.

Motivo:

La base de datos no debe contener toda la lógica funcional y de negocio.

Las reglas de negocio requieren coordinación desde la capa de aplicación.

---

## Alternativa C — Sin transacciones explícitas

**Decisión:** Rejected.

Motivo:

Los workflows multi-entidad pueden quedar en estados parciales.

---

## Alternativa D — Transacciones para casos de uso + constraints en PostgreSQL

**Decisión:** Accepted.

Esta alternativa proporciona un equilibrio entre:

- reglas de aplicación;
- integridad estructural;
- atomicidad;
- concurrencia;
- mantenibilidad.

---

# 42. Consecuencias positivas

Esta decisión proporciona:

- mayor consistencia de datos;
- menor riesgo de registros huérfanos;
- protección contra duplicados;
- operaciones atómicas;
- mejor comportamiento bajo concurrencia;
- base sólida para agenda futura;
- integridad respaldada por PostgreSQL;
- reglas de dominio más explícitas.

---

# 43. Consecuencias negativas

Implica:

- mayor complejidad;
- necesidad de comprender transacciones;
- mayor cantidad de tests;
- cuidado con locks;
- necesidad de diseñar constraints apropiadamente;
- mayor disciplina en migraciones.

Estos costos son aceptables para un sistema que manejará información médica y operaciones sensibles.

---

# 44. Reglas de implementación

### Regla 1

Las relaciones estructurales deben utilizar foreign keys.

### Regla 2

Las reglas críticas de unicidad deben respaldarse con constraints.

### Regla 3

No depender únicamente de validaciones de aplicación para integridad estructural.

### Regla 4

Los workflows multi-entidad deben usar transacciones cuando deban ser atómicos.

### Regla 5

No mantener transacciones abiertas durante operaciones externas lentas salvo necesidad explícita.

### Regla 6

Analizar race conditions en operaciones `check → write`.

### Regla 7

Utilizar locking únicamente cuando el caso de uso lo requiera.

### Regla 8

Evitar deadlocks manteniendo órdenes consistentes de locking cuando sea posible.

### Regla 9

No utilizar `CASCADE` indiscriminadamente.

### Regla 10

Preservar información histórica cuando el dominio lo requiera.

### Regla 11

Toda nueva entidad sensible debe definir sus reglas de integridad.

### Regla 12

Los cambios estructurales deben realizarse mediante migraciones Django.

---

# 45. Criterios de aceptación

Esta decisión se considera correctamente implementada cuando:

- [ ] PostgreSQL es la base de datos principal.
- [ ] Las relaciones importantes utilizan foreign keys.
- [ ] Las reglas de unicidad importantes tienen constraints.
- [ ] Los modelos relevantes tienen índices apropiados.
- [ ] Las operaciones multi-entidad críticas utilizan transacciones.
- [ ] Los errores de integridad no se ignoran.
- [ ] Las operaciones sensibles han sido evaluadas por race conditions.
- [ ] Las invitaciones se consumen de forma segura y atómica.
- [ ] La eliminación destructiva no se utiliza como mecanismo rutinario para información histórica.
- [ ] Los cambios de esquema utilizan migraciones.
- [ ] Existen tests de integridad.
- [ ] Existen tests de concurrencia para los flujos donde el riesgo lo justifica.
- [ ] La arquitectura de Fase 1 permite implementar posteriormente reservas concurrentes.

---

# 46. Relación con otros ADR

Esta decisión complementa:

```text
ADR-001
Custom User Model
```

al definir cómo mantener la integridad de las relaciones con `User`.

También complementa:

```text
ADR-002
User / Person / Functional Profiles
```

al establecer integridad referencial entre identidad y perfiles.

Se relaciona directamente con:

```text
ADR-003
Invitation Security
```

porque la aceptación de una invitación requiere atomicidad y control de concurrencia.

También complementa:

```text
ADR-004
Role and Object Permissions
```

porque autorización e integridad son capas diferentes.

Y:

```text
ADR-005
Django App Boundaries
```

porque los límites de las apps no deben impedir relaciones transaccionales entre dominios cuando el caso de uso lo requiera.

---

# 47. Evolución futura

Cuando se implementen nuevas fases, este ADR deberá complementarse con decisiones específicas cuando exista complejidad significativa.

Posibles ADR futuros (renumerados 2026-09-09: `ADR-007` ya está en uso — Responsible-Initiated
Minor Patient Registration — por lo que la numeración disponible empieza en `ADR-008`):

```text
ADR-008 — Appointment Concurrency (si la implementación de Fase 2 requiere una decisión
          propia más allá de lo ya fijado en docs/phases/phase-2-agenda.md y en §38-39 de
          este documento — no es automático que se necesite un ADR nuevo)
ADR-009 — Clinical Record Immutability / Versioning
ADR-010 — Private Clinical File Storage
ADR-011 — Notification Delivery Architecture
ADR-012 — Audit Log Architecture
```

Estos ADR deberán profundizar en problemas específicos sin duplicar las reglas generales establecidas aquí.

---

# 48. Principio final

La arquitectura de persistencia de TeCuidoApp debe asumir que:

```text
Requests can fail.
Requests can retry.
Requests can run concurrently.
External services can fail.
Users can submit unexpected input.
```

Por ello:

```text
Validation
   +
Constraints
   +
Transactions
   +
Concurrency Control
   +
Tests
```

deben trabajar conjuntamente para preservar la integridad del sistema.

La base de datos no debe considerarse únicamente un lugar donde almacenar objetos.

Debe considerarse parte activa de las garantías de consistencia de TeCuidoApp.

---

# 49. Estado

**Accepted**

Esta decisión forma parte de la arquitectura base de persistencia de TeCuidoApp.

Las decisiones específicas de concurrencia de cada dominio deberán documentarse mediante ADRs adicionales cuando el nivel de complejidad lo justifique.

---

# 50. Referencias

- `requirements.md`
- `docs/architecture.md`
- `docs/adr/ADR-001-custom-user-model.md`
- `docs/adr/ADR-002-user-person-profile.md`
- `docs/adr/ADR-003-invitation-security.md`
- `docs/adr/ADR-004-role-and-object-permissions.md`
- `docs/adr/ADR-005-django-app-boundaries.md`
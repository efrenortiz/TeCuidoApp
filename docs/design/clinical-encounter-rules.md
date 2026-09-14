# Fase 3 — ClinicalEncounter Rules

**Documento rector de reglas de negocio de `ClinicalEncounter`**  
**Estado:** aprobado para diseño e implementación  
**Fecha de cierre de políticas:** 2026-09-11

---

## 1. Propósito

Este documento transforma las decisiones funcionales y el workflow de `ClinicalEncounter` en reglas de negocio atómicas, expresadas como invariantes, precondiciones, postcondiciones y condiciones de error.

Este documento no redefine el modelo de datos, la API, la UI, la matriz completa de permisos clínicos ni `MedicalRecord`. Esos aspectos se documentarán en sus documentos correspondientes.

Fuentes normativas inmediatas:

```text
phase-3-clinical-encounter.md
clinical-encounter-workflow.md
phase-2-agenda.md
requirements.md
```

En caso de contradicción específica para `ClinicalEncounter`, prevalece la decisión funcional más reciente documentada en los contratos de Fase 3.

---

## 2. Principios de dominio

### R-001 — Una consulta clínica nace de una cita

Todo `ClinicalEncounter` debe originarse en una `Appointment` existente.

No existe en Fase 3 la creación funcional de consultas independientes de una cita.

### R-002 — Cita y consulta son entidades distintas

`Appointment` pertenece al dominio de Agenda y `ClinicalEncounter` pertenece al dominio clínico.

La cita representa el evento de agenda. El encuentro representa lo sucedido durante la atención clínica.

### R-003 — Una cita genera como máximo un encuentro

La cardinalidad funcional es:

```text
Appointment 1 ─── 0..1 ClinicalEncounter
```

Una misma `Appointment` nunca puede tener más de un `ClinicalEncounter`.

### R-004 — El encuentro no crea relación médico-paciente

Crear, guardar, retomar o completar un `ClinicalEncounter` no crea, activa, modifica, desactiva ni sustituye una `DoctorPatientRelationship`.

### R-005 — No diagnóstico ni recomendaciones autónomas

TeCuidoApp registra la información proporcionada por el médico.

El sistema no determina si un diagnóstico es médicamente correcto, no diagnostica y no genera recomendaciones médicas autónomas.

---

## 3. Identidad y consistencia con Appointment

### R-006 — Appointment obligatoria

`ClinicalEncounter.appointment` es conceptualmente obligatorio.

Un encuentro sin cita de origen es un estado inválido y no forma parte del dominio funcional de Fase 3.

### R-007 — Datos canónicos derivados de Appointment

El encuentro debe corresponder al mismo:

- paciente;
- médico;
- consultorio/clínica;
- contexto de atención;

que la `Appointment` de origen.

La implementación no debe permitir que el médico cambie durante la consulta estos vínculos estructurales mediante edición clínica.

### R-008 — Integridad de referencias

Debe cumplirse siempre:

```text
ClinicalEncounter.patient == Appointment.patient
ClinicalEncounter.doctor  == Appointment.doctor
ClinicalEncounter.clinic  == Appointment.clinic
```

Estas igualdades son invariantes de dominio.

### R-009 — No reasignación clínica

Un `ClinicalEncounter` no puede ser transferido manualmente a otra `Appointment`, otro paciente, otro médico o otro consultorio.

Los cambios estructurales de Agenda no forman parte del dominio clínico del encuentro.

---

## 4. Precondiciones para iniciar

### R-010 — Estado requerido de Appointment

La operación de inicio solo es válida cuando:

```text
Appointment.status == SCHEDULED
```

### R-011 — Médico asignado

Solo el médico asignado a la `Appointment` puede iniciar la consulta.

### R-012 — Presencia del paciente

La política de Agenda establece que el inicio clínico ocurre cuando el paciente está físicamente presente en el consultorio y el médico asignado verifica su presencia.

Fase 3 no introduce un mecanismo adicional de check-in ni un estado `WAITING`.

### R-013 — No debe existir encuentro previo

Para una primera operación de inicio no debe existir un `ClinicalEncounter` para la `Appointment`.

### R-014 — Citas canceladas o NO_SHOW

Una `Appointment` en `CANCELLED` o `NO_SHOW` no puede iniciar una consulta.

### R-015 — El tiempo no inicia la consulta

El simple paso del tiempo nunca cambia el estado de `Appointment` ni crea un `ClinicalEncounter`.

### R-016 — Sin ventana temporal adicional de Fase 3

Fase 3 no añade una ventana horaria propia para iniciar la consulta.

Se respetan las reglas de Agenda existentes. En particular, una cita que siga en `SCHEDULED` puede ser iniciada por el médico asignado aun después de su hora programada, siempre que todavía sea iniciable conforme a Agenda y no haya sido convertida en `NO_SHOW`.

---

## 5. Regla de inicio

### R-017 — Acción de inicio

La acción funcional es:

```text
Iniciar consulta
```

### R-018 — Transición atómica de inicio

El inicio debe producir una única operación de negocio:

```text
Appointment:        SCHEDULED      → IN_CONSULTATION
ClinicalEncounter:  inexistente    → IN_PROGRESS
```

No es válido persistir solo una de las dos transiciones.

### R-019 — Resultado parcial prohibido

Nunca debe persistir como resultado normal de `Iniciar consulta`:

```text
Appointment = IN_CONSULTATION
ClinicalEncounter = inexistente
```

### R-020 — Reversión ante fallo

Si la creación del encuentro falla, el cambio de estado de `Appointment` debe revertirse dentro de la misma operación transaccional.

### R-021 — Creación exactamente una vez

Una ejecución concurrente de la misma acción debe producir como resultado final un solo `ClinicalEncounter`.

### R-022 — Segundo inicio idempotente

Si una primera operación ya creó exitosamente el encuentro, un segundo intento equivalente no crea otro encuentro ni reinicia la consulta.

El resultado funcional debe reconocer el encuentro existente.

### R-023 — Concurrencia de inicio

Dos solicitudes concurrentes para iniciar la misma cita deben resolverse mediante transacción, bloqueo apropiado e integridad de base de datos.

La interfaz nunca es la autoridad final para esta garantía.

---

## 6. Estado IN_PROGRESS

### R-024 — Significado

`IN_PROGRESS` significa que existe una consulta clínica abierta que todavía no ha sido completada.

### R-025 — Acciones permitidas

Mientras el encuentro esté `IN_PROGRESS`, el médico asignado puede:

- capturar información;
- guardar información;
- modificar información previamente guardada;
- abandonar temporalmente la consulta;
- retomar la consulta;
- completar la consulta.

### R-026 — El guardado no completa

Una operación de `Guardar` nunca cambia el encuentro a `COMPLETED`.

### R-027 — No existe reapertura en este estado

La reapertura es relevante únicamente como concepto posterior al cierre. En Fase 3 no existe ningún flujo para reabrir un encuentro `COMPLETED`.

---

## 7. Guardado parcial

### R-028 — Guardado incompleto permitido

Un encuentro `IN_PROGRESS` puede almacenarse aunque falten uno o varios campos obligatorios de completado.

### R-029 — Persistencia explícita

Fase 3 no exige autosalvado implícito del lado del cliente.

Solo se garantiza la persistencia de la información que haya sido guardada exitosamente.

### R-030 — updated_at

Cada guardado exitoso actualiza `updated_at`.

`updated_at` representa el último momento de persistencia exitosa del encuentro.

### R-031 — Fallo de guardado

Si un guardado falla:

- no debe persistir una actualización parcial de esa operación;
- permanece disponible el último estado exitosamente guardado;
- el encuentro continúa `IN_PROGRESS`;
- el error debe comunicarse al usuario.

### R-032 — Guardado no altera timestamps de cierre

Un guardado parcial no establece `completed_at`.

Tampoco modifica `started_at`.

---

## 8. Interrupción y reanudación

### R-033 — Interrupción no equivale a finalización

Cerrar la ventana, perder conectividad, cerrar o expirar la sesión o abandonar temporalmente el consultorio no completa la consulta.

### R-034 — Sin autocierre

No existe cierre automático por:

- tiempo transcurrido;
- cierre del navegador;
- fin de sesión;
- fin de la duración prevista de la cita;
- cambio de fecha u hora;
- cualquier otro temporizador operativo.

### R-035 — Estado después de interrupción

La interrupción conserva:

```text
Appointment = IN_CONSULTATION
ClinicalEncounter = IN_PROGRESS
```

### R-036 — Reanudación por médico asignado

Solo el médico asignado puede retomar la consulta mediante el flujo de acceso autorizado correspondiente.

### R-037 — Retomar no reinicia la consulta

Retomar un encuentro no crea uno nuevo y no modifica `started_at`.

### R-038 — Múltiples encuentros abiertos

Un médico puede tener más de un `ClinicalEncounter` en `IN_PROGRESS` simultáneamente si cada uno corresponde a una `Appointment` distinta y válida.

No existe una regla de exclusión por médico entre consultas abiertas.

---

## 9. Regla de duración

### R-039 — Duración de Appointment no equivale a duración clínica

Una vez iniciada la consulta:

```text
Appointment duration ≠ ClinicalEncounter duration
```

### R-040 — La consulta puede exceder la duración programada

El encuentro puede durar menos, igual o más que la duración prevista de la cita.

### R-041 — La duración no completa

La llegada al final de la duración de `Appointment` nunca cambia por sí sola el `ClinicalEncounter` a `COMPLETED`.

---

## 10. Transiciones prohibidas durante la consulta

### R-042 — IN_CONSULTATION es estado clínico activo

Una vez iniciada la consulta, la `Appointment` no puede ser cancelada.

### R-043 — NO_SHOW prohibido después del inicio

Una `Appointment` en `IN_CONSULTATION` no puede pasar a `NO_SHOW`.

### R-044 — Estados válidos de Agenda

Las transiciones prohibidas incluyen:

```text
IN_CONSULTATION → CANCELLED   ✗
IN_CONSULTATION → NO_SHOW     ✗
```

### R-045 — Cambios estructurales fuera del encuentro

El encuentro no permite cambiar:

- paciente;
- médico;
- clínica/consultorio;
- cita de origen.

Cualquier cambio de Agenda debe resolverse dentro del dominio de Agenda y respetando sus propias restricciones.

---

## 11. Campos obligatorios para completar

### R-046 — Cinco campos mínimos

Para completar el encuentro deben existir contenidos clínicos reales en:

1. Motivo de consulta.
2. Padecimiento actual.
3. Exploración física.
4. Evaluación / diagnóstico.
5. Plan / indicaciones.

### R-047 — Validación solo al completar

Los cinco campos no necesitan estar completos durante `IN_PROGRESS`.

La validación de completitud se aplica al intentar `Completar consulta`.

### R-048 — Diagnóstico como texto libre

En Fase 3, `Evaluación / diagnóstico` se maneja como texto libre.

No se exige CIE-10 ni un catálogo estructurado.

### R-049 — Campos opcionales

Pueden capturarse, entre otros:

- signos vitales;
- peso;
- talla;
- antecedentes relevantes;
- estudios y paraclínicos;
- resultados relevantes;
- observaciones;
- evolución;
- pronóstico;
- otros datos clínicos pertinentes.

Su ausencia no impide completar el encuentro, salvo que una política especializada posterior establezca un requisito para su propio módulo.

---

## 12. Regla de contenido clínico real

### R-050 — No basta con una cadena no vacía

Los campos obligatorios deben contener información clínica sustancial mínima.

### R-051 — Normalización previa

Para determinar si existe contenido, el valor debe normalizarse al menos eliminando espacios al inicio y al final.

### R-052 — Espacios en blanco equivalen a vacío

Los valores formados únicamente por espacios, saltos de línea o tabulaciones no son contenido válido.

### R-053 — Placeholders prohibidos

No son válidos como contenido clínico los valores de relleno conocidos, incluyendo:

```text
N/A
NA
No aplica
No Aplica
Sin datos
Ninguno
-
--
.
...
No disponible
Desconocido
```

La comparación debe ser resistente a diferencias irrelevantes de mayúsculas/minúsculas y espacios externos.

### R-054 — Variantes equivalentes

No debe ser posible evadir la validación mediante una variante obvia de un placeholder, por ejemplo agregando espacios externos o modificando únicamente mayúsculas/minúsculas.

### R-055 — Etiquetas no son contenido

No es válido introducir únicamente el nombre de la sección o campo con el propósito de satisfacer la validación.

### R-056 — Sin umbral arbitrario de caracteres

Fase 3 no establece un número mínimo arbitrario de caracteres como sustituto de la validación clínica.

Una nota breve puede ser válida si contiene información clínica real.

### R-057 — La aplicación no evalúa calidad médica

La validación no intenta decidir si una nota es correcta, suficiente desde el punto de vista médico o clínicamente apropiada.

La responsabilidad clínica corresponde al médico.

---

## 13. Completar consulta

### R-058 — Acción explícita

Solo una acción explícita de `Completar consulta` puede finalizar el encuentro.

### R-059 — Precondición de estado

El encuentro debe encontrarse en:

```text
IN_PROGRESS
```

y la cita en:

```text
IN_CONSULTATION
```

### R-060 — Validación previa

Antes del cierre se deben validar los cinco campos obligatorios y su contenido clínico real.

### R-061 — Fallo de validación

Si cualquier campo falla la validación:

```text
ClinicalEncounter = IN_PROGRESS
Appointment = IN_CONSULTATION
```

No se modifica `completed_at` y no se realiza la transición de cierre.

### R-062 — Conservación del contenido

Un intento fallido de completar no puede borrar ni sobrescribir el contenido previamente guardado.

### R-063 — Reintento permitido

Después de un fallo de validación, el médico asignado puede corregir la información y volver a intentar completar.

---

## 14. Cierre atómico

### R-064 — Transición obligatoria de cierre

Cuando todas las validaciones son exitosas, deben producirse dentro de la misma operación transaccional:

```text
ClinicalEncounter: IN_PROGRESS      → COMPLETED
Appointment:      IN_CONSULTATION   → COMPLETED
```

### R-065 — Estados finales consistentes

Nunca debe quedar como estado final:

```text
ClinicalEncounter = COMPLETED
Appointment = IN_CONSULTATION
```

ni:

```text
ClinicalEncounter = IN_PROGRESS
Appointment = COMPLETED
```

### R-066 — Rollback completo

Si una parte del cierre falla, la transacción completa debe revertirse.

### R-067 — completed_at

`completed_at` se establece únicamente cuando el cierre es exitoso.

No se establece durante:

- creación;
- guardado parcial;
- interrupción;
- intento de completar con validación fallida.

### R-068 — updated_at al completar

La operación de completar es una persistencia exitosa y debe actualizar `updated_at`.

### R-069 — Cierre concurrente

Dos solicitudes concurrentes de `Completar consulta` no pueden completar dos veces el mismo encuentro.

Solo una transición:

```text
IN_PROGRESS → COMPLETED
```

puede tener éxito como cierre efectivo.

### R-070 — Solicitud posterior a COMPLETED

Cualquier escritura que llegue cuando el encuentro ya esté `COMPLETED` debe rechazarse.

---

## 15. Reglas temporales

### R-071 — created_at

`created_at` registra el momento en que se crea el `ClinicalEncounter`.

### R-072 — started_at

`started_at` registra el momento real de inicio de la consulta y se establece durante la transición de inicio.

### R-073 — started_at inmutable

`started_at` no se modifica al guardar parcialmente ni al retomar una consulta interrumpida.

### R-074 — updated_at

`updated_at` representa el último momento de persistencia exitosa, incluido el cierre.

### R-075 — completed_at

`completed_at` registra el momento del cierre exitoso.

### R-076 — Orden temporal

Cuando existe `completed_at`, debe cumplirse:

```text
created_at ≤ started_at ≤ completed_at
```

Y mientras el encuentro permanezca `IN_PROGRESS`:

```text
completed_at IS NULL
```

### R-077 — Contexto temporal

Los timestamps de negocio deben ser consistentes con la zona horaria de la `Clinic`, no con la zona horaria local arbitraria del dispositivo del usuario.

---

## 16. Inmutabilidad posterior a COMPLETED

### R-078 — Bloqueo permanente en Fase 3

Un encuentro `COMPLETED` no puede volver a `IN_PROGRESS`.

### R-079 — Sin edición posterior

No se permite editar campos clínicos después de `COMPLETED`.

### R-080 — Sin guardado posterior

No se permite guardar cambios sobre un encuentro `COMPLETED`.

### R-081 — Sin eliminación funcional

`ClinicalEncounter` no tiene DELETE funcional en Fase 3.

### R-082 — Sin enmienda en Fase 3

No existe en esta fase ningún mecanismo de corrección silenciosa, reapertura o versionado posterior al cierre.

Una necesidad futura de corrección deberá resolverse mediante una especificación independiente de enmiendas/versionado.

---

## 17. Integridad y concurrencia

### R-083 — La base de datos es autoridad final

Las garantías críticas no deben depender exclusivamente de validaciones de formularios o UI.

### R-084 — Inicio concurrente

La combinación de transacción, bloqueo apropiado e integridad de base de datos debe impedir la creación duplicada de encuentros.

### R-085 — Cierre concurrente

La misma combinación debe impedir dos cierres efectivos del mismo encuentro.

### R-086 — Escritura contra encuentro recién completado

Una solicitud de modificación que pierda la carrera contra un cierre debe ser rechazada si el encuentro quedó `COMPLETED` antes de que la escritura pudiera persistirse legítimamente.

### R-087 — No estado clínico parcial

No se permite que fallos técnicos produzcan estados parciales persistidos entre Agenda y atención clínica.

---

## 18. Invariantes de alto nivel

El dominio debe conservar siempre estos invariantes:

```text
I-001  ClinicalEncounter.appointment es obligatorio
I-002  Una Appointment tiene 0..1 ClinicalEncounter
I-003  Appointment.patient == ClinicalEncounter.patient
I-004  Appointment.doctor  == ClinicalEncounter.doctor
I-005  Appointment.clinic  == ClinicalEncounter.clinic
I-006  Appointment IN_CONSULTATION ↔ ClinicalEncounter IN_PROGRESS
I-007  Appointment COMPLETED ↔ ClinicalEncounter COMPLETED
I-008  ClinicalEncounter IN_PROGRESS ⇒ completed_at IS NULL
I-009  ClinicalEncounter COMPLETED ⇒ completed_at IS NOT NULL
I-010  COMPLETED ⇒ no edición
I-011  COMPLETED ⇒ no DELETE funcional
I-012  ClinicalEncounter no modifica DoctorPatientRelationship
```

Las equivalencias `I-006` e `I-007` deben entenderse en el contexto de las operaciones transaccionales que coordinan ambos dominios y no como una autorización para modificar directamente un dominio desde el otro sin pasar por su contrato.

---

## 19. Errores de dominio mínimos

El nombre técnico definitivo de cada excepción podrá definirse en `clinical-service-contracts.md`, pero las situaciones siguientes deben ser distinguibles funcionalmente.

### R-088 — Appointment inválida

No puede iniciarse una consulta si la cita no existe o no puede ser utilizada como cita de origen válida.

### R-089 — Appointment no iniciable

Debe rechazarse el inicio si el estado de la cita no es `SCHEDULED`.

### R-090 — Actor no autorizado

Debe rechazarse el inicio o modificación cuando el actor no sea el médico asignado, sujeto a la matriz completa de permisos de `clinical-permissions.md`.

### R-091 — Appointment cancelada o NO_SHOW

Debe rechazarse cualquier intento de inicio sobre estos estados.

### R-092 — Encounter ya existente

Un segundo intento de inicio sobre la misma cita no crea otro encuentro y se resuelve según la semántica idempotente definida en el workflow.

### R-093 — Validación clínica incompleta

Debe rechazarse `Completar consulta` si falta cualquiera de los cinco campos obligatorios o si alguno contiene un placeholder inválido.

### R-094 — Encounter ya completado

Debe rechazarse cualquier modificación posterior al cierre.

### R-095 — Transición de Agenda incompatible

Debe rechazarse el cierre si la `Appointment` ya no está en `IN_CONSULTATION` o si la transición conjunta no puede realizarse de manera atómica.

### R-096 — Inconsistencia de referencias

Debe rechazarse cualquier operación que detecte que paciente, médico o clínica del encuentro no corresponden a su `Appointment` de origen.

---

## 20. Situaciones que son errores de integridad, no nuevos flujos

Las siguientes condiciones nunca deben utilizarse para inventar mecanismos de recuperación automática dentro de este dominio:

```text
Appointment = IN_CONSULTATION
ClinicalEncounter = inexistente
```

```text
ClinicalEncounter.appointment = NULL
```

```text
ClinicalEncounter.patient != Appointment.patient
```

```text
ClinicalEncounter.doctor != Appointment.doctor
```

```text
ClinicalEncounter.clinic != Appointment.clinic
```

Si alguna de estas condiciones se detecta, debe tratarse como una inconsistencia del sistema y no como autorización para crear duplicados, reasignar consultas o modificar silenciosamente datos históricos.

---

## 21. Reglas explícitamente fuera de este documento

No se definen aquí:

- matriz de lectura por otros médicos;
- reglas de acceso clínico detalladas;
- `MedicalRecord` completo;
- historia clínica longitudinal;
- `ClinicalAlert`;
- recetas;
- órdenes de estudios;
- documentos clínicos;
- archivos adjuntos;
- auditoría clínica avanzada;
- enmiendas/versionado posteriores a `COMPLETED`;
- módulos específicos de ginecología, obstetricia, colposcopia, menopausia u osteoporosis;
- CIE-10 o catálogos diagnósticos;
- detalles de API;
- detalles de UI/UX.

La política de acceso de otros médicos queda específicamente reservada a:

```text
clinical-permissions.md
```

---

## 22. Matriz resumida de reglas

| Regla | Tema | Estado |
|---|---|---|
| R-001–R-005 | Principios de dominio | Cerrada |
| R-006–R-009 | Integridad con Appointment | Cerrada |
| R-010–R-016 | Precondiciones de inicio | Cerrada |
| R-017–R-023 | Inicio e idempotencia | Cerrada |
| R-024–R-027 | IN_PROGRESS | Cerrada |
| R-028–R-032 | Guardado parcial | Cerrada |
| R-033–R-038 | Interrupción/reanudación | Cerrada |
| R-039–R-041 | Duración | Cerrada |
| R-042–R-045 | Transiciones prohibidas | Cerrada |
| R-046–R-049 | Campos y diagnóstico | Cerrada |
| R-050–R-057 | Contenido clínico real | Cerrada |
| R-058–R-063 | Completar y validar | Cerrada |
| R-064–R-070 | Cierre atómico | Cerrada |
| R-071–R-077 | Timestamps | Cerrada |
| R-078–R-082 | Inmutabilidad | Cerrada |
| R-083–R-087 | Concurrencia | Cerrada |
| R-088–R-096 | Errores de dominio | Cerrada |

---

## 23. Criterio de salida de Rules

`clinical-encounter-rules.md` se considera cerrado cuando el equipo puede implementar `ClinicalEncounter` sin tener que inventar reglas respecto de:

1. cuándo puede iniciarse una consulta;
2. quién puede iniciarla o modificarla;
3. cómo se crea y cómo se evita la duplicación;
4. cómo se guarda parcialmente;
5. qué sucede cuando la consulta se interrumpe;
6. cómo se retoma;
7. cómo se valida el contenido clínico mínimo;
8. cómo se completa;
9. cómo se sincronizan atómicamente `ClinicalEncounter` y `Appointment`;
10. cómo se manejan timestamps;
11. qué estados y transiciones son imposibles;
12. qué ocurre ante concurrencia;
13. qué queda definitivamente bloqueado después de `COMPLETED`.

La única dimensión deliberadamente reservada para un documento posterior es la **lectura del expediente por otros médicos**, que no debe inferirse a partir de estas reglas.

---

## 24. Próximo documento

Con las reglas de negocio de `ClinicalEncounter` cerradas, el siguiente documento previsto es:

```text
clinical-encounter-domain.md
```

Ese documento debe convertir estas reglas en la definición del dominio técnico: entidad, identidad, invariantes persistentes, ciclo de vida, operaciones del dominio y límites con `Appointment`, sin volver a abrir decisiones funcionales ya cerradas aquí.

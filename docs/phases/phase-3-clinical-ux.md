# TeCuidoApp — Fase 3: Clinical UX

> **Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11 — sin hallazgos que requirieran corrección de contenido)
>
> **Propósito:** definir la experiencia de usuario de la atención clínica de Fase 3 sin inventar capacidades que todavía pertenecen a fases posteriores.
>
> **Regla rectora:** la UX debe representar fielmente las reglas de dominio, permisos, seguridad, servicios y API. La interfaz nunca constituye una regla de negocio ni una barrera de seguridad.

---

## 1. Propósito y alcance

Este documento define la experiencia de usuario de la primera versión clínica de TeCuidoApp.

El objetivo es que un usuario autorizado pueda:

1. identificar una cita válida;
2. iniciar la consulta desde Agenda;
3. documentar la atención de forma incremental;
4. guardar avances sin obligar a completar la consulta;
5. reanudar una consulta interrumpida;
6. completar la consulta cuando existan los cinco campos clínicos mínimos;
7. consultar posteriormente la información clínica que sus permisos permitan.

La UX debe ser coherente con:

- `phase-3-clinical-encounter.md`;
- `clinical-encounter-workflow.md`;
- `clinical-encounter-rules.md`;
- `clinical-encounter-domain.md`;
- `clinical-record-domain.md`;
- `clinical-data-model.md`;
- `clinical-permissions.md`;
- `clinical-security-and-privacy.md`;
- `clinical-service-contracts.md`;
- `clinical-api-contracts.md`;
- requisitos generales y decisiones arquitectónicas previas.

---

# 2. Principios UX cerrados

## UX-001 — La UX no redefine el dominio

La interfaz presenta acciones que el dominio permite. No debe introducir estados ni reglas que no existan en los contratos.

## UX-002 — El servidor es la autoridad

Ocultar un botón es una mejora de UX, no una autorización. Toda operación clínica debe volver a validar identidad, estado y permiso en backend.

## UX-003 — La consulta empieza en Agenda

La entrada nominal a Fase 3 es la cita válida que pasa de `SCHEDULED` a `IN_CONSULTATION` al iniciar la atención.

## UX-004 — No existe pantalla de check-in

Fase 3 no introduce `WAITING`, `CHECKED_IN` ni otro estado intermedio.

## UX-005 — `IN_CONSULTATION` significa atención clínica activa

La interfaz debe distinguir una consulta abierta de una consulta terminada.

## UX-006 — Guardar y completar son acciones distintas

"Guardar" persiste avances. "Completar consulta" valida requisitos mínimos y cierra el encuentro.

## UX-007 — Guardado parcial permitido

No se debe impedir guardar porque alguno de los cinco campos mínimos todavía esté vacío.

## UX-008 — Los cinco mínimos solo son obligatorios para completar

Son:

- Motivo de consulta
- Padecimiento actual
- Exploración física
- Evaluación / diagnóstico
- Plan / indicaciones

## UX-009 — Los campos clínicos deben aceptar texto clínico real

La UX puede ayudar a visualizar errores de vacío o placeholder, pero no intenta juzgar la calidad médica del contenido.

## UX-010 — Diagnóstico es texto libre

Fase 3 no expone un selector CIE-10 ni un catálogo diagnóstico obligatorio.

## UX-011 — Sin borrado clínico

No debe aparecer una acción de "Eliminar consulta" o "Eliminar expediente".

## UX-012 — Sin reapertura

Una consulta `COMPLETED` se presenta como histórica y de solo lectura.

## UX-013 — Una interrupción no equivale a completar

Cerrar pestaña, navegar fuera o perder conexión no debe presentar la consulta como terminada.

## UX-014 — No autocierre por tiempo

El vencimiento de la duración programada de la cita no completa la consulta automáticamente.

## UX-015 — La identidad del paciente es contextual y estable

La pantalla debe mostrar claramente a qué paciente corresponde la atención y evitar confusión entre pacientes.

## UX-016 — Privacidad por defecto

La interfaz muestra únicamente la información clínica autorizada para el actor actual.

## UX-017 — No duplicar información canónica

Los datos personales básicos del paciente provienen de `Patient`; no se crean copias clínicas innecesarias.

## UX-018 — El expediente es longitudinal

La UX debe permitir distinguir entre información histórica, datos longitudinales y encuentros individuales.

## UX-019 — El contexto de atención es visible

Cuando se trabaja sobre un encuentro, deben ser visibles al menos paciente, médico, clínica, cita y estado del encuentro según los permisos.

## UX-020 — Estados claros y humanos

Los estados técnicos pueden mostrarse con etiquetas comprensibles, pero su significado debe ser inequívoco.

---

# 3. Usuarios y necesidades

## 3.1 Médico asignado

Es el actor central del flujo de Fase 3.

Necesita:

- encontrar una cita elegible;
- iniciar la consulta;
- registrar información progresivamente;
- continuar una consulta abierta;
- completarla;
- consultar su historial autorizado.

## 3.2 Médico no asignado

En Fase 3 puede consultar historia clínica cuando exista autorización longitudinal conforme a `clinical-permissions.md`, pero no puede editar ni completar un encuentro ajeno.

## 3.3 Paciente

Puede consultar su información clínica permitida, pero no editar la nota médica ni los datos estructurales del expediente.

## 3.4 Responsable

Puede consultar información de pacientes para los que tenga una relación activa y permisos aplicables.

## 3.5 Administrador

El acceso administrativo global no se convierte en permiso clínico ordinario. La UX no debe ofrecer un modo "superusuario médico" genérico.

---

# 4. Arquitectura de navegación clínica

La navegación de Fase 3 se mantiene pequeña.

### Ruta nominal

`Agenda → Cita → Iniciar consulta → Consulta clínica → Guardar / Completar → Historial`

### Rutas de lectura

`Paciente → Expediente → Historial clínico → Encuentro`

### Regla

La existencia de un encuentro no obliga a que la aplicación tenga un módulo clínico independiente de Agenda en Fase 3. Puede existir una pantalla clínica dedicada, pero el origen nominal de una consulta continúa siendo la cita.

---

# 5. Pantalla de Agenda: preparación para iniciar

## UX-021 — La cita elegible muestra "Iniciar consulta"

Cuando las precondiciones del workflow son verdaderas, la Agenda puede mostrar la acción.

## UX-022 — La UI no determina elegibilidad por sí sola

La visibilidad del botón se basa en datos del servidor, pero el backend vuelve a comprobar:

- actor autenticado;
- médico asignado;
- estado de la cita;
- presencia física cuando corresponda;
- ausencia de conflicto clínico;
- integridad de relaciones.

## UX-023 — Cita `CANCELLED`

No debe mostrar "Iniciar consulta".

## UX-024 — Cita `NO_SHOW`

No debe mostrar "Iniciar consulta".

## UX-025 — Cita `IN_CONSULTATION`

Debe permitir al médico asignado continuar la consulta existente, no iniciar otra.

## UX-026 — Cita `COMPLETED`

Debe presentar la consulta como cerrada o histórica, según contexto.

## UX-027 — Doble clic en iniciar

El segundo intento no debe generar un mensaje de duplicidad si el encuentro ya existe y la solicitud corresponde al mismo contexto autorizado. El resultado debe conducir al encuentro existente.

---

# 6. Acción "Iniciar consulta"

## UX-028 — Confirmación innecesaria evitada

No se requiere un modal de confirmación adicional cuando la acción es inequívoca y el backend ejecuta la transición atómica.

## UX-029 — Feedback inmediato

Tras un inicio exitoso, la interfaz debe cambiar de contexto a la consulta clínica y reflejar `EN PROGRESO`.

## UX-030 — Error de precondición

Si el servidor rechaza el inicio, la UX debe explicar la causa funcional sin exponer detalles internos.

## UX-031 — Error por estado concurrente

Si otra solicitud inició la consulta primero, la UX debe recuperar el encuentro existente cuando el contrato lo considere idempotente.

## UX-032 — No mostrar mensajes técnicos

No deben mostrarse al médico excepciones, SQL, nombres de tablas ni detalles de concurrencia.

---

# 7. Pantalla de consulta clínica

## 7.1 Estructura recomendada

La pantalla debe priorizar el trabajo clínico y minimizar navegación innecesaria.

Estructura recomendada:

1. encabezado del paciente;
2. contexto de la cita y del médico;
3. estado de la consulta;
4. campos clínicos principales;
5. campos opcionales;
6. acciones persistentes;
7. indicación de última persistencia exitosa.

## UX-033 — Encabezado del paciente

Debe mostrar una identificación suficiente del paciente para evitar errores de selección.

Como mínimo, la identificación visual debe permitir distinguir al paciente de otro del mismo turno. La fuente de verdad sigue siendo `Patient`.

## UX-034 — Contexto de cita

Debe mostrarse la fecha/hora programada, clínica y médico responsable cuando estos datos estén disponibles y sean pertinentes.

## UX-035 — Estado visible

Debe mostrarse una etiqueta clara:

- `En progreso` para `IN_PROGRESS`;
- `Completada` para `COMPLETED`.

## UX-036 — No mostrar controles de estado técnico

El usuario no cambia manualmente `IN_PROGRESS` o `COMPLETED` desde un selector.

---

# 8. Campos clínicos obligatorios

## UX-037 — Motivo de consulta

Debe ser un campo de texto clínico libre.

## UX-038 — Padecimiento actual

Debe ser un campo de texto clínico libre, con suficiente espacio visual para narración.

## UX-039 — Exploración física

Debe ser un campo de texto clínico libre.

## UX-040 — Evaluación / diagnóstico

Debe ser un campo de texto libre. No se requiere catálogo.

## UX-041 — Plan / indicaciones

Debe ser un campo de texto clínico libre.

## UX-042 — Orden visual

Los cinco campos pueden presentarse agrupados en una sección principal porque constituyen el núcleo mínimo de cierre.

## UX-043 — Indicador de requisito

Durante `IN_PROGRESS`, los campos pueden mostrar si contienen contenido suficiente para el criterio de cierre, sin impedir el guardado.

## UX-044 — No convertir la pantalla en checklist rígido

El usuario puede guardar aunque todavía existan campos sin completar.

---

# 9. Campos opcionales

La UX puede incorporar los campos definidos por el modelo F3, siempre que su presencia no cambie el núcleo del workflow.

Entre ellos pueden incluirse:

- signos vitales;
- peso;
- talla;
- antecedentes relevantes;
- estudios;
- observaciones;
- otros datos longitudinales permitidos.

## UX-045 — Opcionales no bloquean por ausencia

Ningún campo opcional debe impedir completar una consulta salvo una política específica futura.

## UX-046 — No usar JSON visible como estructura de captura

La interfaz debe presentar campos concretos y etiquetados.

## UX-047 — Especialidades posteriores

Ginecología, obstetricia, colposcopia, menopausia y otros módulos pueden agregarse como secciones especializadas sin alterar el flujo central.

---

# 10. Validación de contenido

## UX-048 — Validación básica en cliente

Puede realizarse una validación ligera para mejorar la experiencia:

- eliminar visualmente espacios externos al enviar;
- detectar campo vacío o solo con espacios;
- detectar placeholders conocidos;
- informar campos incompletos al intentar completar.

## UX-049 — Validación definitiva en servidor

La validación del cliente nunca sustituye al backend.

## UX-050 — Placeholders

Debe evitarse aceptar como contenido suficiente textos como:

- `N/A`;
- `NA`;
- `No aplica`;
- `Sin información` cuando sea utilizado como mero sustituto;
- equivalentes claramente vacíos;
- variantes con mayúsculas/minúsculas o espacios.

La lista definitiva de patrones corresponde a las reglas de dominio.

## UX-051 — No imponer mínimo de caracteres

No debe aparecer una regla arbitraria como "mínimo 20 caracteres".

## UX-052 — No evaluar calidad clínica

La interfaz no intenta determinar si el diagnóstico es médicamente correcto, suficiente o apropiado.

---

# 11. Guardado parcial

## UX-053 — Acción "Guardar"

Debe estar disponible durante `IN_PROGRESS`.

## UX-054 — Guardar no completa

Después de guardar, la consulta permanece `IN_PROGRESS`.

## UX-055 — Feedback de guardado

Después de un guardado exitoso, la UX debe mostrar una señal discreta de persistencia, por ejemplo:

`Guardado` / `Guardado a las HH:MM`.

## UX-056 — Debe distinguirse último guardado exitoso

No debe afirmarse que una información está guardada si el servidor rechazó la operación.

## UX-057 — Fallo de guardado

La interfaz debe conservar localmente el contenido todavía presente en el formulario mientras la página permanezca abierta, pero no debe presentar ese contenido como persistido.

## UX-058 — No autosave obligatorio

Fase 3 no exige guardado automático.

## UX-059 — No prometer persistencia fuera del formulario

Un contenido no enviado o rechazado no se considera parte de la historia clínica.

---

# 12. Interrupción y reanudación

## UX-060 — Cerrar navegador

No debe aparecer una confirmación que sugiera que cerrar navegador completa la consulta.

## UX-061 — Reingreso

Al regresar a una cita `IN_CONSULTATION`, el médico asignado debe poder abrir el encuentro `IN_PROGRESS` existente.

## UX-062 — Reanudar no reinicia

No debe aparecer nuevamente el flujo de inicio ni modificarse `started_at` por regresar.

## UX-063 — Consulta abandonada visualmente

Si la consulta permanece abierta, debe verse como "En progreso", no como "pendiente de inicio".

## UX-064 — Sin autocierre

No mostrar un mensaje tipo "la consulta terminó automáticamente por superar la duración".

---

# 13. Acción "Completar consulta"

## UX-065 — Acción explícita

La finalización debe ser una acción consciente del médico.

## UX-066 — Ubicación persistente

La acción puede mantenerse visible en un encabezado fijo o pie de formulario para evitar navegación innecesaria.

## UX-067 — Advertencia antes del cierre

Cuando el encuentro esté listo, puede mostrarse una confirmación ligera indicando que después de completarlo no podrá editarse en Fase 3.

Esta confirmación es UX, no una segunda regla de dominio.

## UX-068 — Validación antes de cerrar

Si faltan campos mínimos o existen placeholders inválidos, la interfaz debe identificar claramente cuáles deben corregirse.

## UX-069 — No borrar contenido por validación fallida

Al fallar la validación de completion, el formulario conserva el contenido enviado y permite corregirlo.

## UX-070 — Guardado final incluido

Al presionar "Completar consulta", la interfaz envía los valores actuales. No debe exigir un clic previo en "Guardar" si los datos actuales ya forman parte de la solicitud de completion.

## UX-071 — Resultado exitoso

La pantalla cambia a modo histórico/solo lectura y muestra la hora de cierre.

---

# 14. Estado `COMPLETED`

## UX-072 — Formulario bloqueado

Los campos clínicos no deben aparecer editables.

## UX-073 — El historial sigue visible

Completar no oculta la nota. La convierte en registro histórico.

## UX-074 — No acción "Reabrir"

La interfaz no ofrece reapertura.

## UX-075 — No acción "Editar"

No debe ofrecerse edición de la nota cerrada en Fase 3.

## UX-076 — Visualización temporal

Deben mostrarse `started_at`, `completed_at` y la identidad del médico cuando correspondan a la autorización del actor.

---

# 15. Historia clínica

## UX-077 — El expediente no es una sola nota

La vista de expediente debe distinguir:

- datos longitudinales;
- resumen clínico derivado;
- historial de encuentros.

## UX-078 — Orden cronológico

El historial de encuentros debe mostrarse de forma ordenada y consistente, preferentemente del más reciente al más antiguo para lectura clínica.

## UX-079 — Encuentro como unidad histórica

Cada encuentro debe poder abrirse individualmente cuando el actor tenga autorización.

## UX-080 — No mezclar agenda con historia

Una cita cancelada o `NO_SHOW` no debe aparecer como si hubiera generado una consulta clínica.

## UX-081 — Identificación temporal

Cada entrada histórica debe permitir distinguir al menos fecha, médico y estado cuando corresponda.

---

# 16. Expediente longitudinal

## UX-082 — Datos estructurados

La edición de antecedentes longitudinales se realizará en campos estructurados definidos por el dominio y el modelo de datos.

## UX-083 — Separación de encuentro

Editar un dato longitudinal no equivale a modificar una nota histórica cerrada.

## UX-084 — No sobrescribir historia

La modificación de un dato actual no debe reescribir retrospectivamente el contenido de encuentros históricos.

## UX-085 — Alertas futuras

Las `ClinicalAlert` se mostrarán como componentes diferenciados cuando se implemente su módulo.

## UX-086 — Recetas, estudios y documentos futuros

No deben simularse como texto genérico dentro de la nota si aún no existen sus módulos.

---

# 17. Permisos y UX por actor

## 17.1 Médico asignado

### UX-087

Puede ver y trabajar el encuentro `IN_PROGRESS` que le corresponde.

### UX-088

Puede completar su encuentro abierto.

### UX-089

Después de completar, solo lectura.

## 17.2 Médico no asignado

### UX-090

No se debe mostrar botón de edición en un encuentro que no puede modificar.

### UX-091

Puede consultar historia cuando la relación/autorización longitudinal lo permita.

## 17.3 Paciente

### UX-092

Puede consultar la información clínica permitida.

### UX-093

No debe ver botones de editar nota médica, completar consulta o modificar antecedentes estructurales.

## 17.4 Responsable

### UX-094

Puede consultar únicamente pacientes autorizados por relación activa y políticas correspondientes.

## 17.5 Administrador

### UX-095

No se crea un modo clínico privilegiado por ser administrador.

---

# 18. Protección contra errores de paciente

## UX-096 — Identificación fuerte

Antes de iniciar, el paciente debe identificarse de forma clara.

## UX-097 — Evitar acciones destructivas

Como no existe borrado de notas, la UX debe priorizar prevención de equivocaciones sobre mecanismos de "deshacer" clínico.

## UX-098 — Contexto persistente

Durante la captura, la identidad del paciente debe permanecer visible o fácilmente verificable.

## UX-099 — Evitar cambio silencioso de paciente

Cambiar el paciente durante una consulta abierta debe requerir abandonar el contexto actual y volver a un recurso explícito; no se permite reusar el mismo encuentro para otro paciente.

---

# 19. Manejo de errores UX

## UX-100 — Error de autenticación

Redirigir al flujo de autenticación correspondiente o mostrar sesión expirada sin revelar información clínica.

## UX-101 — Error de autorización

Mostrar una respuesta funcional tipo "No tienes permiso para realizar esta acción".

## UX-102 — Recurso inexistente o no visible

No debe revelarse información que permita inferir un recurso clínico restringido.

## UX-103 — Estado clínico inválido

Explicar que la operación ya no es válida por el estado actual de la consulta.

## UX-104 — Validación de campos

Los errores de completion deben ser específicos por campo.

## UX-105 — Error de conflicto

Cuando una solicitud concurrente pierde la carrera, mostrar el estado resultante sin detalles técnicos.

## UX-106 — Error temporal de red

Indicar que el guardado no pudo confirmarse y evitar afirmar persistencia.

## UX-107 — Reintento

Las acciones seguras e idempotentes pueden permitir reintento explícito.

## UX-108 — No duplicar acciones

Durante una operación en curso, el botón puede deshabilitarse visualmente para evitar dobles envíos, sin confiar en ello para la integridad.

---

# 20. Concurrencia en la interfaz

## UX-109 — Doble clic en "Iniciar"

La UI puede deshabilitar momentáneamente el botón, pero el backend debe mantener idempotencia.

## UX-110 — Doble clic en "Completar"

La UI puede impedir segundos clics inmediatos. El backend debe resolver solicitudes concurrentes de manera segura.

## UX-111 — Edición en pestañas múltiples

Fase 3 no exige edición colaborativa en tiempo real. El comportamiento mínimo esperado es conservar integridad del estado en servidor.

## UX-112 — No fingir tiempo real

La UX no debe mostrar simultáneamente que dos usuarios editan el mismo encuentro salvo que exista infraestructura explícita futura.

---

# 21. Indicadores de persistencia y estado

## UX-113 — Estado de persistencia

La pantalla debe distinguir entre:

- cambios aún no enviados;
- último guardado exitoso;
- guardado rechazado;
- consulta completada.

## UX-114 — `updated_at`

Puede presentarse como "Última actualización" cuando sea útil, pero su semántica es la del servidor: último guardado exitoso.

## UX-115 — `started_at`

Representa el inicio real de la consulta, no la hora programada de la cita.

## UX-116 — `completed_at`

Solo aparece cuando la consulta ha completado correctamente.

---

# 22. Formularios

## UX-117 — Campos de texto amplios

Los cinco campos centrales deben tener espacio suficiente para narración clínica.

## UX-118 — Etiquetas claras

Las etiquetas deben utilizar lenguaje clínico comprensible y evitar abreviaturas internas.

## UX-119 — No depender de placeholders como única etiqueta

El nombre del campo debe seguir visible incluso cuando exista contenido.

## UX-120 — Accesibilidad

Los controles deben ser navegables por teclado y tener etiquetas asociadas.

## UX-121 — Validación cerca del campo

Los errores específicos deben aparecer junto al campo afectado y también resumirse al intentar completar cuando existan varios errores.

## UX-122 — Persistencia de scroll

Después de un guardado, no debe producirse un salto de pantalla que haga perder el contexto de captura.

---

# 23. Salida de la consulta

## UX-123 — Abandonar sin completar

La UX debe permitir salir. La consulta permanece `IN_PROGRESS`.

## UX-124 — Advertencia opcional de cambios no guardados

Puede advertirse si existen modificaciones del formulario no confirmadas por el servidor.

## UX-125 — No confundir salida con cierre

Salir de la pantalla no cambia `ClinicalEncounter.status`.

## UX-126 — Volver a la agenda

Después de salir, la cita debe seguir representada como `IN_CONSULTATION` mientras el encuentro continúe abierto.

---

# 24. Diseño de respuestas y lenguaje

## UX-127 — Lenguaje humano

Usar mensajes funcionales, no términos de implementación.

## UX-128 — Mensajes breves

No explicar al usuario el detalle de constraints, locks o transacciones.

## UX-129 — No atribuir decisiones a la UI

Evitar mensajes como "la pantalla no te deja porque..." cuando el motivo real es una regla de autorización del servidor. Mejor explicar la consecuencia funcional.

## UX-130 — Confirmación clara de cierre

La finalización exitosa debe comunicar que la consulta quedó registrada y cerrada.

---

# 25. Estados visuales recomendados

| Estado técnico | Etiqueta UX | Acción principal |
|---|---|---|
| `SCHEDULED` | Programada | Iniciar consulta, si el actor está autorizado y se cumplen precondiciones |
| `IN_CONSULTATION` | En consulta | Continuar consulta |
| `IN_PROGRESS` | En progreso | Guardar / Completar |
| `COMPLETED` | Completada | Ver consulta |
| `CANCELLED` | Cancelada | Ver cita, sin iniciar |
| `NO_SHOW` | No asistió | Ver cita, sin iniciar |

Nota: `Appointment` y `ClinicalEncounter` son estados de entidades distintas. La UX puede presentar un estado combinado para facilitar comprensión, pero no debe fingir que son el mismo atributo.

---

# 26. Flujo nominal de UX

1. El médico abre Agenda.
2. Visualiza una cita `SCHEDULED` elegible.
3. Selecciona "Iniciar consulta".
4. El servidor cambia la cita a `IN_CONSULTATION` y crea el `ClinicalEncounter` `IN_PROGRESS` de forma atómica.
5. La interfaz abre la pantalla clínica.
6. El médico captura información.
7. Puede guardar parcial tantas veces como necesite.
8. Si interrumpe, el encuentro permanece abierto.
9. Al regresar, continúa el mismo encuentro.
10. Cuando los cinco campos mínimos contienen contenido clínico válido, selecciona "Completar consulta".
11. El sistema valida, guarda los últimos cambios y cierra de forma atómica.
12. La interfaz cambia a modo solo lectura y permite regresar al historial autorizado.

---

# 27. Flujo alternativo: contenido incompleto

1. El médico selecciona "Completar consulta".
2. El servidor identifica campos mínimos faltantes o inválidos.
3. La UI muestra los campos afectados.
4. El encuentro permanece `IN_PROGRESS`.
5. El médico corrige.
6. Se permite reintentar.

---

# 28. Flujo alternativo: consulta interrumpida

1. El médico captura algunos campos.
2. Guarda o abandona la pantalla.
3. La consulta permanece `IN_PROGRESS`.
4. Posteriormente vuelve al recurso.
5. Recupera el último estado persistido.
6. Continúa y eventualmente completa.

---

# 29. Flujo alternativo: otro médico

1. Un médico no asignado abre un expediente autorizado.
2. Puede leer los encuentros históricos que la política de acceso permita.
3. El encuentro abierto de otro médico no presenta controles de edición.
4. No puede completar ni apropiarse de la consulta.

---

# 30. Flujo alternativo: paciente o responsable

La vista es de lectura y está limitada por objeto y relación.

No se ofrecen controles de edición clínica.

---

# 31. Seguridad visible al usuario

## UX-131 — No exponer identificadores internos innecesarios

No es necesario mostrar UUIDs técnicos, claves internas o IDs de base de datos salvo necesidad funcional explícita.

## UX-132 — No mostrar datos fuera de permiso para "contexto"

El encabezado no debe incluir información que el usuario no podría consultar en una lectura directa.

## UX-133 — Descargas

No deben existir descargas clínicas abiertas o enlaces que omitan autorización del backend.

## UX-134 — Caché del navegador

La UX no debe asumir que ocultar una ruta impide recuperar contenido ya cargado. Las políticas de seguridad y cabeceras se definen en backend.

---

# 32. Documentos y archivos

Fase 3 core no requiere adjuntos clínicos como parte del formulario de consulta.

## UX-135

No crear un área genérica de "archivos" si todavía no existe `ClinicalDocument` operativo.

## UX-136

Cuando se implemente documentación clínica, la descarga y visualización respetarán los permisos del documento y quedarán sujetas a las políticas de seguridad/auditoría.

---

# 33. Resumen clínico y panel del paciente

El resumen clínico puede mostrarse como una proyección útil para la atención.

## UX-137 — No presentarlo como una nueva fuente de verdad

Los datos deben vincularse conceptualmente a sus fuentes.

## UX-138 — No etiquetar diagnósticos inferidos

La interfaz no debe fabricar "diagnóstico actual" a partir de texto histórico.

## UX-139 — Actividad reciente

Puede presentar los encuentros más recientes y otros datos permitidos, siempre sin alterar la semántica histórica.

---

# 34. Diseño para especialidades futuras

## UX-140 — Núcleo genérico primero

La interfaz F3 debe resolver la consulta general antes de especializarse.

## UX-141 — Extensiones por secciones

Módulos como ginecología, obstetricia, colposcopia o menopausia podrán aparecer como secciones especializadas que reutilicen el flujo principal.

## UX-142 — No contaminar el núcleo

No crear campos especializados obligatorios en el formulario genérico sin una decisión de fase posterior.

---

# 35. Qué no debe aparecer en la UX de Fase 3

No debe aparecer, salvo que otro módulo ya existente lo requiera:

- check-in / waiting room;
- temporizador que autocierre;
- reapertura de consultas;
- edición de consultas completadas;
- CIE-10 obligatorio;
- catálogo diagnóstico obligatorio;
- IA que diagnostique;
- recomendaciones clínicas autónomas;
- botón de borrado de expediente;
- botón de borrado de consulta;
- escritura masiva por rol;
- "admin bypass" clínico;
- edición por cualquier médico por el simple hecho de ser médico;
- creación automática de `DoctorPatientRelationship` al iniciar una consulta;
- intercambio de paciente dentro del mismo encuentro.

---

# 36. Accesibilidad mínima

## UX-143

Todos los campos deben tener etiquetas accesibles.

## UX-144

Los mensajes de error deben ser identificables por tecnologías de asistencia.

## UX-145

Los estados no deben comunicarse únicamente por color.

## UX-146

Las acciones primarias deben tener nombres explícitos.

## UX-147

El orden de tabulación debe seguir el orden clínico lógico.

---

# 37. Responsividad

## UX-148

En escritorio, la consulta debe priorizar una vista de trabajo amplia.

## UX-149

En pantallas reducidas, los campos de texto deben mantener altura suficiente y evitar pérdida de contenido.

## UX-150

Las acciones Guardar y Completar deben permanecer accesibles sin requerir desplazamientos extremos.

---

# 38. Telemetría y analytics

Fase 3 no requiere analítica de contenido clínico.

## UX-151

No registrar en analytics valores textuales de campos clínicos.

## UX-152

Métricas de UX permitidas, cuando exista infraestructura adecuada, pueden limitarse a eventos no clínicos como tiempo de carga o error técnico, sin incluir contenido sensible.

---

# 39. Auditoría vs. UX

La UX no necesita exponer el detalle completo del `audit trail` en el flujo normal.

## UX-153

Puede existir una vista administrativa/clínica de auditoría en fases posteriores.

## UX-154

La ausencia de una pantalla de auditoría no significa ausencia de auditoría del backend.

---

# 40. Reglas de cierre propuestas

Las siguientes decisiones se consideran cerradas para Fase 3 UX:

| ID | Decisión |
|---|---|
| UX-C-001 | El flujo clínico nace de una cita iniciada desde Agenda |
| UX-C-002 | No existe check-in/waiting |
| UX-C-003 | La pantalla clínica usa `IN_PROGRESS` y `COMPLETED` como estados del encuentro |
| UX-C-004 | Guardar es independiente de completar |
| UX-C-005 | Se permite guardado parcial |
| UX-C-006 | Los cinco campos mínimos solo bloquean completion |
| UX-C-007 | Diagnóstico es texto libre |
| UX-C-008 | No existe autosave obligatorio |
| UX-C-009 | Una interrupción deja la consulta abierta |
| UX-C-010 | La duración de la cita no autocierra |
| UX-C-011 | Complete persiste los últimos cambios y cierra atómicamente |
| UX-C-012 | `COMPLETED` es solo lectura |
| UX-C-013 | No existe reapertura en Fase 3 |
| UX-C-014 | No existe DELETE clínico funcional |
| UX-C-015 | La UI no sustituye autorización backend |
| UX-C-016 | Otro médico puede leer solo si existe autorización longitudinal |
| UX-C-017 | El médico no asignado no edita ni completa el encuentro ajeno |
| UX-C-018 | Paciente y responsable son lectura según permiso |
| UX-C-019 | Administrador no obtiene bypass clínico genérico |
| UX-C-020 | No crear relación médico-paciente automáticamente |
| UX-C-021 | No introducir CIE-10 obligatorio |
| UX-C-022 | No introducir IA diagnóstica |
| UX-C-023 | No crear checklists especializados obligatorios |
| UX-C-024 | El expediente es longitudinal y los encuentros son históricos |
| UX-C-025 | Los datos clínicos sensibles no se envían a analytics |

---

# 41. Criterios de aceptación UX

La UX de Fase 3 se considera coherente cuando:

1. un médico asignado puede iniciar una consulta desde una cita válida;
2. la UI representa correctamente `IN_PROGRESS` y `COMPLETED`;
3. guardar no bloquea por campos clínicos faltantes;
4. completar sí valida los cinco mínimos;
5. los placeholders inválidos se rechazan de acuerdo con el contrato de dominio;
6. se puede interrumpir y reanudar sin crear otro encuentro;
7. no existe autocierre por tiempo;
8. no existe edición después de completar;
9. no existe borrado clínico;
10. otro médico autorizado puede leer sin editar;
11. paciente/responsable ven solo lo permitido;
12. las operaciones no dependen de la UI para seguridad;
13. los mensajes no exponen detalles internos;
14. la identidad del paciente permanece clara durante toda la captura;
15. los cambios no confirmados no se presentan como persistidos;
16. el flujo de completion incluye los últimos cambios enviados;
17. el historial diferencia cita de consulta clínica;
18. no se introducen capacidades fuera del alcance F3.

---

# 42. Dependencias

Este documento depende de:

- `clinical-permissions.md` para autorización;
- `clinical-security-and-privacy.md` para controles de seguridad;
- `clinical-api-contracts.md` para transporte;
- `clinical-service-contracts.md` para operaciones;
- `clinical-encounter-workflow.md` para transiciones;
- `clinical-encounter-rules.md` para reglas;
- `clinical-data-model.md` para campos y estados.

No redefine esas fuentes.

---

# 43. Próximo documento

El siguiente documento de la secuencia definida para Fase 3 es:

`clinical-screens.md`

Ese documento debe convertir estas políticas UX en especificaciones concretas de pantallas, componentes, estados visuales, acciones y navegación, sin cambiar las reglas aquí cerradas.

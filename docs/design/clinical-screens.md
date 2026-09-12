# TeCuidoApp — Fase 3: Clinical Screens

> **Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11 — sin hallazgos que requirieran corrección de contenido)
>
> **Propósito:** traducir las políticas de UX de Fase 3 a pantallas concretas, sus componentes, estados, acciones y comportamiento visible, sin introducir reglas nuevas de negocio.
>
> **Regla rectora:** una pantalla representa capacidades autorizadas; nunca es la autoridad de seguridad, autorización, estado o integridad clínica.

---

## 1. Propósito y alcance

Este documento especifica las pantallas necesarias para el núcleo clínico de Fase 3.

El conjunto mínimo propuesto es deliberadamente pequeño:

1. Agenda clínica con contexto de atención.
2. Preparación/inicio de consulta.
3. Consulta clínica `IN_PROGRESS`.
4. Consulta clínica `COMPLETED`.
5. Expediente clínico.
6. Historial clínico.
7. Detalle de encuentro histórico.

La pantalla de expediente puede incorporar el historial como sección o navegación secundaria; no se exige una arquitectura de múltiples páginas si el routing existente permite una experiencia equivalente.

Fuera de alcance quedan interfaces completas para:

- recetas estructuradas;
- órdenes y resultados de estudios;
- documentos clínicos adjuntos;
- alertas clínicas avanzadas;
- especialidades específicas;
- auditoría administrativa avanzada;
- exportación clínica avanzada;
- edición de consultas completadas.

---

# 2. Fuentes normativas

La especificación depende directamente de:

- `phase-3-clinical-ux.md`;
- `clinical-encounter-workflow.md`;
- `clinical-encounter-rules.md`;
- `clinical-encounter-domain.md`;
- `clinical-record-domain.md`;
- `clinical-data-model.md`;
- `clinical-permissions.md`;
- `clinical-security-and-privacy.md`;
- `clinical-service-contracts.md`;
- `clinical-api-contracts.md`.

En caso de contradicción, una regla de dominio, seguridad, permisos, servicio o API prevalece sobre la apariencia o comportamiento propuesto aquí.

---

# 3. Principios de diseño de pantallas

## SCREEN-001 — Una pantalla, una responsabilidad principal

Cada pantalla debe tener un objetivo clínico principal identificable.

## SCREEN-002 — La pantalla no muta directamente el ORM

Toda escritura se realiza mediante los contratos de servicio/API definidos.

## SCREEN-003 — La pantalla no decide permisos

La ausencia de un botón mejora la UX, pero el backend debe volver a autorizar.

## SCREEN-004 — El paciente debe ser identificable siempre

En todo contexto clínico debe existir una identificación suficientemente clara del paciente.

## SCREEN-005 — El estado debe ser visible

El usuario debe distinguir claramente consulta en progreso de consulta completada.

## SCREEN-006 — No mostrar estados técnicos innecesarios

`IN_PROGRESS` y `COMPLETED` pueden representarse como `En progreso` y `Completada`.

## SCREEN-007 — No introducir estados funcionales nuevos

No deben aparecer `WAITING`, `CHECKED_IN`, `PAUSED`, `DRAFT` u otros estados como equivalentes funcionales del dominio.

## SCREEN-008 — No usar colores como única señal

Estado, errores o permisos no deben comunicarse únicamente por color.

## SCREEN-009 — Acciones primarias persistentes

Guardar y completar deben ser accesibles sin navegación innecesaria.

## SCREEN-010 — Persistencia visible

El usuario debe poder distinguir cambios sin guardar de información confirmada por servidor.

## SCREEN-011 — Sin confirmaciones innecesarias

No se agregan modales de confirmación para operaciones inequívocas, salvo aquellas cuyo propósito sea advertir sobre consecuencias irreversibles.

## SCREEN-012 — Cierre explícito

Completar consulta es una acción consciente y visible.

## SCREEN-013 — Sin reapertura

Las pantallas de encuentro completado no presentan reapertura.

## SCREEN-014 — Sin borrado clínico

No presentar acciones para eliminar expediente o encuentro.

## SCREEN-015 — Datos derivados identificables

Cuando se muestre un resumen derivado, no debe parecer una nota clínica independiente.

---

# 4. Inventario de pantallas

| ID | Pantalla | Propósito principal | Modo | Actor central |
|---|---|---|---|---|
| S-01 | Agenda clínica | Identificar citas y estado de atención | lectura + transición | Médico |
| S-02 | Inicio de consulta | Confirmar contexto e iniciar | acción | Médico asignado |
| S-03 | Consulta en progreso | Capturar y guardar atención | edición | Médico asignado |
| S-04 | Consulta completada | Visualizar nota cerrada | solo lectura | Actor autorizado |
| S-05 | Expediente clínico | Ver resumen y datos longitudinales | lectura / edición selectiva | Actor autorizado |
| S-06 | Historial clínico | Recorrer encuentros históricos | solo lectura | Actor autorizado |
| S-07 | Detalle de encuentro | Leer una consulta específica | solo lectura | Actor autorizado |

No es obligatorio que cada ID corresponda a una URL independiente; pueden ser estados de una misma página, siempre que la responsabilidad y autorización sean equivalentes.

---

# 5. S-01 — Agenda clínica

## 5.1 Objetivo

Permitir al médico identificar una cita válida y entrar al flujo clínico.

## SCREEN-016 — Fuente de verdad

La cita se obtiene desde Agenda; no se recrea una agenda paralela en el módulo clínico.

## SCREEN-017 — Información mínima por cita

Cada tarjeta/fila debe mostrar, cuando sea aplicable:

- paciente;
- fecha y hora;
- clínica;
- médico asignado;
- estado de la cita;
- acción disponible.

## SCREEN-018 — Acción para `SCHEDULED`

La cita elegible puede mostrar `Iniciar consulta`.

## SCREEN-019 — Acción para `IN_CONSULTATION`

La cita debe mostrar `Continuar consulta` o equivalente.

## SCREEN-020 — Acción para `COMPLETED`

La cita puede mostrar `Ver consulta`.

## SCREEN-021 — `CANCELLED`

No presenta inicio ni continuación clínica.

## SCREEN-022 — `NO_SHOW`

No presenta inicio ni continuación clínica.

## SCREEN-023 — Estado clínico visible

Cuando una cita está `IN_CONSULTATION`, la UI puede mostrar la relación con `ClinicalEncounter IN_PROGRESS` sin duplicar el estado como un nuevo estado de dominio.

## SCREEN-024 — Doble inicio

La UI puede bloquear el segundo clic, pero si llega al backend debe recibir la semántica idempotente definida.

## SCREEN-025 — Paciente inequívoco

El nombre visible debe acompañarse de otros datos permitidos para diferenciar homónimos.

## SCREEN-026 — Acceso restringido

La Agenda clínica no debe listar pacientes ajenos a los alcances definidos por la autorización existente.

---

# 6. S-02 — Inicio de consulta

## 6.1 Cuándo usarla

Puede implementarse como una vista previa, drawer, modal breve o transición directa. La elección visual no cambia el contrato.

## SCREEN-027 — Contexto visible

Antes de iniciar, el usuario debe poder verificar:

- paciente;
- cita;
- médico asignado;
- clínica;
- fecha/hora;
- condición de inicio según la UI disponible.

## SCREEN-028 — Paciente presente

Si la política de Agenda exige verificación de presencia, la pantalla debe mostrar su estado o confirmación funcional antes de permitir iniciar.

## SCREEN-029 — Sin selector de médico

El usuario no elige un médico alterno para apropiarse de la consulta.

## SCREEN-030 — Acción primaria

`Iniciar consulta` debe ser inequívoca.

## SCREEN-031 — No cambiar la cita manualmente

No se expone un selector para cambiar la cita a `IN_CONSULTATION`; el servidor realiza la transición.

## SCREEN-032 — Éxito

El flujo navega a S-03.

## SCREEN-033 — Repetición idempotente

Si ya existe el encuentro equivalente, la UX conduce a S-03 en vez de mostrar un error de duplicado.

## SCREEN-034 — Estado inválido

Si la cita ya no es iniciable, la UI informa que el estado actual no permite iniciar y ofrece una salida segura.

---

# 7. S-03 — Consulta clínica en progreso

## 7.1 Objetivo

Permitir al médico asignado documentar una atención abierta y persistir avances.

## 7.2 Estructura visual propuesta

### Cabecera clínica

Debe incluir:

- paciente;
- identificadores visuales suficientes;
- médico responsable;
- clínica;
- estado `En progreso`;
- fecha/hora de la cita;
- opcionalmente `Inicio: HH:MM`.

### Cuerpo clínico

Secciones principales:

1. Motivo de consulta.
2. Padecimiento actual.
3. Exploración física.
4. Evaluación / diagnóstico.
5. Plan / indicaciones.

### Sección opcional

Campos adicionales definidos por el modelo F3 pueden aparecer después del núcleo clínico.

### Barra de acciones

- `Guardar`;
- `Completar consulta`;
- salir/regresar.

## SCREEN-035 — Cinco campos principales

Los cinco campos obligatorios deben estar claramente identificados y no deben confundirse con opcionales.

## SCREEN-036 — Motivo de consulta

Textarea de texto clínico libre.

## SCREEN-037 — Padecimiento actual

Textarea de mayor altura que permita narración clínica.

## SCREEN-038 — Exploración física

Textarea de texto clínico libre.

## SCREEN-039 — Evaluación / diagnóstico

Textarea de texto libre. No existe selector CIE-10 obligatorio.

## SCREEN-040 — Plan / indicaciones

Textarea de texto clínico libre.

## SCREEN-041 — Campos opcionales

Se muestran bajo una sección secundaria, por ejemplo `Datos complementarios`, sin afectar la regla de completion salvo políticas futuras.

## SCREEN-042 — No usar JSON visible

La captura se realiza mediante controles etiquetados, no mediante una caja JSON.

---

# 8. Encabezado clínico del paciente

## SCREEN-043 — Identidad del paciente

El encabezado debe permanecer visible o recuperable fácilmente durante toda la captura.

## SCREEN-044 — Fuente de datos

Los datos personales se presentan desde `Patient` y no deben duplicarse como datos clínicos libres.

## SCREEN-045 — Homónimos

La interfaz debe permitir distinguir pacientes con nombre similar mediante información secundaria autorizada.

## SCREEN-046 — Evitar sobresaturación

La identificación debe ser suficientemente fuerte sin mostrar más información sensible de la necesaria.

## SCREEN-047 — Sin cambio silencioso

No debe ser posible cambiar el paciente del formulario manteniendo el mismo encuentro.

---

# 9. Estado del formulario

## SCREEN-048 — Estado inicial

Al abrir un encuentro `IN_PROGRESS`, los valores persistidos se cargan como último estado confirmado por servidor.

## SCREEN-049 — Cambios locales

La edición en el formulario puede existir temporalmente sin implicar persistencia.

## SCREEN-050 — Indicador de cambios

Puede mostrarse `Cambios sin guardar` cuando el formulario difiera del último estado persistido.

## SCREEN-051 — Último guardado

Después de un guardado exitoso debe mostrarse una indicación discreta como `Guardado a las HH:MM`.

## SCREEN-052 — Guardado fallido

La interfaz debe conservar los valores aún presentes en el formulario, pero no debe mostrarlos como guardados.

## SCREEN-053 — Estado cargado correctamente

No debe presentarse un indicador de guardado hasta existir una confirmación del servidor.

---

# 10. Validación de campos en S-03

## SCREEN-054 — Guardar sin requisitos mínimos completos

Permitido.

## SCREEN-055 — Completar con campos vacíos

Bloqueado por validación del dominio/API.

## SCREEN-056 — Completar con placeholders

Bloqueado cuando el contenido coincide con patrones de placeholder definidos por dominio.

## SCREEN-057 — Espacios

Los valores de solo espacios deben tratarse como vacíos.

## SCREEN-058 — Sin longitud mínima arbitraria

No mostrar contadores que obliguen a un número de caracteres no definido por el dominio.

## SCREEN-059 — Validación cercana

Los errores se muestran junto al campo afectado y, si son varios, también en un resumen superior o inferior.

## SCREEN-060 — No evaluar corrección clínica

La UI no califica diagnóstico, plan ni calidad médica.

---

# 11. Acción `Guardar`

## SCREEN-061 — Disponibilidad

`Guardar` está disponible mientras el encuentro esté `IN_PROGRESS` y el actor tenga permiso de edición.

## SCREEN-062 — Semántica

Guardar persiste solamente los valores enviados y mantiene el encuentro `IN_PROGRESS`.

## SCREEN-063 — Timestamps

Los timestamps los controla el servidor; la UI no los envía como valores editables.

## SCREEN-064 — Identidad inmutable

No se puede cambiar paciente, appointment, doctor responsable ni identidad estructural del encuentro desde el formulario.

## SCREEN-065 — Estado inmutable desde UI

No existe selector para cambiar `IN_PROGRESS`.

## SCREEN-066 — Éxito

Se actualiza el indicador de último guardado y el formulario permanece en la misma pantalla.

## SCREEN-067 — Fallo

Se informa que el cambio no pudo confirmarse y se conserva la captura visible.

## SCREEN-068 — Doble envío

La UI puede deshabilitar temporalmente el botón mientras procesa la petición.

---

# 12. Acción `Completar consulta`

## SCREEN-069 — Acción consciente

Debe diferenciarse visualmente de `Guardar`.

## SCREEN-070 — Advertencia final

Puede existir una confirmación breve indicando que la consulta quedará cerrada y no podrá editarse en Fase 3.

## SCREEN-071 — No exigir clic previo en Guardar

Completion debe incluir los valores actuales del formulario.

## SCREEN-072 — Validación

La UI muestra los cinco campos mínimos faltantes o inválidos cuando el servidor los rechaza.

## SCREEN-073 — Fallo de validación

El encuentro continúa `IN_PROGRESS`.

## SCREEN-074 — Éxito

La interfaz cambia a S-04 o al modo solo lectura equivalente.

## SCREEN-075 — Doble completion

La UI puede evitar el doble clic, pero el backend sigue siendo responsable de la integridad.

---

# 13. S-04 — Consulta completada

## 13.1 Objetivo

Mostrar una consulta clínica histórica sin capacidades de modificación.

## SCREEN-076 — Indicador de cierre

Mostrar `Completada` de manera inequívoca.

## SCREEN-077 — Formulario bloqueado

Todos los campos clínicos aparecen como texto de solo lectura.

## SCREEN-078 — Sin `Editar`

No se muestra botón de edición.

## SCREEN-079 — Sin `Reabrir`

No existe acción de reapertura.

## SCREEN-080 — Sin `Eliminar`

No existe acción de eliminación.

## SCREEN-081 — Metadatos temporales

Mostrar cuando corresponda:

- inicio real;
- última actualización;
- cierre;
- médico.

## SCREEN-082 — Historia visible

La nota permanece accesible al actor autorizado.

## SCREEN-083 — Lectura por otro médico

No mostrar controles de edición aunque tenga permiso de lectura longitudinal.

---

# 14. S-05 — Expediente clínico

## 14.1 Objetivo

Presentar la vista longitudinal del paciente sin convertirla en una segunda nota clínica.

## SCREEN-084 — Cabecera

Mostrar la identidad del paciente permitida y el contexto actual.

## SCREEN-085 — Resumen clínico

Puede mostrar datos derivados o estructurados útiles para atención, siempre que estén claramente diferenciados de un encuentro histórico.

## SCREEN-086 — Datos longitudinales

La sección puede contener campos explícitos definidos por `MedicalRecord`.

## SCREEN-087 — Historial

Debe incluir acceso a encuentros ordenados cronológicamente.

## SCREEN-088 — Separación semántica

Las secciones `Datos longitudinales`, `Resumen` e `Historial` no deben mezclarse en una sola narrativa sin distinción.

## SCREEN-089 — Diagnóstico actual

No etiquetar como `Diagnóstico actual` un dato que en realidad es derivado de historial o texto libre histórico.

## SCREEN-090 — Datos de Patient

Datos personales provienen de `Patient`; no se muestran como copias editables dentro de `MedicalRecord`.

---

# 15. Edición de datos longitudinales del expediente

## SCREEN-091 — Intención explícita

La edición de un antecedente longitudinal debe utilizar controles definidos y una acción de guardado específica.

## SCREEN-092 — No editar historia por accidente

Guardar cambios longitudinales no debe modificar una consulta histórica.

## SCREEN-093 — Actor autorizado

Los controles de edición solo se muestran a actores que tengan permiso de escritura sobre esos datos.

## SCREEN-094 — No reemplazo total

No ofrecer un botón `Reemplazar expediente`.

## SCREEN-095 — No reasignación

No ofrecer cambio de propietario del expediente.

## SCREEN-096 — Persistencia

El éxito se comunica únicamente después de confirmación del servidor.

---

# 16. S-06 — Historial clínico

## SCREEN-097 — Orden

Por defecto, mostrar encuentros del más reciente al más antiguo.

## SCREEN-098 — Entrada histórica

Cada entrada debe mostrar, según permiso:

- fecha de atención;
- médico;
- clínica;
- estado;
- acceso al detalle.

## SCREEN-099 — Citas sin consulta

`CANCELLED` y `NO_SHOW` no deben aparecer como encuentros clínicos.

## SCREEN-100 — Cita vs encuentro

Cuando se muestre contexto de cita, debe distinguirse del encuentro clínico.

## SCREEN-101 — Paginación

El historial debe soportar paginación si el API la requiere.

## SCREEN-102 — Sin modificación desde lista

La lista no ofrece edición masiva ni modificaciones clínicas.

---

# 17. S-07 — Detalle de encuentro histórico

## SCREEN-103 — Identificación

Mostrar paciente, fecha, médico, clínica y estado conforme a permisos.

## SCREEN-104 — Contenido

Mostrar los campos clínicos persistidos por el encuentro.

## SCREEN-105 — Lectura solamente

En Fase 3, esta pantalla no permite editar un encuentro `COMPLETED`.

## SCREEN-106 — Otros médicos

Cuando tengan lectura autorizada, ven la misma representación histórica sin acciones de edición.

## SCREEN-107 — Paciente/responsable

La representación se limita a la información que las políticas permitan visualizar.

---

# 18. Pantallas y permisos por actor

| Pantalla / acción | Médico asignado | Otro médico autorizado | Paciente | Responsable | Administrador |
|---|---|---|---|---|---|
| Ver cita contextual | Sí, según Agenda | Según acceso | Según política | Según relación | Administrativo según política |
| Iniciar consulta | Sí | No | No | No | No por rol administrativo |
| Editar `IN_PROGRESS` | Sí, si es asignado | No | No | No | No por rol administrativo |
| Completar | Sí, si es asignado | No | No | No | No por rol administrativo |
| Ver `COMPLETED` | Sí, según autorización | Sí, si autorización longitudinal | Sí, según alcance | Sí, según relación | Solo acceso administrativo explícito |
| Editar antecedentes longitudinales | Según permiso | Según permiso | No en F3 | No en F3 salvo política futura | No por defecto |
| Eliminar clínico | No | No | No | No | No |
| Reabrir encuentro | No | No | No | No | No |

La tabla es una representación UX de `clinical-permissions.md`; no lo sustituye.

---

# 19. Médico no asignado

## SCREEN-108 — Lectura sin edición

Si tiene autorización longitudinal, la UI debe mostrar el encuentro en modo de solo lectura.

## SCREEN-109 — No apropiación

No mostrar `Continuar`, `Guardar` ni `Completar` para un encuentro abierto que pertenece a otro médico.

## SCREEN-110 — Contexto

Puede verse el contexto de quién atiende siempre que esté permitido por las reglas de privacidad.

---

# 20. Paciente

## SCREEN-111 — Acceso propio

El paciente consulta únicamente su información autorizada.

## SCREEN-112 — Sin acciones médicas

No presenta `Iniciar`, `Guardar`, `Completar` ni edición de nota.

## SCREEN-113 — Historial comprensible

La vista de historia puede usar lenguaje más comprensible sin alterar los datos clínicos.

---

# 21. Responsable

## SCREEN-114 — Contexto de relación

Solo se muestran pacientes y datos clínicos permitidos por una relación activa y las reglas correspondientes.

## SCREEN-115 — Sin acceso por ID

Introducir manualmente un ID de paciente no debe ampliar el alcance.

## SCREEN-116 — Sin edición clínica

No se muestran controles de edición de la nota médica.

---

# 22. Administrador

## SCREEN-117 — No crear modo médico universal

Ser administrador no debe cambiar automáticamente la UX en un modo con acceso clínico total.

## SCREEN-118 — Soporte explícito

Si existe una herramienta de soporte, debe ser una interfaz separada y claramente identificada.

## SCREEN-119 — Auditoría

Las consultas de soporte no sustituyen la visualización clínica ordinaria.

## SCREEN-120 — Sin bypass

No existe botón `Ver todo` o `Editar como médico` genérico.

---

# 23. Estados vacíos

## SCREEN-121 — Sin historial

Mostrar un estado vacío informativo: aún no existen encuentros clínicos accesibles.

## SCREEN-122 — Sin expediente

Si todavía no existe `MedicalRecord`, la UI puede mostrar un estado que indique que el expediente se creará cuando corresponda, sin presentar un error técnico.

## SCREEN-123 — Sin acceso

No debe confundirse `sin datos` con `sin autorización` cuando la política de seguridad exige una respuesta indistinguible.

## SCREEN-124 — Sin citas elegibles

La Agenda muestra un estado vacío apropiado, sin fabricar acciones de inicio.

---

# 24. Estados de error

## SCREEN-125 — 401 / sesión

Mostrar sesión expirada o necesidad de autenticación.

## SCREEN-126 — 403 / autorización

Mostrar un mensaje funcional de acceso no permitido.

## SCREEN-127 — 404 / recurso no visible

No revelar si el recurso existe cuando la política lo prohíba.

## SCREEN-128 — Estado de dominio inválido

Mostrar que la operación ya no es válida por el estado actual.

## SCREEN-129 — Error de validación

Mostrar errores específicos por campo.

## SCREEN-130 — Conflicto de concurrencia

Mostrar el estado resultante de manera funcional y segura.

## SCREEN-131 — Error de red

No afirmar persistencia si el servidor no confirmó el guardado.

## SCREEN-132 — Recuperación

Permitir reintento explícito cuando la operación sea segura.

## SCREEN-133 — No mostrar stack trace

Nunca mostrar excepciones, SQL, nombres de tablas, locks ni internals.

---

# 25. Concurrencia visible

## SCREEN-134 — Doble clic

La UI puede deshabilitar temporalmente acciones mientras espera respuesta.

## SCREEN-135 — El backend sigue siendo autoridad

Una pantalla nunca depende exclusivamente de disabled buttons para evitar duplicados.

## SCREEN-136 — Estado cambiado externamente

Si el recurso ya fue completado o su estado cambió, la UI debe refrescar y representar el estado actual.

## SCREEN-137 — Múltiples pestañas

Si el usuario abre el mismo encuentro en dos pestañas, la UI no promete edición colaborativa en tiempo real.

## SCREEN-138 — Persistencia en servidor

Siempre prevalece el estado confirmado por API.

---

# 26. Salida de la pantalla de consulta

## SCREEN-139 — Salir sin completar

Debe ser posible regresar a Agenda o al historial sin cerrar el encuentro.

## SCREEN-140 — Cambios sin guardar

Puede mostrarse una advertencia antes de abandonar cuando existan cambios locales no persistidos.

## SCREEN-141 — No autocierre

Salir no modifica el estado del encuentro.

## SCREEN-142 — Reingreso

Al volver, el médico asignado recupera el encuentro `IN_PROGRESS` existente.

---

# 27. Responsividad

## SCREEN-143 — Escritorio

La vista de consulta prioriza ancho para texto clínico y una barra de acciones persistente.

## SCREEN-144 — Pantalla pequeña

Los textareas mantienen altura utilizable y las acciones primarias siguen accesibles.

## SCREEN-145 — No perder contenido

Cambios de layout, validación o guardado no deben provocar saltos que destruyan el contexto de captura.

---

# 28. Accesibilidad

## SCREEN-146 — Etiquetas

Cada control clínico tiene etiqueta asociada.

## SCREEN-147 — Foco

Los errores deben mover o anunciar el foco de forma razonable sin interrumpir innecesariamente la captura.

## SCREEN-148 — Teclado

Todas las acciones principales deben ser operables mediante teclado.

## SCREEN-149 — Errores legibles

Los errores no dependen exclusivamente del color.

## SCREEN-150 — Orden clínico

El orden de navegación sigue una secuencia coherente: identificación → campos clínicos → opcionales → guardar → completar.

---

# 29. Microcopy recomendado

## SCREEN-151 — Inicio

`Iniciar consulta`

## SCREEN-152 — Continuación

`Continuar consulta`

## SCREEN-153 — Guardado

`Guardar`

## SCREEN-154 — Confirmación de guardado

`Guardado`

## SCREEN-155 — Completion

`Completar consulta`

## SCREEN-156 — Estado abierto

`En progreso`

## SCREEN-157 — Estado cerrado

`Completada`

## SCREEN-158 — Error de autorización

`No tienes permiso para realizar esta acción.`

## SCREEN-159 — Datos no guardados

`Hay cambios sin guardar.`

## SCREEN-160 — Cierre irreversible en F3

`Al completar la consulta quedará cerrada y no podrá editarse en esta fase.`

El microcopy puede adaptarse al tono visual del producto sin cambiar el significado.

---

# 30. Seguridad visible y protección contra exposición accidental

## SCREEN-161 — URLs no son autorización

El acceso por ruta debe volver a validar permisos en backend.

## SCREEN-162 — No renderizar información prohibida y ocultarla después

Preferir que el backend no entregue información no autorizada.

## SCREEN-163 — Sin datos clínicos en analytics

Los eventos de UI no deben enviar contenido clínico.

## SCREEN-164 — Descargas

Una descarga futura debe pasar por autorización del backend; no se generan enlaces públicos permanentes.

## SCREEN-165 — Caché

La pantalla no debe asumir que ocultar datos en el DOM protege contenido ya recibido.

---

# 31. Especialidades futuras

## SCREEN-166 — Núcleo reusable

Las pantallas S-03/S-04 deben admitir extensiones sin alterar el flujo base.

## SCREEN-167 — Secciones especializadas

Ginecología, obstetricia, colposcopia, menopausia y otras áreas pueden incorporarse como secciones o módulos posteriores.

## SCREEN-168 — No obligatorias en F3 core

No introducir campos especializados como requisito para completar la consulta general.

## SCREEN-169 — Compatibilidad histórica

Una nueva sección especializada no debe romper la visualización de encuentros antiguos del núcleo general.

---

# 32. Qué no debe existir como pantalla F3

## SCREEN-170 — No check-in

No existe pantalla independiente de check-in/espera clínica.

## SCREEN-171 — No monitor de tiempo para cierre

No existe pantalla cuya función sea autocerrar por duración de cita.

## SCREEN-172 — No editor de consulta cerrada

No existe una pantalla `Editar consulta completada`.

## SCREEN-173 — No gestión de borrado clínico

No existe pantalla de eliminación física/lógica de encuentro o expediente como acción funcional de usuario.

## SCREEN-174 — No catálogo diagnóstico obligatorio

No existe pantalla de selección CIE-10 requerida para completion.

## SCREEN-175 — No diagnóstico asistido por IA

No existe una pantalla que genere diagnóstico autónomo.

## SCREEN-176 — No admin bypass

No existe una pantalla universal para que un administrador modifique cualquier encuentro.

---

# 33. Navegación propuesta

## SCREEN-177 — Flujo nominal

`Agenda → S-02 Inicio → S-03 En progreso → S-04 Completada → S-06 Historial`

## SCREEN-178 — Continuación

`Agenda → S-03 En progreso`

cuando la cita ya esté `IN_CONSULTATION`.

## SCREEN-179 — Lectura histórica

`Expediente → Historial → S-07 Detalle de encuentro`

## SCREEN-180 — Lectura longitudinal

`Paciente → Expediente → Datos longitudinales / Historial`

## SCREEN-181 — Salida de consulta

`S-03 → Agenda` no completa la consulta.

---

# 34. Compatibilidad con API

La pantalla debe mapearse a operaciones explícitas ya definidas:

| Pantalla | Operación principal |
|---|---|
| S-01 | lectura Agenda / consulta de estado |
| S-02 | `start_encounter` |
| S-03 | `get_encounter`, `save_encounter`, `complete_encounter` |
| S-04 | `get_encounter` |
| S-05 | lectura de `MedicalRecord` / historial |
| S-06 | lectura paginada de historial |
| S-07 | `get_encounter` |

No se deben crear endpoints de presentación cuyo propósito sea sustituir estas operaciones de dominio.

---

# 35. Política de formularios y navegación

## SCREEN-182 — No reset inesperado

Guardar o validar no debe borrar los valores del formulario.

## SCREEN-183 — Mantener contexto

Después de un guardado exitoso el usuario permanece en la consulta.

## SCREEN-184 — Scroll estable

La validación no debe transportar al usuario arbitrariamente al inicio si puede dirigirse al campo afectado.

## SCREEN-185 — Completion exitoso

La transición a solo lectura puede llevar al encabezado o resumen de cierre.

## SCREEN-186 — Error de API

Se conserva el contenido local mientras el usuario pueda corregir o reintentar.

---

# 36. Criterios de aceptación por pantalla

## S-01 Agenda

- [ ] Las citas muestran estados comprensibles.
- [ ] `SCHEDULED` elegible permite iniciar.
- [ ] `IN_CONSULTATION` permite continuar.
- [ ] `CANCELLED` y `NO_SHOW` no permiten iniciar.
- [ ] Paciente y cita se identifican inequívocamente.

## S-02 Inicio

- [ ] El contexto del paciente es visible.
- [ ] No existe selector de médico para apropiación.
- [ ] Inicio exitoso lleva a consulta abierta.
- [ ] Segundo inicio no crea duplicado.

## S-03 En progreso

- [ ] Existen los cinco campos mínimos.
- [ ] Guardar permite información parcial.
- [ ] Se muestra el último guardado exitoso.
- [ ] Completion valida requisitos.
- [ ] Se puede salir sin completar.
- [ ] Se puede reanudar.

## S-04 Completada

- [ ] Todos los campos están bloqueados.
- [ ] No existe editar.
- [ ] No existe reabrir.
- [ ] No existe eliminar.
- [ ] Se muestra contexto temporal/histórico.

## S-05 Expediente

- [ ] Distingue datos longitudinales, resumen e historial.
- [ ] No duplica identidad de Patient como fuente independiente.
- [ ] No inventa diagnóstico actual.
- [ ] Permite navegar a encuentros autorizados.

## S-06 Historial

- [ ] Orden estable y consistente.
- [ ] No confunde cita con encuentro.
- [ ] No incluye canceladas/no-show como consultas.
- [ ] Soporta paginación cuando aplique.

## S-07 Detalle histórico

- [ ] Solo lectura para encuentros completados.
- [ ] Respeta permisos del actor.
- [ ] No expone campos no autorizados.

---

# 37. Reglas de cierre propuestas

| ID | Decisión |
|---|---|
| SCREEN-C-001 | Fase 3 usa un conjunto pequeño de pantallas clínicas |
| SCREEN-C-002 | Agenda sigue siendo la puerta nominal para iniciar |
| SCREEN-C-003 | No existe pantalla de check-in |
| SCREEN-C-004 | `IN_PROGRESS` se representa como `En progreso` |
| SCREEN-C-005 | `COMPLETED` se representa como `Completada` |
| SCREEN-C-006 | S-03 permite guardado parcial |
| SCREEN-C-007 | Los cinco mínimos bloquean solo completion |
| SCREEN-C-008 | Diagnóstico es texto libre |
| SCREEN-C-009 | Completion incluye los cambios actuales |
| SCREEN-C-010 | S-04 es solo lectura |
| SCREEN-C-011 | No existe reapertura |
| SCREEN-C-012 | No existe borrado clínico |
| SCREEN-C-013 | El expediente separa longitudinal, resumen e historial |
| SCREEN-C-014 | La historia se muestra por orden cronológico estable |
| SCREEN-C-015 | Otro médico autorizado lee sin editar |
| SCREEN-C-016 | Paciente y responsable no editan nota clínica |
| SCREEN-C-017 | Administrador no obtiene bypass clínico genérico |
| SCREEN-C-018 | UI no sustituye autorización backend |
| SCREEN-C-019 | No hay analytics con contenido clínico |
| SCREEN-C-020 | Especialidades posteriores se agregan por extensión |

---

# 38. Dependencias de implementación

La implementación concreta deberá respetar:

1. contratos API;
2. servicios de dominio;
3. permisos de objeto;
4. seguridad y privacidad;
5. constraints e integridad del modelo;
6. workflow de Agenda y ClinicalEncounter.

La capa de presentación puede usar plantillas server-rendered, componentes frontend o una combinación, siempre que conserve estas propiedades.

---

# 39. Criterio de simplicidad arquitectónica

La primera versión no debe crear una aplicación clínica paralela con múltiples estados de interfaz independientes del dominio.

La propuesta más simple es:

`Agenda existente → contexto de cita → formulario ClinicalEncounter → lectura histórica desde MedicalRecord`.

Los futuros módulos clínicos deben reutilizar este shell de navegación y agregar únicamente las secciones que tengan un contrato de dominio propio.

---

# 40. Cierre documental

`clinical-screens.md` se considera listo para implementación cuando:

- cada pantalla tiene un propósito único;
- sus datos corresponden a fuentes canónicas;
- las acciones corresponden a contratos de servicio/API;
- los permisos se aplican en servidor;
- no existen estados UI que contradigan el dominio;
- la pantalla de consulta abierta soporta guardado parcial;
- completion cambia la consulta a solo lectura;
- el expediente e historial conservan carácter longitudinal e histórico;
- no se introducen capacidades fuera del alcance de Fase 3.

### Próximo documento de la secuencia

`clinical-audit-and-history.md`

# TeCuidoApp — UI Guidelines

**Estado:** Propuesta inicial  
**Versión:** 1.0  
**Aplicación:** TeCuidoApp  
**Referencia funcional:** `requirements.md`  
**Referencia visual:** `docs/design/design-system.md`  
**Referencia arquitectónica:** `docs/architecture.md`

---

## 1. Propósito

Este documento traduce el Design System de TeCuidoApp a reglas prácticas para el diseño y construcción de pantallas.

Debe utilizarse junto con:

```text
requirements.md
docs/architecture.md
docs/design/design-system.md
docs/adr/
```

La finalidad es mantener una experiencia coherente para:

- Administrador
- Médico
- Paciente
- Responsable

Este documento define principalmente estructura de pantallas, navegación, formularios, dashboards, tablas, estados, responsive design y accesibilidad.

No define reglas de negocio ni permisos del backend.

---

## 2. Principios de UX

### 2.1 Claridad antes que decoración

La información debe ser fácil de localizar y comprender.

No utilizar elementos visuales únicamente por motivos estéticos si dificultan lectura, navegación o toma de decisiones.

### 2.2 Diseñar para el contexto de trabajo

Prioridades por rol:

**Médico**
- agenda;
- pacientes;
- información clínica;
- alertas;
- acciones frecuentes.

**Paciente**
- próxima cita;
- solicitudes;
- documentos;
- información personal.

**Responsable**
- paciente seleccionado;
- próximas citas;
- solicitudes;
- documentos autorizados.

**Administrador**
- usuarios;
- médicos;
- consultorios;
- configuración;
- gestión administrativa.

### 2.3 Profesionalismo médico

La interfaz debe transmitir confianza, precisión, tranquilidad y orden.

Evitar una estética infantil, gamificada, excesivamente saturada o excesivamente tecnológica.

### 2.4 Reducción de carga cognitiva

Agrupar información relacionada, usar secciones, reducir formularios innecesariamente largos y mantener acciones importantes visibles.

---

## 3. Estructura general de la aplicación

Pantallas autenticadas:

```text
┌─────────────────────────────────────────────────────┐
│ Header                                              │
├───────────────┬─────────────────────────────────────┤
│ Sidebar       │ Main Content                        │
│               │                                     │
│ Navigation    │ Page Header                         │
│               │                                     │
│               │ Content                             │
└───────────────┴─────────────────────────────────────┘
```

En móvil:

```text
┌──────────────────────────────┐
│ Header / Menu                │
├──────────────────────────────┤
│ Main Content                 │
└──────────────────────────────┘
```

---

## 4. Header

Debe proporcionar:

- identidad de TeCuidoApp;
- contexto del usuario;
- acceso a cuenta;
- notificaciones cuando existan;
- menú de usuario.

No debe utilizarse para navegación extensa.

---

## 5. Sidebar y navegación

La navegación debe organizarse por módulos y adaptarse al rol.

Ejemplo médico:

```text
Inicio
Pacientes
Agenda
Solicitudes
Documentos
Configuración
```

Ejemplo paciente:

```text
Inicio
Mis citas
Mis documentos
Mi perfil
```

Ejemplo responsable:

```text
Inicio
Pacientes a cargo
Citas
Documentos
Mi perfil
```

Ejemplo administrador:

```text
Inicio
Usuarios
Médicos
Consultorios
Configuración
Auditoría
```

La lista concreta debe ajustarse al alcance de cada fase.

---

## 6. Page Header

Patrón recomendado:

```text
Título
Descripción breve
                         [Acción principal]
```

Ejemplo:

```text
Pacientes
Consulta y administra los pacientes autorizados.

                                      [Nuevo paciente]
```

El título debe describir claramente la pantalla.

---

## 7. Breadcrumbs

Utilizar breadcrumbs cuando exista navegación jerárquica significativa.

Ejemplo:

```text
Pacientes / María López / Información
```

No utilizarlos en pantallas principales cuando no aporten contexto.

---

## 8. Acción principal

Cada pantalla debe tener idealmente una acción primaria.

Ejemplos:

```text
Pacientes       → Nuevo paciente
Consultorios    → Nuevo consultorio
Invitaciones    → Nueva invitación
Perfil           → Guardar cambios
```

No deben existir múltiples botones visualmente primarios sin una razón clara.

---

## 9. Formularios

Agrupar campos por contexto.

Ejemplo:

```text
Datos personales
────────────────────────
Nombre
Apellido paterno
Apellido materno
Fecha de nacimiento

Contacto
────────────────────────
Correo
Teléfono
Teléfono alternativo

Domicilio
────────────────────────
...
```

Cada campo debe tener label visible.

No utilizar placeholders como sustituto de labels.

---

## 10. Formularios largos

Cuando un formulario sea extenso:

- dividir por secciones;
- usar pasos cuando exista una secuencia natural;
- conservar información introducida;
- mostrar claramente el avance con el componente `Stepper`;
- evitar repetir datos.

No utilizar un wizard solamente como recurso visual.

---

## 11. Registro mediante invitación

El registro debe utilizar un flujo guiado, representado con el componente `Stepper`:

```text
Invitación validada
        ↓
Datos de cuenta
        ↓
Datos personales
        ↓
Verificación de correo
        ↓
Registro completado
```

No mostrar detalles técnicos del token.

Este patrón es para el prospecto adulto registrándose a sí mismo (`requirements.md` §7.1). El
registro de un paciente menor por su responsable (§7.2) es un flujo distinto — lo inicia el
responsable ya autenticado, no un prospecto anónimo — y usa un flujo guiado propio (mismo
componente `Stepper`, pasos distintos). Ver `docs/design/screens.md` §6.8 para su detalle.

---

## 12. Login

La pantalla de login debe ser sencilla:

```text
Logo

Bienvenido a TeCuidoApp

Correo
[____________________]

Contraseña
[____________________]

[ Iniciar sesión ]

¿Olvidaste tu contraseña?
```

La acción de autenticación debe tener mayor jerarquía visual.

---

## 13. Recuperación y verificación de correo

Los flujos de recuperación de contraseña y verificación deben ser claros y consistentes con login.

Ejemplo:

```text
Revisa tu correo

Te enviamos un enlace para continuar.
```

No revelar innecesariamente si una cuenta existe.

---

## 14. Dashboard médico

El dashboard debe estar orientado a operación diaria.

Prioridad:

```text
1. Agenda del día (estados reales de Appointment — §33)
2. Alertas operativas
3. Próximas citas
```

"Pacientes en espera" queda pendiente de diseño — Fase 2 no dejó check-in ni un estado
`WAITING` de los que depender (§33); no debe construirse hasta que exista esa decisión.

No convertirlo en una colección de métricas sin utilidad operacional.

---

## 15. Dashboard paciente

Prioridad:

```text
Próxima cita
      ↓
Mis citas
      ↓
Mis documentos
```

La información más importante debe aparecer sin necesidad de navegar a otra pantalla.

---

## 16. Dashboard responsable

Cuando tenga múltiples pacientes, debe existir un selector claro:

```text
Paciente
[ María López ▼ ]
```

Nunca mezclar datos de varios pacientes sin indicar claramente a quién corresponden.

---

## 17. Lista de pacientes

La lista debe permitir localizar rápidamente pacientes por:

- nombre;
- apellidos;
- teléfono;
- correo.

Información prioritaria:

- nombre;
- contacto relevante;
- estado;
- acciones.

Ejemplo:

```text
Paciente       Contacto          Estado       Acciones
--------------------------------------------------------
María López    55 xxx xxxx       Activo       Ver
Ana Pérez      55 xxx xxxx       Activo       Ver
```

---

## 18. Búsqueda y filtros

La búsqueda debe ser visible y comprensible.

Ejemplo:

```text
[ Buscar por nombre, teléfono o correo... ]
```

Los filtros deben estar cerca del contenido que afectan.

Evitar esconder filtros esenciales.

---

## 19. Página de detalle del paciente

Mantener visible el contexto del paciente.

Ejemplo:

```text
Paciente
María López

[Resumen] [Citas] [Consultas] [Documentos]

Información general
──────────────────────────────

Contacto
──────────────────────────────

Relaciones
──────────────────────────────
```

En fases posteriores podrán incorporarse:

```text
Alertas
Historia clínica
Consultas
Tratamientos
Recetas
Estudios
Documentos
```

---

## 20. Contexto de paciente

Dentro de cualquier pantalla del expediente debe ser evidente:

- nombre del paciente;
- contexto actual;
- sección activa.

Esto es especialmente importante para médicos y responsables.

---

## 21. Consultorios

Patrón de lista:

```text
Nombre           Teléfono         Estado       Acciones
---------------------------------------------------------
Consultorio A    ...              Activo       Editar
Consultorio B    ...              Inactivo     Activar
```

Los estados deben ser visibles mediante badges.

---

## 22. Médicos

El listado debe priorizar:

- nombre;
- información profesional relevante;
- consultorios asociados;
- estado.

Las acciones deben mantenerse agrupadas.

---

## 23. Invitaciones

Mostrar el estado de cada invitación de forma clara.

Ejemplo:

```text
Correo              Médico         Estado       Fecha
------------------------------------------------------
usuario@email.com   Dr. López      Pendiente    01/09/26
otro@email.com      Dra. Pérez     Utilizada    30/08/26
```

---

## 24. Badges

Utilizar badges para estados.

Ejemplos:

```text
[Activo]
[Inactivo]
[Pendiente]
[Verificado]
[Expirado]
[Cancelado]
```

El texto debe acompañar siempre al color.

---

## 25. Confirmaciones

Las acciones sensibles deben explicar claramente qué ocurrirá.

Ejemplo:

```text
Desactivar consultorio

El consultorio dejará de estar disponible
para nuevas operaciones.

[Cancelar] [Desactivar]
```

Evitar botones ambiguos como `OK` en acciones importantes.

---

## 26. Acciones destructivas

Las acciones destructivas deben:

- utilizar estilo Danger;
- describir el efecto;
- pedir confirmación cuando corresponda;
- diferenciar Cancelar de Desactivar/Eliminar.

En TeCuidoApp debe preferirse la baja lógica cuando el dominio lo requiera.

---

## 27. Mensajes de éxito

Después de una operación exitosa:

```text
✓ Paciente actualizado correctamente.
```

Los mensajes deben ser breves y claros.

---

## 28. Mensajes de error

Los errores de negocio deben expresarse en lenguaje comprensible.

Incorrecto:

```text
IntegrityError: duplicate key...
```

Correcto:

```text
Este correo electrónico ya está registrado.
```

Los detalles técnicos deben permanecer en logs.

---

## 29. Estado vacío

Toda lista relevante debe contemplar un estado vacío.

Ejemplo:

```text
No hay invitaciones todavía.

Envía una invitación para comenzar el registro
de un nuevo paciente.

[Enviar invitación]
```

Debe explicar qué ocurre y, cuando corresponda, ofrecer una acción.

---

## 30. Loading State

Durante operaciones de carga o guardado:

```text
Cargando...
Guardando...
Enviando...
Procesando...
```

La pantalla no debe quedar en un estado ambiguo.

---

## 31. Unauthorized State

Cuando el usuario no tenga permisos:

```text
No tienes permisos para consultar esta información.
```

No revelar detalles innecesarios sobre la existencia de recursos sensibles.

---

## 32. 404 / recurso no disponible

Mostrar lenguaje de negocio cuando sea posible.

Evitar exponer:

- stack traces;
- IDs internos innecesarios;
- detalles técnicos.

---

## 33. Estados de citas (Fase 2 — Agenda)

Especificación aprobada en `docs/phases/phase-2-agenda.md` §8 (2026-09-09). La UI debe
distinguir únicamente estos cinco estados reales de `Appointment`:

```text
Programada       (SCHEDULED)
En consulta      (IN_CONSULTATION)
Atendida         (COMPLETED)
Cancelada        (CANCELLED)
No se presentó   (NO_SHOW)
```

No existen como estados de `Appointment` — no deben aparecer en la UI como si lo fueran:
"Pendiente de confirmación", "Confirmada", "En espera", "Reprogramada" ni "Liberada". La
reprogramación es un evento con su propio historial (fecha/hora anterior, nueva, quién,
cuándo, motivo), no un estado de la cita; el hold liberado/expirado/consumido es historial
técnico, no algo que se muestre como estado de la cita.

Nunca representar `NO_SHOW` como simple falta de confirmación — solo lo marca el médico
asignado, desde `SCHEDULED`, desde el minuto 1 posterior al horario programado.

---

## 34. Sala de espera — pendiente de diseño

Fase 2 no introdujo check-in ni un estado `WAITING`: nadie registra que el paciente "llegó",
así que no existe una lista de pacientes en espera que la UI pueda construir todavía. Lo que
sí existe es **"Iniciar consulta"** (§14, §33): el médico verifica la presencia del paciente
de forma presencial y ejecuta `SCHEDULED → IN_CONSULTATION` directamente, sin un paso
intermedio de "llegó"/"en espera".

Una sala de espera real requiere su propia decisión funcional explícita (candidata a Fase 5,
`requirements.md` §41) — no debe construirse infiriendo un mecanismo de check-in que no fue
decidido.

---

## 35. Reglas de cierre de Agenda (2026-09-09)

- Las horas de Agenda se muestran siempre en la zona horaria del `Clinic`, nunca en la del
  dispositivo del usuario.
- Un médico no puede tener disponibilidad simultánea en dos consultorios distintos, aunque el
  horario visualmente no se solape en la agenda de cada consultorio por separado.
- Un médico puede reservar la primera cita de un paciente sin que exista `DoctorPatientRelationship`
  previa; la UI no debe exigir ni sugerir que primero debe "agregarse" al paciente. Esa
  reserva no crea ni modifica ninguna relación médico-paciente.

---

## 35. Documentos futuros

Los documentos deberán mostrar como mínimo:

- tipo;
- fecha;
- descripción;
- origen;
- acciones permitidas.

Ejemplo:

```text
Receta
15/09/2026
Dr. López
[Ver] [Descargar]
```

No mostrar rutas privadas de almacenamiento.

---

## 36. Tabs

Utilizar tabs cuando varias categorías pertenezcan al mismo contexto.

Ejemplo:

```text
[Resumen] [Citas] [Consultas] [Documentos]
```

La pestaña activa debe identificarse claramente.

---

## 37. Cards

Usar cards para agrupar información relacionada.

Buenas aplicaciones:

- resumen de cita;
- resumen de paciente;
- estado;
- acciones.

Evitar convertir cada dato en una card.

---

## 38. Tablas

Las tablas deben priorizar:

- lectura rápida;
- encabezados claros;
- alineación;
- filtros cuando hagan falta;
- acciones de fila claramente diferenciadas.

En móvil se debe considerar scroll horizontal o una representación alternativa.

---

## 39. Información sensible

La información médica debe:

- tener jerarquía;
- mostrarse de forma discreta;
- separar datos generales de información clínica;
- destacar solamente aquello que requiere atención.

La interfaz no debe exponer información sensible innecesariamente.

---

## 40. Accesibilidad

Toda pantalla debe considerar:

- navegación con teclado;
- focus visible;
- labels asociados;
- contraste suficiente;
- mensajes de error claros;
- no depender únicamente del color;
- áreas de interacción adecuadas.

---

## 41. Focus

No eliminar el focus visible.

Si se personaliza el focus, debe conservar un indicador claramente perceptible.

---

## 42. Responsive Design

### Desktop

Utilizar:

- sidebar;
- tablas completas;
- múltiples columnas;
- paneles.

### Tablet

Reducir columnas y apilar contenidos cuando sea necesario.

### Mobile

Priorizar:

- contenido;
- acciones principales;
- legibilidad;
- controles táctiles.

No intentar reproducir exactamente el layout desktop en móvil.

---

## 43. Touch Targets

Los elementos táctiles deben tener suficiente área de interacción.

Evitar iconos diminutos o acciones demasiado juntas.

---

## 44. Estados obligatorios

Toda pantalla relevante debe considerar, cuando aplique:

```text
Default
Loading
Empty
Error
Unauthorized
Success
```

No implementar solamente el estado ideal.

---

## 45. UX para errores

Para cada operación importante considerar:

```text
¿Qué pasa si funciona?
¿Qué pasa si falla?
¿Qué pasa si se repite?
¿Qué pasa si no tiene permisos?
¿Qué pasa si el recurso no existe?
¿Qué pasa si la sesión expiró?
```

La interfaz debe tener una respuesta comprensible para cada escenario.

---

## 46. Seguridad visual

La UI ayuda a presentar capacidades, pero nunca constituye la frontera de seguridad.

No asumir:

```text
"El usuario no ve el botón"
```

equivale a:

```text
"El usuario no puede ejecutar la acción"
```

La autorización real debe permanecer en backend.

---

## 47. Componentes reutilizables

Antes de crear un componente, comprobar si existe uno equivalente.

Componentes base esperados:

```text
Button
Input
Select
Textarea
Checkbox
Radio
DateInput
Alert
Badge
Card
Modal
Table
Pagination
Tabs
Stepper
Breadcrumb
Dropdown
Tooltip
EmptyState
LoadingState
ErrorState
PageHeader
Sidebar
Navbar
```

`Stepper` indica avance dentro de un flujo guiado de varios pasos (progreso secuencial);
`Breadcrumb` indica jerarquía de navegación. No son intercambiables. Ver el detalle en
`docs/design/design-system.md` §40.

La lista puede crecer según necesidades reales.

---

## 48. Componentes de dominio

Diferenciar componentes genéricos de componentes específicos del dominio.

### Genéricos

```text
Button
Card
Table
Modal
Badge
Stepper
```

### Dominio

```text
PatientSummary
PatientContextHeader
AppointmentStatus
ClinicalAlert
InvitationStatus
```

Los componentes de dominio deben reutilizar los componentes base.

---

## 49. Design Tokens

Los estilos deben utilizar los tokens definidos en:

```text
docs/design/design-system.md
```

No repetir arbitrariamente:

- colores;
- spacing;
- tipografía;
- radios;
- sombras.

---

## 50. Implementación con Django

Los templates deben permanecer enfocados en presentación.

Evitar:

- lógica de negocio compleja;
- reglas de autorización;
- duplicación excesiva.

El backend continúa siendo responsable de seguridad y permisos.

---

## 51. Regla para Claude Code

Antes de implementar una pantalla:

1. leer `requirements.md`;
2. leer `docs/architecture.md` cuando corresponda;
3. leer `docs/design/design-system.md`;
4. leer este documento;
5. revisar componentes existentes;
6. reutilizar patrones.

Antes de crear un nuevo componente:

1. buscar equivalentes;
2. comprobar si puede extenderse;
3. evitar duplicados;
4. incorporarlo al Design System si se vuelve reutilizable.

No introducir una librería UI nueva sin una decisión técnica explícita.

---

## 52. Proceso de diseño de una pantalla

Antes de programar:

```text
Objetivo
   ↓
Usuario / Rol
   ↓
Acción principal
   ↓
Información crítica
   ↓
Componentes
   ↓
Estados
   ↓
Responsive
   ↓
Accesibilidad
   ↓
Implementación
```

---

## 53. Consistencia

Una misma acción debe verse y comportarse igual en toda la aplicación.

Ejemplos:

```text
Guardar
Cancelar
Volver
Editar
Ver
Desactivar
Confirmar
```

Deben utilizar patrones visuales y de interacción consistentes.

---

## 54. Densidad visual

### Médico

Mayor densidad informativa.

### Paciente

Menor densidad y mayor orientación.

### Responsable

Densidad intermedia.

### Administrador

Densidad orientada a gestión.

La identidad visual debe mantenerse común.

---

## 55. Diferenciación por rol

Los distintos roles pueden tener diferentes prioridades y navegación, pero no deben parecer aplicaciones completamente diferentes.

Debe existir una identidad visual compartida.

---

## 56. Fuera de alcance

Este documento no define:

- modelos Django;
- PostgreSQL;
- APIs;
- autenticación técnica;
- autorización;
- reglas de negocio;
- decisiones clínicas.

Esos aspectos pertenecen a:

```text
requirements.md
docs/architecture.md
docs/adr/
```

---

## 57. Definition of Done de UI

Una pantalla se considera terminada cuando:

- [ ] cumple el requerimiento funcional;
- [ ] respeta el Design System;
- [ ] tiene jerarquía visual clara;
- [ ] tiene acción principal identificable;
- [ ] contempla loading cuando aplica;
- [ ] contempla empty cuando aplica;
- [ ] contempla error;
- [ ] contempla unauthorized cuando aplica;
- [ ] proporciona feedback de operaciones;
- [ ] es responsive;
- [ ] es accesible;
- [ ] reutiliza componentes existentes;
- [ ] no duplica patrones innecesariamente.

---

## 58. Prioridad de decisiones

Cuando exista conflicto entre estética y funcionalidad:

```text
Seguridad
   ↓
Accesibilidad
   ↓
Claridad
   ↓
Usabilidad
   ↓
Consistencia
   ↓
Estética
```

---

## 59. Principio final

La interfaz debe ayudar al usuario a:

1. entender dónde está;
2. identificar qué información importa;
3. saber qué puede hacer;
4. ejecutar la acción correcta;
5. recibir feedback;
6. comprender cualquier error;
7. trabajar con confianza y seguridad.

El objetivo no es añadir más elementos visuales, sino facilitar el trabajo de forma clara, profesional y segura.

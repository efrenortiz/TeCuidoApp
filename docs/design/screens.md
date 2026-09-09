# TeCuidoApp — Screens

**Estado:** Propuesta inicial
**Versión:** 1.0
**Aplicación:** TeCuidoApp
**Referencia funcional:** `requirements.md`
**Referencia de fases:** `docs/phases/phase-1-foundations.md`
**Referencia visual:** `docs/design/design-system.md`
**Referencia de UI:** `docs/design/ui-guidelines.md`
**Referencia arquitectónica:** `docs/architecture.md`

---

# 1. Propósito

Este documento cataloga las pantallas de TeCuidoApp: qué existe, qué falta por construir dentro
del alcance ya decidido, y qué queda como referencia de diseño para fases futuras.

Cada pantalla debe:

- respetar estrictamente `docs/design/design-system.md`;
- seguir los patrones de `docs/design/ui-guidelines.md`;
- reutilizar componentes existentes antes de proponer uno nuevo;
- mantener consistencia visual entre Administrador, Médico, Paciente y Responsable.

Este documento no define modelos, permisos, ni lógica de negocio. Eso pertenece a
`requirements.md`, `docs/architecture.md` y `docs/adr/`.

---

# 2. Cómo leer este documento

Cada pantalla se describe con:

```text
Pantalla        — nombre de negocio
Ruta            — URL name en el código, si ya existe
Fase            — fase funcional a la que pertenece (docs/phases/, requirements.md §41)
Rol(es)         — quién la usa
Estado          — ver §3
Objetivo        — qué resuelve para el usuario
Acción principal— la única acción primaria de la pantalla (Design System §15)
Información clave — qué debe verse sin necesidad de navegar
Componentes     — de la lista base o de dominio (Design System §40, UI Guidelines §47-48)
Patrones        — secciones concretas de ui-guidelines.md que aplican
Estados         — Default/Loading/Empty/Error/Unauthorized/Success que aplican (UI Guidelines §44)
Notas           — aclaraciones puntuales
```

---

# 3. Estados de implementación

```text
Implementada (visual pendiente)  → la lógica y la ruta ya existen (Fase 1), pero el template
                                    actual es HTML mínimo sin tokens/componentes del Design
                                    System. Falta la capa visual, no la funcionalidad.
No implementada — pendiente      → pertenece al alcance funcional ya decidido (Fase 1) pero
                                    todavía no tiene vista/ruta construida.
Diseño de referencia (fase futura) → pantalla de una fase posterior (2-6). Se documenta aquí
                                    únicamente para mantener coherencia visual desde ahora.
                                    No debe implementarse todavía (CLAUDE.md §5, §14).
```

Toda la Fase 1 actual (`accounts`, `doctors`, `clinics`, `patients`) fue construida con
templates funcionales mínimos, sin aplicar el Design System — se priorizó backend, seguridad y
tests. Este documento es el punto de partida para cerrar esa brecha visual.

---

# 4. Mapa de pantallas

## 4.1 Fase 1 — Fundaciones

| Área | Pantalla | Estado |
|---|---|---|
| Auth (compartida) | Login | Implementada (visual pendiente) |
| Auth (compartida) | Recuperar contraseña — solicitud | Implementada (visual pendiente) |
| Auth (compartida) | Recuperar contraseña — revisa tu correo | Implementada (visual pendiente) |
| Auth (compartida) | Restablecer contraseña | Implementada (visual pendiente) |
| Auth (compartida) | Contraseña restablecida | Implementada (visual pendiente) |
| Auth (compartida) | Cambiar contraseña | Implementada (visual pendiente) |
| Auth (compartida) | Contraseña actualizada | Implementada (visual pendiente) |
| Auth (compartida) | Verificación de correo — resultado | Implementada (visual pendiente) |
| Auth (compartida) | Registro por invitación — inválida/expirada/usada | Implementada (visual pendiente) |
| Auth (compartida) | Registro por invitación — formulario | Implementada (visual pendiente) |
| Auth (compartida) | Registro completado | Implementada (visual pendiente) |
| General | Inicio (landing genérico post-login) | Implementada (visual pendiente) |
| Médico | Nueva invitación | Implementada (visual pendiente) |
| Médico | Listado de invitaciones | Implementada (visual pendiente) |
| Médico | Listado de mis pacientes | Implementada (visual pendiente) |
| Médico / Responsable | Detalle de paciente | Implementada, incluida la acción "Marcar como adulto" |
| Paciente | Mi perfil | Implementada (visual pendiente) |
| Responsable | Mis pacientes a cargo | Implementada (visual pendiente) |
| Responsable | Registrar paciente menor (3 pasos) | Implementada (visual pendiente) |
| Administrador | (ver §8 — nota específica) | Django Admin, fuera del Design System |

## 4.2 Fases futuras (referencia de diseño únicamente)

| Fase | Área | Pantallas de referencia |
|---|---|---|
| 2 — Agenda | Médico | Agenda, Disponibilidad (por fecha), Iniciar consulta |
| 2 — Agenda | Paciente/Responsable | Reservar cita (directa), Mis citas |
| 3 — Gestión clínica | Médico | Historia clínica, Consulta, Alertas clínicas |
| 4 — Documentos | Médico/Paciente/Responsable | Recetas, Solicitudes de estudio, Documentos |
| 5 — CareRequest y operación | Médico | Dashboard médico, Solicitudes de atención |
| 5 — CareRequest y operación | Paciente/Responsable | Dashboard paciente/responsable, Solicitud de atención |
| 6 — Notificaciones y auditoría | Administrador | Auditoría |

Ver §9 para el detalle de cada una — son bocetos conceptuales, no especificaciones para construir ahora.

---

# 5. Autenticación y registro (Fase 1 — compartidas por rol)

## 5.1 Login

```text
Pantalla   — Login
Ruta       — accounts:login
Fase       — 1
Rol(es)    — todos (no autenticado)
Estado     — Implementada (visual pendiente)
Objetivo   — autenticar al usuario
Acción principal — Iniciar sesión
Información clave — correo, contraseña, enlace de recuperación
Componentes — Input, Button (primary), Alert (error de credenciales)
Patrones   — UI Guidelines §12 (Login), §37 diseño de autenticación (Design System)
Estados    — Default, Error (credenciales inválidas), Loading (enviando)
Notas      — no revelar si el correo existe o no (UI Guidelines §13); layout centrado, sin sidebar.
```

## 5.2 Recuperar contraseña — solicitud

```text
Pantalla   — Recuperar contraseña
Ruta       — accounts:password_reset
Fase       — 1
Rol(es)    — todos (no autenticado)
Estado     — Implementada (visual pendiente)
Objetivo   — iniciar el flujo de recuperación
Acción principal — Enviar
Información clave — campo de correo
Componentes — Input, Button (primary)
Patrones   — UI Guidelines §13
Estados    — Default, Loading, Error de validación de formato
```

## 5.3 Recuperar contraseña — revisa tu correo

```text
Pantalla   — accounts:password_reset_done
Fase       — 1 | Rol(es) — todos | Estado — Implementada (visual pendiente)
Objetivo   — confirmar que, si el correo existe, se envió un enlace
Acción principal — (ninguna; pantalla informativa)
Componentes — Alert (info)
Patrones   — UI Guidelines §13 (no revelar existencia de cuenta)
Estados    — Success/Info único
```

## 5.4 Restablecer contraseña

```text
Pantalla   — accounts:password_reset_confirm
Fase       — 1 | Rol(es) — todos | Estado — Implementada (visual pendiente)
Objetivo   — capturar la nueva contraseña
Acción principal — Guardar
Componentes — Input (password) x2, Button (primary), Alert (enlace inválido/usado)
Patrones   — UI Guidelines §13, Design System §37
Estados    — Default, Error (enlace inválido — `validlink=False`), Error de validación, Loading
```

## 5.5 Contraseña restablecida

```text
Pantalla   — accounts:password_reset_complete
Fase       — 1 | Rol(es) — todos | Estado — Implementada (visual pendiente)
Objetivo   — confirmar el cambio y dirigir a login
Acción principal — Iniciar sesión
Componentes — Alert (success), Button (link/secondary)
```

## 5.6 Cambiar contraseña (autenticado)

```text
Pantalla   — accounts:password_change / accounts:password_change_done
Fase       — 1 | Rol(es) — todos (autenticado) | Estado — Implementada (visual pendiente)
Objetivo   — cambiar contraseña desde una sesión activa
Acción principal — Guardar
Componentes — Input (password) x3, Button (primary), Alert (success al terminar)
Patrones   — UI Guidelines §27 (mensajes de éxito)
Estados    — Default, Error de validación, Loading, Success
```

## 5.7 Verificación de correo — resultado

```text
Pantalla   — accounts:verify_email
Fase       — 1 | Rol(es) — todos | Estado — Implementada (visual pendiente)
Objetivo   — informar si el correo quedó verificado
Acción principal — (ninguna; informativa) — opcionalmente enlace a Inicio
Componentes — Alert (success/warning/error según `ok`/`reason`)
Patrones   — Design System §48 (errores de negocio en lenguaje claro)
Estados    — Success, Error (`expired` → Warning, `invalid`/`already_verified` → Info/Warning)
Notas      — los tres casos de fallo (expirado, inválido, ya verificado) deben distinguirse
             en el texto, no solo en el color (Design System §5).
```

## 5.8 Registro por invitación — inválida / expirada / usada / cancelada

```text
Pantalla   — accounts:invitation_accept (GET, invitación no PENDING)
Fase       — 1 | Rol(es) — prospecto (no autenticado) | Estado — Implementada (visual pendiente)
Objetivo   — explicar por qué no puede continuar el registro
Acción principal — (ninguna) — sugerir contactar al médico
Componentes — Alert (warning/error), EmptyState
Patrones   — Design System §48, UI Guidelines §32 (recurso no disponible)
Estados    — Error (404 invitación no encontrada), Error (410 no usable: expirada/usada/cancelada)
Notas      — no exponer el estado interno en jerga técnica; usar lenguaje de negocio
             ("Este enlace ya no está disponible", no "HTTP 410").
```

## 5.9 Registro por invitación — formulario

```text
Pantalla   — accounts:invitation_accept (GET/POST, invitación válida)
Fase       — 1 | Rol(es) — prospecto (no autenticado) | Estado — Implementada (visual pendiente)
Objetivo   — capturar cuenta + datos personales + datos de paciente en un solo flujo guiado
Acción principal — Registrarme
Información clave — en qué paso está, qué datos son obligatorios
Componentes — Input, Select (sexo), DateInput (fecha de nacimiento), Button (primary),
              Alert (error de negocio, p. ej. correo ya registrado), **Stepper (nuevo, ver §7)**
Patrones   — UI Guidelines §11, §10 (formularios largos), Design System §38
Estados    — Default, Error de validación por campo, Error de negocio (correo ya registrado),
             Loading
Notas      — el formulario actual es un único paso técnico (una sola vista), pero
             conceptualmente agrupa: Datos de cuenta → Datos personales → Domicilio →
             Datos de paciente. Debe presentarse visualmente como flujo guiado
             (UI Guidelines §11), agrupando por secciones con encabezado (UI Guidelines §9)
             aunque el submit sea único.
```

## 5.10 Registro completado

```text
Pantalla   — accounts:invitation_accept (respuesta de éxito)
Fase       — 1 | Rol(es) — prospecto → ahora paciente | Estado — Implementada (visual pendiente)
Objetivo   — confirmar el registro y explicar el siguiente paso (verificar correo)
Acción principal — (ninguna; informativa)
Componentes — Alert (success)
Patrones   — UI Guidelines §11 (paso final del flujo), §27 (mensajes de éxito)
```

---

# 6. Pantallas por rol (Fase 1)

## 6.1 General — Inicio

```text
Pantalla   — Inicio
Ruta       — home
Fase       — 1 | Rol(es) — todos (autenticado) | Estado — Implementada (visual pendiente)
Objetivo   — landing mínima tras iniciar sesión
Acción principal — según rol (ver notas)
Información clave — usuario autenticado, rol(es) activos
Componentes — PageHeader, Badge (rol)
Patrones   — Design System §46 (diferenciación por rol, mismo lenguaje visual)
Estados    — Default
Notas      — esta pantalla es un placeholder deliberado. Los dashboards reales por rol
             (Design System §29-30, UI Guidelines §14-16) son Fase 5 — no se deben construir
             todavía. Lo único que corresponde ahora es alinear esta pantalla al Design System
             (tokens, tipografía, layout autenticado de UI Guidelines §3) sin inventarle
             widgets de agenda/citas que no existen aún.
```

## 6.2 Médico — Nueva invitación

```text
Pantalla   — Nueva invitación
Ruta       — accounts:invitation_create
Fase       — 1 | Rol(es) — Médico | Estado — Implementada (visual pendiente)
Objetivo   — invitar a un prospecto a registrarse como paciente
Acción principal — Enviar invitación
Información clave — correo del prospecto
Componentes — PageHeader, Input, Button (primary), Alert (success tras enviar)
Patrones   — UI Guidelines §6 (Page Header), §8 (acción principal), §27
Estados    — Default, Error de validación, Success (confirmación de envío), Unauthorized
             (no-médico → 403, ver Design System §39)
```

## 6.3 Médico — Listado de invitaciones

```text
Pantalla   — Listado de invitaciones
Ruta       — accounts:invitation_list
Fase       — 1 | Rol(es) — Médico | Estado — Implementada
Objetivo   — que el médico vea el estado de las invitaciones que ha enviado
Acción principal — Nueva invitación
Información clave — correo, estado, fecha de creación/expiración
Componentes — PageHeader, Table, Badge (**InvitationStatus**, componente de dominio ya
              previsto en UI Guidelines §48), EmptyState
Patrones   — UI Guidelines §23 (tabla de invitaciones, ya da el layout de columnas),
             §29 (estado vacío)
Estados    — Default, Empty ("No hay invitaciones todavía"), Loading
Notas      — el modelo `Invitation` y sus estados (PENDING/USED/EXPIRED/CANCELLED) ya existen
             en Fase 1 y respaldan esta vista.
```

## 6.4 Médico — Listado de mis pacientes

```text
Pantalla   — Mis pacientes
Ruta       — patients:patient_list
Fase       — 1 | Rol(es) — Médico | Estado — Implementada
Objetivo   — que el médico ubique rápidamente a sus pacientes autorizados
Acción principal — (buscar) — no hay acción de "crear paciente" directa en Fase 1
             (el alta ocurre vía invitación, ver notas)
Información clave — nombre, contacto, estado
Componentes — PageHeader, Input (búsqueda), Table, Badge (activo/inactivo), EmptyState
Patrones   — UI Guidelines §17 (lista de pacientes, columnas ya definidas), §18 (búsqueda)
Estados    — Default, Empty, Loading
Notas      — usa `DoctorPatientRelationship` con `is_active=True` (misma regla que
             `patients/services/permissions.py`). Decisión confirmada: en Fase 1 el alta de
             pacientes ocurre **únicamente vía invitación** (§5.9) — no se construye una
             pantalla de "alta directa" por el médico, aunque requirements.md §3.1 mencione
             en general "registrar y actualizar pacientes y responsables" como capacidad del
             médico. Si en una fase posterior se decide agregar alta directa, es una pantalla
             nueva, no una modificación de esta.
```

## 6.5 Médico / Responsable — Detalle de paciente

```text
Pantalla   — Detalle de paciente
Ruta       — patients:patient_detail
Fase       — 1 | Rol(es) — Médico (relación activa), Responsable (relación activa), Paciente (self) |
Estado     — Implementada, incluida la acción "Marcar como adulto" (2026-09-08)
Objetivo   — consultar la información del paciente autorizada en Fase 1
Acción principal — (ninguna dominante todavía; ver notas)
Información clave — datos generales, contacto, domicilio, información médica general
Componentes — **PatientContextHeader** (dominio, UI Guidelines §48), Card (por bloque),
              Badge (estado), **Modal** (confirmación de "Marcar como adulto" — primer uso
              real de este componente en Fase 1; implementado sobre `<dialog>` nativo en
              `static/css/components.css`, sin JS externo)
Patrones   — Design System §28 (bloques del perfil), UI Guidelines §19-20 (detalle y
             contexto de paciente)
Estados    — Default, Unauthorized (404 uniforme — Design System §39, ADR-004: no distinguir
             "no existe" de "no autorizado")
Notas      — §19 de UI Guidelines ya anticipa tabs (Resumen/Citas/Consultas/Documentos);
             en Fase 1 **no debe** mostrarse esa navegación por tabs todavía, porque Citas/
             Consultas/Documentos no existen — mostrar únicamente los bloques de Design
             System §28 que sí aplican ahora: Datos generales, Contacto, Domicilio,
             Información médica, Relaciones. Omitir "Información gineco-obstétrica" e
             "Historial" (no modelados en Fase 1).

             Si el paciente fue registrado como menor (§6.8), `Person.is_minor` ya es `False`
             (cumplió 18 años cronológicamente) y `Patient.regime` todavía es `MINOR`, el
             bloque de encabezado debe mostrar un botón "Marcar como adulto" (secondary),
             visible solo para un médico con `DoctorPatientRelationship` activa hacia ese
             paciente (cualquier `relationship_type`) — no para el responsable ni para el
             propio paciente. Al pulsarlo, un **Modal** de confirmación explica que la acción
             es irreversible y que desactivará el acceso de todos los responsables actuales;
             confirmar ejecuta `transition_patient_to_adult` (ADR-007 §3.8, addendum) y
             refresca la pantalla.

             Si `Patient.regime` ya es `ADULT`, el bloque "Relaciones" no debe listar ninguna
             `ResponsiblePatientRelationship` como activa (todas quedaron `INACTIVE` por la
             transición) — no se muestra el botón ni ningún Alert, la pantalla simplemente ya
             no tiene responsables vigentes que mostrar.

             Estados de la acción — éxito (regime pasa a ADULT, relaciones desactivadas,
             botón desaparece); error de candado de edad (el backend rechaza si
             `Person.is_minor` es `True` — no debería poder ocurrir desde esta UI porque el
             botón no se muestra en ese caso, pero el mensaje de error debe documentarse por
             si se fuerza la petición); sin relación activa (el médico no ve el botón).
```

## 6.6 Paciente — Mi perfil

```text
Pantalla   — Mi perfil
Ruta       — patients:my_profile
Fase       — 1 | Rol(es) — Paciente | Estado — Implementada
Objetivo   — que el paciente consulte y actualice la información permitida de su propio perfil
Acción principal — Guardar cambios
Información clave — datos personales, contacto, domicilio, información médica general
Componentes — PageHeader, Card (por bloque), Input/Select/DateInput, Button (primary),
              Button (secondary/link → accounts:password_change)
Patrones   — UI Guidelines §9 (formulario agrupado por secciones), §8 (acción principal)
Estados    — Default, Loading, Error de validación, Success

Editable — regla confirmada: todo campo de dominio es editable, excepto los campos de
control del sistema y los de autenticación. Concretamente:

  Editable (Person):
    nombre(s), apellido paterno, apellido materno, fecha de nacimiento, teléfono,
    teléfono alternativo, calle, número, colonia, código postal, municipio/alcaldía,
    estado, país

  Editable (Patient):
    CURP, nacionalidad, sexo, contacto de emergencia (nombre y teléfono), tipo sanguíneo,
    alergias, enfermedades crónicas, medicamentos actuales, antecedentes quirúrgicos,
    hospitalizaciones relevantes

  No editable en este formulario:
    correo electrónico (User.email — identificador de autenticación, solo lectura aquí)
    contraseña (no vive en este formulario; enlaza a "Cambiar contraseña", §5.6)
    estado de verificación de correo, activo/inactivo (campos de control del sistema,
    no se exponen como editables)

Notas — el correo se muestra como dato de solo lectura (no oculto) para que el paciente
        sepa con qué cuenta inició sesión; cambiarlo requeriría re-verificación y no está
        definido en Fase 1, por eso queda fuera de este formulario, no solo deshabilitado
        visualmente (Design System §39: ocultar/deshabilitar en la UI no es autorización —
        la vista/servicio tampoco debe aceptar `email` en el payload de este formulario).
```

## 6.7 Responsable — Mis pacientes a cargo

```text
Pantalla   — Mis pacientes a cargo
Ruta       — patients:my_dependents
Fase       — 1 | Rol(es) — Responsable | Estado — Implementada
Objetivo   — que el responsable vea y seleccione entre los pacientes que tiene a su cargo
Acción principal — Ver (por paciente)
Información clave — nombre del paciente, tipo de relación, estado
Componentes — PageHeader, Table o Card por paciente, Badge (tipo de relación, estado)
Patrones   — UI Guidelines §17 (patrón de lista, adaptado), Design System §30/UI Guidelines §16
             (selector de paciente cuando hay más de uno — se resuelve con **Dropdown**,
             componente ya existente, no requiere uno nuevo)
Estados    — Default, Empty ("No tienes pacientes a cargo todavía"), Loading
Notas      — usa `ResponsiblePatientRelationship` con `status=ACTIVE` (ADR-007 §3.7: `status`
             reemplazó el booleano `is_active` original — PENDING/ACTIVE/INACTIVE, no un
             solo flag — porque una relación nunca aprobada no debe verse igual que una que
             sí fue aprobada y luego se desactivó). Las solicitudes de otro responsable
             pidiendo vincularse (§6.7 más abajo) usan `status=PENDING`. Al entrar al detalle
             de un paciente debe quedar visible en todo momento a cuál corresponde
             (Design System §30: "nunca mezclar información de varios pacientes sin
             indicarlo claramente") — mismo `PatientContextHeader` de §6.5. Su acción
             principal es "Registrar paciente menor" (§6.8), no "Ver" — la lista existe para
             administrar a los pacientes a cargo, y agregar uno nuevo es la acción que un
             responsable necesita con más frecuencia que revisitar uno ya conocido.

             Esta pantalla también es donde un responsable **ya autorizado** ve y resuelve
             solicitudes de un segundo responsable pidiendo vincularse al mismo paciente
             (requirements.md §7.2.7, coincidencia por CURP). Cada solicitud pendiente se
             muestra con Badge "Solicitud pendiente" (variante `warning`) y dos acciones,
             Aprobar / Rechazar — no se mezcla con las filas de pacientes ya vigentes. No se
             diseña aquí el detalle de aprobar/rechazar (formulario mínimo: confirmar o
             rechazar); el estado de tres valores que lo sostiene (nunca-aprobada / vigente /
             desactivada) está definido en ADR-007 §3.7.

             Esta lista solo puede mostrar filas con `status=ACTIVE`, así que un paciente cuya
             `ResponsiblePatientRelationship` ya fue desactivada por la transición a régimen
             adulto (ADR-007 §3.8, addendum) **deja de aparecer aquí** — el responsable perdió
             el acceso, no tiene sentido seguir listándolo como a cargo.

             Distinto es un paciente que ya cumplió 18 años cronológicamente
             (`Person.is_minor=False`) pero cuyo `Patient.regime` **todavía es `MINOR`**
             (ningún médico ejecutó la transición todavía): ese paciente sigue apareciendo en
             esta lista igual que cualquier otro, con acceso vigente, distinguido únicamente
             con un Badge adicional "Adulto" (variante `neutral`, junto al de tipo de
             relación) — puramente informativo, para que el responsable sepa que la mayoría
             de edad ya llegó aunque el sistema todavía no haya cerrado su acceso. No es un
             estado de alerta (no usa `warning`/`danger`) y no cambia ninguna acción
             disponible en esta fila.
```

## 6.8 Responsable — Registrar paciente menor

Flujo decidido en `requirements.md` §7.2 y `docs/adr/ADR-007-responsible-initiated-minor-registration.md`.
A diferencia del registro por invitación (§5.9, que es un único formulario con secciones), este
es un wizard real de varios pasos — el responsable ya está autenticado, no hay invitación que
validar antes de empezar, y cada paso puede depender de una operación de servidor separada
(en particular, la detección de "menor ya existente" en el paso 1 antes de dejar avanzar).

```text
Pantalla   — Registrar paciente menor (paso 1 de 3): Datos del menor
Ruta       — patients:register_minor_step1
Fase       — 1 | Rol(es) — Responsable | Estado — Implementada
Objetivo   — capturar los datos mínimos del menor (requirements.md §7.2.1)
Acción principal — Continuar
Información clave — en qué paso está (1 de 3)
Componentes — PageHeader, Stepper, Input, Select (sexo), DateInput (fecha de nacimiento),
              Button (primary)
Patrones   — UI Guidelines §11 (mismo componente Stepper, pasos propios), Design System §16
Estados    — Default, Error de validación, Loading, y dos estados de coincidencia (ver notas):
             coincidencia de baja confianza (bloquea el autoservicio) y coincidencia por CURP
             (permite continuar, pero cambia el resultado del paso 3)
Notas      — el correo electrónico del menor es opcional (requirements.md §7.2.1) — no debe
             marcarse como obligatorio. No pedir datos que pertenecen al responsable (p. ej.
             no preguntar "tu teléfono" en este formulario).

             Detección de "menor ya existente" (regla definida en requirements.md §7.2.7):
             - Sin coincidencia → continúa normalmente al paso 2.
             - Coincidencia solo por nombre + fecha de nacimiento (sin CURP, confianza baja):
               NO deja avanzar el autoservicio. Mensaje genérico tipo Alert (warning):
               "Ya existe un registro relacionado con estos datos. Contacta a tu médico o al
               consultorio para continuar." Nunca debe mostrar datos del registro existente
               (nombre del otro responsable, información del paciente) — regla de privacidad
               obligatoria (requirements.md §7.2.7).
             - Coincidencia por CURP (alta confianza) contra un paciente sin cuenta propia:
               SÍ deja avanzar (no se duplica el registro), pero el resultado ya no es "se
               creó tu paciente" — ver paso 3.
             - Coincidencia (por CURP o por nombre+fecha) contra un paciente que ya tiene
               cuenta propia: no deja avanzar por autoservicio — mismo mensaje genérico que la
               coincidencia de baja confianza (el consentimiento del propio paciente para
               vincular un responsable no está diseñado todavía, requirements.md §7.2.7).
```

```text
Pantalla   — Registrar paciente menor (paso 2 de 3): Relación con el menor
Ruta       — patients:register_minor_step2
Fase       — 1 | Rol(es) — Responsable | Estado — Implementada
Objetivo   — capturar el tipo de relación (Madre/Padre/Tutor legal/Familiar/Cuidador/Otro)
Acción principal — Continuar
Componentes — PageHeader, Stepper, Select o grupo de Radio, Button (primary), Button
              (secondary, "Atrás")
Patrones   — UI Guidelines §11
Estados    — Default, Error de validación, Loading
Notas      — mismo catálogo de `ResponsiblePatientRelationship.RelationType` que ya existe en
             el modelo — no se inventa un catálogo nuevo para esta pantalla.
```

```text
Pantalla   — Registrar paciente menor (paso 3 de 3): Confirmación
Ruta       — patients:register_minor_step3
Fase       — 1 | Rol(es) — Responsable | Estado — Implementada
Objetivo   — confirmar el resultado y explicar el estado de acceso — el resultado no es el
             mismo en los dos casos que puede dejar avanzar el paso 1 (ver notas)
Acción principal — Continuar (vuelve a "Mis pacientes a cargo")
Componentes — Alert (success o info, según el caso), Card (resumen: paciente, edad derivada
              de la fecha de nacimiento, responsable, tipo de relación, estado de acceso)
Patrones   — Design System §36 (confirmaciones), requirements.md §7.2.3 (paciente clínico vs.
             usuario paciente), §7.2.7 (vinculación)
Estados    — Success (menor nuevo), Info (vinculación pendiente de aprobación)
Notas      — dos resultados posibles, según lo que haya pasado en el paso 1:
             - **Menor nuevo**: Alert success — "Paciente registrado correctamente." Debe
               decir explícitamente si el menor tiene o no una cuenta propia todavía
               ("Acceso del paciente: no activado"), consistente con que el registro inicial
               no obliga a crear `User` (requirements.md §7.2.3).
             - **Coincidencia por CURP, vinculación solicitada** (requirements.md §7.2.7):
               Alert info — "Encontramos un registro existente. Se envió una solicitud de
               acceso al responsable actual; podrás ver a este paciente cuando la apruebe."
               No es un estado de éxito inmediato: la `ResponsiblePatientRelationship` existe
               pero no está vigente todavía. No debe decir "paciente registrado".

             En ningún caso debe decir "invitación enviada al paciente" — el mecanismo de
             confirmación/aprobación (cuando lo hay en este punto del flujo) es para el
             responsable, nunca para el menor (requirements.md §7.2.4).
```

Esta pantalla de detalle de paciente reutiliza `patients:patient_detail` (§6.5) — no se
diseña una pantalla nueva para "ver a mi paciente registrado", el patrón ya existe y ya
contempla el `PatientContextHeader`.

---

# 7. Componentes nuevos propuestos

Antes de proponer cualquiera de estos, se revisó la lista de componentes base
(Design System §40 / UI Guidelines §47) y de dominio (UI Guidelines §48). Todo lo demás
necesario para las pantallas de §5-6 ya existe en esas listas (Button, Input, Select,
DateInput, Alert, Badge, Card, Table, Dropdown, EmptyState, PageHeader,
PatientContextHeader, InvitationStatus).

## 7.1 Stepper / Progress Steps

**Propósito:** indicar en qué paso se encuentra el usuario dentro de un flujo guiado de
varios pasos, y cuántos faltan.

**Por qué es necesario:** Design System §10 y UI Guidelines §11 exigen "mostrar claramente
el avance" en formularios largos con secuencia natural (el registro por invitación, §5.9,
es el caso concreto en Fase 1), pero ningún componente de la lista base cubre esto —
`Breadcrumb` comunica jerarquía de navegación, no progreso secuencial.

**Dónde se usa en Fase 1:** Registro por invitación (§5.9).

**Dónde se prevé reutilizar (fases futuras):** cualquier flujo multi-paso posterior
(p. ej. una eventual captura de solicitud de estudio en Fase 4).

**Estado:** incorporado. Agregado a la lista de componentes base en
`docs/design/design-system.md` §40 (con su propia explicación de propósito y diferencia
frente a `Breadcrumb`) y en `docs/design/ui-guidelines.md` §47-48, §10 y §11, siguiendo el
proceso de evolución del propio Design System (§55: identificar → convertir en componente →
documentar → incorporar → reutilizar).

---

# 8. Administrador — nota de alcance

Fase 1 no define una interfaz propia para Administrador: `requirements.md` §3.1 le da acceso
global, y `docs/phases/phase-1-foundations.md` no exige una UI dedicada — esa gestión se
cubre con el Django Admin nativo (Usuarios, Personas, Invitaciones, Médicos, Consultorios,
relaciones), que **no sigue el Design System** (es la interfaz por defecto del framework).

UI Guidelines §5 ya anticipa una navegación de Administrador (Inicio, Usuarios, Médicos,
Consultorios, Configuración, Auditoría) como referencia de diseño, pero construir esa
interfaz propia es una decisión de alcance que no se ha tomado — no se documentan pantallas
de Administrador en este archivo para evitar dar por hecho que se va a construir. Cuando se
decida (dentro de Fase 1 o en una fase posterior), se agrega aquí su propio bloque siguiendo
el mismo formato de §6.

---

# 9. Pantallas de fases futuras (referencia de diseño)

Se listan únicamente para que el vocabulario visual (componentes, patrones, terminología) sea
consistente desde ahora. **No implementar ninguna de estas hasta la fase correspondiente**
(CLAUDE.md §5, §14).

## 9.1 Fase 2 — Agenda

Especificación funcional completa y aprobada en `docs/phases/phase-2-agenda.md`
(2026-09-09) — ese documento manda sobre cualquier detalle de terminología o estados que
aparezca aquí; esta lista sigue siendo solo inventario de pantallas, no especificación visual.

- Agenda del médico (Design System §29, UI Guidelines §14) — disponibilidad **por fecha
  concreta**, sin vista de reglas semanales recurrentes. Las horas se muestran en la zona
  horaria del `Clinic`, nunca en la del dispositivo del usuario (decisión de cierre,
  2026-09-09).
- Disponibilidad del médico (crear/modificar por fecha; el administrador también puede
  apoyar esta operación, siempre que exista `DoctorClinic` válida para el médico y consultorio
  involucrados). Un médico no puede tener disponibilidad simultánea en dos consultorios
  distintos — la UI debe rechazar/advertir ese solapamiento igual que el del mismo
  consultorio.
- Reservar cita — **directa**, sin paso de solicitud ni confirmación posterior (Paciente/
  Responsable/Médico/Administrador, según autorización). Un médico puede reservar la primera
  cita de un paciente sin `DoctorPatientRelationship` previa, siempre que tenga acceso
  legítimo (`DoctorClinic` válida); esa reserva no crea ni modifica la relación (decisión de
  cierre, 2026-09-09).
- Mis citas (Paciente/Responsable) (UI Guidelines §15-16).
- Iniciar consulta (Médico) — reemplaza cualquier concepto de "check-in" o "sala de espera"
  de versiones anteriores de este documento: no hay check-in realizado por paciente,
  responsable ni administrador.
- Estados de `Appointment` a representar en UI — únicamente estos cinco: `SCHEDULED`,
  `IN_CONSULTATION`, `COMPLETED`, `CANCELLED`, `NO_SHOW` (UI Guidelines §33; Design System
  §47: semántica de color por estado). No existen como estados: Pendiente, Confirmada, En
  espera, Reprogramada ni Liberada — la reprogramación es un evento con historial, no un
  estado (§12 de `phase-2-agenda.md`).

## 9.2 Fase 3 — Gestión clínica

- Historia clínica (Design System §26-27)
- Registro de consulta / evolución
- Alertas clínicas (Design System §27, UI Guidelines componente de dominio `ClinicalAlert`)
- Resumen clínico

## 9.3 Fase 4 — Documentos

- Recetas, solicitudes de estudio, documentos (UI Guidelines §35 — campos mínimos ya
  definidos: tipo, fecha, descripción, origen, acciones)

## 9.4 Fase 5 — CareRequest y operación

- Dashboard médico real (Design System §29, UI Guidelines §14): agenda del día (estados reales
  de `Appointment`, §9.1) → alertas operativas → próximas citas. "Pacientes en espera" queda
  **pendiente de diseño** — Fase 2 no dejó check-in ni un estado `WAITING` de los que depender
  (`requirements.md` §41, Fase 5); no debe asumirse resuelto.
- Dashboard paciente/responsable real (Design System §30, UI Guidelines §15-16): próxima
  cita → mis citas → mis documentos
- CareRequest: solicitud de atención, con conversión opcional a cita — un origen alternativo
  que coexiste con la reserva directa de Fase 2, nunca la reemplaza ni la condiciona
  (`requirements.md` §12).
- Búsqueda global

## 9.5 Fase 6 — Notificaciones y auditoría

- Auditoría (Administrador)
- Centro de notificaciones

---

# 10. Verificación antes de dar por cerrada una pantalla

Antes de considerar implementada visualmente una pantalla de este documento, confirmar
(UI Guidelines §57, Definition of Done de UI):

- [ ] usa componentes existentes de §40/§47-48 antes que uno nuevo;
- [ ] si necesitó un componente nuevo, está documentado en §7 y agregado al Design System;
- [ ] respeta tokens de color/tipografía/espaciado (no valores arbitrarios);
- [ ] tiene una sola acción principal dominante;
- [ ] contempla los estados que le apliquen (Default/Loading/Empty/Error/Unauthorized/Success);
- [ ] es consistente con el mismo patrón en las otras áreas de rol;
- [ ] no implementa nada fuera de la fase indicada en su ficha.

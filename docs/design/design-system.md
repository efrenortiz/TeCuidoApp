# TeCuidoApp — Design System

**Estado:** Propuesta inicial  
**Versión:** 1.0  
**Fase:** Fase 1 — Fundaciones  
**Aplicación:** TeCuidoApp  
**Referencia funcional:** `requirements.md`  
**Referencia arquitectónica:** `docs/architecture.md`

---

# 1. Propósito

Este documento define los principios visuales y de experiencia de usuario de **TeCuidoApp**.

Su objetivo es proporcionar una base consistente para todas las interfaces actuales y futuras de la aplicación:

- Administrador
- Médico
- Paciente
- Responsable

El Design System debe favorecer:

- confianza;
- claridad;
- legibilidad;
- accesibilidad;
- reducción de errores;
- orientación profesional;
- consistencia;
- eficiencia operativa.

El sistema debe transmitir la sensación de una plataforma médica profesional, segura y confiable, evitando una estética excesivamente informal o experimental.

---

# 2. Principios de diseño

## 2.1 Claridad antes que decoración

La información debe ser fácil de localizar y comprender.

No utilizar elementos visuales únicamente porque "se ven bien" si dificultan:

- lectura;
- navegación;
- toma de decisiones;
- identificación de estados.

---

## 2.2 Profesionalismo médico

La interfaz debe transmitir:

- confianza;
- precisión;
- tranquilidad;
- orden;
- profesionalismo.

Evitar una estética:

- excesivamente corporativa;
- infantil;
- saturada;
- gamificada;
- excesivamente tecnológica.

---

## 2.3 Jerarquía visual

Cada pantalla debe permitir identificar rápidamente:

1. dónde estoy;
2. qué puedo hacer;
3. cuál es la información importante;
4. qué acción principal debo realizar;
5. qué información requiere atención.

---

## 2.4 Reducción de carga cognitiva

Las pantallas médicas y administrativas pueden contener bastante información.

Por ello:

- agrupar información relacionada;
- utilizar secciones;
- evitar formularios interminables;
- utilizar progressive disclosure cuando corresponda;
- mantener acciones importantes visibles;
- reducir elementos secundarios.

---

## 2.5 Seguridad visible pero no intrusiva

La interfaz debe transmitir seguridad sin llenar cada pantalla de advertencias.

La seguridad debe manifestarse mediante:

- estados claros;
- permisos;
- confirmaciones;
- mensajes comprensibles;
- indicación de documentos privados;
- acciones destructivas protegidas.

---

# 3. Dirección visual

La dirección visual propuesta es:

**Médica + profesional + moderna + limpia + humana.**

Características:

- superficies claras;
- alto contraste de texto;
- colores sobrios;
- espacios generosos;
- bordes discretos;
- sombras sutiles;
- iconografía simple;
- estados claramente diferenciados.

Evitar:

- gradientes decorativos excesivos;
- sombras fuertes;
- animaciones constantes;
- exceso de tarjetas;
- colores muy saturados;
- tipografías decorativas.

---

# 4. Sistema de color

Los valores exactos pueden ajustarse durante el diseño visual definitivo, pero deben conservar los siguientes roles semánticos.

## 4.1 Color primario

Representa:

- acciones principales;
- enlaces principales;
- elementos de navegación destacados;
- identidad visual de la plataforma.

Debe ser sobrio y profesional.

---

## 4.2 Color secundario

Se utiliza para:

- acciones secundarias;
- elementos complementarios;
- estados informativos no críticos.

No debe competir visualmente con el color primario.

---

## 4.3 Success

Utilizar para:

- operaciones completadas;
- estados satisfactorios;
- confirmaciones;
- acciones exitosas.

No utilizar exclusivamente el color para comunicar significado; acompañar con texto, icono o estado.

---

## 4.4 Warning

Utilizar para:

- atención requerida;
- información incompleta;
- situaciones que requieren revisión.

---

## 4.5 Error / Danger

Utilizar para:

- errores;
- operaciones destructivas;
- acciones irreversibles;
- acceso denegado;
- estados problemáticos.

Debe reservarse para situaciones que realmente requieren atención.

---

## 4.6 Info

Utilizar para:

- información contextual;
- ayuda;
- recomendaciones de interfaz;
- estados informativos.

---

## 4.7 Neutral

Utilizar para:

- texto;
- bordes;
- fondos;
- divisores;
- superficies secundarias;
- estados inactivos.

---

# 5. Regla de color semántico

Los colores representan significado, no decoración.

Ejemplo:

```text
Primary  → acción principal
Success  → operación completada
Warning  → requiere atención
Danger   → error / acción destructiva
Info     → información
Neutral  → estructura / contenido secundario
```

No utilizar un color diferente simplemente para "variar" visualmente una pantalla.

---

# 6. Tipografía

La tipografía debe priorizar legibilidad.

Características:

- sans-serif;
- alta legibilidad;
- buena diferenciación entre pesos;
- excelente lectura en pantallas grandes y pequeñas.

Jerarquía:

```text
Display
H1
H2
H3
Body
Small
Caption
```

La interfaz debe evitar utilizar demasiados tamaños de fuente simultáneamente.

---

# 7. Escala tipográfica

Como guía:

```text
Display     → uso excepcional
H1          → título de página
H2          → sección principal
H3          → subsección
Body        → contenido
Small       → información secundaria
Caption     → metadatos
```

Los títulos no deben utilizarse solamente para aumentar visualmente el tamaño de texto.

Cada nivel debe tener una función estructural.

---

# 8. Espaciado

Utilizar una escala consistente de espaciado.

Escala recomendada:

```text
4px
8px
12px
16px
24px
32px
40px
48px
64px
```

Priorizar múltiplos consistentes.

Evitar valores arbitrarios como:

```text
13px
19px
27px
35px
```

salvo que exista una razón específica.

---

# 9. Layout

Utilizar un sistema de layout consistente.

Conceptualmente:

```text
┌─────────────────────────────────────────────┐
│ Header / Navigation                         │
├──────────────┬──────────────────────────────┤
│ Sidebar      │ Main Content                 │
│              │                              │
│              │                              │
└──────────────┴──────────────────────────────┘
```

La estructura podrá cambiar según el rol.

Sin embargo, los patrones globales deben mantenerse consistentes.

---

# 10. Responsive Design

La aplicación debe funcionar correctamente en:

- desktop;
- laptop;
- tablet;
- móvil cuando la funcionalidad lo permita.

La interfaz no debe depender exclusivamente de hover.

Las acciones críticas deben seguir siendo utilizables mediante:

- teclado;
- touch;
- lectores de pantalla cuando corresponda.

---

# 11. Grid y ancho de contenido

Las pantallas deben evitar contenido excesivamente ancho.

Preferir:

- columnas;
- paneles;
- secciones;
- tablas con scroll horizontal cuando sea necesario.

Los formularios deben tener una anchura que facilite lectura y captura.

---

# 12. Navegación

La navegación principal debe ser predecible.

Debe permitir identificar:

- módulo actual;
- sección actual;
- ubicación;
- acciones disponibles.

La navegación de cada rol puede diferir, pero debe utilizar patrones visuales comunes.

---

# 13. Estructura de una página

Patrón recomendado:

```text
Page
├── Breadcrumb / contexto (cuando sea necesario)
├── Page Header
│   ├── Title
│   ├── Description
│   └── Primary Action
├── Filters / controls (si aplica)
├── Main Content
└── Secondary Content / Actions
```

No todas las pantallas necesitan todos los elementos.

---

# 14. Botones

Los botones deben diferenciar claramente:

### Primary

Acción principal de la pantalla.

Ejemplos:

- Guardar;
- Crear;
- Confirmar;
- Continuar.

### Secondary

Acciones alternativas.

Ejemplos:

- Cancelar;
- Volver;
- Ver detalles.

### Tertiary / Link

Acciones de menor jerarquía.

### Danger

Acciones destructivas o de alto riesgo.

---

# 15. Regla de botones

Una pantalla debe tener idealmente **una acción primaria claramente dominante**.

Evitar:

```text
[Crear] [Guardar] [Confirmar] [Continuar] [Procesar]
```

todos con el mismo peso visual.

La jerarquía debe ayudar al usuario a saber qué hacer a continuación.

---

# 16. Formularios

Los formularios son una parte fundamental de TeCuidoApp.

Deben priorizar:

- etiquetas visibles;
- instrucciones claras;
- validación inmediata cuando corresponda;
- mensajes de error junto al campo;
- agrupación lógica;
- navegación por teclado;
- prevención de pérdida de información.

No utilizar placeholders como sustituto de labels.

---

# 17. Campos obligatorios

Los campos obligatorios deben identificarse consistentemente.

Preferir:

```text
Nombre *
```

con una explicación global cuando sea necesario.

No utilizar únicamente color para distinguir campos obligatorios.

---

# 18. Errores de formularios

Los errores deben:

- explicar qué ocurrió;
- indicar cómo corregirlo;
- aparecer cerca del campo afectado;
- mantener el valor introducido cuando sea seguro hacerlo.

Evitar mensajes genéricos como:

```text
Error.
```

Preferir mensajes accionables.

---

# 19. Estados de carga

Durante operaciones asíncronas debe existir feedback.

Ejemplos:

```text
Guardando...
Enviando...
Cargando...
Procesando...
```

No permitir que el usuario tenga que adivinar si una acción fue ejecutada.

---

# 20. Estados vacíos

Cuando no existan registros, mostrar una explicación útil.

Ejemplo:

```text
No hay pacientes registrados.

Los pacientes aparecerán aquí cuando sean registrados
o cuando acepten una invitación.
```

Cuando sea relevante, proporcionar una acción.

---

# 21. Alertas y mensajes

Utilizar componentes semánticos:

```text
Success
Info
Warning
Error
```

Los mensajes deben ser:

- claros;
- breves;
- accionables;
- consistentes.

Evitar mensajes técnicos para usuarios finales.

---

# 22. Modales

Los modales deben utilizarse para:

- confirmaciones;
- acciones que requieren atención;
- información contextual importante.

No utilizarlos para:

- navegación normal;
- formularios excesivamente largos;
- contenido que requiere lectura extensa.

---

# 23. Acciones destructivas

Las acciones destructivas deben:

- utilizar estilo Danger;
- indicar claramente qué ocurrirá;
- solicitar confirmación cuando corresponda;
- evitar confundir Cancelar con Eliminar.

En TeCuidoApp debe preferirse la baja lógica cuando el dominio así lo requiera.

---

# 24. Tablas

Las tablas deben priorizar:

- lectura rápida;
- alineación;
- encabezados claros;
- ordenamiento cuando sea necesario;
- filtros cuando exista volumen de datos;
- acciones por fila claramente diferenciadas.

No introducir tablas con demasiadas columnas sin considerar responsive behavior.

---

# 25. Badges y estados

Los estados deben representarse mediante badges/chips cuando sea útil.

Ejemplos conceptuales:

```text
Activo
Inactivo
Pendiente
Verificado
Expirado
Cancelado
```

En futuras fases también:

```text
Confirmada
En espera
En consulta
Atendida
NO_SHOW
```

El texto del estado debe aparecer siempre; el color por sí solo no es suficiente.

---

# 26. Información sensible

La información médica debe presentarse de forma discreta y organizada.

Evitar mostrar grandes bloques de información clínica sin jerarquía.

La interfaz debe diferenciar visualmente entre:

- datos generales;
- información relevante;
- información histórica;
- alertas.

---

# 27. Alertas clínicas

Cuando se implementen en fases posteriores, las alertas clínicas deberán tener alta visibilidad sin convertirse en ruido visual.

Una alerta activa deberá comunicar:

1. que existe;
2. qué significa;
3. si requiere atención;
4. cuándo fue creada.

La presentación debe ser claramente distinta de una alerta operativa normal.

---

# 28. Perfil del paciente

La información del paciente deberá organizarse por bloques.

Ejemplo conceptual:

```text
Paciente
├── Datos generales
├── Contacto
├── Domicilio
├── Información médica
├── Información gineco-obstétrica
├── Relaciones
└── Historial
```

No mostrar todos los campos simultáneamente si la pantalla se vuelve difícil de leer.

---

# 29. Dashboard médico

En futuras fases, el dashboard médico deberá priorizar:

```text
Agenda del día
       ↓
Pacientes en espera
       ↓
Alertas operativas
       ↓
Próximas citas
```

La información que requiere una acción inmediata debe tener mayor jerarquía.

El dashboard no debe convertirse en una colección de tarjetas sin una función clara.

---

# 30. Dashboard paciente / responsable

Debe priorizar:

```text
Próxima cita
      ↓
Mis citas
      ↓
Mis documentos
```

En el caso del responsable, debe ser evidente qué paciente está seleccionado.

Evitar mezclar información de varios pacientes sin indicarlo claramente.

---

# 31. Terminología de interfaz

Utilizar lenguaje natural para usuarios finales.

Preferir:

```text
Paciente
Médico
Consultorio
Cita
Solicitud
Receta
Documento
Responsable
```

Los nombres técnicos del código no deben aparecer en la interfaz cuando exista un término de negocio adecuado.

Por ejemplo, no mostrar:

```text
MedicalEncounter
CareRequest
DoctorPatientRelationship
```

como etiquetas para usuarios finales.

---

# 32. Fechas y horas

Mostrar fechas y horas de manera consistente.

La interfaz debe evitar formatos ambiguos.

Preferir formatos fácilmente interpretables por usuarios mexicanos.

Ejemplo:

```text
15 de septiembre de 2026
10:30 a. m.
```

Cuando sea importante, indicar claramente zona horaria.

---

# 33. Iconografía

Los iconos deben:

- ser simples;
- consistentes;
- reconocibles;
- acompañar al texto cuando la acción pueda ser ambigua.

No utilizar iconos como única representación de acciones críticas.

---

# 34. Accesibilidad

La interfaz debe seguir buenas prácticas de accesibilidad.

Como mínimo:

- contraste suficiente;
- navegación mediante teclado;
- focus visible;
- labels asociados a controles;
- mensajes de error comprensibles;
- no depender exclusivamente del color;
- tamaños de interacción adecuados;
- estructura semántica.

La accesibilidad debe considerarse parte de la calidad del producto, no una característica opcional.

---

# 35. Focus

Todos los elementos interactivos deben mostrar claramente su estado de focus.

No eliminar el outline del navegador sin proporcionar una alternativa visual equivalente.

---

# 36. Confirmaciones

Las acciones importantes deben proporcionar feedback inmediato.

Ejemplos:

```text
Paciente actualizado correctamente.
Invitación enviada correctamente.
Cambios guardados.
```

No utilizar exclusivamente mensajes de color verde sin texto.

---

# 37. Diseño de autenticación

Las pantallas de:

- login;
- recuperación de contraseña;
- cambio de contraseña;
- verificación de email;
- registro mediante invitación;

deben utilizar un patrón visual común.

Deben transmitir:

- confianza;
- simplicidad;
- seguridad;
- orientación clara.

Evitar formularios innecesariamente complejos.

---

# 38. Registro mediante invitación

El flujo debe ser guiado.

Patrón visual:

```text
Invitación válida
      ↓
Información de registro
      ↓
Datos personales
      ↓
Verificación de email
      ↓
Registro completado
```

El usuario debe saber en qué paso se encuentra.

No mostrar complejidad técnica del proceso.

---

# 39. Seguridad en interfaz

La UI puede ayudar a prevenir errores, pero nunca sustituye la autorización del servidor.

Por ejemplo:

```text
Ocultar botón "Editar"
```

no significa:

```text
Usuario no puede editar
```

El backend debe realizar la validación correspondiente.

---

# 40. Componentes reutilizables

Antes de crear un nuevo componente, comprobar si existe un componente equivalente.

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

La lista puede crecer según las necesidades reales.

### Stepper

Indica en qué paso se encuentra el usuario dentro de un flujo guiado de varios pasos, y
cuántos faltan.

No sustituye a `Breadcrumb`: `Breadcrumb` comunica jerarquía de navegación ("dónde estoy en
la estructura de la app"); `Stepper` comunica avance secuencial dentro de un mismo flujo
("qué tan lejos voy en este proceso").

Debe utilizarse cuando un formulario largo tenga una secuencia natural (ver "Formularios
largos" en `docs/design/ui-guidelines.md`) — por ejemplo, el registro mediante invitación
(§38 de este documento).

El paso activo debe distinguirse claramente de los pasos completados y de los pendientes; el
nombre de cada paso (no solo su posición numérica) debe ser legible, para que el usuario sepa
qué le falta, no solo cuánto le falta.

---

# 41. Design Tokens

Los estilos deben centralizarse mediante tokens.

Conceptualmente:

```text
colors
spacing
typography
radius
shadows
breakpoints
transitions
```

Evitar repetir valores visuales arbitrarios directamente en múltiples templates.

---

# 42. Componentes vs páginas

Separar:

```text
Design Tokens
      ↓
Components
      ↓
Patterns
      ↓
Pages
```

Ejemplo:

```text
Button
  ↓
Form Action Group
  ↓
Patient Registration Form
  ↓
Registration Page
```

Una página no debe implementar desde cero componentes ya existentes.

---

# 43. Consistencia

Una misma acción debe verse y comportarse de forma similar en toda la aplicación.

Ejemplo:

```text
Guardar
```

debe utilizar:

- mismo estilo;
- misma ubicación relativa;
- mismo feedback;
- mismo comportamiento.

Esto aplica especialmente a:

- guardar;
- cancelar;
- eliminar/desactivar;
- confirmar;
- volver.

---

# 44. Animaciones

Las animaciones deben ser mínimas y funcionales.

Pueden utilizarse para:

- cambios de estado;
- feedback;
- apertura/cierre de elementos;
- transiciones ligeras.

Evitar animaciones decorativas frecuentes.

---

# 45. Densidad visual

TeCuidoApp tendrá dos necesidades diferentes:

### Operación clínica

Mayor densidad informativa.

### Portal paciente

Menor densidad y mayor orientación.

La misma identidad visual debe mantenerse, pero la densidad puede variar según el contexto.

---

# 46. Diferenciación por rol

Los roles pueden tener navegación y prioridades diferentes, pero no deben parecer aplicaciones completamente distintas.

Debe existir una identidad visual compartida.

```text
                TeCuidoApp
                    │
        ┌───────────┼───────────┐
        │           │           │
   Administrador  Médico   Paciente/Responsable
        │           │           │
       mismo lenguaje visual
```

---

# 47. Diseño de estados clínicos

En fases posteriores, los estados clínicos y operativos deben tener una semántica consistente.

Por ejemplo:

```text
Pendiente  → Neutral / atención moderada
Confirmada → información positiva
En espera  → atención operacional
En consulta → estado activo
Atendida   → Success
Cancelada  → Neutral / Warning
NO_SHOW    → Danger
```

Los colores exactos se definirán mediante tokens.

---

# 48. Diseño para errores de negocio

Los errores de negocio no deben parecer errores técnicos.

Ejemplo incorrecto:

```text
IntegrityError: duplicate key value violates unique constraint
```

Ejemplo correcto:

```text
Este correo electrónico ya está registrado.
```

Los detalles técnicos deben permanecer en logs y herramientas de diagnóstico.

---

# 49. Diseño para privacidad

No mostrar información sensible innecesariamente.

En listados:

- mostrar solamente los datos necesarios;
- evitar exposición accidental;
- utilizar acciones explícitas para detalles sensibles.

La privacidad visual complementa, pero no reemplaza, el control de acceso del backend.

---

# 50. Responsividad de tablas

Cuando una tabla no quepa en pantallas pequeñas:

Preferir:

1. scroll horizontal controlado;
2. columnas prioritarias;
3. vistas alternativas;
4. cards cuando realmente mejoren comprensión.

No comprimir el texto hasta volverlo ilegible.

---

# 51. Principios de implementación frontend

El Design System debe poder implementarse sin depender de una librería visual concreta.

Claude Code podrá utilizar la tecnología frontend existente o acordada por el proyecto, pero debe respetar:

- tokens;
- componentes;
- patrones;
- jerarquía;
- semántica;
- accesibilidad.

No introducir una librería UI solamente para resolver un componente aislado sin evaluar el impacto global.

---

# 52. Reglas para Claude Code

Antes de crear una pantalla:

1. revisar este Design System;
2. revisar `requirements.md`;
3. revisar la arquitectura;
4. revisar componentes existentes;
5. reutilizar patrones disponibles.

Antes de crear un componente:

1. buscar uno equivalente;
2. determinar si puede extenderse;
3. evitar duplicados;
4. documentar patrones nuevos cuando tengan valor transversal.

Toda pantalla nueva debe respetar el sistema visual.

---

# 53. Regla de consistencia

Si existe discrepancia entre una pantalla existente y este Design System, no asumir automáticamente que el código existente es correcto.

Evaluar:

- intención original;
- requerimiento;
- accesibilidad;
- coherencia con el sistema.

Las correcciones visuales importantes deben aplicarse de forma consistente, no únicamente en una pantalla.

---

# 54. Fuera de alcance

Este documento no define:

- backend;
- modelos Django;
- PostgreSQL;
- autenticación técnica;
- autorización;
- lógica de negocio;
- reglas clínicas;
- APIs.

Esos elementos están definidos en:

```text
requirements.md
docs/architecture.md
docs/adr/
```

El Design System define únicamente la capa visual y de experiencia de usuario.

---

# 55. Evolución

Este documento evolucionará a medida que aparezcan nuevas necesidades.

Cuando un nuevo patrón visual se utilice de forma recurrente:

1. identificarlo;
2. convertirlo en componente o patrón;
3. documentarlo;
4. incorporarlo al Design System;
5. reutilizarlo.

No convertir casos aislados en componentes genéricos sin necesidad real.

---

# 56. Definition of Done del Design System

El sistema visual inicial puede considerarse estable cuando:

- [ ] existe una paleta semántica;
- [ ] existe una escala tipográfica;
- [ ] existe una escala de espaciado;
- [ ] existe una jerarquía de botones;
- [ ] existen patrones de formularios;
- [ ] existen estados de feedback;
- [ ] existen patrones de navegación;
- [ ] existen componentes base;
- [ ] existen reglas de accesibilidad;
- [ ] existen reglas responsive;
- [ ] las pantallas utilizan tokens y componentes;
- [ ] no existen patrones visuales duplicados sin justificación.

---

# 57. Principio final

El Design System de TeCuidoApp debe responder a una pregunta sencilla:

> ¿Esta interfaz ayuda al usuario a realizar su trabajo de manera segura, rápida y clara?

Si la respuesta es no, el elemento visual debe reconsiderarse aunque sea técnicamente correcto.

La consistencia, claridad, accesibilidad y confianza tienen prioridad sobre la decoración.

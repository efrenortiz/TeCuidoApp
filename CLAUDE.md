# TeCuidoApp — Claude Code Instructions

## 1. Propósito

Este repositorio contiene **TeCuidoApp**, una aplicación Web para la gestión integral de un consultorio médico especializado en gineco-obstetricia.

La aplicación utiliza principalmente:

- Python
- Django
- PostgreSQL

La arquitectura contempla además, cuando corresponda:

- Redis
- Celery
- almacenamiento privado de documentos
- generación de documentos PDF

---

# 2. Documentos de referencia

Antes de realizar cambios importantes en el código, debes consultar los documentos de referencia del proyecto.

## 2.1 Requerimientos funcionales

Archivo:

```text
requirements.md
```

Este documento es la **fuente principal de verdad funcional** del proyecto. 

Define:

- alcance;
- funcionalidades;
- roles;
- reglas de negocio;
- entidades;
- fases;
- requisitos no funcionales;
- restricciones;
- funcionalidades fuera de alcance.

Cuando exista una duda sobre **qué debe hacer el sistema**, consulta primero `requirements.md`.

---

## 2.2 Arquitectura

Archivo:

```text
docs/architecture.md
```

Este documento define la **arquitectura técnica y las decisiones estructurales del sistema**. 

requirements.md define qué, architecture.md define cómo, y una decisión arquitectónica nunca debería cambiar un requisito funcional sin documentar ese cambio

Define:

- organización de Django apps;
- separación de responsabilidades;
- modelo de identidad;
- relaciones principales;
- principios de seguridad;
- principios de persistencia;
- estrategia de autorización;
- evolución entre fases;
- decisiones arquitectónicas.

Cuando exista una duda sobre **cómo debe construirse técnicamente una funcionalidad**, consulta `docs/architecture.md`.

---

# 3. Jerarquía de decisiones

Utiliza la siguiente jerarquía:

```text
requirements.md
        ↓
docs/architecture.md
        ↓
Código existente
        ↓
Implementación nueva
```

Esto significa:

1. `requirements.md` define **qué necesita el negocio**.
2. `docs/architecture.md` define **cómo debe estructurarse técnicamente**.
3. El código existente debe respetarse siempre que sea compatible con los dos puntos anteriores.
4. La implementación debe seguir ambos documentos.

No debes modificar silenciosamente los requerimientos para adaptarlos al código.

---

# 4. Qué hacer antes de programar

Antes de realizar cambios relevantes:

1. Lee `requirements.md` si la tarea afecta comportamiento funcional.
2. Lee `docs/architecture.md` si la tarea afecta arquitectura, modelos, relaciones, seguridad o estructura del proyecto.
3. Inspecciona el código existente.
4. Determina qué componentes ya existen.
5. Identifica qué debe modificarse y qué debe crearse.
6. Comprueba si existen tests relacionados.
7. Implementa el cambio.
8. Ejecuta los tests correspondientes.
9. Revisa que el cambio no extienda accidentalmente el alcance.

---

# 5. Desarrollo por fases

TeCuidoApp se desarrolla progresivamente.

No debes implementar funcionalidades de fases futuras solamente porque aparezcan mencionadas en `requirements.md`.

## Fase 1 — Fundaciones

Incluye:

- configuración;
- usuarios;
- roles;
- autenticación;
- verificación de email;
- recuperación de contraseña;
- médicos;
- consultorios;
- pacientes;
- responsables;
- invitaciones.

## Fase 2 — Agenda

Contrato funcional completo y aprobado en `docs/phases/phase-2-agenda.md` (2026-09-09) — ese
documento manda en caso de duda.

Incluye:

- disponibilidad por fecha concreta (sin reglas recurrentes ni excepciones);
- creación directa de citas (sin solicitud previa ni confirmación posterior);
- estados de `Appointment`: `SCHEDULED`, `IN_CONSULTATION`, `COMPLETED`, `CANCELLED`,
  `NO_SHOW` — únicamente estos cinco;
- cancelaciones;
- reprogramaciones;
- hold temporal (bloqueo de 15 minutos; no es un estado de `Appointment`);
- prevención de conflictos y de doble reserva concurrente;
- inicio de consulta por el médico asignado.

No incluye confirmaciones ni check-in/sala de espera — no existen en esta fase.

Decisiones de cierre (2026-09-09): un médico puede crear la primera cita de un paciente sin
`DoctorPatientRelationship` previa (esa creación no crea ni modifica la relación — son
operaciones independientes); un médico no puede tener disponibilidad simultánea en dos
consultorios distintos; la agenda usa la zona horaria del `Clinic`; toda operación
administrativa exige `DoctorClinic` válida además del ámbito sobre la clínica.

## Fase 3 — Gestión clínica

Incluye:

- historia clínica;
- consultas;
- evolución;
- diagnósticos;
- tratamientos;
- pronóstico;
- alertas;
- resumen clínico.

## Fase 4 — Documentos

Incluye:

- recetas;
- solicitudes;
- PDFs;
- archivos;
- descargas autorizadas;
- versionado.

## Fase 5 — CareRequest y operación

Incluye:

- CareRequest;
- conversión a cita;
- dashboard médico;
- dashboard paciente/responsable;
- sala de espera;
- búsqueda.

## Fase 6 — Notificaciones y auditoría

Incluye:

- emails;
- recordatorios;
- confirmaciones;
- auditoría;
- consentimientos;
- revisión de seguridad.

Implementa únicamente la fase solicitada.

---

# 6. Reglas arquitectónicas fundamentales

Estas reglas son obligatorias:

### Identidad

Debe existir un único sistema de autenticación.

Separar conceptualmente:

```text
User
Person
Doctor
Patient
Responsible
```

No crear mecanismos de autenticación independientes por rol.

### Pacientes

Un paciente puede relacionarse con múltiples médicos.

### Responsables

Un responsable puede relacionarse con múltiples pacientes.

### Relaciones

Las relaciones relevantes del dominio deben representarse explícitamente.

### Seguridad

La autorización debe validarse siempre en servidor.

No confiar únicamente en:

- ocultar botones;
- URLs difíciles de adivinar;
- IDs secuenciales;
- controles del frontend.

### Información clínica

La información clínica debe tratarse como histórica.

No sobrescribir registros históricos de forma destructiva.

### Datos sensibles

No hardcodear:

- secretos;
- contraseñas;
- tokens;
- credenciales;
- API keys.

Utilizar variables de entorno.

---

# 7. Cambios arquitectónicos

No realices cambios arquitectónicos importantes de forma silenciosa.

Si una implementación requiere cambiar una decisión documentada en:

```text
docs/architecture.md
```

debes:

1. identificar la decisión actual;
2. explicar por qué ya no es adecuada;
3. evaluar alternativas;
4. actualizar la documentación;
5. crear o actualizar un ADR cuando corresponda.

No sacrifiques la arquitectura únicamente para hacer más sencilla una implementación puntual.

---

# 8. Django

Seguir buenas prácticas idiomáticas de Django.

Preferir:

- Django ORM;
- migraciones;
- autenticación nativa;
- permisos;
- transactions;
- management commands cuando correspondan;
- tests de Django.

Evitar:

- SQL manual innecesario;
- lógica compleja dentro de views;
- duplicación;
- apps excesivamente acopladas;
- dependencias innecesarias.

---

# 9. Base de datos

PostgreSQL es la base de datos principal.

Los cambios estructurales deben realizarse mediante migraciones Django.

Para reglas críticas de integridad:

- utilizar constraints;
- foreign keys;
- unique constraints;
- índices;
- transacciones.

No depender exclusivamente de validaciones del frontend o de Python para integridad crítica.

---

# 10. Testing

Todo cambio relevante debe estar respaldado por tests.

Como mínimo, considera:

- casos exitosos;
- casos inválidos;
- permisos;
- casos límite;
- reglas de negocio;
- integridad de datos.

No consideres terminada una funcionalidad crítica hasta que sus tests pasen.

---

# 11. Seguridad

Debido a la naturaleza médica de TeCuidoApp, la seguridad tiene prioridad.

Prestar especial atención a:

- autenticación;
- autorización;
- object-level permissions;
- CSRF;
- sesiones;
- contraseñas;
- tokens;
- archivos privados;
- validación de entradas;
- exposición de información sensible.

Nunca asumir que una URL privada constituye por sí misma un mecanismo de autorización.

---

# 12. Estilo de implementación

Priorizar:

- código claro;
- responsabilidades pequeñas;
- nombres descriptivos;
- modularidad;
- mantenibilidad;
- soluciones sencillas;
- bajo acoplamiento.

Evitar sobreingeniería.

No crear abstracciones o infraestructura que todavía no tengan una necesidad real.

---

# 13. Dependencias

Antes de agregar una dependencia:

1. comprobar si Django/Python ya resuelven el problema;
2. evaluar el costo de mantenimiento;
3. justificar técnicamente la incorporación;
4. mantener el número de dependencias bajo control.

---

# 14. Regla de alcance

No agregues funcionalidades porque:

- "podrían ser útiles";
- "probablemente se necesiten después";
- "es una buena práctica";
- aparecen en una fase posterior.

Implementa únicamente lo requerido para la tarea actual, dejando solamente las bases arquitectónicas necesarias para evolucionar posteriormente.

---

# 15. Revisión antes de terminar

Antes de considerar una tarea terminada, comprueba:

### Funcionalidad

¿Cumple el requerimiento?

### Arquitectura

¿Respeta `docs/architecture.md`?

### Alcance

¿Se mantuvo dentro de la fase actual?

### Seguridad

¿Los accesos están autorizados en servidor?

### Base de datos

¿Existen constraints y migraciones correctas?

### Testing

¿Existen tests adecuados?

### Regresión

¿Los tests existentes siguen pasando?

### Documentación

¿Debe actualizarse algún documento?

---

# 16. Comandos de referencia

Utiliza los comandos apropiados para validar cambios.

Ejemplos:

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

Si el proyecto utiliza otras herramientas definidas en el repositorio, respeta esas convenciones.

---

# 17. Regla para tareas nuevas

Cuando recibas una nueva tarea:

### Si es funcional

Consulta:

```text
requirements.md
```

### Si es arquitectónica

Consulta:

```text
docs/architecture.md
```

### Si afecta ambas

Consulta ambos documentos antes de modificar código.

---

# 18. Principio final

Tu objetivo no es simplemente producir código que funcione.

Tu objetivo es mantener TeCuidoApp como un sistema:

**seguro + mantenible + modular + trazable + extensible**

Debes preservar las decisiones arquitectónicas y las reglas de negocio existentes mientras implementas las nuevas funcionalidades.
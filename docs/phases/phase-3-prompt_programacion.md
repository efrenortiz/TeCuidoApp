# Prompt profesional para Claude — Programación de Fase 3 por etapas
## TeCuidoApp — Implementación controlada después del cierre documental

Actúa como **Tech Lead / Senior Software Engineer / Architect especializado en Django, Python, PostgreSQL y sistemas clínicos**, responsable de implementar la Fase 3 de TeCuidoApp con disciplina de ingeniería, trazabilidad y cero improvisación arquitectónica.

Se adjunta el ZIP más reciente del proyecto TeCuidoApp. **Ese ZIP es la fuente de verdad del estado actual del código y documentación.**

Tu objetivo es **programar la Fase 3 por etapas pequeñas, verificables y reversibles**, respetando estrictamente las decisiones documentales ya cerradas.

---

# 1. Objetivo principal

Implementar la Fase 3 de TeCuidoApp de forma incremental, ejecutando una etapa solamente cuando la anterior haya quedado correctamente validada.

La implementación debe cubrir el núcleo clínico definido en la documentación:

- `ClinicalEncounter`
- `MedicalRecord`
- flujo clínico asociado a `Appointment`
- permisos clínicos
- seguridad y privacidad
- servicios
- API
- UX/UI
- auditoría
- historial
- pruebas

**No intentes implementar toda la Fase 3 de una sola vez.**

Trabaja por etapas.

Cada etapa debe:

1. implementar exclusivamente su alcance;
2. ejecutar las pruebas relevantes;
3. verificar migraciones;
4. revisar que no se rompan funcionalidades previas;
5. producir evidencia del resultado;
6. detenerse si existe un fallo estructural;
7. pasar a la siguiente etapa solo cuando el gate de salida esté cumplido.

---

# 2. Regla fundamental: la documentación ya cerró la arquitectura

No vuelvas a diseñar la arquitectura salvo que encuentres una contradicción real entre el código y una decisión documental.

Antes de modificar código debes estudiar:

## Documentos de Fase 3

- `docs/phases/phase-3-clinical-encounter.md`
- `docs/design/clinical-encounter-workflow.md`
- `docs/design/clinical-encounter-rules.md`
- `docs/design/clinical-encounter-domain.md`
- `docs/design/clinical-record-domain.md`
- `docs/design/clinical-data-model.md`
- `docs/design/clinical-permissions.md`
- `docs/design/clinical-security-and-privacy.md`
- `docs/design/clinical-service-contracts.md`
- `docs/design/clinical-api-contracts.md`
- `docs/phases/phase-3-clinical-ux.md`
- `docs/design/clinical-screens.md`
- `docs/design/clinical-audit-and-history.md`
- `docs/phases/phase-3-testing-strategy.md`

## ADRs

- `docs/adr/ADR-008-clinical-domain-boundary.md`
- `docs/adr/ADR-009-appointment-originates-encounter.md`
- `docs/adr/ADR-010-clinical-encounter-state-and-closure.md`
- `docs/adr/ADR-011-one-medical-record-per-patient.md`
- `docs/adr/ADR-012-explicit-clinical-fields.md`
- `docs/adr/ADR-013-free-text-diagnosis.md`
- `docs/adr/ADR-014-doctor-patient-relationship-independence.md`
- `docs/adr/ADR-015-clinical-authorization-boundary.md`
- `docs/adr/ADR-016-no-reopen-or-delete-clinical-record.md`
- `docs/adr/ADR-017-audit-vs-history.md`
- `docs/adr/ADR-018-clinical-api-services-boundary.md`
- `docs/adr/ADR-019-optimistic-ui-server-source-of-truth.md`

## Documentación transversal

También revisa, según corresponda:

- `requirements.md`
- `docs/architecture.md`
- `CLAUDE.md`
- documentos vigentes de Fase 1;
- documentos vigentes de Fase 2;
- código actual de `appointments`, `patients`, `doctors`, `clinics` y autenticación.

---

# 3. Principios arquitectónicos obligatorios

Mantén como frontera:

```text
UI / API
   ↓
Clinical Service
   ↓
Authorization
   ↓
Transaction
   ↓
Domain invariants
   ↓
ORM / PostgreSQL
```

Reglas:

- No poner lógica clínica crítica directamente en templates.
- No confiar en JavaScript para autorización o estados.
- No duplicar reglas entre HTML y API.
- No acceder directamente al ORM desde la UI.
- No crear lógica paralela para la misma operación.
- No crear entidades duplicadas de `Patient`, `Doctor`, `Clinic` o `Appointment`.
- No convertir `Appointment` en un modelo clínico.
- No introducir una segunda fuente de verdad para estados clínicos.

---

# 4. Stack y restricciones técnicas

Respeta el stack existente.

En particular:

- Python
- Django
- PostgreSQL
- vistas Django y `JsonResponse` cuando ese patrón ya sea el utilizado por Fase 2
- sin Django REST Framework salvo que el propio repositorio ya lo utilice y exista una decisión documental explícita que lo requiera
- no agregar dependencias innecesarias
- no introducir arquitectura distribuida
- no agregar Redis/Celery a Fase 3 salvo que una función concreta de Fase 3 lo requiera y exista justificación documental

No reemplaces la arquitectura existente por un framework distinto.

---

# 5. Decisiones clínicas que NO pueden modificarse

Implementa exactamente estas reglas:

## ClinicalEncounter

```text
Appointment 1 ─── 0..1 ClinicalEncounter
```

- un encounter nace de una Appointment;
- `Appointment` debe estar en estado elegible;
- el médico asignado inicia la consulta;
- el inicio mueve `Appointment → IN_CONSULTATION`;
- se crea o reconoce un único `ClinicalEncounter`;
- `ClinicalEncounter` comienza en `IN_PROGRESS`;
- el segundo intento de iniciar es idempotente;
- puede haber varios `IN_PROGRESS` de un mismo médico para diferentes appointments;
- una consulta interrumpida permanece `IN_PROGRESS`;
- no hay estado `PAUSED`;
- no hay `WAITING`;
- no hay autocierre;
- una vez iniciada la consulta, la cita no puede pasar a `CANCELLED` ni `NO_SHOW`.

## Completion

La finalización debe ser atómica:

```text
ClinicalEncounter IN_PROGRESS
        ↓
ClinicalEncounter COMPLETED

Appointment IN_CONSULTATION
        ↓
Appointment COMPLETED
```

No debe existir persistencia parcial de una de las dos transiciones.

El último contenido enviado con "Completar" debe formar parte de la misma transacción.

Después de `COMPLETED`:

- no editar;
- no reabrir;
- no borrar;
- no versionar en Fase 3.

## Campos mínimos obligatorios

Para completar:

1. motivo de consulta;
2. padecimiento actual;
3. exploración física;
4. evaluación/diagnóstico;
5. plan/indicaciones.

Los campos deben contener contenido clínico real.

No se permiten:

- vacío;
- whitespace;
- N/A;
- no aplica;
- equivalentes obvios;
- variantes de placeholder que intenten evadir validación.

No impongas un mínimo arbitrario de caracteres.

## Diagnóstico

En Fase 3:

- texto libre;
- sin CIE-10;
- sin catálogo diagnóstico;
- sin automatización diagnóstica;
- sin recomendaciones diagnósticas automáticas.

## MedicalRecord

Conceptualmente:

```text
Patient 1 ─── 1 MedicalRecord
```

En persistencia puede existir temporalmente:

```text
Patient 1 ─── 0..1 MedicalRecord
```

solamente por creación lazy.

Una vez creado:

- único;
- no duplicar;
- no cambiar de Patient;
- no borrar funcionalmente.

## DoctorPatientRelationship

Permanece independiente de:

- Appointment;
- ClinicalEncounter;
- MedicalRecord.

Atender una primera consulta no crea automáticamente una relación médico-paciente.

---

# 6. Permisos clínicos

Respeta `clinical-permissions.md`.

No confundas:

```text
puede atender
```

con:

```text
puede leer historial clínico
```

Toda autorización debe comprobarse en servidor.

Nunca dependas solamente de:

- botones ocultos;
- URLs "secretas";
- ids no adivinables;
- frontend.

Debes probar protección contra IDOR y acceso horizontal no autorizado.

---

# 7. Seguridad y privacidad

Respeta `clinical-security-and-privacy.md`.

La información clínica debe tratarse como información sensible.

No expongas innecesariamente:

- datos clínicos en logs;
- payloads completos en errores;
- documentos mediante rutas públicas;
- información clínica mediante endpoints sin autorización.

No agregues infraestructura de seguridad compleja si no es necesaria.

Implementa el nivel mínimo suficiente que ya quedó definido documentalmente.

---

# 8. Auditoría

Respeta:

`clinical-audit-and-history.md`

Mantén:

```text
Clinical History ≠ Audit Trail
```

Registra las operaciones clínicas relevantes que el documento exige.

No uses auditoría como sustituto del historial clínico.

No uses historial como sustituto de auditoría.

---

# 9. Estrategia de implementación por etapas

## ETAPA 0 — Baseline y diagnóstico

Antes de programar:

1. inspecciona estructura del repositorio;
2. identifica apps existentes;
3. revisa modelos relevantes;
4. identifica cómo Fase 2 implementa servicios y API;
5. identifica el patrón de tests;
6. ejecuta:

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

o los comandos equivalentes ya definidos por el proyecto.

Si el baseline falla, **no lo ocultes**.

Determina si el fallo ya existía antes de Fase 3.

### Gate 0

No empezar Etapa 1 hasta conocer:

- estado del baseline;
- tests existentes;
- migraciones;
- arquitectura actual de Agenda;
- puntos de integración.

---

# ETAPA 1 — App `medical_records` y modelo base

Implementa únicamente:

- creación de la app `medical_records`;
- estructura mínima necesaria;
- `MedicalRecord`;
- `ClinicalEncounter`;
- relaciones con entidades canónicas;
- constraints esenciales;
- índices esenciales;
- timestamps;
- migraciones.

No implementes todavía UI completa.

No implementes todavía todos los endpoints.

### Validar

- `Patient 1 ─── 1 MedicalRecord` conceptual;
- unicidad del expediente;
- `Appointment 1 ─── 0..1 ClinicalEncounter`;
- `appointment` obligatorio;
- no duplicación;
- estados válidos;
- campos obligatorios según modelo;
- integridad referencial.

### Gate 1

Debe pasar:

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

más tests específicos del modelo.

---

# ETAPA 2 — Domain Services

Implementa únicamente los servicios necesarios:

- `start_encounter`;
- `save_encounter`;
- `complete_encounter`;
- lectura de encounter;
- lectura de expediente/historial;
- actualización de datos longitudinales cuando corresponda al contrato.

Aplica:

- autorización;
- transacciones;
- invariantes;
- idempotencia;
- manejo determinista de errores.

No agregues lógica equivalente en views.

### Gate 2

Cobertura mínima:

- inicio normal;
- doble inicio;
- inicio no autorizado;
- guardado parcial;
- validación de contenido;
- completion;
- double completion;
- save after completion;
- appointment/encounter inconsistency;
- atomicidad.

---

# ETAPA 3 — Concurrencia e integridad transaccional

Esta etapa es obligatoria y no debe saltarse.

Implementa y valida:

- carrera de dos inicios;
- carrera de dos completion;
- save concurrente;
- save vs completion;
- request posterior a completion;
- constraints de unicidad;
- locking cuando corresponda.

No te limites a tests secuenciales.

Usa pruebas concurrentes reales o mecanismos equivalentes apropiados para Django/PostgreSQL.

### Gate 3

Debe demostrarse que nunca queda persistido:

```text
ClinicalEncounter COMPLETED
+
Appointment IN_CONSULTATION
```

ni:

```text
Appointment IN_CONSULTATION
+
ClinicalEncounter inexistente
```

cuando la operación haya sido procesada como inicio clínico válido.

---

# ETAPA 4 — API

Implementa solamente los endpoints definidos por:

`clinical-api-contracts.md`

Respeta:

- nombres;
- métodos;
- payloads;
- errores;
- códigos HTTP;
- autenticación;
- autorización;
- idempotencia;
- semántica de 404;
- conflictos;
- respuestas JSON.

No inventes endpoints CRUD.

No agregues endpoints porque parezcan convenientes.

La API debe delegar a los servicios.

### Gate 4

Probar:

- happy path;
- validación;
- permisos;
- IDOR;
- estados inválidos;
- concurrencia;
- errores;
- idempotencia;
- shape de respuestas;
- no fuga de información clínica.

---

# ETAPA 5 — UX/UI y pantallas

Implementa las pantallas definidas en:

- `phase-3-clinical-ux.md`
- `clinical-screens.md`

Incluye como mínimo:

1. contexto desde Agenda;
2. inicio de consulta;
3. consulta `IN_PROGRESS`;
4. guardado parcial;
5. completion;
6. expediente;
7. historial;
8. detalle histórico.

La UI debe:

- reflejar el estado confirmado por servidor;
- no ser autoridad de seguridad;
- informar guardados exitosos;
- informar errores;
- impedir visualmente acciones inválidas;
- seguir funcionando con responsive básico;
- respetar accesibilidad razonable.

### Gate 5

Validar manualmente:

- inicio;
- captura;
- guardado;
- interrupción;
- reanudación;
- completion;
- pantalla bloqueada después de completion;
- lectura histórica;
- permisos visibles y efectivos.

---

# ETAPA 6 — Auditoría, seguridad y endurecimiento

Completa la implementación de:

- auditoría;
- controles de seguridad;
- privacidad;
- protección de logs;
- control de acceso a objetos;
- manejo seguro de errores;
- protección de recursos clínicos.

Verifica que estas capacidades no hayan quedado únicamente en la documentación.

### Gate 6

Debe existir evidencia de:

- operaciones auditadas;
- accesos no autorizados rechazados;
- ausencia de IDOR;
- ausencia de documentos públicos;
- ausencia de información clínica innecesariamente expuesta en logs o respuestas de error.

---

# ETAPA 7 — Suite de pruebas y cierre

Ejecuta toda la estrategia de:

`phase-3-testing-strategy.md`

Debe incluir:

- unit tests;
- domain tests;
- service tests;
- database tests;
- transactional tests;
- concurrency tests;
- permission tests;
- API tests;
- UI tests;
- regression tests de Fase 2;
- smoke tests;
- `manage.py check`;
- migraciones.

No declares Fase 3 completada por una sola prueba de navegador.

---

# 10. Regresión obligatoria de Fase 2

Después de cada etapa que toque `appointments`, permisos compartidos o navegación relevante, ejecuta las pruebas de regresión de Fase 2.

Especialmente:

- crear cita;
- reservar;
- reprogramar;
- cancelar;
- no-show;
- permisos existentes;
- disponibilidad;
- invariantes de Agenda.

No romper Agenda para implementar atención clínica.

---

# 11. Manejo de contradicciones

Si encuentras una contradicción real:

**NO decidas silenciosamente.**

Haz lo siguiente:

1. identifica el documento;
2. identifica la decisión;
3. muestra la contradicción;
4. explica cuál fuente tiene precedencia;
5. propone la solución mínima;
6. detén la etapa afectada si la contradicción puede alterar arquitectura o datos.

No cambies una decisión cerrada solo porque otra opción parezca más elegante.

---

# 12. Regla contra el scope creep

No implementes en Fase 3:

- CIE-10;
- catálogos diagnósticos;
- IA diagnóstica;
- recomendaciones automáticas;
- ginecología especializada;
- obstetricia especializada;
- colposcopia especializada;
- menopausia especializada;
- recetas avanzadas;
- órdenes de estudios avanzadas;
- documentos clínicos avanzados;
- notificaciones complejas;
- funcionalidades de Fase 4 o Fase 5.

Si detectas que una necesidad futura requiere una extensión, deja la interfaz preparada únicamente cuando eso no aumente innecesariamente la complejidad de Fase 3.

---

# 13. Reglas de calidad del código

Todo código nuevo debe:

- seguir el estilo existente;
- ser pequeño y legible;
- evitar abstracciones prematuras;
- evitar duplicación;
- tener nombres consistentes con los documentos;
- incluir pruebas para reglas nuevas;
- respetar transacciones;
- usar errores de dominio previsibles;
- evitar efectos secundarios ocultos.

No refactorices grandes partes del sistema sin necesidad.

No reescribas Fase 2.

No introduzcas patrones arquitectónicos nuevos sin justificarlo.

---

# 14. Entregable obligatorio al terminar cada etapa

Para cada etapa entrega un resumen como:

```text
ETAPA X — <nombre>

Implementado:
- ...

Archivos creados:
- ...

Archivos modificados:
- ...

Decisiones aplicadas:
- ...

Tests ejecutados:
- ...

Resultado:
PASS / FAIL

Regresión Fase 2:
PASS / FAIL / N/A

Migraciones:
PASS / FAIL / N/A

Hallazgos:
- ...

Riesgos:
- ...

Gate:
OPEN / CLOSED
```

Si el gate es `FAIL`, **no avances a la siguiente etapa**.

---

# 15. Regla especial para migraciones

Antes de ejecutar migraciones:

1. revisar modelos;
2. revisar constraints;
3. revisar índices;
4. revisar relaciones;
5. revisar compatibilidad con datos existentes.

Nunca ejecutes una migración destructiva sin justificación explícita.

No elimines ni transformes datos existentes de Fase 1/2 de forma silenciosa.

---

# 16. Regla especial para datos clínicos

La información clínica debe considerarse histórica una vez persistida.

No sobrescribas información histórica para simular una modificación retrospectiva.

No borres encuentros clínicos.

No borres expedientes.

No agregues versionado salvo decisión explícita futura.

---

# 17. Regla especial para estado

La UI puede mantener estado temporal.

Solo el servidor y la base de datos determinan:

- estado de Appointment;
- estado de ClinicalEncounter;
- existencia del expediente;
- autorización.

Nunca confíes en:

```text
hidden fields
disabled buttons
frontend state
URL obscurity
```

como controles de seguridad.

---

# 18. Criterio para declarar Fase 3 implementada

Solo puedes declarar:

```text
PHASE 3 — IMPLEMENTED
```

cuando:

- las etapas 1–7 hayan pasado sus gates;
- tests completos pasen;
- regresión de Fase 2 pase;
- migraciones estén limpias;
- no existan hallazgos HIGH o CRITICAL abiertos;
- las invariantes clínicas estén verificadas;
- permisos estén verificados;
- auditoría esté verificada;
- concurrencia esté verificada;
- la UI corresponda a los contratos;
- no queden decisiones arquitectónicas importantes pendientes.

---

# 19. Comportamiento inicial obligatorio

Comienza por **ETAPA 0**.

No programes todavía.

Primero:

1. inspecciona el ZIP;
2. revisa los documentos;
3. ejecuta el baseline disponible;
4. identifica el estado actual;
5. propone el plan concreto de ETAPA 0;
6. ejecuta ETAPA 0;
7. reporta el gate.

**No avances automáticamente a ETAPA 1 en la misma respuesta si ETAPA 0 descubre problemas que deban resolverse primero.**

Tu prioridad es mantener el proyecto correcto y trazable, no avanzar rápidamente.

---

# 20. Principio final

Cuando exista una elección entre:

- una solución elegante pero compleja;
- una solución ligeramente menos sofisticada pero consistente con el proyecto, simple, segura y fácil de probar;

elige la segunda.

La Fase 3 debe terminar siendo:

```text
simple
+
consistente
+
segura
+
transaccional
+
probable
+
mantenible
```

sin introducir complejidad que no haya sido justificada.

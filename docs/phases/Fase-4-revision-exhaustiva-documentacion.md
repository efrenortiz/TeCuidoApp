# TeCuidoApp — Revisión exhaustiva, corrección y cierre documental de Fase 4

## Objetivo

Actúa como **Arquitecto de Software Senior, Tech Lead, revisor de arquitectura y especialista en sistemas clínicos**, con experiencia en:

- Django / Python / PostgreSQL;
- diseño orientado a dominio;
- sistemas clínicos y expedientes médicos;
- seguridad y privacidad de información clínica;
- autorización por objeto;
- auditoría y trazabilidad;
- APIs REST;
- concurrencia e integridad transaccional;
- UX/UI;
- documentación arquitectónica y ADRs.

Tu misión es realizar una **auditoría documental exhaustiva de Fase 4**, corregir las inconsistencias o ambigüedades que puedan resolverse de manera inequívoca, y producir un **reporte final en Markdown** con todo el proceso realizado.

## REGLA FUNDAMENTAL

**NO CONSTRUIR CÓDIGO.**

Esta actividad es exclusivamente documental y arquitectónica.

No debes:

- crear modelos Django;
- crear migraciones;
- crear servicios;
- crear endpoints;
- modificar Python;
- modificar JavaScript;
- modificar HTML;
- modificar CSS;
- agregar dependencias;
- ejecutar una implementación parcial.

El objetivo es dejar la especificación de Fase 4 suficientemente cerrada para que, posteriormente, la programación pueda comenzar sin decisiones arquitectónicas improvisadas.

---

# 1. Estado de partida

Fase 3 ya fue cerrada formalmente.

Las decisiones de Fase 3 son una fuente normativa para Fase 4 y **no deben ser reabiertas** salvo que detectes una contradicción real.

En particular, deben conservarse:

- separación entre Agenda y dominio clínico;
- `Appointment 1 ─── 0..1 ClinicalEncounter`;
- `ClinicalEncounter` con estados `IN_PROGRESS` y `COMPLETED`;
- cierre atómico de Encounter + Appointment;
- inmutabilidad posterior a `COMPLETED`;
- ausencia de DELETE funcional de información clínica;
- `Patient` como entidad canónica;
- `MedicalRecord` único por paciente;
- independencia de `DoctorPatientRelationship`;
- autorización por objeto;
- diferencia entre capacidad de atender y capacidad de leer historial;
- `Clinical History ≠ Audit Trail`;
- servicios como frontera de negocio;
- servidor/base de datos como fuente de verdad;
- simplicidad arquitectónica;
- no introducir funcionalidades futuras sin justificación.

---

# 2. Documentos de Fase 4 que debes revisar

Revisa todos los documentos generados para Fase 4, incluyendo como mínimo:

## Contrato de Fase

`docs/phases/phase-4-documents.md`

## Workflow

`docs/design/phase-4-documents-workflow.md`

## Reglas

`docs/design/phase-4-documents-rules.md`

## Dominios

`docs/design/clinical-document-domain.md`

`docs/design/prescription-domain.md`

`docs/design/study-order-domain.md`

## Modelo de datos

`docs/design/clinical-documents-data-model.md`

## Permisos

`docs/design/phase-4-permissions.md`

## Seguridad y privacidad

`docs/design/phase-4-security-and-privacy.md`

## Servicios

`docs/design/phase-4-service-contracts.md`

## API

`docs/design/phase-4-api-contracts.md`

## UX

`docs/design/phase-4-ux.md`

## Pantallas

`docs/design/phase-4-screens.md`

## Auditoría e historial

`docs/design/phase-4-audit-and-history.md`

## Testing

`docs/phases/phase-4-testing-strategy.md`

## Índice

`docs/phases/phase-4-documentation-index.md`

## ADRs

Revisa todos los ADRs de Fase 4, especialmente:

- `ADR-021`
- `ADR-022`
- `ADR-023`
- `ADR-024`
- `ADR-025`
- `ADR-026`
- `ADR-027`
- `ADR-028`
- `ADR-029`
- `ADR-030`

También revisa:

- `README.md`
- `architecture.md`
- `requirements.md`
- `CLAUDE.md`
- documentación vigente de Fase 1;
- documentación vigente de Fase 2;
- documentación cerrada de Fase 3.

---

# 3. Jerarquía de fuentes de verdad

Cuando encuentres una contradicción, utiliza esta prioridad:

1. decisiones explícitamente cerradas previamente;
2. ADRs vigentes;
3. contrato de Fase 4;
4. workflow;
5. rules;
6. domain;
7. data model;
8. permissions/security;
9. services;
10. API;
11. UX/screens;
12. audit/testing;
13. requirements históricos;
14. inferencias.

No cambies silenciosamente una decisión cerrada.

Si una decisión previa debe cambiar para resolver una contradicción real, primero documenta:

- qué decisión está en conflicto;
- por qué existe el conflicto;
- impacto;
- alternativa;
- recomendación.

No realices el cambio silenciosamente.

---

# 4. Principio de simplicidad

La prioridad arquitectónica es:

1. consistencia con fases anteriores;
2. seguridad;
3. integridad de datos;
4. mantenibilidad;
5. facilidad de prueba;
6. simplicidad.

Cuando existan varias soluciones válidas, selecciona la **más simple que cumpla las garantías necesarias**.

Evita:

- abstracciones prematuras;
- entidades genéricas innecesarias;
- tablas redundantes;
- JSON como solución universal;
- catálogos prematuros;
- estados excesivos;
- workflows complejos;
- infraestructura innecesaria;
- microservicios;
- colas;
- Event Sourcing;
- sistemas documentales tipo Drive;
- motores externos de búsqueda;
- firmas electrónicas avanzadas;
- funcionalidades futuras.

---

# 5. Alcance exacto de Fase 4 que debe respetarse

La revisión debe comprobar que Fase 4 conserve como núcleo:

- `ClinicalDocument`;
- `Prescription`;
- `PrescriptionItem`;
- `StudyOrder`;
- `StudyOrderItem`;
- archivos clínicos asociados;
- generación de PDF;
- almacenamiento privado;
- lectura/descarga autorizada;
- versionado;
- anulación lógica;
- auditoría.

Y que mantenga fuera de alcance:

- CIE-10;
- catálogos diagnósticos;
- resultados de laboratorio;
- gestión avanzada de resultados;
- firma electrónica;
- CareRequest;
- notificaciones complejas;
- funcionalidades de Fase 5;
- funcionalidades de Fase 6;
- gestión documental genérica no clínica.

Si un documento contradice este límite, repórtalo y corrígelo cuando sea inequívoco.

---

# 6. Revisión conceptual profunda

Comprueba que exista una definición única y consistente de:

## ClinicalDocument

Debe quedar claro:

- qué representa;
- qué no representa;
- relación con el archivo físico;
- origen `UPLOADED` / `GENERATED`;
- relación con Patient;
- relación opcional con Appointment;
- relación opcional con ClinicalEncounter;
- relación con Prescription / StudyOrder cuando corresponda;
- inmutabilidad;
- versionado;
- anulación.

## Prescription

Debe quedar claro:

- relación obligatoria con Patient;
- relación con ClinicalEncounter;
- autoría;
- items;
- emisión;
- anulación;
- versionado;
- PDF;
- inmutabilidad.

## StudyOrder

Debe quedar claro:

- relación con Patient;
- relación con ClinicalEncounter;
- items;
- tipo de estudio;
- emisión;
- anulación;
- versionado;
- PDF;
- diferencia respecto de resultados.

---

# 7. Revisión de relaciones

Verifica que no existan relaciones redundantes o ambiguas.

Especialmente:

```text
Patient
   ├── MedicalRecord
   ├── ClinicalEncounter
   ├── Prescription
   ├── StudyOrder
   └── ClinicalDocument
```

Y comprueba que:

- no se duplique `Patient`;
- no se duplique `MedicalRecord`;
- no se cree una segunda relación equivalente a `ClinicalEncounter`;
- no se añada una FK redundante a `MedicalRecord` cuando `Patient` ya determina el expediente;
- no se rompa la independencia de `DoctorPatientRelationship`.

---

# 8. Revisión de inmutabilidad y versionado

Éste es uno de los puntos más importantes.

Determina con precisión:

- qué registros son inmutables;
- cuándo se vuelven inmutables;
- cómo se corrigen errores;
- qué significa "nueva versión";
- cómo se relaciona una versión con la anterior;
- cuál es la versión actual;
- si una versión anulada puede generar otra;
- qué archivo físico corresponde a cada versión;
- si el documento anterior permanece accesible.

Debe quedar prohibido sobrescribir silenciosamente un documento clínico emitido.

---

# 9. Revisión de DELETE / VOIDED

Comprueba que todos los documentos sean coherentes respecto a:

- borrado;
- anulación;
- inactivación;
- conservación del histórico.

La regla recomendada es:

```text
DELETE funcional → NO
VOIDED / inactivación → SÍ
```

pero debe quedar definido exactamente:

- quién puede anular;
- cuándo puede hacerlo;
- si requiere motivo;
- qué ocurre con el PDF;
- qué ocurre con versiones anteriores;
- qué puede seguir viendo el paciente;
- qué queda registrado en auditoría.

---

# 10. Revisión de archivos físicos

Comprueba la separación:

```text
ClinicalDocument
        ↓
metadatos clínicos
        +
archivo físico privado
```

Verifica:

- almacenamiento privado;
- nunca `static/`;
- no URL pública;
- filename original separado del nombre físico;
- MIME validado;
- tamaño limitado;
- path seguro;
- descarga autorizada;
- no exposición directa del storage;
- eliminación física diferenciada de anulación lógica.

No introduzcas almacenamiento externo complejo salvo necesidad explícita.

---

# 11. PDFs

Comprueba coherencia en:

- server-side;
- síncrono;
- determinista;
- generación por tipo documental;
- contenido histórico;
- no regeneración destructiva;
- versión;
- fecha/hora;
- clínica;
- autoría;
- impresión.

La transacción de BD no debe presentarse falsamente como una transacción atómica del sistema de archivos.

Si existe un flujo:

```text
DB transaction
+
file generation
```

debe definirse correctamente cómo se maneja un fallo entre ambos.

---

# 12. Recetas

Comprueba:

### Prescription

- estado;
- autor;
- paciente;
- encounter;
- fecha;
- items.

### PrescriptionItem

Debe existir una definición clara y mínima de:

- medicamento;
- presentación opcional;
- dosis;
- unidad;
- vía;
- frecuencia;
- duración;
- indicaciones.

No introduzcas catálogo farmacológico obligatorio.

No introduzcas reglas clínicas de prescripción que no hayan sido requeridas.

---

# 13. StudyOrder

Comprueba:

### StudyOrder

- estado;
- autor;
- paciente;
- encounter;
- fecha;
- motivo/indicación;
- items.

### StudyOrderItem

Debe existir estructura suficiente pero simple para:

- estudio;
- tipo;
- indicación;
- observaciones.

No implementar resultados.

---

# 14. Permisos

Realiza una matriz completa:

| Acción | Médico asignado | Médico con relación activa | Paciente | Responsable | Admin |
|---|---|---|---|---|---|

Como mínimo para:

- ver documento;
- descargar;
- crear;
- emitir;
- versionar;
- anular;
- ver receta;
- ver StudyOrder;
- cargar archivo;
- consultar historial.

Comprueba que no exista una regla diferente en cada documento.

---

# 15. Auditoría

Comprueba que todas las acciones sensibles tengan una política uniforme:

- CREATE;
- READ;
- DOWNLOAD;
- VERSION;
- VOID;
- ISSUE;
- accesos administrativos.

No guardes binarios dentro del audit trail.

Debe existir actor para operaciones humanas autenticadas.

No utilizar `UNKNOWN`, `NULL` o actor artificial para ocultar problemas de propagación de identidad.

---

# 16. Concurrencia e idempotencia

Simula conceptualmente:

1. doble submit de receta;
2. doble submit de StudyOrder;
3. dos versiones simultáneas;
4. versionado mientras otro usuario visualiza;
5. doble anulación;
6. descarga durante anulación;
7. emisión mientras cambia autorización;
8. generación PDF duplicada.

Cada escenario debe tener una respuesta definida.

---

# 17. API

Verifica consistencia entre:

- nombres de endpoints;
- métodos HTTP;
- payloads;
- responses;
- errores;
- códigos HTTP;
- permisos;
- idempotencia;
- descargas;
- PDFs;
- versionado;
- anulación.

No debe haber endpoints documentados que contradigan los servicios.

No debe haber operaciones importantes accesibles solamente mediante una operación genérica no documentada.

---

# 18. Servicios

Comprueba:

```text
UI / API
    ↓
Service
    ↓
Authorization
    ↓
Transaction
    ↓
ORM / PostgreSQL
```

Verifica que:

- la lógica clínica esté en servicios;
- la autorización no dependa de la UI;
- la API no implemente reglas clínicas;
- los servicios tengan contratos deterministas;
- los errores sean coherentes.

---

# 19. UX y pantallas

Comprueba que UX/Screens reflejen exactamente:

- creación;
- emisión;
- guardado;
- anulación;
- versionado;
- visualización;
- descarga;
- errores;
- estados.

Ningún botón debe representar una operación que el backend no permite.

Ninguna operación crítica definida por backend debe quedar ambigua en UI.

---

# 20. Testing

Verifica que `phase-4-testing-strategy.md` pueda validar realmente todo lo definido.

Debe existir cobertura conceptual para:

- modelos;
- constraints;
- servicios;
- permisos;
- storage;
- PDFs;
- versionado;
- VOIDED;
- auditoría;
- idempotencia;
- concurrencia;
- API;
- UI;
- regresión de Fases 1–3.

---

# 21. Revisión de coherencia entre todos los documentos

Construye una matriz:

| Decisión | Contract | Workflow | Rules | Domain | Data | Permissions | Security | Services | API | UX | Screens | Audit | Testing | ADR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Usa:

- `✓` consistente;
- `⚠` inconsistente;
- `—` no aplica.

Haz esto para las decisiones críticas:

- alcance;
- entidades;
- relaciones;
- versionado;
- inmutabilidad;
- VOIDED;
- almacenamiento;
- PDF;
- permisos;
- auditoría;
- concurrencia;
- API;
- UX.

---

# 22. Detección de ambigüedades

Busca frases como:

- "según se decida";
- "por definir";
- "puede";
- "opcional";
- "según corresponda";
- "etc.";
- "más adelante";
- "si aplica";

y determina si realmente representan una decisión abierta.

No todas las palabras "opcional" son un problema. Solo reporta una ambigüedad cuando un desarrollador pueda implementar dos comportamientos distintos.

---

# 23. Compatibilidad con fases anteriores

Comprueba especialmente que Fase 4 no rompa conceptos ya definidos en Fases 1–3.

Revisa:

- `Patient`;
- `Doctor`;
- `Clinic`;
- `Appointment`;
- `ClinicalEncounter`;
- `MedicalRecord`;
- `DoctorPatientRelationship`;
- autorización;
- timestamps;
- auditoría;
- seguridad.

No cambies una regla de Fase 3 solo para hacer Fase 4 más cómoda.

---

# 24. Detección de scope creep

Identifica cualquier documento que accidentalmente introduzca:

- Fase 5;
- Fase 6;
- resultados;
- CareRequest;
- notificaciones;
- catálogos;
- firma electrónica;
- funcionalidades clínicas avanzadas.

Clasifícalo y elimínalo de Fase 4 cuando corresponda.

---

# 25. Clasificación de hallazgos

Clasifica:

### CRITICAL
Compromete integridad, seguridad o una decisión arquitectónica esencial.

### HIGH
Puede generar implementaciones incompatibles o un fallo funcional importante.

### MEDIUM
Ambigüedad o inconsistencia relevante que conviene cerrar antes de programar.

### LOW
Problema editorial o menor.

### INFO
Mejora opcional.

---

# 26. Corrección de documentos

Después de realizar la auditoría:

Puedes modificar los documentos cuando:

- el problema sea inequívoco;
- la corrección no cambie una decisión arquitectónica cerrada;
- la modificación aumente consistencia;
- la modificación sea compatible con Fases 1–3.

Ejemplos de cambios permitidos:

- corregir nombres;
- corregir rutas;
- corregir referencias cruzadas;
- eliminar contradicciones editoriales;
- normalizar definiciones;
- reemplazar decisiones obsoletas;
- aclarar una decisión que ya está implícitamente cerrada.

---

# 27. Decisiones que requieren revisión humana

Si encuentras una decisión que no puede resolverse inequívocamente, **NO la decidas silenciosamente**.

Para cada una genera:

```text
DECISIÓN PENDIENTE D-XXX

Pregunta:
Contexto:
Opciones:
Opción recomendada:
Motivo:
Documentos afectados:
```

La opción recomendada debe favorecer:

- simplicidad;
- consistencia;
- seguridad;
- menor número de entidades;
- menor número de estados;
- facilidad de pruebas;
- compatibilidad con fases anteriores.

---

# 28. Segunda auditoría obligatoria

Después de corregir los documentos:

**vuelve a auditar todo el conjunto desde cero.**

No asumas que la primera revisión garantiza que las correcciones sean correctas.

Comprueba:

- consistencia;
- referencias;
- nombres;
- rutas;
- relaciones;
- permisos;
- seguridad;
- API;
- testing;
- ADRs.

La segunda auditoría debe ser independiente de la primera.

---

# 29. No construir código

Durante todo el proceso:

**NO PROGRAMAR.**

No ejecutar desarrollo de:

- modelos;
- migraciones;
- APIs;
- servicios;
- UI;
- almacenamiento;
- PDFs.

La única excepción sería inspeccionar código existente para comprobar si alguna decisión documental contradice una implementación previa de Fase 3. Incluso en ese caso, no debes modificar el código.

---

# 30. Reporte final requerido

Genera:

```text
docs/phases/phase-4-documentation-review-report.md
```

El reporte debe contener:

# 1. Resumen ejecutivo

- objetivo;
- documentos revisados;
- resultado general.

# 2. Proceso realizado

Explica brevemente:

- análisis inicial;
- revisión cruzada;
- revisión contra fases anteriores;
- correcciones;
- segunda auditoría.

# 3. Hallazgos iniciales

Tabla:

| ID | Severidad | Documento | Problema | Impacto | Solución |
|---|---|---|---|---|---|

# 4. Decisiones tomadas

Lista de decisiones cerradas durante la revisión.

Para cada una:

- decisión;
- motivo;
- documentos afectados.

# 5. Hallazgos pendientes

Separar:

- CRITICAL;
- HIGH;
- MEDIUM;
- LOW;
- INFO.

Si no quedan pendientes, decir explícitamente:

```text
No quedan hallazgos pendientes.
```

# 6. Documentos modificados

Tabla:

| Documento | Modificación | Motivo |
|---|---|---|

# 7. Matriz de consistencia final

Incluir la matriz completa de decisiones críticas.

# 8. Compatibilidad con Fases 1–3

Indicar explícitamente si se mantuvo la compatibilidad.

# 9. Scope control

Confirmar que Fase 4 no absorbió funcionalidad de fases posteriores.

# 10. Decisiones humanas requeridas

Si no existen:

```text
No se requieren decisiones humanas adicionales.
```

# 11. Resultado final

Usa exactamente:

```text
PHASE 4 DOCUMENTATION REVIEW

CRITICAL: X
HIGH: X
MEDIUM: X
LOW: X
INFO: X

Contradicciones críticas: X
Decisiones pendientes: X

Consistencia documental:
PASS / FAIL

Consistencia con Fases 1–3:
PASS / FAIL

Scope control:
PASS / FAIL

Documentación:
READY / NOT READY
```

Si todo está cerrado:

```text
READY FOR PHASE 4 IMPLEMENTATION
```

Si existen decisiones relevantes pendientes:

```text
NOT READY FOR PHASE 4 IMPLEMENTATION
```

---

# 31. Entregable adicional

Al finalizar, entrega también un resumen breve en la respuesta principal con:

- cuántos documentos revisaste;
- cuántos hallazgos encontraste;
- cuántos corregiste;
- cuántos quedaron pendientes;
- si la documentación está lista para comenzar programación.

---

# Regla final

Tu objetivo no es validar que los documentos "se vean bien".

Tu objetivo es comprobar que:

```text
Contrato
   =
Workflow
   =
Rules
   =
Domain
   =
Data
   =
Permissions
   =
Security
   =
Services
   =
API
   =
UX
   =
Screens
   =
Audit
   =
Testing
   =
ADRs
```

y que todos ellos cuenten **la misma historia arquitectónica**.

Debes buscar activamente contradicciones, decisiones implícitas, dependencias ocultas y complejidad innecesaria.

No seas complaciente.

**No programes nada.**

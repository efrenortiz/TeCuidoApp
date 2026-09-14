# TeCuidoApp — Implementación de Fase 4 por etapas

## Rol

Actúa como **Tech Lead, Senior Software Engineer y responsable de la implementación de Fase 4 de TeCuidoApp**, con experiencia en Django/Python/PostgreSQL, sistemas clínicos, seguridad, auditoría, APIs y aplicaciones web.

La documentación de Fase 4 ya fue revisada y cerrada documentalmente. El reporte:

`docs/phases/phase-4-documentation-review-report.md`

establece que la documentación está:

- consistente;
- compatible con Fases 1–3;
- sin decisiones pendientes;
- sin hallazgos CRITICAL/HIGH/MEDIUM/LOW abiertos;
- dentro del alcance definido;
- `READY FOR PHASE 4 IMPLEMENTATION`.

Por lo tanto, **ahora sí debe comenzar la programación de Fase 4**.

---

# 1. Objetivo general

Implementar Fase 4 completa de forma:

- incremental;
- verificable;
- trazable;
- segura;
- compatible con Fases 1–3;
- simple;
- fácil de probar;
- sin introducir complejidad innecesaria.

La implementación debe realizarse **por etapas independientes**, con un gate de salida al final de cada una.

No debes intentar desarrollar toda la fase de una sola vez.

---

# 2. Documentación normativa

Antes de escribir código debes estudiar:

## Contrato de fase

`docs/phases/phase-4-documents.md`

## Workflow

`docs/design/phase-4-documents-workflow.md`

## Rules

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

## Auditoría

`docs/design/phase-4-audit-and-history.md`

## Testing

`docs/phases/phase-4-testing-strategy.md`

## Índice documental

`docs/phases/phase-4-documentation-index.md`

## ADRs

Revisa todos los ADRs de Fase 4:

- ADR-021
- ADR-022
- ADR-023
- ADR-024
- ADR-025
- ADR-026
- ADR-027
- ADR-028
- ADR-029
- ADR-030

También revisa:

- `requirements.md`
- `architecture.md`
- `README.md`
- `CLAUDE.md`
- Fases 1–3 vigentes y cerradas.

---

# 3. Regla fundamental: documentación antes de código

No programes una funcionalidad basándote solamente en una interpretación propia.

Para cada capacidad debes identificar:

1. documento normativo;
2. regla aplicable;
3. servicio correspondiente;
4. endpoint correspondiente;
5. modelo involucrado;
6. permisos;
7. auditoría;
8. pruebas.

Si no puedes determinarlo, detente en esa parte y documenta el gap.

---

# 4. Principios arquitectónicos obligatorios

Conserva la frontera:

```text
UI / API
   ↓
Domain Service
   ↓
Authorization
   ↓
Transaction
   ↓
ORM / PostgreSQL
```

No:

- pongas lógica de negocio clínica crítica en templates;
- confíes en el frontend para seguridad;
- dupliques reglas entre views/services;
- accedas al ORM desde la UI;
- crees CRUD genérico innecesario;
- dupliques `Patient`, `Doctor`, `Clinic`, `Appointment`, `ClinicalEncounter` o `MedicalRecord`.

---

# 5. Restricciones de simplicidad

Prioriza:

1. reutilización de patrones existentes;
2. mínimo número de entidades;
3. mínimo número de estados;
4. mínima infraestructura;
5. facilidad de pruebas;
6. consistencia con fases anteriores.

No introduzcas sin una necesidad explícita:

- microservicios;
- Redis;
- Celery;
- colas;
- Event Sourcing;
- nuevos frameworks;
- motores de almacenamiento externos complejos;
- motores de búsqueda;
- sistemas documentales genéricos tipo Drive.

Respeta el stack actual.

---

# 6. Alcance de Fase 4

Implementa únicamente:

- `ClinicalDocument`;
- `Prescription`;
- `PrescriptionItem`;
- `StudyOrder`;
- `StudyOrderItem`;
- archivos clínicos;
- generación de PDF;
- almacenamiento privado;
- lectura/descarga autorizada;
- versionado;
- anulación lógica;
- auditoría.

Mantén fuera:

- CIE-10;
- catálogos diagnósticos;
- resultados de laboratorio;
- gestión avanzada de resultados;
- firma electrónica;
- `CareRequest`;
- notificaciones complejas;
- funcionalidades de Fase 5;
- funcionalidades de Fase 6;
- gestor documental genérico no clínico.

---

# 7. Reglas clínicas y documentales que no pueden romperse

## ClinicalDocument

Debe estar ligado a un `Patient`.

Puede tener referencias clínicas adicionales según el contrato.

No debe convertirse en un contenedor genérico de cualquier archivo.

## Prescription

Debe tener:

- paciente;
- contexto clínico;
- autor;
- items;
- emisión;
- PDF/documento cuando corresponda.

Una receta emitida es histórica.

## StudyOrder

Debe tener:

- paciente;
- contexto clínico;
- autor;
- items;
- tipo;
- indicación/observaciones;
- emisión;
- PDF/documento cuando corresponda.

No captura resultados en Fase 4.

## Inmutabilidad

Una vez emitido un documento clínico:

```text
UPDATE destructivo → NO
DELETE funcional → NO
```

Las correcciones deben usar versionado cuando el contrato lo determine.

## VOIDED

La anulación debe preservar la historia y quedar auditada.

## Archivos

Los archivos clínicos son privados.

Nunca deben exponerse mediante una URL pública sin autorización.

---

# 8. Compatibilidad obligatoria con Fase 3

No romper:

- Agenda;
- Appointment;
- ClinicalEncounter;
- MedicalRecord;
- permisos existentes;
- seguridad;
- auditoría;
- timestamps;
- navegación.

No cambies el comportamiento de Fase 3 solo para facilitar Fase 4.

Si necesitas modificar un componente de Fase 3, demuestra por qué es estrictamente necesario y verifica regresión completa.

---

# 9. Plan obligatorio de implementación por etapas

## ETAPA 0 — Baseline

Antes de modificar código:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py test
```

Registra:

- cantidad de tests;
- resultado;
- migraciones;
- warnings relevantes;
- estado del repositorio.

### Gate 0

No continuar si el baseline presenta fallos que no estén explicados.

---

# ETAPA 1 — Apps y modelo de datos

Implementa:

- apps necesarias;
- modelos;
- relaciones;
- enums/choices;
- constraints;
- índices;
- timestamps;
- migraciones.

No implementes aún toda la UI.

Valida:

- unicidad;
- integridad referencial;
- relaciones con Patient/Encounter;
- versionado;
- estados;
- eliminación lógica;
- almacenamiento de metadatos.

### Gate 1

Debe pasar:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

más tests de modelos y constraints.

---

# ETAPA 2 — Dominio y servicios

Implementa:

- `ClinicalDocumentService`;
- `PrescriptionService`;
- `StudyOrderService`;
- operaciones de emisión;
- versionado;
- anulación;
- acceso/descarga cuando corresponda.

Toda lógica debe pasar por los servicios.

### Gate 2

Probar:

- crear;
- emitir;
- versionar;
- anular;
- invalidar;
- permisos;
- idempotencia;
- errores.

---

# ETAPA 3 — Archivos y PDF

Implementa:

- almacenamiento privado;
- validación de archivos;
- rutas seguras;
- metadatos;
- generación server-side;
- PDFs;
- relación documento ↔ archivo;
- descarga protegida.

Respetar la decisión de no presentar la BD y el filesystem como una sola transacción mágica.

Debe existir estrategia clara ante fallo durante generación/persistencia.

### Gate 3

Probar:

- archivo válido;
- archivo inválido;
- MIME;
- tamaño;
- acceso autorizado;
- acceso no autorizado;
- path traversal;
- PDF;
- impresión;
- fallo de almacenamiento;
- consistencia metadatos/archivo.

---

# ETAPA 4 — API

Implementa los endpoints definidos en:

`docs/design/phase-4-api-contracts.md`

Respeta exactamente:

- métodos;
- paths;
- payloads;
- responses;
- errores;
- permisos;
- códigos HTTP;
- idempotencia;
- descarga;
- versionado;
- anulación.

No inventes endpoints.

### Gate 4

Validar:

- happy path;
- errores;
- permisos;
- IDOR;
- idempotencia;
- concurrencia;
- shape JSON;
- seguridad.

---

# ETAPA 5 — UX y pantallas

Implementa las pantallas definidas en:

- `docs/design/phase-4-ux.md`
- `docs/design/phase-4-screens.md`

Reutiliza los patrones visuales existentes.

La UI debe reflejar:

- emisión;
- estado;
- versionado;
- anulación;
- documentos;
- recetas;
- estudios;
- descarga.

Nunca uses frontend como mecanismo de seguridad.

### Gate 5

Validar manualmente:

- navegación;
- creación;
- emisión;
- descarga;
- versionado;
- anulación;
- estados;
- errores;
- permisos;
- responsive;
- accesibilidad básica.

---

# ETAPA 6 — Auditoría y seguridad

Implementa/verifica:

- auditoría;
- actor;
- autorización por objeto;
- protección de recursos;
- errores seguros;
- privacidad;
- acceso documental.

Comprueba especialmente que:

```text
Clinical History ≠ Audit Trail
```

y que no existan eventos clínicos con actor nulo cuando se requiere actor.

### Gate 6

Debe existir evidencia de:

- emisión auditada;
- lectura;
- descarga;
- versionado;
- anulación;
- accesos rechazados;
- ausencia de IDOR;
- ausencia de archivos públicos.

---

# ETAPA 7 — Concurrencia e idempotencia

Ejecuta pruebas reales de:

- doble emisión;
- doble versionado;
- doble anulación;
- emisión concurrente;
- descarga durante cambios de estado;
- cambio de permisos durante operación;
- doble submit desde UI.

### Gate 7

No deben existir:

- duplicados;
- estados imposibles;
- versiones inconsistentes;
- bypass de autorización.

---

# ETAPA 8 — Regresión completa y cierre técnico

Ejecuta toda la estrategia de pruebas de Fase 4 y regresión de Fases 1–3:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py test
```

Además, ejecuta las pruebas específicas definidas en:

`docs/phases/phase-4-testing-strategy.md`

### Gate 8

Debe verificarse:

- suite completa;
- migraciones;
- seguridad;
- concurrencia;
- auditoría;
- API;
- UI;
- regresión F1–F3.

---

# 10. Documentación de cada etapa

Al finalizar cada etapa debes crear o actualizar un registro documental.

Usa una carpeta:

```text
docs/phases/phase-4-implementation/
```

y un archivo por etapa:

```text
stage-00-baseline.md
stage-01-data-model.md
stage-02-domain-services.md
stage-03-files-pdf.md
stage-04-api.md
stage-05-ux-screens.md
stage-06-security-audit.md
stage-07-concurrency.md
stage-08-final-validation.md
```

Cada archivo debe contener:

```text
# Stage X — <nombre>

## Objetivo

## Alcance

## Implementación realizada

## Decisiones aplicadas

## Archivos creados

## Archivos modificados

## Migraciones

## Tests ejecutados

## Resultado de tests

## Validaciones manuales

## Problemas encontrados

## Problemas resueltos

## Gaps conocidos

## Riesgos

## Gate

PASS / FAIL
```

No declares PASS si existe un defecto bloqueante.

---

# 11. Control de cambios

Después de cada etapa ejecuta:

```bash
git status
git diff --stat
```

y revisa los cambios.

No mezcles cambios no relacionados.

No modifiques código de Fases 1–3 sin justificación.

---

# 12. Reglas ante fallos

Si una etapa falla:

1. identifica causa raíz;
2. registra el fallo;
3. corrige;
4. vuelve a ejecutar pruebas;
5. actualiza el documento de etapa;
6. solo entonces marca PASS.

No ocultes fallos.

No reduzcas cobertura para lograr PASS.

No desactives tests.

No hagas que una prueba deje de verificar la regla para evitar el error.

---

# 13. Gaps durante la implementación

Un **gap** es cualquier situación en la que:

- el contrato documental no cubra un comportamiento;
- la implementación no pueda cumplir una regla;
- una decisión documental sea insuficiente;
- una dependencia externa impida completar una capacidad;
- exista deuda técnica necesaria para el cierre.

Cada gap debe registrarse con:

```text
GAP-ID
Severidad
Descripción
Etapa
Impacto
Estado
Workaround, si existe
Acción necesaria
¿Bloquea cierre?
```

No ocultes gaps pequeños. Diferéncialos correctamente.

---

# 14. Criterios para considerar una etapa completada

Una etapa sólo puede marcarse `PASS` si:

- su código compila;
- tests relevantes pasan;
- migraciones están correctas;
- no introduce regresiones conocidas;
- su documentación está actualizada;
- no quedan fallos CRITICAL/HIGH en su alcance.

---

# 15. Regresión obligatoria

Después de cualquier cambio que toque componentes compartidos con Fase 3:

- ejecuta la regresión correspondiente;
- comprueba Agenda;
- comprueba ClinicalEncounter;
- comprueba MedicalRecord;
- comprueba permisos.

Fase 4 no puede romper Fase 3.

---

# 16. Reporte final obligatorio

Al terminar todas las etapas crea:

```text
docs/phases/phase-4-final-report.md
```

Este documento debe ser suficientemente detallado para que un responsable técnico pueda decidir objetivamente:

**¿Fase 4 está lista para cierre o existen gaps pendientes?**

El reporte debe contener:

## 1. Resumen ejecutivo

- objetivo;
- alcance;
- resultado general;
- estado final.

## 2. Resumen de etapas

| Etapa | Nombre | Estado | Tests | Migraciones | Gaps |
|---|---|---|---:|---|---:|

## 3. Cambios implementados

Separar:

- modelos;
- servicios;
- storage;
- PDF;
- API;
- UX/UI;
- seguridad;
- auditoría;
- pruebas.

## 4. Evidencia de pruebas

Indicar:

- comando;
- resultado;
- cantidad;
- fecha/hora;
- ambiente;
- regresión F1–F3.

## 5. Evidencia manual/browser

Para cada flujo crítico:

| Flujo | Resultado | Evidencia |
|---|---|---|
| Crear receta | PASS/FAIL | referencia |
| Emitir receta | PASS/FAIL | referencia |
| Generar PDF | PASS/FAIL | referencia |
| Descargar | PASS/FAIL | referencia |
| Crear StudyOrder | PASS/FAIL | referencia |
| Versionar | PASS/FAIL | referencia |
| Anular | PASS/FAIL | referencia |
| Acceso no autorizado | PASS/FAIL | referencia |

## 6. Seguridad

Reportar:

- autorización;
- IDOR;
- almacenamiento privado;
- descargas;
- logs;
- auditoría.

## 7. Concurrencia

Reportar:

- pruebas realizadas;
- escenarios;
- resultados;
- problemas encontrados;
- problemas corregidos.

## 8. Auditoría

Confirmar que:

- las acciones requeridas generan eventos;
- actor es correcto;
- no existen eventos inválidos;
- el historial clínico permanece separado del audit trail.

## 9. Gaps

Crear una tabla completa:

| GAP | Severidad | Descripción | Estado | ¿Bloquea cierre? |
|---|---|---|---|---|

Separar:

- CRITICAL;
- HIGH;
- MEDIUM;
- LOW;
- INFO.

## 10. Deuda técnica

Separar claramente:

- deuda que bloquea cierre;
- deuda aceptable;
- mejoras futuras.

No etiquetes una funcionalidad futura como gap de Fase 4 si está correctamente fuera de alcance.

## 11. Desviaciones respecto de la documentación

Documenta toda diferencia entre:

- diseño;
- ADRs;
- implementación.

Para cada desviación:

- motivo;
- impacto;
- decisión tomada;
- documento que debe actualizarse.

## 12. Regresión de Fases 1–3

Reportar:

- resultados;
- regresiones;
- correcciones.

## 13. Estado de la documentación

Indicar si:

- documentación de Fase 4 sigue siendo consistente;
- las etapas están documentadas;
- existen contradicciones nuevas;
- deben actualizarse documentos antes del cierre.

## 14. Criterios de cierre

Crear una matriz:

| Criterio | Estado | Evidencia | Bloquea |
|---|---|---|---|
| Alcance implementado | PASS/FAIL | ... | ... |
| Modelo | PASS/FAIL | ... | ... |
| Servicios | PASS/FAIL | ... | ... |
| API | PASS/FAIL | ... | ... |
| UX/UI | PASS/FAIL | ... | ... |
| Seguridad | PASS/FAIL | ... | ... |
| Auditoría | PASS/FAIL | ... | ... |
| Concurrencia | PASS/FAIL | ... | ... |
| Tests | PASS/FAIL | ... | ... |
| Regresión F1–F3 | PASS/FAIL | ... | ... |
| Documentación | PASS/FAIL | ... | ... |

## 15. Recomendación final

El reporte debe terminar exactamente con uno de:

```text
PHASE 4 — READY TO CLOSE
```

o:

```text
PHASE 4 — NOT READY TO CLOSE
```

No declares `READY TO CLOSE` si existe cualquier gap CRITICAL/HIGH que bloquee cierre o cualquier criterio obligatorio que no haya sido validado.

---

# 17. Regla para el cierre

No cierres Fase 4 simplemente porque:

```text
tests = PASS
```

El cierre requiere:

```text
Código
+
Pruebas
+
Migraciones
+
Seguridad
+
Concurrencia
+
Auditoría
+
UX/UI
+
Regresión
+
Documentación
+
Cero gaps bloqueantes
```

---

# 18. No avanzar a Fase 5

Una vez terminada la implementación de Fase 4:

- no implementar `CareRequest`;
- no implementar notificaciones de Fase 5;
- no diseñar funcionalidades nuevas;
- no comenzar otra fase.

Primero debe generarse el reporte final y determinar si Fase 4 puede cerrarse.

---

# 19. Comportamiento inicial obligatorio

Comienza por:

## ETAPA 0 — Baseline

Primero inspecciona el repositorio y documentación, ejecuta las verificaciones base y documenta el estado.

Después reporta:

```text
STAGE 0 — PASS / FAIL
```

No avances silenciosamente si el baseline tiene problemas.

---

# Principio final

Implementa Fase 4 con la misma disciplina utilizada en Fase 3:

```text
Diseño cerrado
      ↓
Etapa pequeña
      ↓
Implementación
      ↓
Pruebas
      ↓
Evidencia
      ↓
Documentación
      ↓
Gate
      ↓
Siguiente etapa
```

La prioridad no es terminar rápido.

La prioridad es que, al finalizar, pueda responderse objetivamente:

> **¿Fase 4 está realmente terminada y lista para cierre formal?**

Y si la respuesta es no, el `phase-4-final-report.md` debe mostrar claramente **qué gaps existen, cuál es su severidad, qué impide el cierre y qué debe hacerse después**.

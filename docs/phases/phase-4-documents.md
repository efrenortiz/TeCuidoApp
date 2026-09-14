# Fase 4 — Documentos clínicos

**Estado:** especificación funcional aprobada — lista para diseño técnico y programación

**Fecha de aprobación de políticas:** 2026-09-11

**Dependencias:** Fase 1 — Fundaciones; Fase 2 — Agenda; Fase 3 — Gestión clínica

---

## 1. Propósito

La Fase 4 incorpora la emisión, generación, consulta, descarga y conservación histórica de documentos clínicos asociados a la atención de pacientes en TeCuidoApp.

El objetivo es añadir capacidades documentales sin modificar las decisiones ya cerradas de Fase 1, Fase 2 y Fase 3, manteniendo el principio de mínima complejidad y evitando convertir el módulo clínico en un gestor documental genérico.

La Fase 4 se centra en:

- recetas médicas;
- solicitudes de laboratorio, gabinete, histopatología y otros estudios;
- generación de PDFs;
- documentos clínicos adjuntos;
- almacenamiento privado;
- descargas autorizadas;
- versionado y trazabilidad.

---

## 2. Principios rectores

Las siguientes reglas son obligatorias:

1. Las entidades existentes de `Patient`, `Doctor`, `Clinic`, `Appointment`, `ClinicalEncounter` y `MedicalRecord` son canónicas y no se duplican.
2. Fase 4 no modifica el ciclo de vida de `Appointment` ni `ClinicalEncounter`.
3. Los documentos emitidos tienen carácter histórico.
4. No se utiliza `DELETE` funcional para destruir documentos clínicos emitidos.
5. Una corrección de un documento emitido no sobrescribe silenciosamente la versión anterior.
6. Toda lectura, descarga, emisión, anulación o cambio documental relevante debe respetar autorización por objeto y auditoría.
7. Los archivos clínicos permanecen en almacenamiento privado.
8. La UI no es autoridad de seguridad; las autorizaciones se verifican en servidor.
9. No se introduce un catálogo farmacológico, catálogo diagnóstico ni catálogo obligatorio de estudios en esta fase.
10. No se implementan en Fase 4 resultados de laboratorio, interpretación automática, firma electrónica ni notificaciones complejas.

---

## 3. Alcance de Fase 4

### 3.1 Incluye

- `Prescription`.
- `PrescriptionItem`.
- `StudyOrder`.
- `StudyOrderItem`.
- `ClinicalDocument`.
- generación de PDFs para recetas y solicitudes de estudios;
- carga de archivos clínicos autorizados;
- consulta y descarga de documentos;
- versionado de documentos emitidos;
- anulación lógica mediante `VOIDED` cuando corresponda;
- auditoría de operaciones documentales;
- pruebas y controles de seguridad asociados.

### 3.2 No incluye

- `CareRequest` como flujo operativo; pertenece a Fase 5.
- resultados de estudios;
- interpretación de resultados;
- OCR;
- firma electrónica criptográfica;
- recetas electrónicas regulatorias avanzadas;
- catálogo farmacológico;
- CIE-10;
- catálogo diagnóstico;
- búsqueda documental avanzada;
- exportación masiva del expediente;
- notificaciones;
- dashboard de operación de Fase 5;
- gestor de archivos genérico tipo Drive.

---

## 4. Fronteras de aplicación

Fase 4 mantiene separación de responsabilidades mediante aplicaciones especializadas:

```text
prescriptions/
    └── Prescription
        └── PrescriptionItem

study_orders/
    └── StudyOrder
        └── StudyOrderItem

clinical_documents/
    └── ClinicalDocument
```

Las aplicaciones no duplican entidades existentes.

La relación lógica queda:

```text
Patient
 ├── MedicalRecord
 ├── ClinicalEncounter
 ├── Prescription
 ├── StudyOrder
 └── ClinicalDocument
```

Cuando corresponda, `Prescription` y `StudyOrder` se relacionan además con el `ClinicalEncounter` que les da contexto.

---

## 5. Dependencias con Fase 3

### 5.1 ClinicalEncounter

Una receta o solicitud de estudio clínica debe identificar el `ClinicalEncounter` que la originó.

Esto no significa que el encuentro deba estar `COMPLETED` para poder emitir el documento. La emisión puede realizarse durante `IN_PROGRESS` cuando el flujo clínico lo requiera.

La emisión no cambia el estado del encounter.

### 5.2 MedicalRecord

El documento pertenece al paciente y queda integrado en su historial documental.

No se agrega una relación redundante a `MedicalRecord` si el `Patient` ya determina inequívocamente el expediente.

### 5.3 DoctorPatientRelationship

La existencia de una receta, solicitud de estudio o documento no crea ni modifica una `DoctorPatientRelationship`.

### 5.4 Appointment

La relación con `Appointment` es contextual y no altera su ciclo de vida.

---

## 6. Recetas médicas

### 6.1 Prescription

Una `Prescription` representa una receta emitida por un médico para un paciente en el contexto de un `ClinicalEncounter`.

Debe identificar como mínimo:

- paciente;
- médico;
- encounter;
- fecha/hora de emisión;
- estado;
- observaciones cuando correspondan;
- información de versionado cuando la receta sea corregida mediante una nueva versión.

### 6.2 PrescriptionItem

Cada medicamento se representa mediante un `PrescriptionItem` con campos explícitos.

Como mínimo:

- nombre del medicamento;
- presentación, cuando aplique;
- dosis;
- unidad de dosis, cuando aplique;
- vía;
- frecuencia;
- duración, cuando aplique;
- indicaciones;
- posición/orden.

No existe catálogo farmacológico obligatorio en Fase 4.

### 6.3 Estados

Se utilizarán únicamente los estados necesarios:

```text
ISSUED
VOIDED
```

No se agregan estados como `DISPENSED`, `PARTIALLY_FILLED`, `EXPIRED` o equivalentes porque corresponden a procesos externos o fases posteriores.

### 6.4 Correcciones

Una receta `ISSUED` no se modifica directamente.

Cuando sea necesaria una corrección:

- se conserva la versión anterior;
- se crea una nueva versión;
- se registra el motivo;
- se conserva el usuario y fecha/hora de la modificación;
- se establece la relación con la versión anterior;
- se identifica una única versión vigente.

### 6.5 Anulación

Una receta emitida puede pasar a `VOIDED` cuando corresponda.

La anulación:

- no elimina físicamente la receta;
- requiere motivo;
- registra usuario y fecha/hora;
- se audita.

---

## 7. Solicitudes de estudios

### 7.1 StudyOrder

`StudyOrder` representa una solicitud emitida por un médico para uno o más estudios.

Debe identificar como mínimo:

- paciente;
- médico;
- encounter;
- fecha/hora de emisión;
- tipo de estudio;
- indicaciones;
- observaciones;
- estado;
- versionado cuando corresponda.

### 7.2 Tipos de estudio

El tipo inicial será un conjunto pequeño y estable:

```text
LABORATORY
IMAGING
HISTOPATHOLOGY
OTHER
```

No se crea un catálogo exhaustivo de estudios en Fase 4.

### 7.3 StudyOrderItem

Cada estudio solicitado se representa mediante un `StudyOrderItem` con:

- nombre del estudio;
- indicaciones específicas cuando correspondan;
- posición/orden.

### 7.4 Estados

Se utilizarán:

```text
ISSUED
VOIDED
```

Los resultados y estados posteriores del estudio quedan fuera de Fase 4.

### 7.5 Correcciones y anulación

Se aplican las mismas reglas de preservación histórica que a las recetas:

- no sobrescribir una solicitud emitida;
- nueva versión para correcciones;
- motivo;
- actor;
- timestamp;
- auditoría;
- `VOIDED` para anulación.

---

## 8. ClinicalDocument

### 8.1 Propósito

`ClinicalDocument` representa el documento clínico persistido y sus metadatos, no solamente el archivo binario.

Debe permitir representar documentos:

- subidos por un usuario;
- generados por TeCuidoApp;
- asociados al paciente;
- asociados a una cita;
- asociados a un encounter;
- asociados a una receta;
- asociados a una solicitud de estudio.

### 8.2 Paciente obligatorio

Todo `ClinicalDocument` clínico debe pertenecer a un `Patient`.

Las demás relaciones son opcionales y deben utilizarse solamente cuando tengan significado clínico.

No se permite crear un documento clínico huérfano del paciente.

### 8.3 Tipos iniciales

```text
LABORATORY
IMAGING
HISTOPATHOLOGY
PHOTOGRAPH
PRESCRIPTION
INSTRUCTIONS
STUDY_ORDER
OTHER
```

La lista puede evolucionar mediante una decisión posterior; no se crea un catálogo externo en Fase 4 sin necesidad.

### 8.4 Origen

El documento identifica su origen:

```text
UPLOADED
GENERATED
```

### 8.5 Metadatos mínimos

Debe conservarse como mínimo:

- archivo;
- nombre original;
- tipo documental;
- descripción opcional;
- paciente;
- relaciones clínicas correspondientes;
- usuario que cargó/generó;
- fecha/hora de creación;
- versión cuando aplique;
- estado cuando corresponda.

---

## 9. Archivos y almacenamiento

Los archivos clínicos deben almacenarse en un medio privado.

No deben exponerse mediante rutas públicas directas.

La ruta física no se construye a partir del nombre suministrado por el cliente.

El nombre original se conserva como metadato independiente del nombre físico de almacenamiento.

### 9.1 Tipos permitidos inicialmente

Para archivos subidos se soportarán inicialmente:

- PDF;
- imágenes comunes necesarias para documentos clínicos.

No se aceptan ejecutables ni formatos no requeridos por Fase 4.

### 9.2 Validación

La aplicación debe validar:

- extensión;
- MIME informado;
- tamaño máximo configurado;
- autorización;
- integridad suficiente para el tipo de archivo cuando sea viable.

No se debe confiar exclusivamente en `Content-Type` enviado por el cliente.

---

## 10. Generación de PDF

TeCuidoApp generará PDFs para:

- recetas;
- solicitudes de laboratorio;
- solicitudes de gabinete;
- solicitudes de histopatología;
- solicitudes de otros estudios.

Los PDFs deben:

- identificar al paciente;
- identificar al médico;
- identificar al consultorio cuando corresponda;
- mostrar fecha/hora de emisión;
- contener la información emitida;
- ser imprimibles;
- conservar la versión emitida.

La generación será **server-side** y, para Fase 4, preferentemente síncrona.

No se incorpora Celery u otra infraestructura asíncrona solamente para generación de PDF.

---

## 11. Conservación histórica y versionado

Una vez emitido un documento clínico, su contenido histórico no debe sobrescribirse silenciosamente.

Para correcciones se utilizará:

```text
Version 1
   ↓
Version 2
   ↓
Version 3
```

Cada nueva versión debe conservar:

- número de versión;
- fecha/hora;
- usuario;
- motivo;
- referencia a versión anterior;
- identificación de la versión vigente.

El PDF emitido debe representar el estado documental de esa versión y no reconstruirse posteriormente con datos mutables del sistema.

No se requiere hash criptográfico de archivo en la primera implementación de Fase 4.

---

## 12. Eliminación y anulación

No existe `DELETE` funcional para documentos clínicos emitidos.

Cuando una receta o solicitud de estudio deba dejar de estar vigente, se utilizará `VOIDED` con:

- motivo;
- usuario;
- fecha/hora;
- auditoría.

Para archivos subidos erróneamente se utilizará la estrategia de inactivación definida por el dominio documental, preservando trazabilidad cuando el archivo haya formado parte del historial clínico.

---

## 13. Autorización

Las reglas de acceso se heredan de la política clínica de Fase 3 y se aplican al recurso documental concreto.

### Paciente

Puede consultar y descargar documentos para los que tenga autorización sobre su propio expediente.

### Responsable

Puede consultar y descargar documentos del paciente mientras exista `ResponsiblePatientRelationship.status == ACTIVE` y la política clínica le conceda acceso.

### Médico

Puede consultar y descargar documentos de pacientes sobre los que tenga autorización clínica vigente.

El médico que emite una receta o solicitud debe tener además la autorización necesaria para realizar la operación de emisión.

### Administrador

Conserva su acceso administrativo global conforme a las decisiones de Fase 1–3 y queda sujeto a auditoría en operaciones sensibles.

La UI nunca sustituye estas comprobaciones.

---

## 14. Auditoría

Deben auditarse, como mínimo cuando corresponda:

- emisión de receta;
- emisión de StudyOrder;
- generación de PDF;
- carga de documento;
- lectura de documento sensible;
- descarga;
- creación de versión;
- anulación;
- accesos administrativos relevantes.

El audit trail conserva metadatos del evento.

No debe almacenar el binario completo del documento dentro del registro de auditoría.

La auditoría y el historial clínico siguen siendo conceptos distintos.

---

## 15. Idempotencia y concurrencia

Las operaciones sensibles deben soportar reintentos técnicos y doble submit sin crear duplicados indebidos.

Como mínimo:

- emisión de receta;
- emisión de StudyOrder;
- generación de documento asociado;
- creación de versión;
- anulación.

Las invariantes deben estar protegidas por transacciones y constraints apropiados de PostgreSQL.

No se debe confiar únicamente en la UI para evitar dobles envíos.

---

## 16. API y servicios

La implementación seguirá la frontera ya adoptada:

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

Los servicios previstos son:

```text
PrescriptionService
StudyOrderService
ClinicalDocumentService
```

No se crea un `GenericClinicalDocumentService` que absorba lógicas incompatibles sólo para reducir el número de archivos.

Los contratos API se definirán en el documento específico posterior y no deben ampliarse mediante CRUD genérico.

---

## 17. UX/UI

Las operaciones principales deberán ser accesibles desde el contexto clínico ya existente:

- crear receta;
- crear solicitud de estudio;
- visualizar documentos del paciente;
- visualizar detalle documental;
- descargar documento autorizado.

La interfaz debe reutilizar los patrones visuales de Fase 3.

No se crea un gestor documental independiente con carpetas, etiquetas complejas, edición de archivos o búsqueda avanzada.

---

## 18. Filtros e historial documental

El historial documental debe mostrar los documentos más recientes primero.

Se permitirán filtros mínimos por:

- tipo documental;
- fecha.

La búsqueda libre de texto y exportación masiva quedan fuera de la implementación inicial.

La paginación debe seguir el patrón utilizado en Fase 3 para información histórica.

---

## 19. CareRequest

Aunque `ClinicalDocument` podrá relacionarse arquitectónicamente con `CareRequest` en el futuro, Fase 4 no implementará el flujo operativo de `CareRequest`.

No debe existir dependencia funcional de Fase 5 para emitir una receta, una solicitud de estudio o adjuntar un documento en Fase 4.

---

## 20. Datos clínicos y privacidad

Los PDFs y archivos deben conservar los datos relevantes al momento de emisión.

No deben regenerarse posteriormente utilizando información mutable que pueda cambiar el significado histórico del documento.

No deben contener más información sensible de la necesaria para su finalidad.

No deben aparecer datos clínicos completos en:

- URLs;
- mensajes de error;
- logs técnicos;
- nombres físicos de archivos.

---

## 21. Criterios de aceptación funcional

Fase 4 se considera funcionalmente implementada cuando, como mínimo:

### Recetas

- un médico autorizado puede emitir una receta;
- la receta queda vinculada al paciente, médico y encounter;
- puede contener múltiples medicamentos;
- genera PDF;
- el PDF puede consultarse, descargarse e imprimirse;
- la receta emitida no puede sobrescribirse;
- las correcciones producen versiones trazables;
- la anulación conserva historial.

### StudyOrder

- un médico autorizado puede emitir una solicitud;
- puede incluir uno o varios estudios;
- identifica tipo de estudio;
- genera PDF;
- puede consultarse, descargarse e imprimirse;
- las correcciones generan nuevas versiones;
- puede anularse sin borrado destructivo.

### ClinicalDocument

- un usuario autorizado puede cargar un documento;
- el documento pertenece a un paciente;
- el archivo se almacena privadamente;
- la descarga requiere autorización;
- el documento histórico permanece trazable.

### Seguridad

- un usuario no autorizado no puede leer ni descargar documentos;
- no existe acceso por IDOR;
- las operaciones sensibles generan auditoría;
- los binarios no quedan públicos.

---

## 22. Criterios de aceptación no funcional

Antes del cierre de Fase 4 deben verificarse:

- integridad de base de datos;
- ausencia de migraciones pendientes;
- transacciones correctas;
- concurrencia;
- autorización por objeto;
- almacenamiento privado;
- protección de archivos;
- auditoría;
- generación reproducible de PDFs;
- regresión de Fases 1–3;
- pruebas automatizadas;
- pruebas de navegador de flujos críticos.

---

## 23. Reglas de compatibilidad con fases anteriores

Fase 4 no debe:

- modificar la semántica de los estados de Appointment;
- alterar los estados de ClinicalEncounter;
- crear o modificar automáticamente DoctorPatientRelationship;
- reemplazar el MedicalRecord;
- introducir datos duplicados de Patient;
- cambiar las reglas de autorización establecidas en Fase 3;
- romper la auditoría existente;
- alterar la semántica histórica de encuentros completados.

---

## 24. Decisiones explícitamente fuera de alcance

Quedan fuera de este contrato, aunque puedan ser futuras extensiones:

- catálogo farmacológico;
- catálogo de estudios completo;
- resultados de laboratorio;
- imágenes diagnósticas estructuradas;
- firma electrónica;
- firma biométrica;
- receta electrónica regulatoria avanzada;
- CIE-10;
- IA clínica;
- notificaciones;
- CareRequest operativo;
- dashboards de Fase 5;
- exportación masiva;
- búsqueda documental avanzada;
- almacenamiento externo especializado;
- checksum/firmas de archivo como garantía de integridad regulatoria.

---

## 25. Dependencias documentales posteriores

Este contrato es el documento rector funcional de Fase 4.

Los documentos posteriores deberán desarrollar, sin contradecirlo:

1. `phase-4-documents-workflow.md`
2. `phase-4-documents-rules.md`
3. `clinical-document-domain.md`
4. `prescription-domain.md`
5. `study-order-domain.md`
6. `clinical-documents-data-model.md`
7. `phase-4-permissions.md`
8. `phase-4-security-and-privacy.md`
9. `phase-4-service-contracts.md`
10. `phase-4-api-contracts.md`
11. `phase-4-ux.md`
12. `phase-4-screens.md`
13. `phase-4-audit-and-history.md`
14. `phase-4-testing-strategy.md`
15. ADRs específicos de Fase 4.

---

## 26. Fuente de verdad

En caso de contradicción dentro de la documentación de Fase 4, este documento prevalece sobre documentos derivados, salvo una decisión posterior formalmente aprobada y registrada mediante el mecanismo de ADR correspondiente.

Si una regla de Fase 1–3 es referenciada aquí, conserva su semántica original.

---

## 27. Estado del contrato

**FASE 4 — CONTRATO FUNCIONAL APROBADO**

La Fase 4 puede avanzar al diseño detallado siempre que los documentos posteriores respeten las decisiones anteriores y no introduzcan funcionalidad fuera de alcance.

# Fase 4 — Workflow de documentos clínicos

**Estado:** cerrado para diseño e implementación.

## 1. Propósito

Define los flujos operativos de receta, solicitud de estudios y documentos clínicos, preservando las decisiones cerradas de Fases 1–3.

## 2. Principios

- Cada documento clínico se crea desde un contexto autorizado.
- La emisión es una operación explícita y no cambia el estado de Appointment ni ClinicalEncounter.
- Las operaciones sensibles son transaccionales.
- La información emitida es histórica.
- Las correcciones generan nueva versión; no sobrescriben la anterior.
- La descarga siempre vuelve a autorizar el recurso.

## 3. Flujo de receta

```text
ClinicalEncounter válido
        ↓
verificar autorización
        ↓
capturar Prescription + PrescriptionItems
        ↓
validar datos
        ↓
transacción
        ↓
crear Prescription ISSUED
        ↓
generar PDF
        ↓
crear ClinicalDocument GENERATED
        ↓
auditar
```

La emisión de la receta y su ClinicalDocument deben quedar consistentes. La transacción de base de datos controla los registros de emisión; el archivo físico se genera fuera de la transacción de base de datos y, si falla la persistencia posterior, debe eliminarse/compensarse el artefacto no referenciado. No debe quedar una receta marcada como emitida sin su representación documental requerida.

**Corrección de consistencia (2026-09-11):** la compensación es siempre **síncrona**, dentro de la
misma llamada de servicio (p. ej. `try/finally` alrededor de la escritura del archivo), nunca un
job diferido — coherente con que Fase 4 no incorpora Celery ni infraestructura asíncrona (§16 del
contrato). Orden exacto: (1) generar el PDF en memoria; (2) escribir el archivo en el almacenamiento
privado; (3) abrir la transacción de base de datos, crear `Prescription`/`ClinicalDocument`
referenciando el `storage_key` ya escrito, y hacer commit. Si (2) falla, no se abre la transacción
— no hay nada que compensar. Si (3) falla después de (2), el archivo ya escrito queda huérfano (sin
ninguna fila que lo referencie): el servicio intenta borrarlo en el mismo `except` como mejor
esfuerzo; si ese borrado también falla, el archivo huérfano no representa un riesgo de seguridad ni
de integridad (nunca es referenciado por ningún `ClinicalDocument`, por lo tanto nunca es
accesible) y su limpieza eventual es una tarea operativa de mantenimiento, no un requisito de
cierre de Fase 4.

## 4. Corrección de receta

```text
Prescription ISSUED
        ↓
solicitud de corrección autorizada
        ↓
crear nueva versión
        ↓
conservar versión anterior
        ↓
generar nuevo PDF
        ↓
actualizar referencia de versión vigente
        ↓
auditar
```

## 5. Anulación de receta

```text
ISSUED
  ↓
validar actor
  ↓
motivo obligatorio
  ↓
VOIDED
  ↓
auditar
```

No existe borrado físico funcional.

## 6. Flujo de StudyOrder

El flujo es equivalente al de Prescription:

```text
ClinicalEncounter
   ↓
autorización
   ↓
StudyOrder + StudyOrderItems
   ↓
ISSUED
   ↓
PDF
   ↓
ClinicalDocument
   ↓
auditoría
```

## 7. Flujo de documento subido

```text
Paciente/contexto autorizado
        ↓
seleccionar archivo
        ↓
validar extensión + MIME + tamaño
        ↓
crear ClinicalDocument
        ↓
almacenar archivo privado
        ↓
auditar
```

El archivo no se publica antes de completar autorización y persistencia.

## 8. Lectura y descarga

```text
solicitud
  ↓
autenticación
  ↓
autorización por objeto
  ↓
registro de auditoría cuando aplique
  ↓
servir archivo privado
```

No se utilizan URLs públicas permanentes como mecanismo de acceso.

## 9. Interrupciones

Un fallo después de guardar parcialmente el contexto de una receta o solicitud no altera ClinicalEncounter. Una operación de emisión fallida debe poder reintentarse sin producir duplicados indebidos.

## 10. Concurrencia

Se contemplan como mínimo:

- doble submit de emisión;
- dos correcciones simultáneas;
- anulación concurrente con corrección;
- descarga concurrente;
- acceso simultáneo desde varias pestañas.

Las invariantes se resuelven en servicio + transacción + constraints, no sólo en UI.

**Corrección de consistencia (2026-09-11) — resolución explícita por escenario.** Los documentos
de Fase 4 enumeraban estos escenarios (aquí, en `phase-4-testing-strategy.md` §11 y en
`phase-4-documents.md` §15/16) sin definir el resultado exacto de cada uno — `phase-4-service-contracts.md`
§3 dejaba además el mecanismo de idempotencia como "opcional según infraestructura existente" sin
confirmar si esa infraestructura existe. Se verificó: **sí existe** — Fase 2 ya estableció el patrón
`Idempotency-Key` (header opcional) + `UniqueConstraint` parcial sobre `(actor, idempotency_key)`
(`appointments/models.py`: `appointment_idempotency_key_unique`, `reschedule_idempotency_key_unique`).
Fase 4 reutiliza exactamente ese patrón, sin inventar uno nuevo:

| Escenario | Resolución |
|---|---|
| Doble submit de emisión (Prescription/StudyOrder) con el mismo `Idempotency-Key` | La segunda petición no crea un segundo recurso; devuelve el ya emitido (idempotente, `200`). Sin `Idempotency-Key`, ambas peticiones son intentos independientes y válidos — Fase 4 no deduce "misma intención" a partir del contenido. |
| Mismo `Idempotency-Key` reutilizado por el mismo actor para una intención lógica distinta | `Conflict` (`409`) — mismo comportamiento ya cerrado en Fase 2 para este caso. |
| Dos correcciones simultáneas sobre la misma versión vigente | La primera adquiere `select_for_update` sobre la versión actual y la marca `is_current_version=False` al crear la nueva versión (D-001). La segunda, tras el lock, encuentra `is_current_version=False` y se rechaza con `Conflict` (`409`) — no crea una tercera versión "huérfana". |
| Anulación repetida con el mismo motivo sobre un recurso ya `VOIDED` | Idempotente: no duplica el evento de auditoría ni cambia `voided_at` — mismo patrón que SC-065 (Fase 3) para repeticiones exactas. |
| Anulación con datos distintos sobre un recurso ya `VOIDED` | `InvalidState` (`409`) — nunca sobrescribe el motivo/actor de la anulación original. |
| Anulación concurrente con corrección sobre la misma versión | Ambas compiten por el mismo `select_for_update`; la que llega primero gana, la segunda recibe `Conflict` (`409`) sobre el estado ya cambiado. |
| Descarga durante anulación | La descarga re-autoriza en el momento de servirse (§8); no requiere bloqueo — sirve el archivo si la autorización era válida en ese instante, sin importar si el estado cambia inmediatamente después. |
| Emisión mientras cambia la autorización del actor (p. ej. `DoctorPatientRelationship` desactivada a mitad de la operación) | La autorización se valida dentro de la misma transacción que la mutación; un cambio posterior al commit no la invalida retroactivamente — mismo principio ya aplicado en Fase 3. |
| Dos uploads de archivo con intención idéntica sin `Idempotency-Key` | Se tratan como dos `ClinicalDocument` independientes y válidos; Fase 4 no intenta deduplicar contenido de archivos subidos (fuera de alcance — evita heurísticas de similitud). |
| Generación de PDF duplicada dentro de una emisión ya protegida por `Idempotency-Key` | No ocurre: la generación de PDF es parte de la misma operación transaccional que la idempotencia ya cubre. |

## 11. Fuera de flujo

No forman parte de Fase 4:

- resultados de estudios;
- procesamiento de laboratorio;
- firma electrónica;
- CareRequest operativo;
- notificaciones complejas.

## 12. Criterio de cierre

Cada flujo debe tener comportamiento definido para éxito, validación, autorización, duplicidad, concurrencia, error de almacenamiento y auditoría.

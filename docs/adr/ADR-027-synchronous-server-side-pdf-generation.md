# ADR-027 — Synchronous Server-Side PDF Generation, No Async Infrastructure

**Estado:** Accepted
**Fecha:** 2026-09-11
**Área:** Arquitectura / Infraestructura

## 1. Contexto

Recetas y solicitudes de estudio requieren un PDF generado por el servidor, consultable,
descargable e imprimible, que represente fielmente el estado documental en el momento de emisión.

## 2. Decisión

La generación de PDF es **server-side y síncrona**: ocurre dentro de la misma operación de
emisión/versionado, antes de confirmar la transacción de base de datos. No se incorpora Celery ni
otra infraestructura asíncrona sólo para esto.

Orden exacto de la operación de emisión:

1. generar el PDF en memoria (determinista, a partir de los datos ya validados);
2. escribir el archivo en el almacenamiento privado (ADR-026);
3. abrir la transacción de base de datos, crear `Prescription`/`StudyOrder` y su
   `ClinicalDocument` referenciando el `storage_key` ya escrito, y hacer commit.

Si el paso 2 falla, no se abre la transacción — no hay nada que compensar. Si el paso 3 falla
después del 2, el archivo ya escrito queda huérfano (sin ninguna fila que lo referencie); el
servicio intenta borrarlo como mejor esfuerzo en el mismo bloque `except`. Un archivo huérfano que
sobrevive a ese intento no representa un riesgo de seguridad ni de integridad (nunca es
referenciado por ningún `ClinicalDocument`, por lo tanto nunca es accesible) y su limpieza eventual
es una tarea operativa, no un requisito de cierre de Fase 4.

**Nota de implementación (Stage 3/7 de la implementación, 2026-09-11):** para el caso
`GENERATED` (`Prescription`/`StudyOrder`), la implementación real escribe el archivo en el paso 2
DENTRO del mismo `with transaction.atomic()` que abre el paso 3, en vez de estrictamente antes de
abrirlo — Django anida `atomic()` como SAVEPOINT sobre la misma conexión, así que
`Prescription`/`StudyOrder` + su `ClinicalDocument` comparten una única transacción real: un fallo
en cualquier punto posterior revierte todo junto, incluyendo el registro que apuntaría al archivo.
Esto no contradice la decisión — es una garantía más fuerte que la secuencia estrictamente
"antes/afuera" descrita arriba, sin dejar nunca una fila emitida sin su documento — y se documenta
aquí para que la implementación y el ADR cuenten la misma historia exacta. El caso `UPLOADED`
(`ClinicalDocumentService.upload`, sin transacción padre preexistente) sí sigue la secuencia
original tal como está descrita arriba, con borrado best-effort ante un fallo posterior.

El PDF de una versión emitida no se regenera posteriormente con datos mutables del sistema — el
contenido histórico de esa versión es fijo desde su creación.

## 3. Reglas derivadas

- No debe quedar una `Prescription`/`StudyOrder` marcada `ISSUED` sin su `ClinicalDocument`
  `GENERATED` correspondiente.
- No se requiere hash criptográfico del archivo en la primera implementación.
- La zona horaria del PDF sigue la de la `Clinic`, igual que el resto de timestamps clínicos de
  Fase 2/3.

## 4. Alternativas consideradas

### Generar el PDF de forma asíncrona (cola/worker) tras confirmar la emisión
**Rejected para esta fase.** Introduce una ventana en la que la receta existe sin su PDF, y
requiere infraestructura (Celery/broker) que el proyecto no necesita todavía sólo para esta
funcionalidad — contradice el principio de simplicidad del contrato (§4/§10).

### Regenerar el PDF bajo demanda en cada descarga, sin persistir el archivo
**Rejected.** Un documento clínico histórico debe representar el estado en el momento de emisión;
regenerarlo con datos actuales (que pueden haber cambiado) alteraría silenciosamente su significado
histórico — contradice `phase-4-security-and-privacy.md` §5.

## 5. Consecuencias

Positivas:
- ninguna ventana de inconsistencia entre "receta emitida" y "PDF disponible";
- ninguna dependencia de infraestructura nueva.

Negativas:
- la latencia de la operación de emisión incluye la generación completa del PDF (aceptable dado el
  volumen esperado de Fase 4).

## 6. Relación

Complementa el principio de "no introducir infraestructura innecesaria" del contrato de Fase 4 §4.

## 7. Estado

**Accepted.**

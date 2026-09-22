# TeCuidoApp — Fase 6
# Design Freeze — Notificaciones y Auditoría

**Estado:** DESIGN FREEZE  
**Fase:** Fase 6  
**Nombre oficial:** **Notificaciones y auditoría**  
**Tipo de documento:** Contrato normativo de diseño  
**Versión:** 1.1  
**Fecha:** 2026-09-20

> **Estado de implementación (2026-09-21):** el paquete derivado de este Design Freeze está
> implementado. `docs/phases/phase-6-implementation-summary.md` es la bitácora oficial de código,
> tests, migraciones y las ocho decisiones finales del propietario (PD-001 a PD-008) que
> incorporan/precisan lo congelado aquí sin contradecirlo. Este documento sigue siendo la
> autoridad normativa de alcance — no se modifica su contenido más allá de esta nota.

---

## 1. Propósito

Este documento constituye el **contrato normativo único de diseño de Fase 6**.

Su propósito es establecer el alcance funcional y los principios arquitectónicos que deberán respetar todos los documentos de diseño posteriores de Fase 6.

Los documentos derivados especificarán **cómo** se implementan las capacidades aquí definidas, pero no podrán cambiar su alcance ni introducir reglas funcionales incompatibles.

Fuentes principales:

1. `requirements.md`.
2. `docs/architecture.md`.
3. ADRs vigentes aplicables.
4. Patrones y decisiones consolidados en Fases 1–5.

---

## 2. Precedencia normativa

Para Fase 6 se establece:

```text
requirements.md
      ↓
ADR vigente aplicable
      ↓
docs/architecture.md
      ↓
phase-6-design-freeze.md
      ↓
documentos de diseño Fase 6
      ↓
implementación
```

Reglas:

- Ningún documento derivado puede ampliar, reducir o reinterpretar el alcance de esta fase.
- UX no define reglas de negocio.
- API no define reglas de dominio.
- Los servicios implementan intenciones de negocio; no inventan políticas.
- Los detalles técnicos deben resolverse preferentemente reutilizando componentes existentes.
- Una cuestión que requiera decisión de producto, política clínica, privacidad o legalidad no debe resolverse unilateralmente durante la implementación.

---

## 3. Identidad oficial de Fase 6

La definición vigente es:

> **Fase 6 — Notificaciones y auditoría**

Esta denominación debe utilizarse en la documentación de fase, reportes, commits y artefactos de release.

El paquete anterior denominado **“Fase 6 — Expediente Clínico + Acceso + Auditoría/Seguridad”** fue descartado y no forma parte de Fase 6.

El expediente clínico, permisos clínicos y auditoría clínica ya existentes en `medical_records` permanecen como capacidades de fases históricas. Fase 6 no los reimplementa.

---

## 4. Objetivo

Fase 6 establece capacidades transversales para:

1. enviar notificaciones operativas por correo electrónico;
2. programar y ejecutar recordatorios;
3. enviar notificaciones relacionadas con eventos operativos definidos;
4. registrar y consultar eventos de auditoría;
5. registrar aceptación de documentos de plataforma, específicamente aviso de privacidad y términos y condiciones;
6. aplicar controles de seguridad asociados a estas capacidades;
7. mantener separada la lógica de negocio de los proveedores concretos de transporte.

La fase se construye sobre las capacidades existentes de Fases 1–5.

---

## 5. Alcance funcional

### 5.1 Notificaciones por correo

Debe contemplarse correo electrónico para:

- invitación de registro;
- verificación de correo;
- recuperación de contraseña;
- cita creada;
- cita modificada;
- cita cancelada;
- recordatorios;
- otras notificaciones operativas que sean definidas explícitamente durante el diseño detallado.

### 5.1.1 Cita creada

La notificación de **cita creada** representa que la reserva fue realizada correctamente.

No existe una etapa separada de “confirmación de cita” en Agenda. No debe introducirse un nuevo estado de `Appointment` para representar una confirmación por correo.

### 5.1.2 Destinatarios de citas

Para las notificaciones de:

- cita creada;
- cita modificada/reprogramada;
- cita cancelada;

los destinatarios son:

```text
Appointment
   ├── Patient
   ├── Responsible autorizado (si corresponde)
   └── Doctor asignado
```

El responsable debe ser un responsable autorizado conforme a las relaciones vigentes del sistema.

### 5.1.3 Opt-out de notificaciones operativas

Las notificaciones operativas definidas en esta fase **no pueden desactivarse por el usuario**.

No se contempla un mecanismo de opt-out para las notificaciones de citas ni para los recordatorios definidos en Fase 6.

---

## 6. Recordatorios

Los recordatorios iniciales definidos por requisitos son:

```text
15 días antes
10 días antes
5 días antes
1 día antes
```

Las reglas deben poder configurarse sin modificar la lógica de negocio principal.

Un recordatorio:

- no cancela una cita;
- no confirma una cita;
- no reprograma una cita;
- no cambia estados de `Appointment`;
- no crea disponibilidad;
- no sustituye las reglas de Agenda.

El paso del tiempo por sí mismo no cambia el estado de un `Appointment`.

### 6.1 Destinatarios de recordatorios

Los recordatorios periódicos de 15, 10, 5 y 1 días antes se envían únicamente a:

```text
Appointment
   ├── Patient
   └── Responsible autorizado (si corresponde)
```

El **Doctor asignado no recibe recordatorios periódicos**.

Esta exclusión aplica únicamente a los recordatorios periódicos. Las notificaciones de cita creada, modificada/reprogramada y cancelada mantienen los tres destinatarios definidos en §5.1.2.

---

## 7. Canales

La arquitectura debe permitir evolución a múltiples canales:

```text
Notification
    ├── Email
    ├── WhatsApp   (futuro)
    └── SMS / otros (futuro)
```

La primera versión implementa únicamente **Email**.

**WhatsApp queda fuera de la primera versión.**

La lógica de negocio no debe depender directamente de un proveedor concreto.

---

## 8. Separación de responsabilidades

Las apps transversales `notifications` y `audit` permanecen separadas de las apps de dominio.

### 8.1 `notifications`

Responsable de:

- intención de notificación;
- plantillas/representación;
- recordatorios;
- coordinación del transporte;
- resultado del envío;
- abstracción del proveedor de correo.

No es responsable de crear, cancelar o reprogramar citas ni de decidir reglas clínicas.

### 8.2 `audit`

Responsable de:

- registrar eventos de auditoría;
- conservar trazabilidad;
- permitir la consulta administrativa autorizada del audit trail;
- registrar actor, contexto y resultado cuando corresponda.

La consulta del audit trail queda restringida exclusivamente a **Administradores autorizados**.

No es responsable de autorizar operaciones, modificar datos de dominio ni sustituir historia clínica.

---

## 9. Arquitectura de notificaciones

La forma conceptual es:

```text
Business Operation
       ↓
Notification Intent
       ↓
Notification Service
       ↓
Transport abstraction
       ↓
Email transport
```

La operación de negocio solicita una notificación; no conoce el proveedor SMTP/transporte concreto.

No se introduce un sistema distribuido de eventos por defecto.

Redis/Celery u otra infraestructura asíncrona solo debe incorporarse cuando exista una necesidad real para recordatorios, reintentos o envío diferido y sea consistente con la infraestructura ya contemplada por el proyecto.

---

## 10. Integración con fases anteriores

Fase 6 reutiliza las operaciones ya existentes.

Como mínimo, debe poder reaccionar a:

- invitación de registro;
- verificación de correo;
- recuperación de contraseña;
- cita creada;
- cita modificada/reprogramada;
- cita cancelada.

Agenda continúa siendo la autoridad sobre creación, modificación y cancelación de `Appointment`.

Fase 6 no duplica reglas de Agenda.

---

## 11. Auditoría transversal

Debe existir un módulo de auditoría transversal.

El catálogo base de auditoría contempla, como mínimo:

- inicio de sesión;
- consulta de expediente;
- creación/modificación de consulta;
- creación/modificación de receta;
- generación de documento;
- descarga de documento;
- modificación de paciente;
- cambio de permisos;
- desactivación de usuario;
- acceso administrativo a información sensible.

Los documentos derivados deberán convertir estos elementos en una taxonomía técnica concreta sin alterar el significado de las operaciones origen.

Además, **todo rechazo correspondiente a una operación incluida en el catálogo base debe generar un `AuditEvent`**. Esto permite registrar intentos no autorizados o rechazados además de las operaciones efectivamente realizadas.

**Precisión PD-002 (decisión final del propietario, incorporada en la ronda de corrección
post-implementación — no reabre esta regla, la precisa):** esta obligación aplica a los rechazos
que alcanzan el boundary instrumentado de TeCuidoApp y para los que puede identificarse un actor
real (`User`) al que atribuir el evento — `record_event`/`safe_record_event` exigen un actor real
por invariante ya cerrada de Fase 3 (AH-086), y esta fase no la relaja. Quedan fuera, sin que ello
incumpla esta regla: fallos previos al boundary de auditoría, rechazos del framework anteriores a
la instrumentación propia de TeCuidoApp, y casos en los que no puede resolverse ningún actor (p.
ej. un intento de login contra un correo que no existe en el sistema). Detalle completo y ejemplos
en `docs/design/phase-6-audit-domain.md` §4 y `docs/phases/phase-6-implementation-summary.md`.

---

## 12. Principios de auditoría

La auditoría:

```text
NO concede permisos
NO modifica el dominio
NO sustituye historia clínica
NO reemplaza autorización
```

Un evento exitoso debe representar una operación efectivamente realizada.

Si la operación hace rollback, no debe registrarse como éxito persistido.

Los eventos pueden distinguir:

- intento;
- éxito;
- rechazo;
- error;
- repetición/idempotencia cuando aplique.

La auditoría de Fase 6 exige registrar los **rechazos de las operaciones comprendidas en el catálogo base**, con la misma precisión PD-002 de §11: dentro del boundary instrumentado y con actor identificable.

---

## 13. Información del evento

El evento de auditoría debe poder identificar, cuando corresponda:

- actor;
- recurso/contexto;
- operación;
- fecha y hora;
- resultado;
- correlación.

No debe copiar el contenido clínico protegido dentro del evento por defecto.

No debe copiar cuerpos completos de requests ni secretos.

### 13.1 Retención de auditoría

Los `AuditEvent` se conservarán **indefinidamente**.

No existirá depuración automática por antigüedad.

La depuración de información de auditoría, cuando sea requerida para liberar espacio u otra necesidad operativa, será **manual** y no forma parte de un proceso automático de Fase 6.

---

## 14. Consentimientos y aceptación

Fase 6 contempla únicamente el mecanismo técnico para registrar la aceptación de **documentos de la plataforma**:

- aviso de privacidad;
- términos y condiciones.

No se incluyen en esta fase consentimientos clínicos específicos ni otros consentimientos cuyo contenido, finalidad o obligatoriedad jurídica pertenezcan al dominio clínico o a una definición normativa distinta.

Como mínimo se registra:

```text
Usuario
Fecha/hora
Versión del documento aceptado
```

La implementación técnica no determina qué documento o requisito es jurídicamente obligatorio más allá del alcance funcional congelado en esta fase.

---

## 15. Privacidad de notificaciones

Las notificaciones deberán aplicar el principio de mínima información necesaria.

Un usuario que pueda consultar información clínica en la plataforma no implica que todo ese contenido deba enviarse por correo.

Los documentos derivados definirán el contenido funcional de cada notificación sin exponer innecesariamente información clínica sensible.

---

## 16. Seguridad

Fase 6 respetará como mínimo:

- autenticación existente;
- autorización existente;
- CSRF;
- secretos fuera del código;
- configuración segura de producción;
- protección frente a accesos directos no autorizados;
- protección de información sensible en logs;
- mensajes de error sin exposición innecesaria.

La primera versión no incorpora automáticamente:

- MFA/2FA;
- cifrado universal por campo;
- SIEM;
- DLP;
- detección avanzada de anomalías;
- break-glass.

---

## 17. Proveedor de correo

El diseño separará:

```text
contenido/plantilla
        +
intención de envío
        +
transporte
```

La elección de proveedor y sus credenciales pertenece a configuración/infraestructura.

No debe entrar al dominio una dependencia directa a un proveedor específico.

---

## 18. Persistencia de notificaciones

Los documentos derivados deben determinar el mínimo de información que debe conservarse para:

- trazabilidad;
- reintento;
- diagnóstico operacional;
- historial de envío cuando exista necesidad real.

No se debe crear una bandeja o historial complejo de notificaciones sin un requerimiento que lo justifique.

---

## 19. Asincronía y programación

Los recordatorios requieren ejecución diferida.

La implementación debe aprovechar las capacidades existentes del proyecto cuando sean apropiadas.

La arquitectura no obliga a incorporar infraestructura asíncrona para operaciones que puedan permanecer síncronas sin pérdida funcional.

---

## 20. Idempotencia de notificaciones

Los reintentos no deben producir múltiples efectos funcionales de la misma notificación.

El diseño derivado deberá establecer una identidad operacional suficiente para distinguir:

```text
misma operación
≠
notificación diferente
```

El mecanismo debe reutilizar los patrones de idempotencia ya utilizados por TeCuidoApp siempre que sean adecuados.

---

## 21. Fallos del transporte

El fallo del proveedor de correo no debe revertir una operación de negocio ya confirmada.

Ejemplo:

```text
Appointment creado correctamente
        ↓
envío de correo falla
        ↓
Appointment permanece creado
```

El subsistema de notificaciones será responsable del tratamiento del fallo, reintento y observabilidad según los contratos derivados.

No se debe tratar un proveedor externo como parte de una única transacción ACID con la operación de negocio.

---

## 22. Reutilización de componentes

Se priorizará:

1. `AuditEvent` y capacidades de auditoría existentes;
2. autenticación y cuentas existentes;
3. `Appointment` y servicios existentes;
4. configuración y convenciones Django existentes;
5. patrones de errores, transacciones y pruebas de Fases 1–5.

No deben crearse mecanismos paralelos sin necesidad demostrada.

---

## 23. Límites de alcance

### Dentro de Fase 6

- Email.
- Recordatorios 15/10/5/1 días.
- Notificaciones de eventos operativos definidos.
- Auditoría transversal.
- Trazabilidad.
- Registro técnico de aceptación de documentos de plataforma.
- Controles de seguridad requeridos para estas capacidades.

### Fuera de la primera versión

- WhatsApp.
- SMS real.
- MFA/2FA.
- FHIR/interoperabilidad.
- facturación.
- pagos en línea.
- inventario.
- nuevas capacidades clínicas no definidas para esta fase.

---

## 24. Prohibiciones arquitectónicas

Fase 6 no debe introducir sin decisión explícita:

- modificación de reglas de Agenda;
- nueva fuente de verdad para `Appointment`;
- nueva fuente de verdad paralela para auditoría;
- lógica de negocio duplicada;
- acoplamiento del dominio a un proveedor de correo;
- microservicios;
- event sourcing;
- CQRS;
- broker adicional sin necesidad;
- ACL paralela;
- almacenamiento paralelo de información clínica;
- almacenamiento indiscriminado de contenido clínico en logs.

---

## 25. Documentos derivados

Los documentos posteriores de Fase 6 deberán derivarse de este Design Freeze y cubrir, como mínimo:

```text
phase-6-documentation-index.md
phase-6-notification-domain.md
phase-6-notification-data-model.md
phase-6-notification-service-contracts.md
phase-6-notification-api-contracts.md
phase-6-notification-security-and-privacy.md
phase-6-audit-domain.md
phase-6-audit-data-model.md
phase-6-audit-service-contracts.md
phase-6-audit-api-contracts.md
phase-6-audit-and-history.md
phase-6-consent-domain.md
phase-6-consent-service-contracts.md
phase-6-ux.md
phase-6-screens.md
phase-6-testing-strategy.md
phase-6-implementation-handoff.md
phase-6-final-report.md
```

El índice podrá consolidar documentos si demuestra que hacerlo no crea pérdida de claridad ni responsabilidades mezcladas.

---

## 26. Relación con fases anteriores

Fase 6 utiliza las capacidades existentes y no reabre fases cerradas:

```text
Agenda
→ Fase 2

ClinicalEncounter / expediente
→ Fase 3

ClinicalDocument / documentos
→ Fase 4

CareRequest / operación
→ Fase 5

Notificaciones + auditoría transversal
→ Fase 6
```

Una nueva necesidad de una fase previa debe resolverse respetando la trazabilidad y reglas de esa fase, no trasladando lógica a `notifications` o `audit`.

---

## 27. Decisiones funcionales congeladas

Quedan congeladas las siguientes reglas provenientes de requisitos, arquitectura y decisiones explícitas del propietario del proyecto:

| ID | Tema | Regla |
|---|---|---|
| F6-D01 | Destinatarios de citas | Cita creada, modificada/reprogramada y cancelada: Patient + Responsible autorizado + Doctor asignado |
| F6-D02 | Destinatarios de recordatorios | Recordatorios 15/10/5/1 días: Patient + Responsible autorizado; el Doctor asignado no recibe recordatorios periódicos |
| F6-D03 | Opt-out operativo | Las notificaciones operativas y recordatorios de Fase 6 no pueden desactivarse por el usuario |
| F6-D04 | Consentimientos y aceptación | Solo aceptación de documentos de plataforma: Aviso de Privacidad y Términos y Condiciones; Usuario + fecha/hora + versión |
| F6-D05 | Acceso al audit trail | Solo Administradores autorizados pueden consultar el historial de auditoría |
| F6-D06 | Alcance de auditoría | Catálogo base + auditoría de los rechazos correspondientes a las operaciones del catálogo |
| F6-D07 | Retención de auditoría | Retención indefinida; no hay depuración automática y cualquier depuración es manual |
| — | Identidad de fase | Fase 6 = Notificaciones y auditoría |
| — | Canal inicial | Email |
| — | WhatsApp | Fuera de la primera versión |
| — | Recordatorios | 15, 10, 5 y 1 días antes |
| — | Cita creada | El correo informa que la reserva fue realizada |
| — | Estado de Appointment | El correo no crea un estado de confirmación adicional |
| — | Auditoría | Módulo transversal |
| — | AuditEvent | No debe copiar contenido clínico por defecto |
| — | Agenda | Fuente de verdad de reglas de cita |

---

## 28. Decisiones técnicas pendientes de los documentos derivados

Este Design Freeze no inventa detalles físicos que aún no están respaldados por los requisitos.

Los documentos derivados podrán cerrar técnicamente:

- estructura física de notificaciones;
- modelo de persistencia;
- taxonomía técnica y mapeo de eventos auditables;
- plantillas;
- mecanismo de programación;
- reintentos;
- deduplicación;
- estrategia técnica de almacenamiento/archivo de datos de notificaciones, si resulta necesaria;
- endpoints;
- pantallas;
- pruebas.

Estas decisiones deben priorizar:

```text
simplicidad
+
reutilización
+
consistencia con Fases 1–5
+
Django/PostgreSQL
+
infraestructura mínima necesaria
```

Si una elección implica una política de producto, privacidad, legalidad o una ampliación de alcance, debe detenerse y solicitar decisión explícita.

---

## 29. Regla de cambio del Design Freeze

Si durante el diseño o implementación aparece una necesidad incompatible:

```text
NO corregir silenciosamente.
NO ampliar alcance en un documento derivado.
NO resolver una política por preferencia del implementador.
```

Debe:

1. identificarse la contradicción;
2. explicarse su impacto;
3. proponerse una solución o alternativas;
4. obtener la decisión correspondiente;
5. actualizar este Design Freeze y documentos afectados;
6. conservar trazabilidad.

---

## 30. Gate de implementación

La implementación de Fase 6 solo puede comenzar cuando el paquete de documentos derivados:

1. sea coherente con este Design Freeze;
2. sea coherente con `requirements.md` y `docs/architecture.md`;
3. no contenga decisiones funcionales pendientes;
4. identifique dependencias con Fases 1–5;
5. defina la estrategia de pruebas;
6. permita implementar sin inventar reglas esenciales.

---

## 31. Estado

**DESIGN FREEZE — FASE 6: NOTIFICACIONES Y AUDITORÍA**

Este estado significa que el alcance y los principios normativos están congelados para elaborar el diseño técnico detallado.

No significa:

```text
Fase 6 implementada
Fase 6 validada
Fase 6 cerrada
```

El cierre de la fase requerirá posteriormente implementación, pruebas, auditoría y un reporte final independiente.

---

## 32. Resumen normativo

```text
                 FASE 6
        NOTIFICACIONES Y AUDITORÍA
                     │
       ┌─────────────┴─────────────┐
       ▼                           ▼
┌───────────────┐           ┌───────────────┐
│ notifications │           │     audit     │
└───────┬───────┘           └───────┬───────┘
        │                           │
        ▼                           ▼
   Email / reminders          AuditEvent / trace
        │                           │
        └───────────┬───────────────┘
                    ▼
        Seguridad y trazabilidad
```

Principios centrales:

- no duplicar dominio;
- no cambiar estados clínicos por notificaciones;
- no acoplar proveedores al dominio;
- auditar sin copiar contenido clínico;
- reutilizar capacidades existentes;
- mantener complejidad mínima necesaria;
- conservar la trazabilidad de las decisiones.

**Estado oficial: `DESIGN FREEZE — FASE 6`**

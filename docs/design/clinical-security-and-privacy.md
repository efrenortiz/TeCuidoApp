# TeCuidoApp — Fase 3: Clinical Security and Privacy

**Documento:** `clinical-security-and-privacy.md`  
**Fase:** 3 — Clinical Care  
**Estado:** Cerrada (ratificado en auditoría de cierre, 2026-09-11)  
**Fecha:** 2026-09-11  
**Ámbito:** seguridad técnica y privacidad de información clínica  
**Aplicación prevista:** `medical_records` y componentes transversales del proyecto

---

## 1. Propósito

Este documento traduce las reglas funcionales, de dominio, datos y autorización de Fase 3 a una política única de seguridad y privacidad para TeCuidoApp.

Su objetivo es cerrar las decisiones que todavía no estaban especificadas con suficiente precisión sobre:

- protección de información clínica;
- separación entre autenticación y autorización;
- control de acceso a nivel de objeto;
- protección de consultas y expedientes;
- protección de documentos clínicos futuros;
- manejo de sesiones y credenciales;
- secretos y configuración;
- exposición en logs;
- auditoría;
- eliminación y retención;
- exportaciones e importaciones;
- errores y respuestas HTTP;
- prevención de accesos directos e IDOR;
- privacidad por defecto;
- seguridad operacional mínima.

No sustituye una revisión jurídica de aviso de privacidad, consentimiento informado, conservación documental u otras obligaciones regulatorias. Define las decisiones de ingeniería que TeCuidoApp debe aplicar independientemente de esa revisión legal.

---

# 2. Fuentes normativas

La política debe interpretarse junto con:

```text
requirements.md

docs/architecture.md

docs/phases/phase-3-clinical-encounter.md
docs/design/clinical-encounter-workflow.md
docs/design/clinical-encounter-rules.md
docs/design/clinical-encounter-domain.md
docs/design/clinical-record-domain.md
docs/design/clinical-data-model.md
docs/design/clinical-permissions.md
```

## 2.1 Jerarquía

Cuando exista una contradicción sobre el comportamiento específico de Fase 3:

1. decisión funcional posterior y explícita de Fase 3;
2. `clinical-permissions.md` para autorización;
3. `clinical-security-and-privacy.md` para controles de seguridad y privacidad;
4. `clinical-data-model.md` para integridad física;
5. `clinical-record-domain.md` y `clinical-encounter-domain.md` para dominio;
6. `requirements.md` y arquitectura general como marco global.

Una política de seguridad no debe reinterpretar una regla clínica ya cerrada.

---

# 3. Principios rectores

## SEC-001 — Privacy by default

La información clínica debe considerarse privada por defecto.

Ningún recurso clínico será públicamente accesible salvo que una decisión futura lo autorice explícitamente y exista un modelo de exposición separado.

## SEC-002 — Deny by default

Cuando la autorización no pueda demostrarse de forma suficiente, la operación se rechaza.

## SEC-003 — Least privilege

Cada actor debe recibir únicamente las capacidades necesarias para la operación que está realizando.

## SEC-004 — Server-side enforcement

Las reglas de seguridad se validan en backend. La interfaz no es frontera de seguridad.

## SEC-005 — Object-level authorization

La existencia de un permiso funcional no sustituye la comprobación de que el actor puede acceder al objeto específico.

## SEC-006 — Separation of concerns

Autenticación, autorización, dominio clínico, almacenamiento de archivos y auditoría son responsabilidades separadas.

## SEC-007 — No security by obscurity

Una URL no pública, un UUID o un identificador difícil de adivinar no sustituyen autorización.

## SEC-008 — Fail closed

Ante una excepción, ausencia de relación, inconsistencia de datos o duda no resoluble, el acceso clínico debe fallar de forma segura.

## SEC-009 — Historical integrity

La seguridad no debe permitir que una corrección administrativa borre o reescriba silenciosamente la historia clínica.

## SEC-010 — Auditability

Las operaciones sensibles deben ser reconstruibles mediante auditoría suficiente, sin convertir el propio log en una copia de la historia clínica.

---

# 4. Clasificación de información

## SEC-011 — Información clínica sensible

Se consideran sensibles, como mínimo:

- `MedicalRecord`;
- `ClinicalEncounter`;
- diagnósticos escritos por profesionales;
- exploraciones físicas;
- padecimientos actuales;
- planes e indicaciones;
- antecedentes clínicos;
- alergias;
- recetas;
- estudios y resultados;
- alertas clínicas;
- documentos clínicos;
- metadatos que permitan inferir atención médica.

## SEC-012 — Datos de identidad y contacto

Nombre, teléfono, correo y demás datos personales de `Patient` también requieren protección, aunque no sean clínicos por sí mismos.

## SEC-013 — Datos administrativos

Los datos de agenda pueden ser menos sensibles que una nota clínica, pero siguen sujetos a autorización por objeto.

## SEC-014 — No mezclar clasificación con permisos

Que un dato sea “clínico” no determina por sí solo quién puede verlo. La clasificación identifica sensibilidad; la autorización define acceso.

---

# 5. Autenticación

## SEC-015 — Usuario autenticado obligatorio

Toda operación clínica protegida requiere un usuario autenticado.

## SEC-016 — Cuenta activa

Una cuenta desactivada no puede iniciar nuevas operaciones clínicas.

## SEC-017 — No confiar en identidad enviada por cliente

El backend debe obtener la identidad del actor desde la sesión/token autenticado, no desde un `user_id` enviado arbitrariamente en el payload.

## SEC-018 — Verificación de correo

Las operaciones protegidas deben respetar el estado de verificación de correo establecido por la política de identidad del proyecto.

## SEC-019 — Recuperación segura de contraseña

La recuperación de contraseña debe utilizar tokens de un solo uso y duración limitada, sin revelar si una cuenta existe más allá de lo estrictamente necesario.

## SEC-020 — No registrar contraseñas

Contraseñas, códigos de recuperación y secretos equivalentes nunca deben escribirse en logs.

## SEC-021 — Política de sesión centralizada

La expiración, renovación, invalidación y protección de sesión deben residir en la configuración transversal de autenticación, no en cada vista clínica.

## SEC-022 — Invalidación de sesión

Una sesión asociada a una cuenta desactivada no debe seguir permitiendo operaciones clínicas nuevas.

---

# 6. Autorización

## SEC-023 — Autorización separada por operación

Cada operación clínica debe verificar explícitamente la capacidad requerida:

```text
read
create
edit
complete
manage
export
```

No se debe reutilizar un permiso de lectura como sustituto de uno de escritura.

## SEC-024 — Consultar antes de mutar

Las operaciones de modificación deben evaluar autorización antes de ejecutar la mutación y volver a comprobar las invariantes relevantes dentro de la transacción.

## SEC-025 — Querysets autorizados

Para listar o buscar recursos clínicos, el servidor debe construir querysets limitados por el contexto autorizado del actor.

## SEC-026 — No filtrar después de recuperar todo

No se debe descargar a memoria toda la tabla clínica y filtrar posteriormente en Python como mecanismo de autorización.

## SEC-027 — IDs opacos no son autorización

Cambiar un `encounter_id` por otro nunca debe ampliar acceso.

## SEC-028 — Denegación uniforme

Cuando sea razonable, recursos protegidos inexistentes y recursos existentes no autorizados deben producir respuestas indistinguibles para reducir enumeración.

## SEC-029 — Separación de lectura y escritura

El derecho a leer un expediente no implica derecho a modificarlo.

## SEC-030 — Permisos de exportación separados

Exportar o descargar información masivamente debe considerarse una operación distinta de la lectura interactiva y requiere una autorización explícita.

---

# 7. Reglas específicas de ClinicalEncounter

## SEC-031 — Inicio protegido

La creación de un `ClinicalEncounter` sólo puede producirse mediante la operación de inicio autorizada.

## SEC-032 — Médico asignado

El inicio depende de que el actor sea el médico asignado a la cita válida, conforme a Agenda y `clinical-permissions.md`.

## SEC-033 — Una sola creación efectiva

La combinación de transacción y unicidad de `appointment_id` debe impedir duplicados concurrentes.

## SEC-034 — Guardado de encuentro abierto

Sólo el médico autorizado puede modificar un `ClinicalEncounter` en `IN_PROGRESS`.

## SEC-035 — Completar encuentro

Sólo el médico autorizado puede completar el encuentro.

## SEC-036 — Bloqueo después de completar

Un `ClinicalEncounter` `COMPLETED` no puede modificarse mediante ninguna operación funcional ordinaria.

## SEC-037 — No reapertura

Ningún permiso administrativo ordinario debe permitir reabrir un encuentro completado.

## SEC-038 — No borrado clínico

No debe existir endpoint o acción de UI para eliminar funcionalmente un `ClinicalEncounter`.

## SEC-039 — Save versus complete

La operación de completar debe respetar la misma autorización del encuentro abierto y persistir la última modificación autorizada de manera atómica.

## SEC-040 — Seguridad ante concurrencia

Debe prevalecer el estado persistido dentro de la transacción, no la suposición del cliente sobre el estado del encuentro.

---

# 8. Reglas específicas de MedicalRecord

## SEC-041 — Un expediente por paciente

El acceso a `MedicalRecord` se resuelve a partir del `Patient` autorizado.

## SEC-042 — No propiedad del médico

El médico no es propietario del expediente; sólo tiene las capacidades de acceso que las reglas de autorización le concedan.

## SEC-043 — No reasignación

El vínculo `MedicalRecord → Patient` no puede modificarse para transferir historia a otra persona.

## SEC-044 — No reemplazo total

No debe existir una API genérica que acepte un objeto completo y reemplace indiscriminadamente todos los datos del expediente.

## SEC-045 — Escritura por intención

La modificación del expediente debe efectuarse mediante operaciones explícitas para campos o secciones definidas por el dominio.

## SEC-046 — Historial clínico protegido

La seguridad no debe permitir la sobreescritura silenciosa de hechos históricos.

## SEC-047 — No diagnóstico automático

Ningún control de seguridad debe interpretarse como permiso para ejecutar inferencia o diagnóstico automático en Fase 3.

## SEC-048 — Resumen clínico derivado

Cuando exista un resumen de expediente, su lectura debe respetar la autorización del expediente y no debe convertirse en una fuente paralela de permisos.

---

# 9. Médico y relación médico-paciente

## SEC-049 — DoctorClinic no equivale a acceso histórico

Estar asociado a una clínica no concede lectura indiscriminada de expedientes.

## SEC-050 — Primera atención

Un médico puede iniciar una primera consulta válida sin relación `DoctorPatientRelationship` previa cuando Agenda lo permita.

## SEC-051 — Primera atención no crea acceso longitudinal automático

La creación del primer encuentro no debe otorgar retrospectivamente acceso completo al historial por tiempo indefinido.

## SEC-052 — Relación activa para lectura longitudinal

La lectura histórica ordinaria por otro médico se basa en una `DoctorPatientRelationship` autorizante vigente, conforme a `clinical-permissions.md`.

## SEC-053 — Acceso contextual

La existencia de una cita o encuentro actual puede proporcionar acceso contextual a la información necesaria para esa atención, sin crear por ello una relación longitudinal permanente.

## SEC-054 — Revocación

La revocación de la relación debe impedir nuevo acceso longitudinal ordinario, sin alterar la autoría de información histórica ya registrada.

---

# 10. Paciente y responsable

## SEC-055 — Paciente: alcance propio

El paciente sólo accede a su propio contexto autorizado.

**Cerrado (auditoría de cierre, 2026-09-11):** el alcance exacto de campos está definido en `clinical-permissions.md` P-017 y `clinical-record-domain.md` CR-034 (Decisión D-004) — los cinco campos obligatorios completos de cada `ClinicalEncounter` propio en `COMPLETED`, metadatos y campos opcionales. Este documento no introduce una restricción adicional de campo.

## SEC-056 — Responsable: relación activa

El responsable accede sólo a pacientes con relación `ResponsiblePatientRelationship.ACTIVE` cuando la política clínica lo permita.

## SEC-057 — Cambio menor → adulto

El cambio de régimen no debe duplicar ni mover físicamente el expediente.

## SEC-058 — Recalcular autorización

Las decisiones de autorización deben evaluarse según el estado actual del paciente y sus relaciones, no según permisos históricos cacheados indefinidamente.

## SEC-059 — No herencia automática al adulto

Un responsable de menor no conserva automáticamente capacidad equivalente para el paciente después de que éste pase al régimen adulto.

---

# 11. Administrador y soporte

## SEC-060 — Superusuario no equivale a lector clínico ordinario

La capacidad técnica de `is_superuser` no debe traducirse automáticamente en un bypass genérico de privacidad clínica.

## SEC-061 — Soporte explícito

Cuando una función administrativa requiera acceder a información clínica sensible, debe existir una capacidad funcional explícita, separada y auditable.

**Nota de estado (revisión de cierre, 2026-09-11):** capacidad no implementada en Fase 3 — ver la nota equivalente en `clinical-permissions.md` P-040. Ningún administrador tiene hoy ningún camino de acceso a información clínica.

## SEC-062 — No endpoint bypass

No debe existir un endpoint administrativo genérico que devuelva cualquier registro clínico mediante un `id` sin autorización contextual. Verificado: no existe ninguno en el código actual.

## SEC-063 — Auditoría obligatoria de soporte

Los accesos administrativos excepcionales a información clínica deben generar auditoría suficiente para identificar actor, momento, recurso y motivo/contexto disponible — aplicable cuando la capacidad de SEC-061 se implemente.

## SEC-064 — No acciones clínicas por rol administrativo

El rol administrativo no permite iniciar, completar o editar un `ClinicalEncounter` por sí mismo.

## SEC-065 — No reapertura administrativa

Ni siquiera un administrador debe reabrir un encuentro `COMPLETED` mediante una operación ordinaria.

---

# 12. Documentos clínicos

## SEC-066 — Almacenamiento privado

Los archivos clínicos deben almacenarse en un medio privado, nunca en una carpeta pública que dependa de ocultar la URL.

## SEC-067 — Descarga autorizada

La descarga debe pasar por autorización de objeto antes de obtener el archivo.

## SEC-068 — No servir archivos por URL pública

No se debe exponer directamente el directorio o bucket de documentos clínicos al navegador.

## SEC-069 — Validación de archivo

La futura funcionalidad de documentos debe validar al menos:

- tamaño máximo;
- tipo permitido;
- extensión coherente;
- contenido cuando sea viable;
- relación con el paciente/recurso;
- actor que intenta cargarlo.

## SEC-070 — Nombre original no es confiable

El nombre de archivo enviado por cliente no debe convertirse directamente en una ruta de almacenamiento.

## SEC-071 — Path traversal

Las rutas derivadas de datos de usuario no deben permitir `../`, rutas absolutas o equivalentes.

## SEC-072 — Content-Disposition seguro

Las descargas deben utilizar cabeceras seguras y evitar que nombres arbitrarios inyecten cabeceras.

## SEC-073 — Tipos no confiables

No se debe confiar sólo en `Content-Type` enviado por el cliente para decidir que un archivo es seguro.

## SEC-074 — Archivos ejecutables

Los tipos ejecutables no forman parte de la primera política de documentos clínicos permitidos.

## SEC-075 — Versionado independiente

El versionado futuro de documentos debe preservar versiones históricas y no alterar silenciosamente el contenido previamente emitido.

## SEC-076 — Eliminación de documentos

La eliminación funcional de un documento clínico debe seguir una política explícita y no debe convertirse en una forma de borrar historia.

---

# 13. Protección de API y HTTP

## SEC-077 — CSRF

Las operaciones autenticadas mediante sesión web deben conservar protección CSRF.

## SEC-078 — CORS restringido

No se debe habilitar CORS globalmente con `*` para endpoints clínicos autenticados.

## SEC-079 — Métodos HTTP coherentes

Los endpoints deben aceptar únicamente los métodos necesarios para cada operación.

## SEC-080 — Validación de payload

Toda entrada externa debe validarse antes de llegar al dominio.

## SEC-081 — Mass assignment

No se deben aceptar campos arbitrarios de modelos mediante serialización automática sin lista explícita de campos permitidos.

## SEC-082 — No confiar en campos de servidor

Campos como actor, doctor responsable, timestamps de auditoría y autoría no deben poder ser enviados libremente por el cliente.

## SEC-083 — Rate limiting

Las operaciones sensibles y de autenticación deben poder estar sujetas a límites de frecuencia apropiados. Fase 3 no necesita todavía una política de números exactos, pero la arquitectura no debe impedirla.

## SEC-084 — Enumeración de recursos

Las APIs clínicas deben evitar respuestas que permitan recorrer IDs consecutivos para descubrir pacientes o encuentros.

## SEC-085 — Paginación autorizada

La paginación debe aplicarse sobre el queryset ya autorizado, no antes de determinar el alcance permitido.

---

# 14. Protección contra IDOR

## SEC-086 — Regla general

Toda referencia externa a `patient_id`, `record_id`, `encounter_id`, `appointment_id` o futuro `document_id` debe validarse contra autorización.

## SEC-087 — IDOR de paciente

Conocer el ID de otro paciente no concede acceso.

## SEC-088 — IDOR de encounter

Conocer el ID de un encuentro no concede acceso.

## SEC-089 — IDOR de documento

Conocer un nombre de archivo o identificador de documento no concede descarga.

## SEC-090 — IDOR en endpoints secundarios

Endpoints anidados como `/patients/{id}/encounters/` deben volver a validar el paciente y el actor.

## SEC-091 — No confiar en nesting

El hecho de que una URL esté anidada no demuestra que el recurso hijo pertenezca al recurso padre especificado por el cliente.

## SEC-092 — Verificación cruzada

Cuando existan relaciones cruzadas, el servicio debe comprobarlas explícitamente antes de devolver datos.

---

# 15. Datos en logs

## SEC-093 — Logs operativos mínimos

Los logs técnicos deben contener la información necesaria para diagnosticar fallos sin convertirse en un duplicado del expediente.

## SEC-094 — No loggear contenido clínico por defecto

No deben registrarse en logs generales campos como padecimiento actual, exploración, diagnóstico, plan o antecedentes completos.

## SEC-095 — No loggear tokens

Tokens de sesión, recuperación, acceso, refresh o equivalentes no deben escribirse en claro.

## SEC-096 — No loggear secretos

Contraseñas, API keys, credenciales de proveedores y secretos de infraestructura no deben aparecer en logs.

## SEC-097 — IDs con minimización

Cuando un identificador sea necesario para diagnóstico, debe preferirse el identificador técnico mínimo necesario y evitar incluir datos personales en el mensaje.

## SEC-098 — Error técnico separado de respuesta clínica

El detalle completo de una excepción debe ir a logs protegidos; el cliente recibe un error seguro y utilizable.

---

# 16. Mensajes de error

## SEC-099 — No filtrar información sensible en errores

Las respuestas no deben revelar nombres, diagnósticos, relaciones o datos del recurso al que el usuario no tiene acceso.

## SEC-100 — 401 versus 403

La implementación debe utilizar consistentemente autenticación requerida y autorización denegada, evitando diferencias innecesarias que permitan enumeración cuando la política lo requiera.

## SEC-101 — No stack traces en producción

Nunca deben mostrarse trazas de Python/Django al usuario final en producción.

## SEC-102 — Errores de dominio explícitos

Las reglas clínicas deben traducirse a errores funcionales estables sin exponer detalles internos de PostgreSQL.

## SEC-103 — Integridad interna

Una violación de integridad de base de datos debe registrarse técnicamente y devolverse al cliente como error funcional seguro.

---

# 17. Protección de base de datos

## SEC-104 — Credenciales fuera del código

Las credenciales de PostgreSQL deben configurarse fuera del repositorio mediante variables de entorno o mecanismo equivalente seguro.

## SEC-105 — Principio de mínimo privilegio

La cuenta de aplicación en producción debe tener únicamente los permisos necesarios para operar el esquema.

## SEC-106 — No usar superusuario PostgreSQL para la aplicación

La aplicación no debe conectarse normalmente con una cuenta PostgreSQL superuser.

## SEC-107 — Integridad en DB

Unicidad, claves foráneas y constraints estructurales definidos en `clinical-data-model.md` deben estar en PostgreSQL cuando corresponda.

## SEC-108 — Transacciones

Las operaciones de inicio, guardado crítico y cierre clínico que requieran atomicidad deben ejecutarse transaccionalmente.

## SEC-109 — Backups

La estrategia operacional debe contemplar copias de seguridad de la base de datos y verificación de restaurabilidad, aunque su automatización detallada pertenezca a infraestructura.

## SEC-110 — Backups protegidos

Las copias que contengan datos clínicos deben recibir una protección equivalente al entorno de producción respecto de acceso y almacenamiento.

---

# 18. Secretos y configuración

## SEC-111 — Secretos fuera de Git

No se deben commitear secretos reales al repositorio.

## SEC-112 — `.env.example` sin secretos reales

El archivo de ejemplo debe documentar nombres de variables sin valores confidenciales reales.

## SEC-113 — SECRET_KEY

`SECRET_KEY` debe configurarse externamente y no utilizar un valor compartido públicamente en producción.

## SEC-114 — Credenciales de correo

Credenciales SMTP y tokens de proveedores deben almacenarse fuera del código.

## SEC-115 — Rotación futura

La arquitectura debe permitir rotar secretos sin cambiar código clínico.

## SEC-116 — Entornos separados

Desarrollo, pruebas y producción deben usar configuraciones y credenciales separadas.

## SEC-117 — No usar producción para pruebas ordinarias

Los datos clínicos reales no deben utilizarse en ambientes de desarrollo o prueba salvo mediante una política específica de datos anonimizados o controles equivalentes.

---

# 19. Protección en desarrollo y pruebas

## SEC-118 — Datos sintéticos preferidos

Los tests funcionales deben utilizar datos clínicos sintéticos.

## SEC-119 — Fixtures sin datos reales

Los fixtures del repositorio no deben contener expedientes reales.

## SEC-120 — Capturas y logs de pruebas

La evidencia de pruebas compartida en tickets o documentos debe evitar datos clínicos reales.

## SEC-121 — Debug mode

`DEBUG=True` no debe utilizarse en producción.

## SEC-122 — Host allowlist

La configuración de producción debe restringir hosts válidos.

## SEC-123 — Cookies seguras

En producción, cookies de sesión y equivalentes deben configurarse con las banderas de seguridad apropiadas para HTTPS.

---

# 20. HTTPS y transporte

## SEC-124 — HTTPS obligatorio en producción

Las operaciones clínicas deben transmitirse sobre HTTPS en producción.

## SEC-125 — No enviar secretos por query string

Tokens, contraseñas y credenciales no deben viajar como parámetros de URL.

## SEC-126 — URLs clínicas no son credenciales

Una URL de detalle de expediente o encuentro nunca debe ser tratada como un secreto suficiente para autorizar acceso.

## SEC-127 — HSTS según infraestructura

La producción debe poder habilitar HSTS cuando el despliegue HTTPS sea estable.

---

# 21. Caché y navegador

## SEC-128 — No cachear clínicos públicamente

Las respuestas con información clínica no deben configurarse para caché público compartido.

## SEC-129 — No almacenar documentos sensibles en cache CDN público

Los documentos clínicos deben excluirse de caches públicos.

## SEC-130 — Headers de control

Las respuestas sensibles deben usar cabeceras coherentes con su nivel de sensibilidad, especialmente `Cache-Control`.

## SEC-131 — Evitar filtración por referer

Cuando exista riesgo razonable de exponer identificadores sensibles, el producto debe aplicar una política de `Referrer-Policy` adecuada.

## SEC-132 — Portales compartidos

La UI no debe asumir que un ordenador compartido mantiene aislamiento entre usuarios; la sesión debe invalidarse y el navegador debe recibir instrucciones adecuadas de no almacenamiento cuando corresponda.

---

# 22. Exportación de expediente

## SEC-133 — Exportación no es lectura ordinaria

Generar una copia descargable de un expediente es una operación de alto impacto de privacidad.

## SEC-134 — Autorización explícita

La exportación requiere autorización propia y no debe heredarse automáticamente sólo porque el actor pueda visualizar una pantalla.

## SEC-135 — Formato y contenido explícitos

Una exportación debe definir exactamente qué datos incluye y cuáles no.

## SEC-136 — Archivos temporales protegidos

Los archivos temporales generados para exportación deben almacenarse en ubicación privada y eliminarse conforme a una política definida.

## SEC-137 — Auditoría de exportación

La generación y descarga de exportaciones deben auditarse.

## SEC-138 — No exportación administrativa masiva por defecto

Fase 3 no crea una capacidad de exportación masiva global para administradores.

---

# 23. Importación y migración

## SEC-139 — Importaciones futuras separadas

La importación de expedientes externos no forma parte del núcleo operativo de Fase 3.

## SEC-140 — Validación de origen

Una futura importación debe validar formato, origen, actor autorizado y correspondencia con el paciente.

## SEC-141 — No importar a ciegas

Los datos externos no deben insertarse directamente en modelos clínicos sin validación de dominio.

## SEC-142 — Trazabilidad de importación

Una futura importación deberá poder distinguir datos originados en TeCuidoApp de datos migrados de fuentes externas.

## SEC-143 — No alterar historia original sin política

La migración no debe sobrescribir información clínica existente sin una estrategia explícita de reconciliación.

---

# 24. Retención, baja lógica y borrado

## SEC-144 — No borrado físico rutinario

La información clínica importante no debe eliminarse físicamente como operación normal.

## SEC-145 — Baja lógica administrativa

Cuando una entidad permita desactivación, debe preferirse baja lógica sobre borrado destructivo, conforme al modelo del dominio.

## SEC-146 — Baja lógica no significa ocultar historia

Desactivar un paciente, médico o relación no debe desaparecer la historia clínica que legal y funcionalmente deba conservarse.

## SEC-147 — Borrado por dependencia

Las FK de datos clínicos críticos deben configurarse evitando cascadas destructivas accidentales.

## SEC-148 — Retención legal pendiente

Los periodos exactos de conservación clínica no se fijan aquí; requieren decisión legal y de producto antes de implementarse.

---

# 25. Privacidad y consentimiento

## SEC-149 — Aviso de privacidad

El producto debe contemplar la aceptación del aviso de privacidad cuando la funcionalidad legalmente lo requiera.

## SEC-150 — Versión del documento

La aceptación debe registrar la versión del texto aceptado, no sólo un booleano.

## SEC-151 — Timestamp de consentimiento

Debe conservarse fecha/hora y actor asociados al consentimiento.

## SEC-152 — Consentimiento separado de autorización clínica

Aceptar un aviso o término no concede automáticamente permiso para consultar expedientes de terceros.

## SEC-153 — Consentimiento no sustituye relación

El consentimiento no reemplaza las reglas estructurales de `ResponsiblePatientRelationship` ni `DoctorPatientRelationship`.

## SEC-154 — Mecanismo legal fuera del dominio clínico

La lógica de consentimiento debe permanecer separada del modelo de `MedicalRecord` y `ClinicalEncounter`.

---

# 26. Auditoría de seguridad

## SEC-155 — Módulo separado

La auditoría debe vivir en un módulo transversal (`audit` o equivalente), separado del dominio clínico.

## SEC-156 — Lectura clínica sensible

Debe poder auditarse el acceso a información clínica sensible.

## SEC-157 — Escritura clínica sensible

Creación, modificación y finalización de información clínica relevante deben quedar registradas según la estrategia de auditoría del proyecto.

## SEC-158 — Descarga de documentos

Las descargas de documentos clínicos deben auditarse.

## SEC-159 — Acceso administrativo

Los accesos administrativos excepcionales deben auditarse de forma prioritaria.

## SEC-160 — Cambio de permisos

Los cambios de autorización o relaciones relevantes deben generar eventos auditables.

## SEC-161 — Denegaciones críticas

Fase 3 puede registrar denegaciones de acceso clínico sensibles cuando aporten valor de seguridad, evitando ruido excesivo.

## SEC-162 — No almacenar contenido completo en auditoría

El audit log no debe duplicar automáticamente la totalidad del contenido clínico.

## SEC-163 — Metadatos mínimos

Un evento de auditoría debería poder incluir, según el caso:

- actor;
- acción;
- recurso/tipo de entidad;
- identificador técnico del recurso;
- fecha/hora;
- resultado;
- contexto suficiente;
- motivo cuando exista una operación excepcional que lo requiera.

---

# 27. Seguridad de búsqueda

## SEC-164 — Búsqueda limitada por autorización

Las búsquedas de pacientes deben devolver únicamente entidades que el actor puede conocer bajo sus permisos funcionales.

## SEC-165 — No búsqueda global por texto clínico

No se habilita en Fase 3 una búsqueda global sobre el contenido de todas las notas clínicas.

## SEC-166 — No sugerencias que filtren datos

Autocompletados y sugerencias deben respetar exactamente el mismo alcance autorizado que la búsqueda principal.

## SEC-167 — Minimización de resultados

Los resultados de búsqueda deben incluir sólo los campos necesarios para elegir el recurso.

---

# 28. Seguridad de servicios de dominio

## SEC-168 — Servicio como frontera

Las operaciones clínicas críticas deben entrar por servicios de dominio y no por manipulación directa del ORM desde múltiples vistas.

## SEC-169 — Authorization before transaction

La autorización debe verificarse antes de iniciar la mutación, sin confiar únicamente en la UI.

## SEC-170 — Revalidación dentro de transacción

Las condiciones sujetas a concurrencia deben volver a evaluarse sobre datos bloqueados o transaccionalmente consistentes.

## SEC-171 — Servicios no reciben actor arbitrario

El actor efectivo debe proceder del contexto autenticado del request y no de un campo de negocio controlado por el cliente.

## SEC-172 — Reutilización de policy

La lectura, guardado y completado deben reutilizar políticas de autorización comunes para evitar divergencias.

---

# 29. Seguridad de tareas asíncronas futuras

## SEC-173 — Fase 3 no depende de Celery para autorización

Ningún permiso clínico debe depender de que una tarea asíncrona haya corrido previamente.

## SEC-174 — Contexto seguro en tareas

Una futura tarea que maneje documentos o datos clínicos debe transportar sólo identificadores y contexto mínimo, nunca secretos innecesarios.

## SEC-175 — No ejecutar tareas con permisos del usuario implícitos

Una tarea asíncrona no debe asumir que el actor que la programó conserva indefinidamente las mismas autorizaciones al momento de ejecutarse; cuando corresponda, debe volver a evaluar reglas.

---

# 30. Consideraciones específicas de Django

## SEC-176 — ORM preferido

Las consultas clínicas deben usar el ORM de Django o SQL parametrizado; nunca construir SQL con concatenación de entrada del usuario.

## SEC-177 — Consultas parametrizadas

Cuando sea indispensable SQL directo, siempre deben utilizarse parámetros vinculados.

## SEC-178 — CSRF middleware

La configuración de producción debe mantener CSRF activo para el flujo de sesión web.

## SEC-179 — Secure cookies

Las cookies de sesión deben utilizar las opciones seguras adecuadas al despliegue HTTPS.

## SEC-180 — Clickjacking

Las vistas clínicas deben estar protegidas contra embedding no autorizado según la estrategia global de seguridad del proyecto.

## SEC-181 — XSS

El contenido clínico introducido por usuario debe renderizarse de forma segura y no utilizarse como HTML confiable por defecto.

## SEC-182 — Sanitización no sustituye escaping

Para texto clínico simple, el patrón preferido es tratarlo como texto y escapar al renderizar, evitando convertirlo en HTML salvo requerimiento específico.

---

# 31. Contenido clínico y HTML

## SEC-183 — Texto clínico plano en Fase 3

Los cinco campos obligatorios y campos textuales clínicos iniciales deben almacenarse como texto, no como HTML arbitrario.

## SEC-184 — No Markdown ejecutable

No se define en Fase 3 un lenguaje de marcado ejecutable o con HTML embebido para las notas clínicas.

## SEC-185 — Placeholders no son seguridad

La validación de `N/A`, `No aplica` y equivalentes pertenece al dominio clínico; no sustituye controles de seguridad.

---

# 32. Privacidad de cachés de aplicación

## SEC-186 — No cache global de expediente

No se debe usar una cache global compartida para almacenar respuestas de expedientes sin incluir una clave de autorización suficientemente aislada.

## SEC-187 — Cache por usuario o recurso

Una futura cache clínica debe aislar datos por actor y recurso o emplear invalidación/autorización equivalente.

## SEC-188 — Invalidación ante cambio de permisos

Si se implementa cache de lectura clínica, cambios de relación y permisos deben evitar que un acceso revocado siga visible desde cache.

---

# 33. Concurrencia y seguridad

## SEC-189 — No confiar en estado leído previamente

Un cliente no puede asumir que `IN_PROGRESS` o una relación activa seguirá vigente cuando envíe una mutación.

## SEC-190 — Race conditions

Las transiciones sensibles deben protegerse contra solicitudes concurrentes.

## SEC-191 — Doble inicio

Dos solicitudes simultáneas de inicio no deben producir dos encuentros.

## SEC-192 — Doble completion

Dos solicitudes simultáneas de completar no deben producir dos cierres inconsistentes.

## SEC-193 — Save después de completion

Una escritura que llegue después de que otro proceso haya completado el encuentro debe ser rechazada de acuerdo con el estado persistido.

## SEC-194 — Revocación durante acceso

Si una relación autorizante deja de ser válida, un nuevo acceso debe reevaluarla; no se debe asumir autorización eterna por sesión.

---

# 34. Seguridad ante errores de datos

## SEC-195 — Inconsistencia Appointment/Encounter

Una inconsistencia entre `Appointment` y `ClinicalEncounter` no debe abrir acceso clínico adicional.

## SEC-196 — Encounter sin Appointment válido

Un encuentro huérfano debe considerarse error de integridad y no un recurso clínico normal accesible por API.

## SEC-197 — Record de paciente incorrecto

Un expediente que no corresponda al paciente real debe detener la operación y entrar en flujo técnico de corrección/auditoría.

## SEC-198 — No reparar silenciosamente

Los servicios clínicos no deben “arreglar” silenciosamente inconsistencias estructurales mientras procesan una consulta de usuario.

---

# 35. Privacidad en interfaz

## SEC-199 — No mostrar datos innecesarios

Las pantallas deben aplicar minimización: mostrar sólo los datos necesarios para la tarea.

## SEC-200 — Ocultar no sustituye autorización

Ocultar controles clínicos en la UI es un complemento, no una barrera de seguridad.

## SEC-201 — No prefetch indiscriminado

El frontend no debe cargar por anticipado expedientes, documentos o encuentros que el usuario no necesite y quizá no esté autorizado a leer.

## SEC-202 — No persistir clínicos en local storage por defecto

Fase 3 no debe utilizar `localStorage` como repositorio de expediente o nota médica salvo decisión específica futura.

## SEC-203 — Cierre de sesión

Al cerrar sesión, la aplicación debe invalidar el contexto autenticado y evitar que la navegación posterior exponga contenido sensible desde páginas cacheadas.

---

# 36. Registro local y telemetría

## SEC-204 — Telemetría mínima

Métricas y telemetría no deben capturar contenido clínico.

## SEC-205 — Identificadores minimizados

Cuando se necesite correlación técnica, debe preferirse un identificador técnico o hash controlado frente a nombre, correo o diagnóstico.

## SEC-206 — Herramientas de terceros

Cualquier analítica de frontend que pueda recibir datos clínicos debe estar prohibida por defecto.

## SEC-207 — Error tracking

Las herramientas de error tracking deben configurarse para eliminar o enmascarar campos sensibles.

---

# 37. Dependencias externas

## SEC-208 — No enviar expediente a terceros por defecto

Fase 3 no autoriza transmitir contenido de expedientes a proveedores externos salvo integración explícita y documentada.

## SEC-209 — Minimización hacia proveedores

Una futura integración debe enviar sólo los datos estrictamente necesarios.

## SEC-210 — Secrets de proveedores separados

Cada integración debe tener credenciales separadas y configuradas externamente.

## SEC-211 — Fallo seguro de proveedor

Si un proveedor externo falla, la aplicación no debe degradar las reglas de autorización local para completar la operación.

---

# 38. Dispositivo y sesión compartida

## SEC-212 — No asumir dispositivo confiable

Las interfaces clínicas deben funcionar suponiendo que un usuario puede trabajar en un equipo compartido o accesible a terceros.

## SEC-213 — Sesiones visibles

Las áreas sensibles deben mostrar claramente el usuario activo cuando sea apropiado para reducir errores operativos.

## SEC-214 — Evitar exposición accidental

Las pantallas no deben mostrar información clínica completa en listados donde sólo se requiere identificar al paciente.

---

# 39. Seguridad operacional mínima

## SEC-215 — Producción separada

La base de datos y almacenamiento de producción deben estar aislados de desarrollo cuando la infraestructura lo permita.

## SEC-216 — Acceso administrativo a infraestructura

El acceso a servidores, base de datos, almacenamiento y backups debe estar restringido a personal autorizado.

## SEC-217 — Secretos del despliegue

Credenciales de despliegue y administración de infraestructura no deben residir en el código fuente.

## SEC-218 — Parches

Django, Python, PostgreSQL y dependencias críticas deben mantenerse en versiones soportadas durante producción.

## SEC-219 — Vulnerabilidades de dependencias

El proyecto debe disponer de un proceso para identificar vulnerabilidades relevantes de dependencias antes de liberar cambios importantes.

## SEC-220 — Dependencias mínimas

No introducir librerías de seguridad o infraestructura sin una necesidad concreta y evaluación de mantenimiento.

---

# 40. Principios para pruebas de seguridad

## SEC-221 — Test de autorización positiva

Cada operación protegida debe tener pruebas para el actor autorizado.

## SEC-222 — Test de autorización negativa

Cada operación protegida debe tener al menos un caso de actor no autorizado.

## SEC-223 — Test IDOR

Los tests deben intentar acceder a recursos pertenecientes a otro paciente cambiando IDs.

## SEC-224 — Test de concurrencia

Las operaciones críticas deben tener cobertura de solicitudes concurrentes cuando la infraestructura de pruebas lo permita.

## SEC-225 — Test de estado terminal

Debe verificarse que un encuentro `COMPLETED` no pueda editarse.

## SEC-226 — Test de revocación

Debe verificarse que una relación revocada deje de conceder acceso longitudinal nuevo.

## SEC-227 — Test de administrador

Debe verificarse que el rol administrativo no se convierta en bypass clínico genérico.

## SEC-228 — Test de archivos futuros

Cuando se implemente `ClinicalDocument`, debe existir cobertura de autorización de descarga y protección de rutas.

---

# 41. Políticas propuestas que permanecen pendientes de definición futura

## SEC-229 — Periodos legales de retención

Pendiente de decisión jurídica y de producto.

## SEC-230 — Consentimiento clínico específico

La plataforma deberá definir por separado cualquier consentimiento clínico que exceda la aceptación legal de plataforma.

## SEC-231 — Acceso por emergencia

No se habilita en Fase 3. Si se incorpora, deberá existir un flujo explícito, temporal, mínimo y altamente auditable.

## SEC-232 — Break-glass

No existe un bypass de emergencia genérico en Fase 3.

## SEC-233 — Cifrado en reposo

La aplicación debe asumir almacenamiento protegido; la configuración exacta de cifrado en reposo corresponde a infraestructura y despliegue. No se inventa aquí una tecnología concreta.

## SEC-234 — Cifrado de campos

No se introduce cifrado por campo para todos los textos clínicos en Fase 3 sin requerimiento operativo claro, porque complica búsquedas, migraciones y mantenimiento. Una necesidad posterior debe justificarse mediante ADR.

## SEC-235 — MFA

La arquitectura debe poder evolucionar hacia MFA, pero Fase 3 no lo convierte en prerrequisito de dominio clínico sin una decisión de producto e infraestructura.

## SEC-236 — Detección avanzada de anomalías

No se implementan reglas complejas de detección de comportamiento en Fase 3.

---

# 42. Invariantes de seguridad consolidadas

## SI-001

Ningún usuario no autenticado puede acceder a información clínica protegida.

## SI-002

La autenticación no concede por sí sola acceso a ningún paciente concreto.

## SI-003

Toda lectura clínica está limitada por autorización de objeto.

## SI-004

Toda escritura clínica está limitada por autorización de operación y objeto.

## SI-005

El paciente no puede editar la nota profesional de un `ClinicalEncounter`.

## SI-006

El médico no asignado no puede editar un encuentro abierto sólo por pertenecer a la misma clínica.

## SI-007

El médico con acceso longitudinal de lectura no obtiene derecho de escritura.

## SI-008

La relación revocada no conserva acceso longitudinal nuevo por mera existencia de sesión.

## SI-009

El administrador no dispone de bypass clínico genérico.

## SI-010

Los documentos clínicos no se sirven desde rutas públicas sin autorización.

## SI-011

Los logs generales no contienen el contenido completo de la historia clínica.

## SI-012

Los secretos nunca se almacenan en el repositorio.

## SI-013

Un `ClinicalEncounter` completado no puede modificarse mediante la aplicación ordinaria.

## SI-014

Los errores no autorizados no revelan información del recurso protegido.

## SI-015

Los accesos administrativos excepcionales a clínica son auditables.

## SI-016

Los consentimientos de plataforma no sustituyen las relaciones de autorización clínica.

## SI-017

La seguridad no depende de ocultar botones, URLs o IDs.

## SI-018

La inconsistencia de datos no se convierte en una vía de acceso.

## SI-019

Las operaciones concurrentes no deben producir duplicados o bypass de autorización.

## SI-020

El expediente longitudinal no puede reasignarse de paciente.

---

# 43. Matriz resumida de controles

| Control | Fase 3 | Mecanismo principal |
|---|---|---|
| Autenticación | Sí | Django auth / sesión |
| Verificación de correo | Sí | Política de identidad existente |
| Autorización por objeto | Sí | Servicios/policies backend |
| Deny by default | Sí | Capa de autorización |
| CSRF | Sí | Django |
| Protección IDOR | Sí | Querysets y policies autorizadas |
| Privacidad de documentos | Sí, cuando existan | Storage privado + autorización |
| Auditoría sensible | Sí, transversal | `audit` futuro |
| Secretos fuera de código | Sí | Variables de entorno |
| HTTPS producción | Sí | Infraestructura |
| No delete clínico | Sí | Dominio + DB |
| Cifrado de campo universal | No | Requiere ADR futuro |
| MFA obligatorio | No en F3 | Evolución futura |
| Break-glass | No en F3 | Evolución futura |
| Retención legal exacta | Pendiente | Decisión jurídica |

---

# 44. Casos mínimos de seguridad

## Caso S-001 — Paciente accede a otro paciente

**Resultado esperado:** denegación sin revelar datos del segundo paciente.

## Caso S-002 — Responsable sin relación activa

**Resultado esperado:** denegación.

## Caso S-003 — Médico de otra clínica intenta leer historial

**Resultado esperado:** denegación salvo que exista una autorización de dominio explícita que lo permita.

## Caso S-004 — Médico con relación activa intenta editar encuentro ajeno abierto

**Resultado esperado:** denegación; la relación longitudinal de lectura no confiere edición.

## Caso S-005 — Médico asignado completa encuentro válido

**Resultado esperado:** autorización aceptada y cierre atómico.

## Caso S-006 — Administrador intenta reabrir encuentro completado

**Resultado esperado:** denegación.

## Caso S-007 — Cambio de ID en URL

**Resultado esperado:** no cambia el alcance autorizado.

## Caso S-008 — Descarga de archivo con ID conocido

**Resultado esperado:** sólo si el actor tiene autorización sobre el documento.

## Caso S-009 — Solicitud concurrente de inicio

**Resultado esperado:** una única consulta efectiva.

## Caso S-010 — Solicitud después de revocación

**Resultado esperado:** nuevo acceso evaluado con relación actual; no se utiliza autorización obsoleta.

---

# 45. Fuera de alcance de Fase 3

No quedan definidos aquí:

- implementación legal de aviso de privacidad;
- textos jurídicos finales;
- firma electrónica avanzada;
- expediente externo interoperable;
- cifrado específico por campo;
- KMS/HSM concreto;
- MFA obligatorio;
- acceso de emergencia break-glass;
- SIEM o SOC;
- detección avanzada de fraude;
- DLP empresarial;
- política exacta de retención legal;
- procedimiento de respuesta a incidentes completo;
- gestión de consentimientos clínicos específicos;
- integración con aseguradoras o terceros;
- anonimización irreversible para investigación.

Estas materias requieren documentos o ADR específicos cuando entren al roadmap.

---

# 46. Criterios de aceptación

Fase 3 de seguridad y privacidad se considera suficientemente definida cuando:

1. toda lectura clínica pasa por autorización de servidor;
2. toda escritura clínica pasa por autorización de servidor;
3. la matriz de `clinical-permissions.md` puede implementarse sin ambigüedad;
4. no existe bypass clínico genérico por URL, ID o rol administrativo;
5. los encuentros completados permanecen bloqueados;
6. documentos clínicos futuros tendrán storage privado y autorización por objeto;
7. logs generales no contienen notas clínicas completas ni secretos;
8. los accesos sensibles pueden auditarse;
9. secrets y configuración sensible permanecen fuera del repositorio;
10. producción puede operar con HTTPS, cookies seguras y `DEBUG=False`;
11. las condiciones de concurrencia se verifican dentro de transacciones;
12. las áreas pendientes están explícitamente separadas de las decisiones cerradas.

---

# 47. Decisiones cerradas

**Corrección de consistencia (revisión de cierre, 2026-09-11):** esta sección se titulaba "Decisiones propuestas para cierre" y marcaba cada fila como "Propuesta de cierre", contradiciendo el encabezado del documento ("Estado: Cerrada"). Las siguientes decisiones quedan cerradas como política de Fase 3:

| ID | Decisión | Estado |
|---|---|---|
| SEC-001 | Privacidad por defecto | Cerrado |
| SEC-002 | Deny by default | Cerrado |
| SEC-005 | Autorización por objeto | Cerrado |
| SEC-015 | Usuario autenticado requerido | Cerrado |
| SEC-031 | Inicio de encounter protegido | Cerrado |
| SEC-036 | Encounter completado bloqueado | Cerrado |
| SEC-041 | Acceso al record por paciente autorizado | Cerrado |
| SEC-060 | Superuser no equivale a acceso clínico irrestricto | Cerrado |
| SEC-066 | Documentos privados | Cerrado |
| SEC-086 | Protección explícita contra IDOR | Cerrado |
| SEC-093 | Minimización en logs | Cerrado |
| SEC-104 | Credenciales DB fuera de código | Cerrado |
| SEC-117 | No usar datos clínicos reales en tests ordinarios | Cerrado |
| SEC-124 | HTTPS en producción | Cerrado |
| SEC-133 | Exportación como operación sensible separada | Cerrado |
| SEC-144 | No borrado físico rutinario | Cerrado |
| SEC-149 | Consentimiento/aviso separados del permiso clínico | Cerrado |
| SEC-155 | Auditoría separada del dominio clínico | Cerrado |
| SEC-231 | Sin acceso de emergencia automático en F3 | Cerrado |
| SEC-234 | No cifrado universal por campo en F3 | Cerrado |

---

# 48. Decisión arquitectónica resultante

La política de seguridad de TeCuidoApp para Fase 3 queda resumida así:

```text
                     User autenticado
                           │
                           ▼
                    Rol / identidad
                           │
                           ▼
                 Autorización por objeto
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
        Lectura permitida          Escritura permitida
             │                           │
             ▼                           ▼
      Datos clínicos               Servicio de dominio
             │                           │
             └─────────────┬─────────────┘
                           ▼
                     PostgreSQL
                           │
                           ▼
                    Auditoría sensible
```

Los archivos clínicos, cuando entren al producto, seguirán un camino equivalente:

```text
Actor autorizado
      ↓
Policy de documento
      ↓
Storage privado
      ↓
Descarga autorizada
      ↓
AuditLog
```

---

# 49. Principio final

La seguridad clínica de TeCuidoApp no debe depender de una sola barrera.

Debe existir una defensa en profundidad, pero deliberadamente sencilla:

```text
Autenticación
    +
Autorización por objeto
    +
Integridad de dominio
    +
Constraints de base de datos
    +
Transacciones
    +
Storage privado
    +
Configuración segura
    +
Auditoría
```

La regla práctica es:

> **Si una operación clínica no puede demostrar de manera explícita quién la realiza, sobre qué paciente, sobre qué recurso y con qué permiso, la operación debe rechazarse.**

---

# 50. Siguiente documento

Con las políticas anteriores cerradas, el siguiente documento de Fase 3 recomendado por el orden de trabajo es:

```text
clinical-service-contracts.md
```

Ese documento deberá traducir estas políticas a contratos de servicios, sin volver a definirlas.

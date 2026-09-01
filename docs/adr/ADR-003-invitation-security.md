# ADR-003 — Invitation Security

**Estado:** Accepted  
**Fecha:** 2026-08-31  
**Decisores:** Equipo de desarrollo  
**Área:** Seguridad / Identidad / Registro de pacientes

---

## 1. Contexto

TeCuidoApp permite que un médico envíe a un prospecto una invitación para iniciar su registro en la plataforma.

La invitación constituye el punto de entrada para crear una relación entre:

```text id="f3q8y9"
Doctor
   ↓
Invitation
   ↓
Prospect
   ↓
User / Person / Patient
```

La especificación funcional establece que el prospecto:

- no es considerado paciente hasta completar correctamente su registro;
- recibe una liga de registro enviada por un médico;
- debe utilizar un token seguro;
- debe existir una expiración;
- la invitación debe ser de un solo uso o quedar invalidada después de completarse;
- la invitación debe identificar al médico que la generó;
- deben registrarse las fechas de creación, utilización y expiración;
- debe poder identificarse el estado de la invitación;
- el correo debe verificarse antes de concluir el registro.

Dado que el flujo de invitación está directamente relacionado con la creación de identidades y pacientes, una implementación insegura podría permitir:

- reutilización de invitaciones;
- acceso no autorizado al proceso de registro;
- asociación incorrecta de un paciente con un médico;
- manipulación de datos de registro;
- uso de invitaciones después de su expiración;
- enumeración de invitaciones válidas;
- creación de cuentas mediante tokens predecibles.

Por ello, la seguridad de las invitaciones debe quedar definida como una decisión arquitectónica explícita.

---

# 2. Problema

Una implementación simple podría generar enlaces como:

```text
/register?doctor=12&patient=45
```

o utilizar tokens predecibles:

```text
/register?token=123456
```

Esto sería inadecuado porque expone información del dominio o permite inferir/alterar identificadores.

También sería problemático permitir:

```text
Invitation
    ↓
Registration
    ↓
Invitation remains valid
```

porque una misma invitación podría utilizarse varias veces.

La arquitectura necesita garantizar que una invitación represente una autorización temporal y limitada para iniciar un registro.

---

# 3. Decisión

TeCuidoApp utilizará **tokens criptográficamente seguros, de un solo uso y con expiración**, asociados internamente a una entidad `Invitation`.

La invitación será una entidad del dominio y no solamente un token almacenado sin contexto.

Conceptualmente:

```text id="qpdhd5"
Invitation
├── doctor
├── email
├── token / token reference
├── status
├── created_at
├── expires_at
├── used_at
└── ...
```

El token otorgará acceso únicamente al flujo de registro correspondiente.

La URL pública no deberá exponer identificadores sensibles del dominio cuando no sean necesarios.

---

# 4. Objetivos de seguridad

La implementación debe garantizar:

### Confidencialidad

No revelar información innecesaria mediante el enlace de invitación.

### Integridad

El usuario no debe poder modificar el médico asociado a la invitación alterando parámetros de la URL.

### Autenticidad

El sistema debe poder determinar que el enlace corresponde a una invitación válida generada por el sistema.

### Unicidad

Una invitación completada no podrá utilizarse nuevamente.

### Temporalidad

Una invitación expirada no podrá utilizarse.

### Trazabilidad

Debe poder determinarse:

- quién generó la invitación;
- cuándo se creó;
- cuándo se utilizó;
- cuándo expiró;
- cuál era su estado.

---

# 5. Modelo conceptual

La entidad `Invitation` deberá mantener la asociación con el médico que generó la invitación.

Conceptualmente:

```text id="zhy1tj"
Doctor
   │
   │ creates
   ▼
Invitation
   │
   ├── recipient email
   ├── secure token
   ├── created_at
   ├── expires_at
   ├── used_at
   └── status
```

La asociación con el médico será parte del registro persistente.

El cliente no podrá decidir libremente qué médico será asociado al paciente.

---

# 6. Estados

La invitación deberá tener un estado explícito.

Estados iniciales recomendados:

```text id="v5dyeq"
PENDING
USED
EXPIRED
CANCELLED
```

### `PENDING`

La invitación puede utilizarse.

### `USED`

La invitación ya completó su flujo de registro y no puede utilizarse nuevamente.

### `EXPIRED`

La fecha de expiración fue alcanzada.

### `CANCELLED`

La invitación fue invalidada antes de su utilización.

La implementación puede utilizar nombres diferentes si conserva el mismo significado funcional.

---

# 7. Token seguro

El token debe generarse utilizando mecanismos criptográficamente seguros proporcionados por Python/Django.

No utilizar:

- IDs secuenciales;
- timestamps;
- códigos incrementales;
- valores derivados del email;
- nombre del médico;
- UUIDs predecibles o manipulados manualmente;
- hashes débiles;
- valores generados con `random` no criptográfico.

El token debe ser suficientemente largo para evitar ataques de adivinación.

La implementación debe preferir mecanismos estándar y seguros del ecosistema Python/Django.

---

# 8. Token vs. datos de dominio

El token debe actuar como una **credencial temporal**, no como una representación directa del dominio.

El enlace puede ser conceptualmente:

```text id="m5c8zs"
https://app.example.com/register/invitation/<secure-token>/
```

pero no debe depender de parámetros manipulables como:

```text id="ojat7l"
?doctor_id=15
?patient_id=42
?role=patient
```

Los datos sensibles deben determinarse a partir de la invitación almacenada en servidor.

---

# 9. Asociación con el médico

El médico asociado a la invitación será determinado por el registro persistente:

```text id="hr8lzo"
Invitation.doctor
```

El cliente no deberá enviar ni modificar este valor para completar el registro.

Ejemplo incorrecto:

```python id="93mbrk"
doctor_id = request.POST["doctor_id"]
```

La aplicación deberá obtener el médico desde la invitación validada.

Conceptualmente:

```text id="8q3m7a"
secure_token
    ↓
Invitation
    ↓
Invitation.doctor
```

Esto evita que un prospecto pueda cambiar artificialmente la asociación.

---

# 10. Asociación con el paciente

Una invitación no representa por sí misma a un paciente.

El proceso debe ser:

```text id="4yvxwe"
Invitation
    ↓
Registration
    ↓
User
    ↓
Person
    ↓
Patient
    ↓
DoctorPatientRelationship
```

La relación con el médico debe derivarse de la invitación utilizada.

Esto es coherente con el requerimiento de que una invitación enviada por un médico asocie automáticamente al futuro paciente con dicho médico.

---

# 11. Uso único

Una invitación debe poder utilizarse una sola vez.

Después de completar correctamente el flujo:

```text id="ie6h3b"
PENDING
   ↓
USED
```

El sistema debe registrar:

```text id="to8v8c"
used_at
```

A partir de ese momento, cualquier intento de reutilización deberá rechazarse.

La invalidación debe ser aplicada en servidor.

No depender de:

- cookies;
- session state;
- comportamiento del navegador;
- JavaScript.

---

# 12. Expiración

La invitación debe tener una fecha/hora de expiración:

```text id="oyxngz"
expires_at
```

Una invitación debe considerarse no utilizable cuando:

```text id="yqg4nu"
current_time >= expires_at
```

La validación debe realizarse del lado servidor.

No confiar en la hora del cliente.

Cuando una invitación expirada sea detectada, podrá marcarse:

```text id="g3r2lc"
status = EXPIRED
```

La duración concreta de la invitación debe mantenerse configurable y no codificarse en múltiples lugares del sistema.

---

# 13. Consistencia temporal

La aplicación debe utilizar datetimes conscientes de zona horaria.

La configuración deberá ser consistente con la arquitectura global de Django.

Las comparaciones de expiración deberán utilizar una fuente temporal del servidor.

No utilizar:

```python id="e8y9xg"
datetime.now()
```

de forma inconsistente con la configuración de timezone del proyecto.

Preferir las utilidades de timezone proporcionadas por Django.

---

# 14. Consumo atómico de la invitación

La aceptación de una invitación debe ser una operación atómica.

El flujo conceptual es:

```text id="23j8i6"
BEGIN TRANSACTION

Validate Invitation
        ↓
Verify pending
        ↓
Verify not expired
        ↓
Create User
        ↓
Create Person
        ↓
Create Patient
        ↓
Create DoctorPatientRelationship
        ↓
Mark Invitation USED
        ↓
Commit
```

Si cualquier operación falla:

```text id="uscvsc"
ROLLBACK
```

Esto evita estados inconsistentes.

Ejemplo de inconsistencia que debe prevenirse:

```text id="icr3zq"
Patient creado
Invitation todavía PENDING
```

---

# 15. Protección contra concurrencia

Debe considerarse el escenario donde dos solicitudes intenten utilizar la misma invitación prácticamente al mismo tiempo.

La aplicación debe impedir:

```text id="ok2j6u"
Request A ──┐
            ├── Invitation USED
Request B ──┘
```

dando como resultado dos pacientes o dos cuentas.

La aceptación de la invitación debe realizarse dentro de una transacción con control apropiado de concurrencia y bloqueo de la fila cuando sea necesario.

En Django/PostgreSQL, la implementación deberá utilizar los mecanismos apropiados de transacciones y locking para garantizar que una invitación no pueda consumirse dos veces.

---

# 16. Verificación de email

La invitación y la verificación de email son conceptos relacionados pero diferentes.

El flujo debe distinguir:

```text id="s5h6lq"
Invitation token
        ≠
Email verification token
```

La invitación autoriza el inicio del proceso de registro.

La verificación de email confirma que la persona controla el correo utilizado en el registro.

La cuenta no debe considerarse correctamente registrada solamente porque la invitación sea válida.

La especificación exige que el correo sea verificado antes de concluir el registro.

---

# 17. Email destinatario

La invitación debe registrar el email al que fue enviada.

Conceptualmente:

```text id="kznfbb"
Invitation.email
```

El proceso de registro debe mantener coherencia con ese correo.

La implementación debe definir cuidadosamente si el correo puede modificarse durante el registro.

Como regla inicial, no debe permitirse cambiar silenciosamente el destinatario de la invitación, porque ello podría permitir utilizar una invitación destinada a otra persona.

---

# 18. Protección contra enumeración

El sistema debe evitar revelar información innecesaria acerca de invitaciones.

No debe permitir inferir fácilmente:

- qué tokens existen;
- qué emails tienen invitaciones;
- qué médico generó una invitación;
- si un token concreto pertenece a un usuario existente.

Las respuestas públicas deben revelar solamente la información necesaria para continuar el flujo.

---

# 19. Errores

Los errores de invitación deben manejarse de forma segura.

Casos posibles:

- token inexistente;
- token inválido;
- token expirado;
- token utilizado;
- token cancelado;
- registro incompleto;
- email incompatible.

La respuesta para el usuario puede ser funcionalmente clara sin revelar detalles internos innecesarios.

No exponer:

- IDs internos;
- stack traces;
- información de base de datos;
- detalles internos del sistema.

---

# 20. Reenvío de invitaciones

La especificación establece que el médico puede enviar una invitación a un prospecto, pero no define completamente la política de reenvío.

Por ello, la arquitectura no debe imponer una política compleja de reenvío en esta fase.

Cuando posteriormente se implemente esta funcionalidad deberá decidirse explícitamente si:

1. se reutiliza la invitación vigente;
2. se crea una nueva invitación y se invalida la anterior;
3. se permite más de una invitación pendiente con reglas específicas.

Esta decisión deberá documentarse mediante un ADR o actualización de este ADR antes de implementarse.

---

# 21. Cancelación

Debe existir la posibilidad de invalidar una invitación si el negocio la requiere.

El estado:

```text id="kqe9f4"
CANCELLED
```

representa una invitación que ya no debe poder utilizarse.

Una invitación cancelada no debe volver a convertirse en `PENDING`.

---

# 22. Auditoría y trazabilidad

La especificación exige conservar:

- fecha/hora de creación;
- fecha/hora de utilización;
- fecha/hora de expiración;
- estado;
- médico generador.

La implementación debe conservar estos datos como parte de la entidad `Invitation`.

La auditoría transversal completa de operaciones sensibles pertenece a una fase posterior, pero la invitación debe mantener desde esta fase la trazabilidad mínima requerida para su propio ciclo de vida.

---

# 23. Privacidad

No almacenar información sensible adicional en el token.

El token debe ser únicamente un identificador seguro de acceso al flujo.

La información del prospecto y del médico debe recuperarse desde PostgreSQL después de validar el token.

No codificar datos personales dentro del token para que sean legibles por el cliente.

---

# 24. Almacenamiento del token

La estrategia de almacenamiento del token deberá seleccionarse considerando que el token funciona como credencial temporal.

Preferencia:

- no almacenar tokens de acceso de forma innecesariamente expuesta;
- cuando sea viable, almacenar una representación segura del token y comparar de forma apropiada;
- nunca registrar el token completo en logs.

La implementación concreta podrá utilizar mecanismos estándar de Django siempre que cumplan con los requisitos de seguridad y uso único.

---

# 25. Logs

Nunca deben registrarse en logs:

- token completo;
- contraseña;
- credenciales;
- enlaces completos de invitación que contengan el token.

Los logs pueden registrar eventos como:

```text id="09nrnk"
Invitation created
Invitation accepted
Invitation expired
Invitation rejected
```

junto con identificadores internos no sensibles cuando sea apropiado.

---

# 26. Separación entre invitación y autenticación

`Invitation` no sustituye al sistema de autenticación.

El token de invitación no debe convertirse en una sesión permanente.

Después del registro y verificación:

```text id="wq2wkh"
Invitation Token
      ↓
Registration
      ↓
Email Verification
      ↓
Normal User Authentication
```

La sesión posterior debe utilizar los mecanismos normales de autenticación de Django.

---

# 27. Dependencias con ADR-001 y ADR-002

Esta decisión depende de:

### ADR-001

`ADR-001-custom-user-model.md`

Define el Custom User Model como núcleo de autenticación.

### ADR-002

`ADR-002-user-person-profile.md`

Define la separación:

```text id="tfvd3q"
User
 ↓
Person
 ↓
Patient
```

La invitación coordina estos componentes, pero no los sustituye.

---

# 28. Flujo completo de seguridad

El flujo esperado es:

```text id="vsbl8w"
Doctor
   │
   ▼
Create Invitation
   │
   ├── Secure Token
   ├── Expiration
   ├── Doctor Association
   └── Recipient Email
   │
   ▼
Send Email
   │
   ▼
Prospect
   │
   ▼
Open Invitation
   │
   ▼
Validate Token
   │
   ├── Invalid ────────> Reject
   │
   ├── Expired ────────> Reject
   │
   ├── Used ───────────> Reject
   │
   └── Valid
        │
        ▼
   Registration
        │
        ▼
   Email Verification
        │
        ▼
   Create User / Person / Patient
        │
        ▼
   Create DoctorPatientRelationship
        │
        ▼
   Mark Invitation USED
        │
        ▼
   Normal Authentication
```

---

# 29. Amenazas consideradas

## Token predecible

**Mitigación:** generación criptográficamente segura.

## Reutilización del token

**Mitigación:** estado `USED` + invalidación server-side.

## Token expirado

**Mitigación:** validación de `expires_at`.

## Manipulación del médico

**Mitigación:** obtener el médico desde `Invitation`, no desde datos enviados por el cliente.

## Doble consumo concurrente

**Mitigación:** transacción + mecanismos de locking apropiados.

## Robo del enlace

El enlace debe considerarse una credencial temporal.

Mitigaciones:

- expiración;
- un solo uso;
- HTTPS en producción;
- evitar registrar el token;
- limitar el alcance del token al proceso de registro.

## Enumeración

**Mitigación:** respuestas públicas controladas y tokens suficientemente impredecibles.

---

# 30. Alternativas consideradas

## Alternativa A — ID secuencial

```text
/register/123/
```

**Decisión:** Rejected.

Motivo:

- predecible;
- enumerable;
- no proporciona suficiente seguridad como credencial.

---

## Alternativa B — UUID como único mecanismo

```text
/register/550e8400-e29b-41d4-a716-446655440000/
```

**Decisión:** Rejected como mecanismo único.

Aunque un UUID puede proporcionar un identificador difícil de adivinar dependiendo de su versión y generación, el requisito requiere tratar la invitación explícitamente como una credencial temporal con expiración y uso único.

Por ello, el concepto de `Invitation` debe mantenerse independiente del simple formato del identificador.

---

## Alternativa C — JWT

**Decisión:** Rejected para esta necesidad.

No existe una necesidad inicial de utilizar un token auto-contenido y firmado para la invitación.

Añadir JWT introduciría complejidad adicional de:

- revocación;
- expiración;
- invalidación;
- manejo de claims.

Una invitación persistida en PostgreSQL resulta más sencilla para este flujo.

---

## Alternativa D — Token seguro + Invitation persistida

**Decisión:** Accepted.

Proporciona:

- control explícito del ciclo de vida;
- expiración;
- revocación;
- uso único;
- asociación con médico;
- trazabilidad;
- control transaccional.

---

# 31. Consecuencias positivas

Esta decisión proporciona:

- mayor seguridad del registro;
- control explícito del ciclo de vida;
- asociación confiable con el médico;
- prevención de reutilización;
- expiración;
- trazabilidad;
- capacidad de revocación;
- control de concurrencia;
- integración limpia con `User`, `Person` y `Patient`.

---

# 32. Consecuencias negativas

Implica:

- una entidad adicional;
- lógica de validación;
- transacciones;
- control de concurrencia;
- mayor cantidad de tests;
- necesidad de gestionar estados.

Estos costos se consideran necesarios por la sensibilidad del proceso de registro.

---

# 33. Reglas de implementación

### Regla 1

Las invitaciones deben persistirse.

### Regla 2

Los tokens deben ser criptográficamente seguros.

### Regla 3

Los tokens deben tener expiración.

### Regla 4

Las invitaciones deben ser de un solo uso.

### Regla 5

El médico asociado debe determinarse desde la entidad `Invitation`.

### Regla 6

El cliente no puede cambiar el médico asociado.

### Regla 7

El consumo de la invitación debe ser atómico.

### Regla 8

La creación de `User`, `Person`, `Patient` y la relación con el médico debe ser consistente.

### Regla 9

El email debe verificarse antes de completar el registro.

### Regla 10

Los tokens completos no deben aparecer en logs.

### Regla 11

Los tokens no deben contener información personal legible.

### Regla 12

Una invitación `USED`, `EXPIRED` o `CANCELLED` no puede ser utilizada.

---

# 34. Criterios de aceptación

La implementación se considera correcta cuando:

- [ ] Existe una entidad `Invitation`.
- [ ] La invitación registra al médico que la creó.
- [ ] La invitación registra el email destinatario.
- [ ] Se genera un token seguro.
- [ ] El token no es predecible.
- [ ] Existe fecha de creación.
- [ ] Existe fecha de expiración.
- [ ] Existe fecha de utilización.
- [ ] Existe estado.
- [ ] Una invitación expirada no puede utilizarse.
- [ ] Una invitación utilizada no puede reutilizarse.
- [ ] Una invitación cancelada no puede utilizarse.
- [ ] El médico no puede ser alterado desde el cliente.
- [ ] El registro mediante invitación crea correctamente el paciente.
- [ ] El paciente queda asociado al médico que creó la invitación.
- [ ] La operación de aceptación es transaccional.
- [ ] El sistema evita consumo concurrente de una misma invitación.
- [ ] El email debe verificarse.
- [ ] Los tokens no aparecen completos en logs.
- [ ] Existen tests de seguridad para el ciclo de vida.
- [ ] Existen tests de concurrencia o comportamiento equivalente cuando sea viable.

---

# 35. Estado

**Accepted**

Esta decisión forma parte de la arquitectura de identidad y registro de TeCuidoApp.

Cualquier modificación significativa deberá documentarse mediante una actualización de este ADR o un nuevo ADR relacionado.

---

# 36. Referencias

- `requirements.md`
- `docs/architecture.md`
- `docs/adr/ADR-001-custom-user-model.md`
- `docs/adr/ADR-002-user-person-profile.md`
# ADR-001 — Custom User Model

**Estado:** Accepted  
**Fecha:** 2026-08-31  
**Decisores:** Equipo de desarrollo  
**Área:** Arquitectura / Identidad y autenticación

---

## 1. Contexto

TeCuidoApp requiere un sistema centralizado de autenticación y autorización que pueda soportar diferentes perfiles funcionales:

- Administrador
- Médico
- Paciente
- Responsable

La especificación funcional establece que:

- debe existir un modelo de usuario central para autenticación y autorización;
- no deben existir sistemas independientes de autenticación para cada rol;
- un mismo usuario debe poder asociarse a diferentes perfiles funcionales en el futuro;
- debe existir una separación clara entre:
  - Usuario/autenticación
  - Persona
  - Paciente
  - Responsable
  - Médico;
- el correo electrónico utilizado para el registro debe ser único.

Además, TeCuidoApp se desarrollará progresivamente por fases. La Fase 1 incluye específicamente usuarios, roles, autenticación, verificación de correo, recuperación de contraseña, médicos, pacientes, responsables, consultorios e invitaciones.

La decisión sobre el modelo de usuario debe tomarse al inicio porque cambiar posteriormente el modelo de autenticación de Django puede implicar migraciones complejas y afectar múltiples aplicaciones.

---

## 2. Problema

Django proporciona un modelo de usuario estándar mediante:

```python
django.contrib.auth.models.User
```

Utilizar directamente este modelo puede resultar suficiente para aplicaciones sencillas, pero TeCuidoApp requiere una arquitectura de identidad que pueda evolucionar.

En particular, el sistema debe poder separar:

```text
Autenticación
      ↓
User
      ↓
Person
      ↓
Perfil funcional
```

y debe evitar asumir que:

```text
1 usuario = 1 rol
```

como una restricción permanente.

También necesitamos que el correo electrónico de autenticación sea único y que la estructura pueda evolucionar sin tener que reemplazar posteriormente el modelo principal de identidad.

---

## 3. Decisión

TeCuidoApp utilizará un **Custom User Model de Django** desde el inicio del proyecto.

El modelo será utilizado como el único punto central de:

- autenticación;
- credenciales;
- email;
- estado de la cuenta;
- permisos y autorización relacionados con el usuario.

La aplicación **no utilizará directamente** el modelo:

```python
django.contrib.auth.models.User
```

como entidad principal de autenticación.

El modelo personalizado debe declararse mediante:

```python
AUTH_USER_MODEL = "accounts.User"
```

o mediante el nombre equivalente de la app/modelo definitivo.

---

## 4. Principios del modelo

El Custom User Model debe mantenerse enfocado en **identidad y autenticación**.

No debe convertirse en un contenedor de toda la información del dominio.

Conceptualmente:

```text
User
 ├── authentication
 ├── email
 ├── password
 ├── active state
 └── account metadata

Person
 ├── name
 ├── birth date
 ├── contact
 └── address

Doctor
 └── functional doctor profile

Patient
 └── functional patient profile

Responsible
 └── functional responsible profile
```

Las entidades de dominio no deben almacenarse como una colección creciente de campos dentro de `User`.

---

## 5. Separación de responsabilidades

La arquitectura será:

```text
┌─────────────────────┐
│        User         │
│ Authentication      │
│ Email               │
│ Password            │
│ Account state       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       Person        │
│ Identity data       │
│ Contact information │
│ Address             │
└──────────┬──────────┘
           │
      ┌────┼────┬──────────────┐
      ▼    ▼    ▼              ▼
   Doctor Patient Responsible  ...
```

Esto permite que la autenticación permanezca independiente del dominio clínico.

---

## 6. Email como identificador de autenticación

El email será único dentro del sistema.

Debe existir una restricción de unicidad a nivel de base de datos.

La implementación debe evitar depender exclusivamente de validaciones Python para garantizar esta regla.

La política exacta respecto a:

- mayúsculas/minúsculas;
- normalización;
- espacios;
- comparación;

debe ser consistente en toda la aplicación y documentarse en la implementación.

---

## 7. Identidad y perfiles

El sistema debe distinguir entre:

### Usuario

Cuenta utilizada para autenticarse.

### Persona

Representación de los datos personales de una persona.

### Médico

Perfil funcional de médico.

### Paciente

Perfil funcional de paciente.

### Responsable

Perfil funcional de responsable.

Esto permitirá que la identidad personal no esté fuertemente acoplada a la autenticación.

---

## 8. Roles y perfiles

La arquitectura no debe diseñarse suponiendo una relación rígida:

```text
User → One Role
```

En su lugar, debe permitir una evolución hacia:

```text
User
 ├── Doctor profile
 ├── Patient profile
 ├── Responsible profile
 └── Administrator permissions
```

La implementación inicial puede utilizar los mecanismos nativos de Django para permisos y grupos, siempre que no limite la evolución futura.

La solución concreta de roles debe documentarse en el ADR correspondiente o en la arquitectura general cuando se defina completamente.

---

## 9. Motivación

La decisión se toma por las siguientes razones:

### 9.1 Evolución del dominio

TeCuidoApp tendrá múltiples tipos de usuarios y perfiles funcionales.

### 9.2 Evitar migraciones estructurales futuras

Cambiar posteriormente del User estándar a un usuario personalizado puede resultar costoso después de que existan numerosas aplicaciones y relaciones.

### 9.3 Email como identificador principal

El sistema requiere que el email utilizado para el registro sea único.

### 9.4 Separación entre identidad y dominio

La autenticación no debe contener directamente información específica de paciente, médico o responsable.

### 9.5 Extensibilidad

La arquitectura debe poder incorporar nuevos perfiles sin rediseñar la autenticación.

---

## 10. Alternativas consideradas

### Alternativa A — Utilizar `django.contrib.auth.models.User`

#### Ventajas

- configuración inicial sencilla;
- integración inmediata;
- menor cantidad de código inicial.

#### Desventajas

- menor flexibilidad para evolucionar la identidad;
- mayor dependencia del modelo estándar;
- posibles migraciones complejas posteriormente;
- mayor riesgo de terminar agregando información de dominio al usuario mediante soluciones indirectas.

#### Decisión

**Rejected**

No es adecuada como base principal para TeCuidoApp.

---

### Alternativa B — Utilizar `AbstractUser`

Crear un modelo personalizado heredando de:

```python
django.contrib.auth.models.AbstractUser
```

#### Ventajas

- conserva gran parte del comportamiento estándar de Django;
- permite extender el modelo;
- reduce código de autenticación personalizado;
- mantiene compatibilidad con muchas herramientas de Django.

#### Desventajas

- requiere definir y configurar un modelo propio;
- requiere adoptar la decisión desde el inicio del proyecto.

#### Decisión

**Accepted**

Es la alternativa preferida para la implementación inicial, salvo que durante la revisión técnica del repositorio exista una razón justificada para utilizar otra estrategia.

---

### Alternativa C — Utilizar `AbstractBaseUser`

Crear un modelo completamente personalizado mediante:

```python
django.contrib.auth.models.AbstractBaseUser
```

#### Ventajas

- máximo control sobre la identidad;
- flexibilidad completa.

#### Desventajas

- mayor complejidad;
- mayor cantidad de código propio;
- mayor superficie para errores;
- necesidad de implementar más componentes de autenticación y administración.

#### Decisión

**Rejected para la Fase 1**

No existe actualmente una necesidad que justifique esa complejidad.

---

## 11. Implementación recomendada

La implementación inicial debe utilizar:

```python
class User(AbstractUser):
    ...
```

dentro de:

```text
accounts/
```

y configurar:

```python
AUTH_USER_MODEL = "accounts.User"
```

Los modelos de otras aplicaciones deben referenciar al usuario mediante:

```python
from django.conf import settings

user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    ...
)
```

No deben utilizarse referencias directas como:

```python
from django.contrib.auth.models import User
```

en los modelos de dominio.

---

## 12. Migraciones

El Custom User Model debe implementarse **antes de crear dependencias significativas con el modelo de usuario**.

La migración inicial de `accounts` debe crear el modelo de usuario desde el comienzo del proyecto.

Todas las relaciones futuras hacia el usuario deben utilizar:

```python
settings.AUTH_USER_MODEL
```

o:

```python
get_user_model()
```

según el contexto.

---

## 13. Reglas para código futuro

Todo código nuevo que necesite referenciar al usuario debe evitar acoplarse al modelo concreto.

### En modelos

Utilizar:

```python
settings.AUTH_USER_MODEL
```

### En lógica de aplicación

Utilizar:

```python
get_user_model()
```

### En consultas

Evitar asumir un modelo concreto llamado `User`.

---

## 14. Seguridad

El Custom User Model debe integrarse con los mecanismos de seguridad estándar de Django.

No se implementará un sistema artesanal de autenticación.

Se utilizarán:

- password hashing de Django;
- sesiones de Django;
- mecanismos estándar de autenticación;
- recuperación de contraseña;
- permisos y grupos;
- protección CSRF.

Las credenciales no deben mezclarse con información clínica.

---

## 15. Impacto sobre otras apps

Las aplicaciones deberán depender del usuario mediante abstracciones de Django.

Ejemplo:

```text
accounts
   │
   ├── User
   └── Person
        │
        ├── Doctor
        ├── Patient
        └── Responsible
```

Otras apps podrán referenciar `User`, pero no deben acoplarse a implementaciones específicas de autenticación.

---

## 16. Consecuencias positivas

Esta decisión proporciona:

- una base correcta para autenticación;
- email único;
- mayor flexibilidad;
- separación entre identidad y dominio;
- menor riesgo de migraciones futuras;
- compatibilidad con el ecosistema de Django;
- capacidad para evolucionar hacia múltiples perfiles;
- integración natural con permisos y grupos de Django.

---

## 17. Consecuencias negativas

Esta decisión implica:

- mayor trabajo inicial;
- configuración adicional;
- necesidad de utilizar correctamente `AUTH_USER_MODEL`;
- mayor disciplina al crear relaciones con el usuario;
- necesidad de definir cuidadosamente la relación User/Person/Profile.

Sin embargo, estos costos se consideran aceptables frente al riesgo de modificar la identidad del sistema en una fase avanzada.

---

## 18. Riesgos

### Riesgo: mezclar información de dominio dentro de User

Mitigación:

Mantener `User` enfocado en autenticación y cuenta.

### Riesgo: asumir que un usuario tiene un único rol

Mitigación:

Diseñar perfiles funcionales y autorización de forma desacoplada.

### Riesgo: referencias directas al User estándar de Django

Mitigación:

Utilizar siempre `settings.AUTH_USER_MODEL` o `get_user_model()`.

### Riesgo: modificar el modelo después de crear muchas migraciones

Mitigación:

Adoptar el Custom User Model desde la Fase 1.

---

## 19. Relación con la Fase 1

Esta decisión es requisito estructural para la Fase 1.

Afecta directamente:

- registro;
- login;
- verificación de email;
- recuperación de contraseña;
- activación/desactivación;
- invitaciones;
- médicos;
- pacientes;
- responsables;
- permisos.

La Fase 1 debe considerarse incompleta si la autenticación todavía depende del `User` estándar de Django.

---

## 20. Relación con fases futuras

Esta decisión permitirá que las siguientes fases agreguen relaciones hacia el usuario sin modificar la arquitectura fundamental.

Ejemplos futuros:

```text
Appointment.created_by → User
MedicalEncounter.created_by → User
Prescription.created_by → User
ClinicalDocument.created_by → User
AuditLog.user → User
Notification.user → User
```

La identidad seguirá siendo centralizada mientras el dominio continúa creciendo.

---

## 21. Criterios de aceptación

La decisión se considera correctamente implementada cuando:

- [ ] existe un Custom User Model;
- [ ] `AUTH_USER_MODEL` está configurado;
- [ ] el email es único;
- [ ] las contraseñas utilizan el sistema de Django;
- [ ] las apps no importan directamente `django.contrib.auth.models.User`;
- [ ] las relaciones utilizan `settings.AUTH_USER_MODEL`;
- [ ] el sistema de autenticación funciona;
- [ ] recuperación de contraseña funciona;
- [ ] verificación de email funciona;
- [ ] activación/desactivación funciona;
- [ ] existen tests del modelo de usuario;
- [ ] las migraciones funcionan desde una base limpia.

---

## 22. Estado

**Accepted**

Esta decisión es aplicable desde la Fase 1 y deberá mantenerse mientras no exista un ADR posterior que la sustituya explícitamente.

---

## 23. Referencias

- `requirements.md`
- `docs/architecture.md`
- Django Authentication documentation
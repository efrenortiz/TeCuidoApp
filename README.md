# TeCuidoApp

Aplicación Web para la gestión integral de un consultorio médico especializado en
gineco-obstetricia. Ver `requirements.md` (requerimientos funcionales) y
`docs/architecture.md` + `docs/adr/` (arquitectura y decisiones técnicas).

Estado actual del proyecto (2026-09-11):

| Fase | Estado |
|---|---|
| Fase 1 — Fundaciones | ✅ COMPLETADA (`docs/phases/phase-1-foundations.md`) |
| Fase 2 — Agenda | ✅ COMPLETADA (`docs/phases/phase-2-agenda-final-report.md`) |
| Fase 3 — Gestión clínica | ✅ COMPLETADA (`docs/phases/phase-3-clinical-final-report.md`) |
| Fase 4 — Documentos | ⏭️ SIGUIENTE (aún no iniciada) |
| Fase 5 — CareRequest y operación | Futura |
| Fase 6 — Notificaciones y auditoría | Futura |

## Stack

- Python 3.12, Django 6.1
- PostgreSQL

## Setup local

1. Activar el virtualenv (vive fuera del repo, en el directorio padre):

   ```bash
   source ../bin/activate   # o la ruta a tu venv
   pip install -r requirements.txt
   ```

2. Copiar `.env.example` a `.env` y completar los valores reales (nunca se
   commitea `.env`, ya está en `.gitignore`):

   ```bash
   cp .env.example .env
   ```

   Variables:

   | Variable | Descripción |
   |---|---|
   | `DJANGO_SECRET_KEY` | Secret key de Django. Generar uno propio en local/prod. |
   | `DJANGO_DEBUG` | `True`/`False`. |
   | `DJANGO_ALLOWED_HOSTS` | Lista separada por comas. |
   | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | Conexión a PostgreSQL. |
   | `EMAIL_BACKEND` | Backend de email de Django (consola en dev). |
   | `DEFAULT_FROM_EMAIL` | Remitente por defecto. |
   | `INVITATION_TTL_HOURS` | Vigencia de las invitaciones de médico a prospecto. |
   | `EMAIL_VERIFICATION_TTL_HOURS` | Vigencia del enlace de verificación de correo. |

3. Crear la base de datos en PostgreSQL (si no existe) y aplicar migraciones:

   ```bash
   python manage.py migrate
   ```

4. Crear un superusuario (rol Administrador):

   ```bash
   python manage.py createsuperuser
   ```

5. Levantar el servidor de desarrollo:

   ```bash
   python manage.py runserver
   ```

## Comandos de verificación

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py migrate --plan
python manage.py test
```

El usuario de PostgreSQL usado en desarrollo necesita el privilegio `CREATEDB`
para que `manage.py test` pueda crear/destruir la base de pruebas:

```sql
ALTER ROLE <tu_usuario> CREATEDB;
```

## Estructura de apps (Fase 1)

- `accounts` — identidad y autenticación: `User`, `Person`, `Invitation`; login/logout,
  cambio y recuperación de contraseña, verificación de correo, aceptación de invitación.
- `doctors` — perfil de médico (`Doctor`).
- `clinics` — consultorios y su relación con médicos (`Clinic`, `DoctorClinic`).
- `patients` — pacientes y responsables (`Patient`, `Responsible`,
  `DoctorPatientRelationship`, `ResponsiblePatientRelationship`) y autorización a
  nivel de objeto (`patients/services/permissions.py`).

El paquete de proyecto `TeCuidoApp/` cumple el rol de la app `config` (settings, URLs).
No se creó una app `config` separada porque la estructura existente ya es equivalente
(permitido explícitamente por `docs/phases/phase-1-foundations.md` §7).

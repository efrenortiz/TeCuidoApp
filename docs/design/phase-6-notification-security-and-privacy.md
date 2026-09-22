# Fase 6 — Notification Security and Privacy

**Estado:** Diseño técnico derivado — **implementado** (ver
`docs/phases/phase-6-implementation-summary.md`, PD-005).

## 1. Principio de mínima información

El correo debe comunicar lo necesario para la operación y evitar trasladar el expediente clínico al correo electrónico.

**PD-005 (decisión final del propietario — implementado, `notifications/services.py::_render`):**

```text
Email
→ información esencial de la cita (fecha/hora, médico, consultorio)
+ enlace a TeCuidoApp

TeCuidoApp
→ información completa de la cita
```

El correo nunca sustituye a la aplicación como fuente de detalle. Se corrigió además el asunto
"Cita confirmada" (Fase 2 no tiene una etapa de confirmación separada de la reserva,
`phase-6-notification-domain.md` §8) por "Cita reservada". Cobertura en
`notifications/tests/test_services.py::EmailContentTests`.

## 2. Datos permitidos por defecto

Para comunicaciones de cita, el contenido funcional puede necesitar:

- tipo de comunicación;
- fecha y hora de la cita;
- identificación operativa del consultorio/ubicación cuando sea necesaria;
- identificación del médico cuando sea necesaria para la cita;
- instrucciones operativas no clínicas.

Implementado exactamente así: fecha/hora (`Appointment.start_at`, en la zona horaria de
`Clinic`), médico (`str(Appointment.doctor)`), consultorio (`Clinic.name`) y un enlace a
`appointments:appointment_detail` construido con `settings.SITE_BASE_URL`.

## 3. Datos excluidos

No incluir por defecto:

- diagnósticos;
- resultados de estudios;
- antecedentes clínicos;
- recetas;
- notas clínicas;
- documentos clínicos adjuntos.

## 4. Destinatarios

Los destinatarios no pueden ser introducidos arbitrariamente por el frontend.

La resolución debe derivarse de las entidades y relaciones existentes:

```text
Appointment
 ├── Patient
 ├── Responsible autorizado
 └── Doctor asignado
```

## 5. Credenciales

Las credenciales del proveedor deben residir en configuración segura y nunca en el código fuente, templates, auditoría o respuestas HTTP.

## 6. Logs

Los logs deben usar códigos seguros y permitir diagnóstico sin registrar:

- tokens;
- contraseñas;
- cuerpo completo del mensaje;
- datos clínicos innecesarios.

## 7. Recuperación de errores

Un fallo de transporte debe producir un resultado operacional auditable/observable sin revertir la operación de negocio.

## 8. Seguridad web

Conservar los controles existentes del proyecto:

- autenticación;
- autorización server-side;
- CSRF donde corresponda;
- protección de endpoints administrativos;
- validación de entrada;
- mensajes de error no sensibles.

## 9. Opt-out

No debe existir una pantalla, flag o endpoint que permita al usuario desactivar las notificaciones operativas o recordatorios congelados por Fase 6.

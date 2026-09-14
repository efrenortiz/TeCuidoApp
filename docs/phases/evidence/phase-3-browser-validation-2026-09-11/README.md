# Evidencia — Validación real de navegador, cierre de Fase 3

## Metadatos

- **Fecha/hora:** 2026-09-11, 13:00–13:01 (hora del servidor de la sesión).
- **Entorno:** servidor de desarrollo local (`python manage.py runserver 127.0.0.1:8877`),
  base de datos PostgreSQL local del entorno de desarrollo (no producción, no compartida).
- **Navegador:** Chromium real (Playwright 1.x, `chromium-1234`), modo headless,
  `args=['--no-sandbox']` (requerido por el sandbox del entorno de ejecución), viewport 1280×900.
  Instalado ad-hoc para esta validación (`pip install playwright && python -m playwright install
  chromium`) porque la extensión Claude-in-Chrome no estaba disponible en esta sesión — ver nota
  al final.
- **Usuarios/rol utilizados (datos de prueba, sin relación con personas reales):**
  - Médico: `bv-doc@example.com` — Dra. Ana Gomez.
  - Paciente de la cita: `bv-patient@example.com` — Lucia Ramirez (con
    `DoctorPatientRelationship` activa preexistente con la doctora, para poder demostrar también
    el acceso al expediente/historial).
  - Paciente ajeno (para el bloque de seguridad): `bv-other-patient@example.com` — Otra Persona.
  - Contraseña de prueba (no reutilizada en ningún otro sistema): `BrowserValidate!2026`.
- **URL inicial:** `http://127.0.0.1:8877/accounts/login/`.
- **Cita utilizada:** `Appointment` id 4, consultorio "Consultorio Validacion Cierre".
- **Contenido clínico introducido:** exclusivamente texto de prueba, cada campo marcado
  explícitamente `(dato de prueba)`/`(prueba)` — ningún dato clínico real.

## Método

Automatización real de navegador (no test client de Django, no simulación) vía Playwright
contra el servidor de desarrollo real, ejecutando exactamente el flujo A–H solicitado. El script
(`/tmp/browser_validation.py`, no forma parte del repositorio) registra cada paso con resultado
OK/FAIL y guarda capturas de pantalla reales en los puntos clave. El registro completo,
paso a paso, está en `validation-log.json` (mismo directorio).

## Resultado por bloque

| Bloque | Pasos | Resultado |
|---|---|---|
| A. Preparación | A1–A3 | OK |
| B. Inicio de consulta | B4–B7 | OK (incluye verificación de idempotencia: un segundo intento de "Iniciar consulta" lleva al mismo encuentro, sin duplicarlo) |
| C. Captura clínica | C8–C12 | OK (guardado parcial persistido, indicador visible, sobrevive a recarga de página) |
| D. Interrupción y reanudación | D13–D16 | OK (el encuentro permanece `IN_PROGRESS` y el contenido capturado sigue disponible) |
| E. Completion | E17–E22 | OK (cierre atómico visible: encuentro "Completada", cita "Atendida" — ver nota de nomenclatura) |
| F. Inmutabilidad | F23–F25 | OK (intento real de edición post-completion, vía `fetch()` desde la propia sesión del navegador, rechazado por el servidor; sin reapertura) |
| G. Historial | G26–G29 | OK (expediente, historial y detalle histórico accesibles y correctos para el médico con relación activa) |
| H. Seguridad clínica | H30–H33 | OK (paciente ajeno recibe 404 tanto en el expediente como en la URL directa del encuentro; sin fuga de contenido clínico) |

**Total: 17/17 verificaciones OK, 0 fallos, en la corrida final registrada en
`validation-log.json`.**

## Nota sobre dos hallazgos de la primera corrida (no defectos de la aplicación)

La primera ejecución del script señaló 2 fallos; ambos se investigaron antes de tocar cualquier
archivo de la aplicación, y en ambos casos la causa fue una suposición incorrecta del script de
validación, no un defecto:

1. **E22** — el script esperaba el texto "Completada" en la pantalla de la cita (Agenda). El
   label real y ya cerrado de `Appointment.Status.COMPLETED` (Fase 2, `appointments/models.py`)
   es **"Atendida"** — distinto del label de `ClinicalEncounter.Status.COMPLETED`
   ("Completada"). Ambos representan el mismo estado final `COMPLETED`; son dos entidades con su
   propio texto de presentación, tal como especifica la tabla de labels ya cerrada en
   `phase-3-clinical-ux.md`. Se corrigió la aserción del script, no la aplicación.
2. **G26** — el script asumía que el médico asignado a la cita tendría automáticamente acceso al
   expediente/historial del paciente. Esto contradice una regla ya cerrada y probada
   repetidamente en la suite automatizada (P-009/P-010, `clinical-permissions.md`): una atención
   puntual, por sí sola, **no** concede acceso longitudinal al expediente — se requiere una
   `DoctorPatientRelationship` activa. Se agregó esa relación a los datos de prueba (reflejando
   un escenario real: un médico que además tiene relación de seguimiento con la paciente) y no se
   tocó ningún archivo de la aplicación.

Ninguno de los dos requirió ni justificó un cambio de código — confirmando, con navegador real,
comportamiento ya cubierto por la suite automatizada.

## Observación no bloqueante

La captura `07-access-denied.png` muestra la página técnica de error 404 de Django
(`DEBUG=True`, propio del entorno de desarrollo local usado para esta validación). Esa página
expone nombres de rutas/vistas internas, pero **no expone ningún dato clínico** — el propio
criterio validado (H30–H33) es la ausencia de fuga de datos clínicos, que se cumple. En un
despliegue con `DEBUG=False` (ya exigido por `TeCuidoApp/settings.py` fuera de desarrollo) esa
misma petición mostraría la página 404 genérica de Django sin ningún detalle interno. No se
modificó nada por esta observación — es comportamiento estándar de Django en modo desarrollo, no
un hallazgo de Fase 3.

## Limpieza posterior

Los usuarios, paciente, cita y consultorio de prueba (`bv-doc@example.com`,
`bv-patient@example.com`, `bv-other-patient@example.com`, "Consultorio Validacion Cierre") se
eliminaron de la base de datos de desarrollo inmediatamente después de esta validación. El
servidor de desarrollo temporal (puerto 8877) se detuvo al finalizar.

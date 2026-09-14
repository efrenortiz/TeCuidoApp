# Fase 4 — Validación real de navegador (Stage 5, Gate 5)

**Fecha/hora:** 2026-09-11
**Entorno:** servidor de desarrollo Django (`runserver`) contra PostgreSQL real (no test DB),
Chromium real vía Playwright (mismo mecanismo ya usado en la validación de navegador de Fase 3 —
la extensión Claude-in-Chrome no estaba conectada en este entorno, verificado explícitamente antes
de recurrir a este mecanismo alternativo).

## Usuarios de prueba

- `doc-f4-browser-validation-2026-09-11@example.com` — médico asignado al encuentro.
- `otherdoc-f4-browser-validation-2026-09-11@example.com` — médico sin relación con el paciente
  (usado para el caso de acceso no autorizado).
- `pat-f4-browser-validation-2026-09-11@example.com` — paciente.

Todos los usuarios, el paciente, la clínica y el `ClinicalEncounter` de prueba fueron eliminados de
la base de datos de desarrollo inmediatamente después de esta validación.

## Alcance

Flujo completo, real, de extremo a extremo, sin mocks:

1. Login como médico asignado.
2. Navegación desde el detalle de la consulta (`encounter_detail.html`) a "Emitir receta".
3. Llenado y envío del formulario de receta.
4. Verificación de que la receta emitida se muestra correctamente.
5. Descarga real del PDF generado — verificado el header `%PDF-` del archivo descargado.
6. Corrección (nueva versión) de la receta — verificado que la v2 muestra el nuevo valor y que
   existe el enlace a "Ver versión anterior".
7. Anulación de la receta — verificado el badge "Anulada".
8. Solicitud de estudio (StudyOrder) desde el mismo encuentro.
9. Lista de documentos del paciente — verificado que aparecen los PDFs generados.
10. Acceso no autorizado: un médico sin relación con el paciente, navegando directamente a la URL
    de la receta ya emitida, recibe la página 404 genérica de Django (IDOR-safe: no distingue
    "no existe" de "no autorizado").

## Resultado

**13/13 verificaciones OK.** Ver `results.json` para el detalle estructurado y las 8 capturas de
pantalla (`01`–`08`) para evidencia visual de cada paso.

## Limpieza posterior

Se eliminaron de la base de datos de desarrollo: los 2 `User`/`Person`/`Doctor` y 1
`User`/`Person`/`Patient` de prueba, la `Clinic`, `DoctorClinic`, `Availability`, `Hold`,
`Appointment`, `ClinicalEncounter`, `Prescription`(+versión)/`PrescriptionItem`, `StudyOrder`/
`StudyOrderItem`, y los `ClinicalDocument`/archivos generados durante la validación. El servidor de
desarrollo (`runserver`) se detuvo al finalizar.

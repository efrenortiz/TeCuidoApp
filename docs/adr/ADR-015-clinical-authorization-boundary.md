# ADR-015 — Clinical Authorization Boundary

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Seguridad / Autorización

## 1. Contexto

Fase 3 distingue entre poder iniciar una atención y poder leer historia clínica. Un médico asignado a una cita puede iniciar esa consulta sin que eso implique acceso global a todo el expediente del paciente.

## 2. Decisión

La autorización clínica se separa en dos dimensiones:

```text
Autoridad operacional de atención
        ≠
Autorización de lectura/modificación clínica
```

La política de Fase 3 será:

- el médico asignado y autorizado puede iniciar y editar el `ClinicalEncounter` abierto correspondiente;
- solo actores con autorización clínica efectiva pueden leer el expediente/historial;
- el administrador conserva las capacidades globales definidas por su rol, pero no inicia/completa/no-show por un médico cuando la política de Agenda lo prohíbe;
- paciente y responsable quedan sujetos a acceso por objeto según las reglas de permisos clínicas aprobadas.

La mera existencia de una cita no se convierte automáticamente en permiso para navegar todo el historial clínico.

## 3. Fuente de verdad

La autorización se evalúa en servidor y por objeto. El frontend solo refleja el permiso ya decidido.

## 4. Consecuencias

- Evita privilegios derivados accidentalmente.
- Permite múltiples médicos y relaciones independientes.
- Requiere una política de lectura explícita y pruebas negativas.

## 5. Alternativa rechazada

### “Si atendió una vez, puede leer todo el historial para siempre”
**Rejected.** Es demasiado amplia y contradice mínimo privilegio.

### “El rol DOCTOR da acceso a todos los pacientes”
**Rejected.** El rol no sustituye la autorización por objeto.

## 6. Relación

Complementa `ADR-004`, `ADR-014` y `clinical-permissions.md`.

## 7. Estado

**Accepted.**

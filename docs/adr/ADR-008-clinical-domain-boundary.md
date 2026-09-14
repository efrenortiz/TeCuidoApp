# ADR-008 — Clinical Domain Boundary

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Límites de dominio / Django

## 1. Contexto

Fase 3 incorpora atención clínica al sistema existente. Fase 2 ya estableció `appointments` como propietario de la Agenda y de los estados de `Appointment`.

La nueva funcionalidad necesita `ClinicalEncounter`, `MedicalRecord` y posteriormente otros componentes clínicos, sin convertir `Appointment` en un modelo clínico ni duplicar `Patient`, `Doctor` o `Clinic`.

## 2. Problema

Sin una frontera explícita, la lógica clínica podría terminar repartida entre `appointments`, `patients` y nuevas apps, produciendo acoplamiento, duplicación e invariantes difíciles de proteger.

## 3. Decisión

El dominio clínico de Fase 3 se ubicará en la app Django `medical_records` y será responsable de `ClinicalEncounter` y `MedicalRecord`.

`appointments` seguirá siendo propietario de `Appointment` y de su ciclo de vida de Agenda. La integración entre ambos dominios ocurrirá mediante casos de uso de dominio, no mediante duplicación de la lógica de negocio.

Mapa mínimo:

```text
appointments                 medical_records
------------                 --------------
Appointment  ─────────────→  ClinicalEncounter
                              MedicalRecord
```

Las entidades canónicas existentes (`Patient`, `Doctor`, `Clinic`, `Appointment`) no se duplican.

## 4. Reglas derivadas

- Agenda decide si una cita es elegible para iniciar atención.
- El dominio clínico decide cómo crear, guardar y completar el encuentro.
- La creación de un encuentro no crea una nueva cita.
- La creación de un encuentro no crea automáticamente `DoctorPatientRelationship`.
- Los módulos especializados futuros podrán extender `medical_records` o crear apps delimitadas sin mover `Appointment`.

## 5. Alternativas consideradas

### Una sola app para Agenda y clínica
**Rejected.** Mezcla dos contextos con responsabilidades diferentes.

### App clínica por especialidad desde Fase 3
**Rejected.** Introduciría complejidad antes de que existan requisitos específicos.

### Microservicio clínico separado
**Rejected.** El proyecto es un monolito Django modular; no existe necesidad arquitectónica actual de separar procesos o bases de datos.

## 6. Consecuencias

Positivas:
- frontera clara;
- menor acoplamiento;
- reutilización de entidades canónicas;
- migraciones y tests más localizados.

Negativas:
- las integraciones entre apps deben respetar contratos explícitos;
- ciertos casos de uso cruzan límites de dominio.

## 7. Relación

Complementa `ADR-005` (Django App Boundaries) y `ADR-006` (Database Integrity and Transactions).

## 8. Estado

**Accepted.** Cambios que muevan ownership entre apps requieren un nuevo ADR o revisión explícita de esta decisión.

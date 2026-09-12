# ADRs — Fase 3 Clinical

**Estado global:** conjunto generado y consolidado 2026-09-11

Estos ADRs registran decisiones arquitectónicas de Fase 3. Las reglas funcionales detalladas permanecen en `docs/phases/`; no deben duplicarse aquí salvo cuando una regla sea necesaria para expresar una decisión arquitectónica.

## Orden de lectura

1. [ADR-008 — Clinical Domain Boundary](ADR-008-clinical-domain-boundary.md)
2. [ADR-009 — Appointment as Origin of ClinicalEncounter](ADR-009-appointment-originates-encounter.md)
3. [ADR-010 — ClinicalEncounter State and Atomic Closure](ADR-010-clinical-encounter-state-and-closure.md)
4. [ADR-011 — One MedicalRecord per Patient](ADR-011-one-medical-record-per-patient.md)
5. [ADR-012 — Explicit Clinical Fields](ADR-012-explicit-clinical-fields.md)
6. [ADR-013 — Free-Text Assessment and Diagnosis](ADR-013-free-text-diagnosis.md)
7. [ADR-014 — DoctorPatientRelationship Independence](ADR-014-doctor-patient-relationship-independence.md)
8. [ADR-015 — Clinical Authorization Boundary](ADR-015-clinical-authorization-boundary.md)
9. [ADR-016 — No Reopen or Functional Delete](ADR-016-no-reopen-or-delete-clinical-record.md)
10. [ADR-017 — Clinical History and Audit Trail Are Separate](ADR-017-audit-vs-history.md)
11. [ADR-018 — Clinical Services as Application Boundary](ADR-018-clinical-api-services-boundary.md)
12. [ADR-019 — Server and Database as Clinical Source of Truth](ADR-019-optimistic-ui-server-source-of-truth.md)
13. [ADR-020 — Legacy Agenda Transition Endpoints Remain Unrestricted](ADR-020-legacy-agenda-transition-endpoints.md)

## Relación con Fase 2

Los ADRs 008–020 complementan `ADR-005-django-app-boundaries.md` y `ADR-006-database-integrity-and-transactions.md` y no sustituyen decisiones ya cerradas de Agenda.

## Regla de mantenimiento

Una modificación estructural importante debe actualizar este ADR o crear uno nuevo. No crear un ADR separado por cada validación, pantalla, endpoint o caso de prueba.

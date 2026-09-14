# Fase 4 — Índice documental

Orden normativo y de implementación:

1. `phase-4-documents.md`
2. `phase-4-documents-workflow.md`
3. `phase-4-documents-rules.md`
4. `clinical-document-domain.md`
5. `prescription-domain.md`
6. `study-order-domain.md`
7. `clinical-documents-data-model.md`
8. `phase-4-permissions.md`
9. `phase-4-security-and-privacy.md`
10. `phase-4-service-contracts.md`
11. `phase-4-api-contracts.md`
12. `phase-4-ux.md`
13. `phase-4-screens.md`
14. `phase-4-audit-and-history.md`
15. `phase-4-testing-strategy.md`
16. ADR-021 … ADR-030

## Decisiones nucleares

- No se modifica el ciclo de vida de Appointment/ClinicalEncounter.
- Prescription y StudyOrder requieren ClinicalEncounter.
- ClinicalDocument requiere Patient.
- Documentos emitidos son históricos.
- Correcciones generan nuevas versiones.
- Almacenamiento es privado.
- No resultados de estudios en F4.
- No CareRequest operativo.
- No catálogos obligatorios.

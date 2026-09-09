# Fixtures TeCuido Fase 1 — versión 2

Incluye el escenario faltante para validar la transición explícita de menor a adulto:

- Patient PK 5 / Person PK 8.
- Fecha de nacimiento: 2007-01-15 (19 años al 2026-09-08).
- `Patient.regime = MINOR` pese a tener 18+ años cronológicos.
- Responsable PK 1 con relación `ACTIVE`.
- Médico PK 1 con `DoctorPatientRelationship` activo.
- `Person.user = null`, para no asumir creación automática de cuenta.
- El caso está listo para ejecutar `transition_patient_to_adult` y verificar que:
  - el régimen cambia a `ADULT`;
  - se registra `regime_changed_at`;
  - se registra `regime_changed_by`;
  - la relación ACTIVE del responsable pasa a `INACTIVE`;
  - se guarda `deactivated_at`;
  - se guarda `deactivation_reason = ADULT_TRANSITION`.

También se corrigió `00_MANIFEST.json` para cargar los fixtures en el orden completo de dependencias.

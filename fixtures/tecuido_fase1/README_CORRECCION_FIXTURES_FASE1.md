# Fixtures Fase 1 — corrección de coherencia

Se generó este conjunto a partir de los fixtures existentes del proyecto.

## Reglas aplicadas

1. Un paciente con `regime = ADULT` no conserva una relación de responsable con `status = ACTIVE`.
2. La relación histórica se conserva y se cambia a `INACTIVE`; no se elimina.
3. No se cambia `birth_date` ni se calcula automáticamente `regime` a partir de la edad.
4. El `regime` representa el régimen/autorización actual del paciente, no su edad cronológica.
5. Se corrigieron referencias del `00_MANIFEST.json` a los nombres reales de los fixtures cuando estaban presentes.

## Cambios realizados

- Relaciones ADULT + ACTIVE convertidas a ADULT + INACTIVE: 2
- IDs de pacientes afectados: [1, 2]
- Manifest corregido: sí

## Caso >=18 + MINOR

No se encontró un paciente existente que represente este escenario. No se inventó uno nuevo para evitar alterar la topología de PKs y relaciones. Conviene agregarlo deliberadamente junto con un test canónico.

## Importante

Estos fixtures no modifican migraciones ni modelos. Antes de declarar cerrada Fase 1, ejecutar la suite de tests en el entorno Django del proyecto.

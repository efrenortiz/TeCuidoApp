# ADR-013 — Free-Text Assessment and Diagnosis in F3

**Estado:** Accepted  
**Fecha:** 2026-09-11  
**Área:** Arquitectura / Semántica clínica

## 1. Contexto

El campo de evaluación/diagnóstico es obligatorio para completar un encuentro, pero Fase 3 aún no define un catálogo diagnóstico ni codificación CIE-10.

## 2. Decisión

En Fase 3, `assessment` será texto clínico libre.

No se implementarán como requisito del núcleo:

- CIE-10;
- catálogo de diagnósticos;
- códigos estructurados obligatorios;
- selector de diagnóstico;
- normalización automática de texto a diagnósticos.

## 3. Seguridad conceptual

El sistema almacenará lo que el médico documente. No inferirá diagnósticos mediante reglas automáticas, IA ni equivalencias heurísticas.

## 4. Consecuencias

Positivas:
- implementación simple;
- menor dependencia externa;
- libertad clínica suficiente para el núcleo genérico.

Negativas:
- menor capacidad de análisis estructurado en Fase 3;
- futuras búsquedas o estadísticas diagnósticas requerirán una extensión deliberada.

## 5. Evolución

Una futura incorporación de CIE-10 deberá introducir una decisión arquitectónica separada y preservar el texto clínico histórico ya almacenado.

## 6. Estado

**Accepted.**

# Fase 6 — Audit and History

**Estado:** Diseño técnico derivado — **implementado** (ver `docs/phases/phase-6-implementation-summary.md`).

## 1. Distinción

`AuditEvent` no sustituye la historia clínica ni el historial funcional de un dominio.

```text
Clinical history → describe hechos clínicos
Audit trail      → describe acciones del sistema/actor
```

## 2. Append-only

La auditoría funcional es append-only.

No se agregan flujos de edición o borrado de eventos desde UI, API o Admin.

## 3. Retención

Regla congelada:

> Retención indefinida.

No hay depuración automática por antigüedad.

La depuración manual podrá realizarse cuando una necesidad operativa de espacio lo exija, siguiendo un procedimiento controlado fuera de Fase 6.

## 4. Auditoría de rechazos

Los rechazos de operaciones del catálogo base son parte de la historia de seguridad y deben persistir aunque la operación de negocio no se haya realizado.

## 5. Auditoría de errores

Los errores técnicos pueden registrarse cuando aporten trazabilidad real, utilizando códigos seguros.

No convertir logs de depuración completos en `AuditEvent`.

## 6. Privacidad

El historial de auditoría no debe convertirse en una copia secundaria de la información clínica. Referenciar recursos por tipo/ID y contexto suficiente es preferible a copiar contenido.

## 7. Acceso

Consulta exclusiva de Administradores autorizados.

## 8. Depuración manual

Cuando se requiera liberar espacio:

1. identificar el volumen y motivo;
2. realizar respaldo/procedimiento aprobado si corresponde;
3. ejecutar una purga manual controlada;
4. documentar la intervención operativa.

El sistema F6 no ejecuta estos pasos automáticamente.

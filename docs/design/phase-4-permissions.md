# Fase 4 — Permisos

## 1. Principio

Fase 4 hereda la autorización clínica de Fase 3. La existencia de un documento no amplía por sí misma el acceso del actor.

## 2. Operaciones y actores

**Corrección de consistencia (2026-09-11):** la matriz original colapsaba toda autorización médica
bajo una única columna "Médico autorizado", sin preservar la distinción ya cerrada en Fase 3 entre
un médico simplemente asignado al `ClinicalEncounter` actual y un médico con
`DoctorPatientRelationship` vigente (P-009/P-010/P-011/P-013, `clinical-permissions.md`). Un
documento clínico (a diferencia de la lectura puntual de UN encuentro) es, por definición, un
artefacto histórico que puede consultarse fuera del encuentro que lo originó — por lo que aplica la
misma regla que ya rige la lectura de `MedicalRecord`/historial en Fase 3: la sola asignación a una
atención puntual no abre acceso histórico permanente. Se corrige la matriz para reflejarlo
explícitamente:

| Acción | Médico asignado al encuentro actual | Médico con relación activa (P-009/010) | Paciente | Responsable activo | Admin |
|---|---:|---:|---:|---:|---:|
| Leer/descargar documentos del `ClinicalEncounter` que él mismo atendió | Sí | Sí | Sí (propios) | Sí (según política del paciente) | Sí |
| Leer/descargar el historial documental completo del paciente (otros encuentros) | No (P-010) | Sí | Sí (propio) | Sí (según política del paciente) | Sí |
| Subir documento | Sí, en el contexto del encuentro que atiende | Sí | Según política del recurso | Según política del recurso | Sí |
| Emitir Prescription | Sí (requiere `ClinicalEncounter` válido propio) | — (no aplica sin encuentro propio) | No | No | Según política administrativa |
| Emitir StudyOrder | Sí (requiere `ClinicalEncounter` válido propio) | — (no aplica sin encuentro propio) | No | No | Según política administrativa |
| Corregir documento emitido | Sí, si es el autor del `ClinicalEncounter` de origen | Sí, si la relación activa lo autoriza | No | No | Según política administrativa |
| Anular receta/orden | Sí, si es el autor del `ClinicalEncounter` de origen | Sí, si la relación activa lo autoriza | No | No | Según política administrativa |
| Ver audit trail | No | No | No | No | Sí |

Emitir/corregir/anular son siempre operaciones ancladas al `ClinicalEncounter` de origen (el médico
que las ejecuta debe ser el asignado a ese encuentro, o tener relación activa que lo autorice, igual
que la lectura de un encuentro ajeno en Fase 3 — P-013). Nunca dependen únicamente de estar
"autorizado en general".

## 3. Médico — asignado vs. relación activa

La autoridad para **emitir** un documento (Prescription/StudyOrder) requiere ser el médico asignado
al `ClinicalEncounter` que le da contexto — igual que iniciar/completar un encuentro en Fase 3
(P-011/P-012). No requiere `DoctorPatientRelationship` para esa operación puntual.

La autoridad para **leer/descargar documentos fuera del encuentro que el médico atendió** (el
historial documental completo del paciente) requiere `DoctorPatientRelationship` vigente y
autorizante — misma regla que ya rige el acceso a `MedicalRecord`/historial clínico en Fase 3
(P-009). Un médico asignado a una única atención puntual no obtiene, por eso, acceso histórico
permanente a los documentos del paciente (P-010).

La relación con `DoctorPatientRelationship` no se crea automáticamente por emitir, leer ni
descargar ningún recurso de Fase 4.

## 4. Responsable

Requiere `ResponsiblePatientRelationship.status == ACTIVE` y sólo accede a pacientes autorizados.

## 5. Descarga

La descarga debe repetir autorización por objeto, aunque el usuario ya haya visto el documento.

## 6. IDOR

Nunca aceptar `patient_id`, `document_id`, `prescription_id` o `study_order_id` como prueba suficiente de autorización.

## 7. Anulación/corrección

Son operaciones de escritura y requieren privilegio adicional al de lectura.

## 8. Auditoría

Las operaciones sensibles se auditan y el audit trail queda restringido según Fase 3.

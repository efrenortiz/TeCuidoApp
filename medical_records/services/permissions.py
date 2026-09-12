"""Object-level authorization for the clinical domain
(docs/design/clinical-permissions.md).

Deliberately does NOT reuse `patients.services.permissions.can_view_patient`
for clinical resources: that helper grants any `is_superuser` actor
unconditional access (Fase 1/ADR-004 functional-global scope), which
directly contradicts the Fase 3 closed decisions that clinical access and
administrative access are distinct (P-008, P-038) and that there must be
no generic admin-bypass pattern (P-042). Administrator support access to
clinical data is a separate, explicit, audited capability (P-040/P-041)
that Etapa 2 does not implement — no clinical read/write path here grants
access by `is_superuser` alone.

Reuses `appointments.services.permissions.is_assigned_doctor` directly
(not a reimplementation) for the médico-asignado gate on
start/save/complete/read-own, per ADR-008 (no duplicated business logic
across the Agenda/clinical boundary), and
`patients.services.permissions.doctor_has_active_relationship` /
`responsible_has_active_relationship` for the longitudinal-read gates.
"""

from appointments.services.permissions import (
    doctor_profile,
    is_assigned_doctor,
    patient_profile,
    responsible_profile,
)
from patients.services.permissions import (
    doctor_has_active_relationship,
    responsible_has_active_relationship,
)


def can_read_encounter(actor, encounter):
    """P-011/012 (médico asignado), P-013/014 (otro médico con relación
    activa, solo lectura), P-017/P-023 (paciente/responsable, solo sobre
    encuentros COMPLETED — D-004). El administrador NO obtiene acceso
    aquí (P-038/039/042) — ver docstring del módulo."""
    if is_assigned_doctor(actor, appointment=encounter.appointment):
        return True

    doctor = doctor_profile(actor)
    if doctor is not None and doctor.is_active and doctor_has_active_relationship(doctor, encounter.patient):
        return True

    if encounter.status != encounter.Status.COMPLETED:
        return False

    patient = patient_profile(actor)
    if patient is not None and patient.is_active and patient.pk == encounter.patient.pk:
        return True

    responsible = responsible_profile(actor)
    if responsible is not None and responsible_has_active_relationship(responsible, encounter.patient):
        return True

    return False


def can_access_patient_record(actor, patient):
    """Autorización de lectura/creación del `MedicalRecord` (P-013, P-017,
    P-023) cuando `get_or_create_for_patient`/`get_medical_record` se
    invocan como punto de entrada protegido por sí mismo (`actor` no es
    `None`).

    Deliberadamente NO cubre el caso "primera consulta sin relación
    previa" (P-031): esa autorización ya la resuelve `start_encounter`
    mediante `is_assigned_doctor` (sin exigir relación) antes de invocar
    `get_or_create_for_patient(actor=None)` como efecto interno de una
    operación ya autorizada — ver `encounter.start_encounter`."""
    doctor = doctor_profile(actor)
    if doctor is not None and doctor.is_active and doctor_has_active_relationship(doctor, patient):
        return True

    patient_actor = patient_profile(actor)
    if patient_actor is not None and patient_actor.is_active and patient_actor.pk == patient.pk:
        return True

    responsible = responsible_profile(actor)
    if responsible is not None and responsible_has_active_relationship(responsible, patient):
        return True

    return False


def can_edit_patient_record(actor, patient):
    """SC-052 — edición de antecedentes longitudinales reservada a
    actores clínicos autorizados (no paciente, no responsable).

    Un médico califica si tiene relación activa (P-013) o si ya atendió
    clínicamente a este paciente al menos una vez (existe un
    `ClinicalEncounter` propio para el paciente) — esto último por la
    misma razón que `start_encounter` no exige relación previa (P-031):
    la primera consulta por sí sola debe bastar para poder documentar el
    expediente compartido, sin esperar a que exista una
    `DoctorPatientRelationship` registrada aparte."""
    from medical_records.models import ClinicalEncounter

    doctor = doctor_profile(actor)
    if doctor is None or not doctor.is_active:
        return False
    if doctor_has_active_relationship(doctor, patient):
        return True
    return ClinicalEncounter.objects.filter(doctor=doctor, appointment__patient=patient).exists()


def can_view_audit_log(actor):
    """P-041/AH-107/182 (cerrado) — el `AuditEvent` solo puede ser leído
    por el Administrador (`is_superuser`). Ningún otro actor —incluido el
    médico asignado— tiene acceso de lectura al registro técnico de
    auditoría; su visibilidad de la actividad clínica se limita al propio
    contenido clínico (encuentro, expediente), nunca al log de accesos."""
    return bool(getattr(actor, "is_authenticated", False) and actor.is_superuser)

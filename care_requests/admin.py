from django.contrib import admin

from care_requests.models import CareRequest


@admin.register(CareRequest)
class CareRequestAdmin(admin.ModelAdmin):
    """Solo lectura — mismo patrón que `medical_records.admin.AuditEventAdmin`.

    El lifecycle de `CareRequest` (`NUEVA` → `CONVERTIDA`) es propiedad
    exclusiva de `care_requests.services.care_request.create()`; ningún rol,
    incluido el Administrador, tiene permiso de editar, cancelar o convertir
    manualmente una `CareRequest` (`docs/design/care-request-permissions.md`
    §7-9/§11 — todas esas celdas de la matriz son ❌). Permitir `add`/`change`
    desde `/admin/` abriría un camino para producir un registro `NUEVA` sin
    `Hold`/`Appointment`, o una `CONVERTIDA` sin `appointment`, saltándose por
    completo la transacción del servicio."""

    list_display = ("id", "patient", "doctor", "clinic", "status", "appointment", "created_at")
    list_filter = ("status",)
    search_fields = ("patient__person__first_name", "patient__person__last_name_paterno")

    # Auditoría de LECTURA administrativa — decisión de alcance (2026-09-18,
    # `phase-5-final-report.md` §36, Opción B): `requirements.md` §62 /
    # ADR-004 §8/§26 exigen que el acceso del administrador a información
    # clínica sensible (`motivo`/`padecimiento`/`descripcion`, presentes en
    # esta pantalla) quede registrado en auditoría. Deliberadamente NO
    # implementado aquí: ningún `ModelAdmin` del proyecto que expone
    # contenido clínico (`ClinicalEncounterAdmin`, `MedicalRecordAdmin`,
    # `PrescriptionAdmin`, `StudyOrderAdmin`, `ClinicalDocumentAdmin`)
    # audita su propia lectura tampoco — no existe ningún hook reutilizable
    # de "auditar una lectura de Admin" en el proyecto (`medical_records.
    # services.audit.safe_record_event` solo se invoca hoy desde la capa de
    # servicio de aplicación, nunca desde `admin.py`). Construir uno ahora,
    # solo para `CareRequest`, sería una excepción aislada e inconsistente
    # con el resto del sistema — CLAUDE.md ubica "auditoría" en Fase 6, que
    # es donde corresponde resolver esto de forma transversal para todos los
    # `ModelAdmin` de contenido clínico sensible a la vez, no app por app.

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

"""Fase 3 — dominio clínico (`medical_records`).

Frontera de dominio (ADR-008): esta app posee `ClinicalEncounter` y
`MedicalRecord`. `appointments` sigue siendo propietaria exclusiva de
`Appointment` y de su ciclo de vida de Agenda — este módulo nunca la
duplica ni la reinterpreta, solo la referencia.

Convención de campos sin `default` en `status`: mismo patrón deny-by-default
ya usado en `appointments.models` (Hold/Appointment) — una fila sin
`status` explícito debe fallar ruidosamente, nunca caer en un valor por
omisión silencioso.

Resolución de contradicción documental (revisión de consistencia,
2026-09-11 — ver informe de ETAPA 1): `clinical-encounter-rules.md` R-008
escribe la invariante como si `ClinicalEncounter.patient` y
`ClinicalEncounter.clinic` fueran columnas propias, pero el modelo físico
ya ratificado en `clinical-data-model.md` §25.2 (documento específicamente
encargado de fijar el esquema físico, y el más reciente/específico en la
jerarquía para esta pregunta) solo materializa `appointment` y `doctor`
como columnas — no `patient` ni `clinic`. `clinical-encounter-domain.md`
§13 además advierte explícitamente contra "una segunda fuente editable de
verdad que pueda entrar en contradicción con la cita". Se resuelve
implementando `patient`/`clinic` como *properties* de solo lectura
derivadas de `appointment.patient`/`appointment.clinic`: esto satisface la
igualdad de R-008 de forma permanente y por construcción (nunca puede
divergir, a diferencia de una columna redundante), sin añadir persistencia
que el esquema ratificado no contempla. No es una decisión de negocio
nueva — ambos documentos coinciden en la sustancia (paciente/clínica del
encuentro deben coincidir siempre con los de la cita); solo difieren en si
eso se expresa como columna o como propiedad derivada.
"""

from django.db import models


class ClinicalEncounter(models.Model):
    """El registro clínico de una consulta iniciada desde una `Appointment`
    válida (ADR-009). `Appointment 1 ─── 0..1 ClinicalEncounter`.

    No se expone como CRUD genérico (clinical-encounter-domain.md §42): la
    creación/transición pasa exclusivamente por
    `medical_records.services.encounter`.
    """

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "En progreso"
        COMPLETED = "COMPLETED", "Completada"

    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        related_name="clinical_encounter",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        related_name="clinical_encounters",
    )

    # Deliberately no default — ver docstring del módulo.
    status = models.CharField(max_length=20, choices=Status.choices)

    # Cinco campos obligatorios al completar (ADR-012), no al guardar
    # parcialmente (clinical-encounter-domain.md I-017) — por eso
    # blank=True/default="" en vez de NOT NULL a secas: la fila nunca es
    # NULL, pero puede estar vacía mientras IN_PROGRESS. La validación de
    # "contenido clínico real" (sin placeholders) vive en el servicio, no
    # en el modelo (clinical-encounter-domain.md §17).
    reason_for_visit = models.TextField("motivo de consulta", blank=True, default="")
    present_illness = models.TextField("padecimiento actual", blank=True, default="")
    physical_exam = models.TextField("exploración física", blank=True, default="")
    assessment = models.TextField("evaluación / diagnóstico", blank=True, default="")
    plan = models.TextField("plan / indicaciones", blank=True, default="")

    # Campos opcionales (clinical-encounter-domain.md §48, corregido).
    vital_signs = models.TextField("signos vitales", blank=True, default="")
    weight_kg = models.DecimalField(
        "peso (kg)", max_digits=5, decimal_places=2, null=True, blank=True
    )
    height_cm = models.DecimalField(
        "talla (cm)", max_digits=5, decimal_places=2, null=True, blank=True
    )
    relevant_history = models.TextField("antecedentes relevantes", blank=True, default="")
    studies = models.TextField("estudios", blank=True, default="")
    observations = models.TextField("observaciones", blank=True, default="")

    # Timestamps (clinical-encounter-domain.md §19/§49-51): created_at y
    # started_at son conceptos distintos aunque coincidan en la práctica
    # normal (ambos se fijan en la misma operación transaccional de
    # inicio) — no se fusionan porque auditoría futura podría necesitar
    # distinguirlos.
    #
    # Deliberadamente NO `auto_now_add`: ese mecanismo calcula su propio
    # `now()` en el momento del INSERT, independiente de cualquier valor
    # que el llamador ya haya capturado para `started_at` — eso puede
    # violar por pura carrera de microsegundos el CHECK
    # `started_at >= created_at` incluso en el flujo normal. El servicio
    # de dominio (Etapa 2) debe capturar un único `now` y asignarlo
    # explícitamente a ambos campos, exactamente como especifica
    # clinical-encounter-domain.md §49.1.
    created_at = models.DateTimeField()
    started_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "encuentro clínico"
        verbose_name_plural = "encuentros clínicos"
        indexes = [
            models.Index(fields=["doctor", "status"]),
            models.Index(fields=["started_at"]),
        ]
        constraints = [
            # Nested class bodies (Meta) no son closures sobre atributos
            # hermanos de la clase envolvente — mismo patrón ya
            # documentado en appointments/models.py; strings literales en
            # vez de referenciar Status.IN_PROGRESS/Status.COMPLETED.
            models.CheckConstraint(
                condition=models.Q(status__in=["IN_PROGRESS", "COMPLETED"]),
                name="clinical_encounter_status_valid",
            ),
            # ADR-010 / clinical-encounter-domain.md I-009: completed_at
            # existe si y solo si status = COMPLETED.
            models.CheckConstraint(
                condition=(
                    models.Q(status="COMPLETED", completed_at__isnull=False)
                    | models.Q(status="IN_PROGRESS", completed_at__isnull=True)
                ),
                name="clinical_encounter_completed_at_matches_status",
            ),
            # DM-042 (clinical-data-model.md, corregido en la auditoría de
            # cierre): comparación pura entre columnas, expresable como
            # CHECK sin depender de NOW() — a diferencia de las
            # restricciones de solapamiento de Fase 2.
            models.CheckConstraint(
                condition=models.Q(started_at__gte=models.F("created_at")),
                name="clinical_encounter_started_after_created",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(completed_at__isnull=True)
                    | models.Q(completed_at__gte=models.F("started_at"))
                ),
                name="clinical_encounter_completed_after_started",
            ),
            models.CheckConstraint(
                condition=models.Q(weight_kg__isnull=True) | models.Q(weight_kg__gt=0),
                name="clinical_encounter_weight_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(height_cm__isnull=True) | models.Q(height_cm__gt=0),
                name="clinical_encounter_height_positive",
            ),
        ]

    def __str__(self):
        return f"Encuentro {self.pk} — {self.appointment_id} ({self.status})"

    @property
    def patient(self):
        """Derivado de `appointment.patient` — nunca una columna propia.
        Ver la nota de resolución de contradicción en el docstring del
        módulo (R-008)."""
        return self.appointment.patient

    @property
    def clinic(self):
        """Derivado de `appointment.clinic` — ver `patient` arriba."""
        return self.appointment.clinic


class MedicalRecord(models.Model):
    """Expediente clínico longitudinal, único por paciente (ADR-011).

    Creación lazy (`clinical-record-domain.md` CR-002): se crea en la
    primera operación clínica que lo requiere, nunca al registrar un
    paciente. No se expone como CRUD genérico (CR-088).
    """

    patient = models.OneToOneField(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="medical_record",
    )

    # Historia longitudinal (clinical-record-domain.md §5.1) — campos
    # explícitos guiados, no JSON genérico (CR-016/DM-014). Todos
    # opcionales (CR-021 y DM-015: "Obligatorio: No" para los seis).
    family_history = models.TextField("antecedentes heredofamiliares", blank=True, default="")
    personal_pathological_history = models.TextField(
        "antecedentes personales patológicos", blank=True, default=""
    )
    personal_non_pathological_history = models.TextField(
        "antecedentes personales no patológicos", blank=True, default=""
    )
    housing_history = models.TextField("vivienda", blank=True, default="")
    gynecologic_obstetric_history = models.TextField(
        "antecedentes gineco-obstétricos", blank=True, default=""
    )
    other_relevant_history = models.TextField("otros antecedentes relevantes", blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    # CR-011: representa el último cambio persistido sobre datos propios
    # del expediente — nunca "última actividad clínica" en general (eso
    # se consulta en los componentes relacionados, no aquí).
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "expediente clínico"
        verbose_name_plural = "expedientes clínicos"

    def __str__(self):
        return f"Expediente de {self.patient}"


class AuditEvent(models.Model):
    """Auditoría clínica de Fase 3 (docs/design/clinical-audit-and-history.md
    §4/§22, AH-011 — entidad separada de los modelos clínicos, AH-012/013:
    referencia por identificador, nunca copia el contenido clínico).

    Append-only por convención de aplicación (AH-082/083): no existe
    ningún servicio de actualización ni borrado — solo
    `medical_records.services.audit.record_event`/`safe_record_event`
    crean filas, y ninguna vista/API expone edición o `DELETE`.

    Simplificación deliberada respecto al esquema conceptual de AH-011:
    se omiten `request_id` y `metadata` — no hay ninguna necesidad real de
    correlación multi-evento ni de contexto adicional en el alcance
    mínimo de Fase 3 (AH-133 ya advierte contra convertir `metadata` en
    "un mecanismo para guardar datos clínicos arbitrarios"); se agregarán
    solo si una necesidad concreta lo justifica.
    """

    class Action(models.TextChoices):
        START_ENCOUNTER = "START_ENCOUNTER", "Inicio de consulta"
        SAVE_ENCOUNTER = "SAVE_ENCOUNTER", "Guardado de consulta"
        COMPLETE_ENCOUNTER = "COMPLETE_ENCOUNTER", "Finalización de consulta"
        READ_CLINICAL_ENCOUNTER = "READ_CLINICAL_ENCOUNTER", "Lectura de encuentro clínico"
        READ_MEDICAL_RECORD = "READ_MEDICAL_RECORD", "Lectura de expediente"
        READ_CLINICAL_HISTORY = "READ_CLINICAL_HISTORY", "Lectura de historial clínico"
        CREATE_MEDICAL_RECORD = "CREATE_MEDICAL_RECORD", "Creación de expediente"
        UPDATE_MEDICAL_RECORD = "UPDATE_MEDICAL_RECORD", "Actualización de expediente"
        # Fase 4 (phase-4-audit-and-history.md §2) — mismo AuditEvent,
        # nuevas acciones documentales; no se crea un modelo de auditoría
        # paralelo (ADR-021 reutiliza explícitamente el mecanismo de Fase 3).
        ISSUE_PRESCRIPTION = "ISSUE_PRESCRIPTION", "Emisión de receta"
        ISSUE_STUDY_ORDER = "ISSUE_STUDY_ORDER", "Emisión de solicitud de estudio"
        VOID_PRESCRIPTION = "VOID_PRESCRIPTION", "Anulación de receta"
        VOID_STUDY_ORDER = "VOID_STUDY_ORDER", "Anulación de solicitud de estudio"
        UPLOAD_CLINICAL_DOCUMENT = "UPLOAD_CLINICAL_DOCUMENT", "Carga de documento clínico"
        GENERATE_CLINICAL_DOCUMENT = "GENERATE_CLINICAL_DOCUMENT", "Generación de documento clínico"
        READ_CLINICAL_DOCUMENT = "READ_CLINICAL_DOCUMENT", "Lectura de documento clínico"
        DOWNLOAD_CLINICAL_DOCUMENT = "DOWNLOAD_CLINICAL_DOCUMENT", "Descarga de documento clínico"
        CREATE_DOCUMENT_VERSION = "CREATE_DOCUMENT_VERSION", "Nueva versión de documento clínico"
        VOID_CLINICAL_DOCUMENT = "VOID_CLINICAL_DOCUMENT", "Anulación de documento clínico"

    class Result(models.TextChoices):
        SUCCESS = "SUCCESS", "Éxito"
        DENIED = "DENIED", "Denegado"
        REJECTED = "REJECTED", "Rechazado"
        ERROR = "ERROR", "Error"

    class ResourceType(models.TextChoices):
        CLINICAL_ENCOUNTER = "ClinicalEncounter", "Encuentro clínico"
        MEDICAL_RECORD = "MedicalRecord", "Expediente clínico"
        CLINICAL_HISTORY = "ClinicalHistory", "Historial clínico"
        APPOINTMENT = "Appointment", "Cita"
        PRESCRIPTION = "Prescription", "Receta"
        STUDY_ORDER = "StudyOrder", "Solicitud de estudio"
        CLINICAL_DOCUMENT = "ClinicalDocument", "Documento clínico"

    # AH-084/175 — asignado por el servidor, nunca por el cliente.
    occurred_at = models.DateTimeField(auto_now_add=True)
    # AH-086/173 — siempre el usuario autenticado real; nunca desde el body.
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="clinical_audit_events"
    )
    # AH-098 — rol operativo observado en el momento del evento (una
    # relación puede desactivarse después sin alterar la autoría histórica).
    actor_role = models.CharField(max_length=20)

    action = models.CharField(max_length=30, choices=Action.choices)
    result = models.CharField(max_length=10, choices=Result.choices)
    # AH-034/036 — código interno seguro, nunca un mensaje de excepción
    # crudo ni un stack trace.
    reason_code = models.CharField(max_length=60, blank=True, default="")

    # AH-014/135 — referencia lógica explícita (siempre presente); las FK
    # específicas de abajo se usan además cuando aportan integridad real.
    resource_type = models.CharField(max_length=30, choices=ResourceType.choices)
    resource_id = models.PositiveBigIntegerField(null=True, blank=True)

    # AH-134 — todas opcionales: no toda acción tiene las tres.
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    appointment = models.ForeignKey(
        "appointments.Appointment", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    clinical_encounter = models.ForeignKey(
        "medical_records.ClinicalEncounter", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # Fase 4 — mismas reglas que las tres FKs de arriba: opcionales, sólo
    # para integridad referencial adicional cuando aportan valor real.
    prescription = models.ForeignKey(
        "prescriptions.Prescription", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    study_order = models.ForeignKey(
        "study_orders.StudyOrder", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    clinical_document = models.ForeignKey(
        "clinical_documents.ClinicalDocument", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "evento de auditoría clínica"
        verbose_name_plural = "eventos de auditoría clínica"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["patient", "occurred_at"]),
            models.Index(fields=["actor", "occurred_at"]),
            models.Index(fields=["action", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.action} · {self.result} · {self.occurred_at:%Y-%m-%d %H:%M}"

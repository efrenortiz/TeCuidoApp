from django.db import models


class Patient(models.Model):
    """Patient functional profile (Fase 1: identification, contact and
    generic medical-relevant info only).

    Full clinical history (evolución, diagnósticos, tratamientos) and
    gineco-obstetric detail are Fase 3 concerns and are intentionally not
    modeled here — this model must stay extensible for that later, without
    building it now.
    """

    class Sex(models.TextChoices):
        FEMALE = "F", "Femenino"
        MALE = "M", "Masculino"
        OTHER = "O", "Otro"

    class Regime(models.TextChoices):
        MINOR = "MINOR", "Menor"
        ADULT = "ADULT", "Adulto"

    person = models.OneToOneField(
        "accounts.Person",
        on_delete=models.PROTECT,
        related_name="patient_profile",
    )

    curp = models.CharField("CURP", max_length=18, blank=True)
    nationality = models.CharField("nacionalidad", max_length=100, blank=True, default="Mexicana")
    sex = models.CharField("sexo", max_length=1, choices=Sex.choices)

    emergency_contact_name = models.CharField(
        "nombre del contacto de emergencia", max_length=150, blank=True
    )
    emergency_contact_phone = models.CharField(
        "teléfono del contacto de emergencia", max_length=20, blank=True
    )

    blood_type = models.CharField("tipo sanguíneo", max_length=5, blank=True)
    allergies = models.TextField("alergias", blank=True)
    chronic_conditions = models.TextField("enfermedades crónicas", blank=True)
    current_medications = models.TextField("medicamentos actuales", blank=True)
    surgical_history = models.TextField("antecedentes quirúrgicos", blank=True)
    relevant_hospitalizations = models.TextField("hospitalizaciones relevantes", blank=True)

    is_active = models.BooleanField(default=True)

    # Authorization regime, independent of Person.is_minor's chronological
    # age (ADR-007 §3.8 addendum). Deliberately no default: every creation
    # path must state it explicitly — register_minor_patient always passes
    # MINOR, accept_invitation always passes ADULT — same deny-by-default
    # reasoning as ResponsiblePatientRelationship.status below. The
    # CheckConstraint is what actually enforces it at the DB level, since
    # `choices` alone would let a bare create() insert "" silently.
    regime = models.CharField(max_length=5, choices=Regime.choices)
    regime_changed_at = models.DateTimeField(null=True, blank=True)
    regime_changed_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="regime_transitions_performed",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"
        constraints = [
            # Nested classes don't see Patient.Regime by name here (class
            # bodies aren't a closure for other nested blocks) — these two
            # strings must match Regime's values.
            models.CheckConstraint(
                condition=models.Q(regime__in=["MINOR", "ADULT"]),
                name="patient_regime_valid",
            ),
        ]

    def __str__(self):
        return str(self.person)


class Responsible(models.Model):
    """Responsible functional profile — manages one or more Patients."""

    person = models.OneToOneField(
        "accounts.Person",
        on_delete=models.PROTECT,
        related_name="responsible_profile",
    )
    alternative_contact = models.CharField(
        "contacto alternativo", max_length=150, blank=True
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "responsable"
        verbose_name_plural = "responsables"

    def __str__(self):
        return str(self.person)


class DoctorPatientRelationship(models.Model):
    """Explicit Doctor <-> Patient relationship (a patient may relate to
    several doctors: tratante, sustituto, otro)."""

    class RelationType(models.TextChoices):
        TRATANTE = "TRATANTE", "Médico tratante"
        SUSTITUTO = "SUSTITUTO", "Médico sustituto"
        OTRO = "OTRO", "Otro"

    doctor = models.ForeignKey(
        "doctors.Doctor", on_delete=models.CASCADE, related_name="patient_relationships"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="doctor_relationships"
    )
    relationship_type = models.CharField(
        max_length=10, choices=RelationType.choices, default=RelationType.TRATANTE
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "relación médico-paciente"
        verbose_name_plural = "relaciones médico-paciente"
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "patient"], name="unique_doctor_patient"
            )
        ]

    def __str__(self):
        return f"{self.doctor} -> {self.patient} ({self.relationship_type})"


class ResponsiblePatientRelationship(models.Model):
    """Explicit Responsible <-> Patient relationship (a responsible may
    manage several patients).

    `status` (not a bare `is_active` boolean) distinguishes three states
    that ADR-007 §3.7 requires to stay separate: a relationship someone
    requested but nobody has approved yet must never look like one that
    was approved and later deactivated.
    """

    class RelationType(models.TextChoices):
        MADRE = "MADRE", "Madre"
        PADRE = "PADRE", "Padre"
        TUTOR_LEGAL = "TUTOR_LEGAL", "Tutor legal"
        FAMILIAR = "FAMILIAR", "Familiar"
        CUIDADOR = "CUIDADOR", "Cuidador"
        OTRO = "OTRO", "Otro"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente de aprobación"
        ACTIVE = "ACTIVE", "Vigente"
        INACTIVE = "INACTIVE", "Desactivada"

    class DeactivationReason(models.TextChoices):
        ADULT_TRANSITION = "ADULT_TRANSITION", "Transición a régimen adulto"
        REQUEST_REJECTED = "REQUEST_REJECTED", "Solicitud rechazada"
        OTHER = "OTHER", "Otro"

    responsible = models.ForeignKey(
        Responsible, on_delete=models.CASCADE, related_name="patient_relationships"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="responsible_relationships"
    )
    relationship_type = models.CharField(max_length=15, choices=RelationType.choices)
    # Deliberately no default: every creation path must choose PENDING vs.
    # ACTIVE on purpose (deny-by-default, ADR-004) — an omitted status must
    # fail loudly, not silently become whichever state happened to be the
    # default. The CheckConstraint below is what actually enforces that: a
    # bare CharField without a default would otherwise just insert "" and
    # succeed, since Django's `choices` isn't a DB-level guarantee.
    status = models.CharField(max_length=10, choices=Status.choices)

    # Deactivation trace (ADR-007 §3.8 addendum): who/what ended the
    # relationship and when. Deliberately no default on the reason — every
    # caller that moves a relationship to INACTIVE (the adult-transition
    # service, reject_relationship_request) must state why explicitly,
    # same deny-by-default reasoning as `status` above.
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(
        max_length=20, choices=DeactivationReason.choices, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "relación responsable-paciente"
        verbose_name_plural = "relaciones responsable-paciente"
        constraints = [
            models.UniqueConstraint(
                fields=["responsible", "patient"], name="unique_responsible_patient"
            ),
            # Nested classes don't see ResponsiblePatientRelationship.Status
            # by name here (class bodies aren't a closure for other nested
            # blocks) — these three strings must match Status's values.
            models.CheckConstraint(
                condition=models.Q(status__in=["PENDING", "ACTIVE", "INACTIVE"]),
                name="responsiblepatientrelationship_status_valid",
            ),
            # A relationship can't be marked INACTIVE without recording when
            # and why (mirrors Invitation.used_at_requires_used_status, but
            # in the direction that matters here: INACTIVE implies both
            # fields are set, not the other way around).
            models.CheckConstraint(
                condition=~models.Q(status="INACTIVE")
                | (models.Q(deactivated_at__isnull=False) & ~models.Q(deactivation_reason="")),
                name="responsiblepatientrelationship_inactive_requires_deactivation_info",
            ),
        ]

    def __str__(self):
        return f"{self.responsible} -> {self.patient} ({self.relationship_type})"

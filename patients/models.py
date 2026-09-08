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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"

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

    responsible = models.ForeignKey(
        Responsible, on_delete=models.CASCADE, related_name="patient_relationships"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="responsible_relationships"
    )
    relationship_type = models.CharField(max_length=15, choices=RelationType.choices)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "relación responsable-paciente"
        verbose_name_plural = "relaciones responsable-paciente"
        constraints = [
            models.UniqueConstraint(
                fields=["responsible", "patient"], name="unique_responsible_patient"
            )
        ]

    def __str__(self):
        return f"{self.responsible} -> {self.patient} ({self.relationship_type})"

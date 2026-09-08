from django import forms

from patients.models import Patient, ResponsiblePatientRelationship


class MinorPatientForm(forms.Form):
    """Step 1 of 'Registrar paciente menor' (requirements.md §7.2.1).

    Deliberately minimal: only the minor's own identity data. No phone or
    address fields — requirements.md explicitly warns against asking the
    minor for data that really belongs to the responsible. No email field
    either — whether a minor patient may have one is an open decision
    (requirements.md §7.2.10), so nothing here assumes an answer.
    """

    first_name = forms.CharField(label="Nombre(s)", max_length=150)
    last_name_paterno = forms.CharField(label="Apellido paterno", max_length=100)
    last_name_materno = forms.CharField(label="Apellido materno", max_length=100, required=False)
    birth_date = forms.DateField(
        label="Fecha de nacimiento", widget=forms.DateInput(attrs={"type": "date"})
    )
    sex = forms.ChoiceField(label="Sexo", choices=Patient.Sex.choices)
    curp = forms.CharField(label="CURP", max_length=18, required=False)
    nationality = forms.CharField(
        label="Nacionalidad", max_length=100, required=False, initial="Mexicana"
    )

    def person_data(self):
        data = self.cleaned_data
        return {
            "first_name": data["first_name"],
            "last_name_paterno": data["last_name_paterno"],
            "last_name_materno": data.get("last_name_materno", ""),
            "birth_date": data["birth_date"],
        }

    def patient_data(self):
        data = self.cleaned_data
        return {
            "sex": data["sex"],
            "curp": data.get("curp", ""),
            "nationality": data.get("nationality") or "Mexicana",
        }


class MinorRelationshipForm(forms.Form):
    """Step 2 of 'Registrar paciente menor' (requirements.md §7.2.2)."""

    relationship_type = forms.ChoiceField(
        label="Relación con el menor", choices=ResponsiblePatientRelationship.RelationType.choices
    )


class PatientProfileForm(forms.Form):
    """Paciente — 'Mi perfil' (requirements.md/docs/design/screens.md §6.6).

    Every domain field is editable except control/auth fields — `email`
    (User.email, the auth identifier) has no field here at all, not just a
    disabled one, so it can never be part of a valid POST regardless of
    what a client sends.
    """

    # Person fields
    first_name = forms.CharField(label="Nombre(s)", max_length=150)
    last_name_paterno = forms.CharField(label="Apellido paterno", max_length=100)
    last_name_materno = forms.CharField(label="Apellido materno", max_length=100, required=False)
    birth_date = forms.DateField(
        label="Fecha de nacimiento", widget=forms.DateInput(attrs={"type": "date"})
    )
    phone = forms.CharField(label="Teléfono celular", max_length=20, required=False)
    alternative_phone = forms.CharField(label="Teléfono alternativo", max_length=20, required=False)
    street = forms.CharField(label="Calle", max_length=150, required=False)
    exterior_number = forms.CharField(label="Número", max_length=20, required=False)
    neighborhood = forms.CharField(label="Colonia", max_length=100, required=False)
    postal_code = forms.CharField(label="Código postal", max_length=10, required=False)
    municipality = forms.CharField(label="Municipio/alcaldía", max_length=100, required=False)
    state = forms.CharField(label="Estado", max_length=100, required=False)
    country = forms.CharField(label="País", max_length=100, required=False)

    # Patient fields
    curp = forms.CharField(label="CURP", max_length=18, required=False)
    nationality = forms.CharField(label="Nacionalidad", max_length=100, required=False)
    sex = forms.ChoiceField(label="Sexo", choices=Patient.Sex.choices)
    emergency_contact_name = forms.CharField(
        label="Nombre del contacto de emergencia", max_length=150, required=False
    )
    emergency_contact_phone = forms.CharField(
        label="Teléfono del contacto de emergencia", max_length=20, required=False
    )
    blood_type = forms.CharField(label="Tipo sanguíneo", max_length=5, required=False)
    allergies = forms.CharField(label="Alergias", widget=forms.Textarea, required=False)
    chronic_conditions = forms.CharField(
        label="Enfermedades crónicas", widget=forms.Textarea, required=False
    )
    current_medications = forms.CharField(
        label="Medicamentos actuales", widget=forms.Textarea, required=False
    )
    surgical_history = forms.CharField(
        label="Antecedentes quirúrgicos", widget=forms.Textarea, required=False
    )
    relevant_hospitalizations = forms.CharField(
        label="Hospitalizaciones relevantes", widget=forms.Textarea, required=False
    )

    _PERSON_FIELDS = (
        "first_name",
        "last_name_paterno",
        "last_name_materno",
        "birth_date",
        "phone",
        "alternative_phone",
        "street",
        "exterior_number",
        "neighborhood",
        "postal_code",
        "municipality",
        "state",
        "country",
    )
    _PATIENT_FIELDS = (
        "curp",
        "nationality",
        "sex",
        "emergency_contact_name",
        "emergency_contact_phone",
        "blood_type",
        "allergies",
        "chronic_conditions",
        "current_medications",
        "surgical_history",
        "relevant_hospitalizations",
    )

    def __init__(self, *args, person, patient, **kwargs):
        self._person = person
        self._patient = patient
        initial = kwargs.pop("initial", {})
        if not args:  # unbound (GET) — prefill from the current records
            for field_name in self._PERSON_FIELDS:
                initial.setdefault(field_name, getattr(person, field_name))
            for field_name in self._PATIENT_FIELDS:
                initial.setdefault(field_name, getattr(patient, field_name))
        super().__init__(*args, initial=initial, **kwargs)

    def save(self):
        for field_name in self._PERSON_FIELDS:
            setattr(self._person, field_name, self.cleaned_data[field_name])
        self._person.save()

        for field_name in self._PATIENT_FIELDS:
            setattr(self._patient, field_name, self.cleaned_data[field_name])
        self._patient.save()

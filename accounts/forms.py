from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from patients.models import Patient


class EmailVerifiedAuthenticationForm(AuthenticationForm):
    """Blocks login for users whose email hasn't been verified yet
    (requirements.md §4, §36 regla 3).

    `confirm_login_allowed` is Django's documented hook for exactly this kind
    of extra check — it runs after credentials are confirmed valid, so a
    wrong password still reports as invalid credentials, not as "unverified".
    """

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.email_verified:
            raise forms.ValidationError(
                "Debes verificar tu correo electrónico antes de iniciar sesión.",
                code="email_not_verified",
            )


class InvitationCreateForm(forms.Form):
    email = forms.EmailField(label="Email del prospecto")


class InvitationAcceptForm(forms.Form):
    """Registration form used at the end of the invitation flow.

    Fase 1 covers the adult-patient-registers-themselves case. A responsible
    registering a minor patient on their behalf is a distinct flow the
    requirements describe but do not fully detail — left for a follow-up
    decision rather than guessed here.
    """

    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")

    first_name = forms.CharField(label="Nombre(s)", max_length=150)
    last_name_paterno = forms.CharField(label="Apellido paterno", max_length=100)
    last_name_materno = forms.CharField(label="Apellido materno", max_length=100, required=False)
    birth_date = forms.DateField(label="Fecha de nacimiento", widget=forms.DateInput(attrs={"type": "date"}))
    phone = forms.CharField(label="Teléfono celular", max_length=20, required=False)
    alternative_phone = forms.CharField(label="Teléfono alternativo", max_length=20, required=False)

    street = forms.CharField(label="Calle", max_length=150, required=False)
    exterior_number = forms.CharField(label="Número", max_length=20, required=False)
    neighborhood = forms.CharField(label="Colonia", max_length=100, required=False)
    postal_code = forms.CharField(label="Código postal", max_length=10, required=False)
    municipality = forms.CharField(label="Municipio/alcaldía", max_length=100, required=False)
    state = forms.CharField(label="Estado", max_length=100, required=False)
    country = forms.CharField(label="País", max_length=100, required=False, initial="México")

    sex = forms.ChoiceField(label="Sexo", choices=Patient.Sex.choices)
    curp = forms.CharField(label="CURP", max_length=18, required=False)
    nationality = forms.CharField(label="Nacionalidad", max_length=100, required=False, initial="Mexicana")
    emergency_contact_name = forms.CharField(label="Contacto de emergencia", max_length=150, required=False)
    emergency_contact_phone = forms.CharField(label="Teléfono de emergencia", max_length=20, required=False)

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("password_confirm")
        if password and confirm and password != confirm:
            self.add_error("password_confirm", "Las contraseñas no coinciden.")
        if password:
            try:
                password_validation.validate_password(password)
            except forms.ValidationError as exc:
                # Attach to the field itself: raising here would file the
                # messages under __all__, far from the input they describe.
                self.add_error("password", exc)
        return cleaned

    def person_data(self):
        data = self.cleaned_data
        return {
            "first_name": data["first_name"],
            "last_name_paterno": data["last_name_paterno"],
            "last_name_materno": data.get("last_name_materno", ""),
            "birth_date": data["birth_date"],
            "phone": data.get("phone", ""),
            "alternative_phone": data.get("alternative_phone", ""),
            "street": data.get("street", ""),
            "exterior_number": data.get("exterior_number", ""),
            "neighborhood": data.get("neighborhood", ""),
            "postal_code": data.get("postal_code", ""),
            "municipality": data.get("municipality", ""),
            "state": data.get("state", ""),
            "country": data.get("country") or "México",
        }

    def patient_data(self):
        data = self.cleaned_data
        return {
            "sex": data["sex"],
            "curp": data.get("curp", ""),
            "nationality": data.get("nationality") or "Mexicana",
            "emergency_contact_name": data.get("emergency_contact_name", ""),
            "emergency_contact_phone": data.get("emergency_contact_phone", ""),
        }

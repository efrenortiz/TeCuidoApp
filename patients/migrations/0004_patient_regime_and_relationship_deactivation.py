# Generated for TeCuidoApp (ADR-007 §3.8 addendum, requirements.md §7.2.8).
#
# `regime` is added nullable first, backfilled from each existing Patient's
# chronological age (mirroring Person.is_minor's own logic, reimplemented
# here because RunPython only sees the frozen historical model — no custom
# properties), then tightened to NOT NULL + CheckConstraint. This keeps the
# field itself default-less (deny-by-default, same reasoning as `status`)
# while still being able to migrate the rows that already exist.

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def backfill_patient_regime(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    today = timezone.now().date()
    for patient in Patient.objects.select_related("person").all():
        birth_date = patient.person.birth_date
        had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
        age = today.year - birth_date.year - (0 if had_birthday else 1)
        patient.regime = "MINOR" if age < 18 else "ADULT"
        patient.save(update_fields=["regime"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("doctors", "0001_initial"),
        ("patients", "0003_alter_responsiblepatientrelationship_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="regime",
            field=models.CharField(
                choices=[("MINOR", "Menor"), ("ADULT", "Adulto")], max_length=5, null=True
            ),
        ),
        migrations.RunPython(backfill_patient_regime, noop_reverse),
        migrations.AlterField(
            model_name="patient",
            name="regime",
            field=models.CharField(choices=[("MINOR", "Menor"), ("ADULT", "Adulto")], max_length=5),
        ),
        migrations.AddConstraint(
            model_name="patient",
            constraint=models.CheckConstraint(
                condition=models.Q(("regime__in", ["MINOR", "ADULT"])), name="patient_regime_valid"
            ),
        ),
        migrations.AddField(
            model_name="patient",
            name="regime_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="patient",
            name="regime_changed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="regime_transitions_performed",
                to="doctors.doctor",
            ),
        ),
        migrations.AddField(
            model_name="responsiblepatientrelationship",
            name="deactivated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="responsiblepatientrelationship",
            name="deactivation_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ADULT_TRANSITION", "Transición a régimen adulto"),
                    ("REQUEST_REJECTED", "Solicitud rechazada"),
                    ("OTHER", "Otro"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="responsiblepatientrelationship",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("status", "INACTIVE"), _negated=True),
                    models.Q(
                        ("deactivated_at__isnull", False), models.Q(("deactivation_reason", ""), _negated=True)
                    ),
                    _connector="OR",
                ),
                name="responsiblepatientrelationship_inactive_requires_deactivation_info",
            ),
        ),
    ]

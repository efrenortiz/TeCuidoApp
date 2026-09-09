# Generated for TeCuidoApp (ADR-007 §3.8 addendum, requirements.md §7.2.8).
#
# `regime` has no `default` and is NOT NULL from the moment it's added —
# deliberately not derived from `Person.birth_date`/age (see ADR-007 §3.8:
# chronological age and authorization regime are independent; a patient can
# be chronologically adult and stay MINOR indefinitely until a doctor
# executes `transition_patient_to_adult`). There is no backfill step here
# on purpose: inferring `regime` from age for pre-existing rows would
# silently "graduate" chronologically-adult MINOR patients to ADULT without
# the explicit doctor-driven transition ever running, and without
# deactivating their ResponsiblePatientRelationships — exactly the
# contradiction this migration must not introduce. Fase 1 has no production
# data; this migration only ever runs against a schema being built fresh
# (migrations always apply before any fixture/data load), so every Patient
# row that will ever exist declares `regime` explicitly at creation time
# (`register_minor_patient` passes MINOR, `accept_invitation` passes ADULT)
# — nothing needs a value backfilled for it.

import django.db.models.deletion
from django.db import migrations, models


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

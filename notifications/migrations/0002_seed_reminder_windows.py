"""Ventanas iniciales de recordatorio (requirements.md §27.1, F6-D02):
15/10/5/1 días. Datos semilla, no una constante Python — ver
docs/design/phase-6-notification-data-model.md §2.2 (cierra H-01)."""

from django.db import migrations

INITIAL_OFFSETS = [15, 10, 5, 1]


def seed_reminder_windows(apps, schema_editor):
    ReminderWindow = apps.get_model("notifications", "ReminderWindow")
    for offset_days in INITIAL_OFFSETS:
        ReminderWindow.objects.get_or_create(offset_days=offset_days, defaults={"is_active": True})


def remove_reminder_windows(apps, schema_editor):
    ReminderWindow = apps.get_model("notifications", "ReminderWindow")
    ReminderWindow.objects.filter(offset_days__in=INITIAL_OFFSETS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_reminder_windows, remove_reminder_windows),
    ]

"""ITD-006 (docs/phases/phase-6-implementation-summary.md): sin Celery/Redis
— este comando está pensado para ejecutarse periódicamente vía cron del
sistema operativo (p. ej. cada 5-15 minutos), consistente con
docs/phases/phase-6-design-freeze.md §19/§24."""

from django.core.management.base import BaseCommand

from notifications.services import process_due_notifications


class Command(BaseCommand):
    help = "Envía las notificaciones/recordatorios pendientes cuya fecha de procesamiento ya llegó."

    def handle(self, *args, **options):
        result = process_due_notifications()
        self.stdout.write(
            self.style.SUCCESS(
                f"Notificaciones procesadas: {result['sent']} enviadas, {result['skipped']} omitidas."
            )
        )

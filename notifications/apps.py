from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Fase 6 (docs/phases/phase-6-design-freeze.md §8.1). App transversal:
    representa y ejecuta intenciones de comunicación por Email. No posee
    reglas de Agenda ni de identidad — ver `notifications/receivers.py` para
    cómo se entera de que existe una `Appointment` sin que `appointments`
    tenga que importar esta app (ITD-002, mantiene la dirección de
    dependencia fase-temprana → no depende de fase-tardía)."""

    name = "notifications"

    def ready(self):
        from notifications import receivers  # noqa: F401

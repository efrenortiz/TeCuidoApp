"""Domain signals dispatched by `appointments.services.appointment` when an
`Appointment` is created, modified or cancelled.

Fase 6 (docs/design/phase-6-notification-service-contracts.md, `notify_appointment_created`)
necesita reaccionar a estos eventos sin que `appointments` (Fase 2) tenga que
importar `notifications` (Fase 6) — esa dirección de dependencia (fase
temprana dependiendo de una fase posterior) rompería el patrón ya usado en
todo el proyecto (`care_requests`/`medical_records` importan `appointments`,
nunca al revés). `appointments` solo declara y despacha estas señales; quien
las escuche (hoy, `notifications.receivers`) es responsabilidad de quien
escucha, no de este módulo.

Estas señales son deliberadamente distintas de `AuditEvent`
(`medical_records.services.audit`): la auditoría clínica nunca se delega a
signals (AH-156, `medical_records/services/audit.py`) porque el significado
clínico debe decidirlo el servicio de dominio en el punto exacto donde
conoce el resultado real. Una notificación de Email es, por diseño
(docs/phases/phase-6-design-freeze.md §21), un efecto secundario
desacoplado de la transacción de negocio — exactamente el caso de uso para
el que Django signals + `transaction.on_commit` existen.
"""

import django.dispatch

# kwargs: appointment
appointment_created = django.dispatch.Signal()

# kwargs: appointment, event_context (dict opcional con detalle de la modificación)
appointment_modified = django.dispatch.Signal()

# kwargs: appointment, event_context (dict opcional con detalle de la cancelación)
appointment_cancelled = django.dispatch.Signal()

"""Date/time helpers shared by Agenda services. Centralized so "6 meses
calendario, no 180 días" (docs/phases/phase-2-agenda.md §6.3) and "zona
horaria = Clinic" (§5.9) are computed the same way everywhere."""

import calendar
import datetime as dt


def add_months(date, months):
    """`date` shifted by `months` calendar months, clamping the day to the
    target month's length (e.g. 31/01 + 1 month -> 28/02 or 29/02)."""
    month_index = date.month - 1 + months
    year = date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    return date.replace(year=year, month=month, day=day)


def combine_local(date, time, clinic):
    """A plain date + time, as they mean them at `clinic`, as a
    timezone-aware datetime (docs/phases/phase-2-agenda.md §5.9)."""
    return dt.datetime.combine(date, time, tzinfo=clinic.zoneinfo)

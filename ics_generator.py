"""Part C helpers backed by the same installed iCalendar library.

Compatibility helpers, not a second export workflow. No missing config module
or separate ics package is required.
"""
from icalendar import Calendar, Event

from calendar_export import generate_ics
from exceptions import ICSGenerationError
from parser import parse_and_convert_time


def generate_ics_content(events: list) -> str:
    if not events or any(not isinstance(event, Event) for event in events):
        raise ICSGenerationError("Provide validated iCalendar Event objects.")
    calendar = Calendar()
    calendar.add("version", "2.0")
    calendar.add("prodid", "-//SnapSched HKU//Compatibility Export//EN")
    for event in events:
        calendar.add_component(event)
    return calendar.to_ical().decode("utf-8")


def create_event_obj(event: dict) -> Event:
    """Primary event only; use calendar_export for deadline-inclusive output."""
    return Calendar.from_ical(generate_ics(event)).walk("VEVENT")[0]


def load_existing_ics(content: str) -> list:
    """Parse only; not automatic merging or real calendar-client evidence."""
    from import_validator import validate_import
    validate_import(content)
    return Calendar.from_ical(content).walk("VEVENT")

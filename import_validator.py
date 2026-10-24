"""Calendar structure check, not a simulation of any actual calendar client."""
from icalendar import Calendar

from exceptions import ICSImportValidationError
from integrations import calendar_file_bytes


def validate_import(ics_content: str | bytes) -> bool:
    try:
        calendar = Calendar.from_ical(calendar_file_bytes(ics_content))
        events = calendar.walk("VEVENT")
        if not events or any(not all(event.get(key) for key in ("summary", "uid", "dtstamp", "dtstart")) for event in events):
            raise ValueError("Missing required event properties.")
        for event in events:
            event.decoded("dtstart")
        return True
    except Exception as error:
        raise ICSImportValidationError("Calendar structure could not be verified.") from error

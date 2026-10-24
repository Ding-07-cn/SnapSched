"""Part C-compatible parsing helpers using strict shared field validation."""
from datetime import datetime
from zoneinfo import ZoneInfo

from interface_state import normalise_event, parse_deadline

DEFAULT_TIMEZONE = "Asia/Hong_Kong"


def parse_event_fields(event_dict: dict) -> dict:
    return normalise_event(event_dict)[0]


def parse_and_convert_time(date_str, time_str, timezone_str=DEFAULT_TIMEZONE):
    if timezone_str != DEFAULT_TIMEZONE:
        raise ValueError("This MVP accepts Hong Kong time only.")
    raw = f"{date_str} {time_str}"
    parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M")
    if parsed.strftime("%Y-%m-%d %H:%M") != raw:
        raise ValueError("Use YYYY-MM-DD and HH:MM.")
    return parsed.replace(tzinfo=ZoneInfo(timezone_str))


def parse_and_convert_time_from_str(value, timezone_str=DEFAULT_TIMEZONE):
    if timezone_str != DEFAULT_TIMEZONE:
        raise ValueError("This MVP accepts Hong Kong time only.")
    parsed = parse_deadline(value)
    if not isinstance(parsed, datetime):
        raise ValueError("No closing time was stated; do not invent one.")
    return parsed.replace(tzinfo=ZoneInfo(timezone_str))

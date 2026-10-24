"""Part C-compatible validation; optional fields must remain optional."""
from exceptions import EventValidationError
from interface_state import confirmation_errors, normalise_event
from parser import (DEFAULT_TIMEZONE, parse_and_convert_time,
                    parse_and_convert_time_from_str)


def validate_event(event: dict) -> None:
    try:
        clean, _ = normalise_event(event)
        problems = confirmation_errors(clean)
    except (ValueError, TypeError, KeyError) as error:
        raise EventValidationError("Invalid event fields.") from error
    if problems:
        raise EventValidationError(" ".join(problems))


def validate_string_content(content: str) -> None:
    if not isinstance(content, str) or any(ord(ch) < 32 and ch not in "\n\r\t" for ch in content):
        raise EventValidationError("Content contains unsupported characters.")

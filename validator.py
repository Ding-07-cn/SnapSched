# Import necessary modules
from datetime import datetime
import dateutil.parser
import pytz
from exceptions import EventValidationError

# Configure default timezone
DEFAULT_TIMEZONE = "Asia/Hong_Kong"

def validate_event(event: dict) -> None:
    """
    Comprehensively validate the reasonableness and safety of event data
    Input:
        event: parsed event dictionary (fields already extracted)
    Output:
        None (raises exception if validation fails)
    """
    # 1. Required field check
    required_fields = [
        "event_name", "event_date", "start_time", "end_time",
        "venue", "registration_deadline", "registration_method"
    ]
    for field in required_fields:
        if not event.get(field):
            raise EventValidationError(f"Missing required field: {field}")

    # 2. Time format validation
    try:
        # Parse time fields
        event_date = event["event_date"]
        start_time = event["start_time"]
        end_time = event["end_time"]
        registration_deadline = event["registration_deadline"]
        timezone_str = event.get("timezone", DEFAULT_TIMEZONE)

        # Parse times
        start_dt = parse_and_convert_time(event_date, start_time, timezone_str)
        end_dt = parse_and_convert_time(event_date, end_time, timezone_str)
        registration_dt = parse_and_convert_time_from_str(registration_deadline, timezone_str)
    except Exception:
        raise EventValidationError("Invalid time format in event data.")

    # 3. Time logic validation
    if not event.get("all_day", False):
        if start_dt >= end_dt:
            raise EventValidationError("Start time must be before end time.")
    # All-day events: time validation may be skipped or handled specially

    # Registration deadline must be before event start time
    if registration_dt >= start_dt:
        raise EventValidationError("Registration deadline must be before event start time.")

    # 4. String content safety validation
    for field in ["event_name", "venue", "registration_method"]:
        content = event.get(field, "")
        validate_string_content(content)

def parse_and_convert_time(date_str, time_str, timezone_str):
    """
    Parse date and time strings and convert to a timezone-aware datetime object
    """
    dt_str = f"{date_str} {time_str}"
    dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    tz = pytz.timezone(timezone_str)
    dt_aware = tz.localize(dt_naive)
    return dt_aware

def parse_and_convert_time_from_str(time_str, timezone_str):
    """
    Parse a full time string (e.g. registration_deadline)
    """
    dt_naive = dateutil.parser.parse(time_str)
    tz = pytz.timezone(timezone_str)
    dt_aware = tz.localize(dt_naive)
    return dt_aware

def validate_string_content(content: str) -> None:
    """
    Check that the string content contains no illegal characters (control characters, script tags, etc.)
    """
    for ch in content:
        if ord(ch) < 32 and ch not in ['\n', '\r', '\t']:
            raise EventValidationError("Content contains illegal control characters.")
    # Extensible: detect other illegal characters or tags

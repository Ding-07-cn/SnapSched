# Import necessary modules
from datetime import datetime
import dateutil.parser
import pytz

# Configure default timezone
DEFAULT_TIMEZONE = "Asia/Hong_Kong"

def parse_event_fields(event_dict: dict) -> dict:
    """
    Extract event fields, handle all-day flag, and return the organized event dictionary
    Input:
        event_dict: raw event data dictionary
    Output:
        Processed dictionary containing:
            - event_name
            - event_date
            - start_time
            - end_time
            - venue
            - registration_deadline
            - registration_method
            - all_day
            - timezone
    """
    # Extract fields; assign empty string or default value if missing
    event = {
        "event_name": event_dict.get("event_name", "").strip(),
        "event_date": event_dict.get("event_date", "").strip(),
        "start_time": event_dict.get("start_time", "").strip(),
        "end_time": event_dict.get("end_time", "").strip(),
        "venue": event_dict.get("venue", "").strip(),
        "registration_deadline": event_dict.get("registration_deadline", "").strip(),
        "registration_method": event_dict.get("registration_method", "").strip(),
        "all_day": event_dict.get("all_day", False),
        "timezone": event_dict.get("timezone", DEFAULT_TIMEZONE).strip(),
    }
    return event

def parse_and_convert_time(date_str, time_str, timezone_str):
    """
    Parse date and time strings and convert to a timezone-aware datetime object
    Input:
        date_str: 'YYYY-MM-DD'
        time_str: 'HH:MM'
        timezone_str: timezone string
    Output:
        timezone-aware datetime object
    """
    dt_str = f"{date_str} {time_str}"
    # Parse time string
    dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    # Get timezone object
    tz = pytz.timezone(timezone_str)
    # Localize to timezone-aware datetime
    dt_aware = tz.localize(dt_naive)
    return dt_aware

def parse_and_convert_time_from_str(time_str, timezone_str):
    """
    Parse a full time string (e.g. registration_deadline)
    Input:
        time_str: 'YYYY-MM-DD HH:MM' or other parseable format
        timezone_str: timezone string
    Output:
        timezone-aware datetime object
    """
    dt_naive = dateutil.parser.parse(time_str)
    tz = pytz.timezone(timezone_str)
    dt_aware = tz.localize(dt_naive)
    return dt_aware

# Import necessary modules
from ics import Calendar, Event
from datetime import datetime
import pytz
from config import DEFAULT_TIMEZONE

def generate_ics_content(events: list) -> str:
    """
    Generate a complete ICS content string based on the event list
    Input:
        events: list of validated event objects (each an `ics` library Event instance)
    Output:
        ICS format string
    """
    cal = Calendar()
    for event in events:
        cal.events.add(event)
    return str(cal)

def create_event_obj(event: dict) -> Event:
    """
    Create an ICS event object from a single event dictionary
    Input:
        event: validated event dictionary
    Output:
        Event instance from the ics library
    """
    ics_event = Event()
    # Set event title
    ics_event.name = event["event_name"]
    # Set location
    ics_event.location = event["venue"]
    # Set description (including registration info)
    description = f"Registration Method: {event['registration_method']}"
    ics_event.description = description

    # Handle all-day events
    all_day = event.get("all_day", False)
    timezone_str = event.get("timezone", DEFAULT_TIMEZONE)
    tz = pytz.timezone(timezone_str)

    if all_day:
        # All-day event: set only the date, no time
        date_str = event["event_date"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        ics_event.begin = date_obj
        ics_event.make_all_day()
    else:
        # Non-all-day event: set specific times
        start_dt = parse_and_convert_time(event["event_date"], event["start_time"], timezone_str)
        end_dt = parse_and_convert_time(event["event_date"], event["end_time"], timezone_str)
        ics_event.begin = start_dt
        ics_event.end = end_dt

    # Set timezone info (optional; the ics library handles it automatically)
    ics_event.timezone = tz

    return ics_event

def parse_and_convert_time(date_str, time_str, timezone_str):
    """
    Parse date and time strings and convert to a timezone-aware datetime object
    """
    dt_str = f"{date_str} {time_str}"
    dt_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    tz = pytz.timezone(timezone_str)
    dt_aware = tz.localize(dt_naive)
    return dt_aware

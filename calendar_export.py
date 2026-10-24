"""Generate portable iCalendar bytes from explicitly reviewed event details.

No accounts, files, network calls or server-side calendar storage. Timed events
are serialized in UTC so calendar clients do not need a custom timezone database.
"""
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import json
from zoneinfo import ZoneInfo

from icalendar import Alarm, Calendar, Event

from interface_state import confirmation_errors, normalise_event, parse_deadline

HK = ZoneInfo("Asia/Hong_Kong")


def _uid(kind, event):
    identity = [kind, event["event_name"].casefold(), event["event_date"],
                event["start_time"] if not event["all_day"] else "all-day"]
    digest = sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:32]
    return f"{digest}@snapsched.invalid"


def _event(kind, event, now):
    item = Event()
    item.add("uid", _uid(kind, event))
    item.add("dtstamp", now.astimezone(timezone.utc).replace(microsecond=0))
    return item


def generate_ics(confirmed_event, *, now=None):
    """Return a new calendar, plus a future registration entry when stated.

    Date-only deadlines stay all-day. If their date is today, the closing time
    is unknown, so no deadline entry is generated. Re-exporting identical event
    identity uses the same UID; clients still control import/dedup behaviour.
    """
    if not isinstance(confirmed_event, dict):
        raise ValueError("Reviewed details must be a dictionary.")
    event, _ = normalise_event(confirmed_event)
    now = now or datetime.now(HK)
    if now.tzinfo is None:
        raise ValueError("Reference time must include a timezone.")
    now = now.astimezone(HK)
    if event["all_day"]:
        event["start_time"] = event["end_time"] = ""
    errors = confirmation_errors(event, today=now.date())
    if errors:
        raise ValueError("Review the event date/time before export.")
    day = date.fromisoformat(event["event_date"])
    item = _event("event", event, now)
    item.add("summary", event["event_name"])
    if event["venue"]:
        item.add("location", event["venue"])
    details = ["Created from user-reviewed poster details. Adding this entry does not register you."]
    for label, field in [("Registration", "registration_method"),
                         ("Registration wording", "registration_text_raw"),
                         ("Registration deadline", "registration_deadline")]:
        if event[field]:
            details.append(f"{label}: {event[field]}")
    item.add("description", "\n".join(details))
    if event["all_day"]:
        item.add("dtstart", day)
        item.add("dtend", day + timedelta(days=1))  # RFC 5545: exclusive end.
    else:
        start = datetime.combine(day, time.fromisoformat(event["start_time"]), HK)
        if start <= now:
            raise ValueError("The start time has passed. Check the event before export.")
        item.add("dtstart", start.astimezone(timezone.utc))
        if event["end_time"]:
            end = datetime.combine(day, time.fromisoformat(event["end_time"]), HK)
            item.add("dtend", end.astimezone(timezone.utc))
        # No printed end time -> omit DTEND, never assume a duration.
    output = Calendar()
    output.add("prodid", "-//SnapSched HKU//Reviewed Event Export//EN")
    output.add("version", "2.0")
    output.add("calscale", "GREGORIAN")
    output.add_component(item)
    deadline = parse_deadline(event["registration_deadline"])
    if isinstance(deadline, datetime):
        deadline = deadline.replace(tzinfo=HK)
        future = deadline > now
    else:
        future = bool(deadline and deadline > now.date())
    if future:
        reminder = _event("registration", event, now)
        reminder.add("summary", "Registration deadline: " + event["event_name"])
        reminder.add("description", "Check the organiser and complete registration yourself.\n" +
                     "\n".join(details[1:]))
        if isinstance(deadline, datetime):
            reminder.add("dtstart", deadline.astimezone(timezone.utc))
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", "Registration deadline: " + event["event_name"])
            alarm.add("trigger", timedelta(0))
            reminder.add_component(alarm)
        else:
            reminder.add("dtstart", deadline)
            reminder.add("dtend", deadline + timedelta(days=1))
        output.add_component(reminder)
    data = output.to_ical()
    parsed = Calendar.from_ical(data)
    if len(parsed.walk("VEVENT")) != (2 if future else 1):
        raise ValueError("Calendar verification failed.")
    return data

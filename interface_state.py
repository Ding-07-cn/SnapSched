"""Small, testable helpers for Part A. No AI calls or calendar creation here."""

from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
import json
from zoneinfo import ZoneInfo

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
TEXT_FIELDS = (
    "event_name", "event_date", "start_time", "end_time", "venue",
    "registration_deadline", "registration_method", "registration_text_raw",
)
FIELD_KEYS = tuple("field_" + field for field in TEXT_FIELDS) + ("field_all_day",)
FIELD_LIMITS = {"event_name": 200, "event_date": 10, "start_time": 5, "end_time": 5,
                "venue": 300, "registration_deadline": 16, "registration_method": 2000,
                "registration_text_raw": 2000}


def empty_event():
    return {**dict.fromkeys(TEXT_FIELDS, ""), "all_day": False,
            "timezone": "Asia/Hong_Kong"}


def sample_event():
    """Fixed saved demo data, NOT inferred from an uploaded image."""
    return {
        "event_name": "Student Research Skills Workshop (DEMO)",
        "event_date": "2026-11-05", "start_time": "15:00", "end_time": "16:00",
        "venue": "Demo Room 101 (sample location)",
        "registration_deadline": "2026-11-03 18:00",
        "registration_method": "https://example.com/register",
        "registration_text_raw": "",
        "all_day": False, "timezone": "Asia/Hong_Kong",
    }


def normalise_event(payload):
    if not isinstance(payload, dict):
        raise ValueError("The extraction module must return a dictionary.")
    result = empty_event()
    for field in TEXT_FIELDS:
        value = payload.get(field, "")
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string or null.")
        if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise ValueError(f"{field} contains invalid control characters.")
        if len(value.strip()) > FIELD_LIMITS[field]:
            raise ValueError(f"{field} is too long for the review form.")
        result[field] = value.strip()
    all_day = payload.get("all_day", False)
    if not isinstance(all_day, bool):
        raise ValueError("all_day must be true or false.")
    result["all_day"] = all_day
    # The UI is intentionally Hong Kong-only; B must not silently convert zones.
    if payload.get("timezone", "Asia/Hong_Kong") != "Asia/Hong_Kong":
        raise ValueError("This interface currently accepts Hong Kong time only.")
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(x, str) for x in warnings):
        raise ValueError("warnings must be a list of strings.")
    if len(warnings) > 30 or any(len(x) > 500 for x in warnings):
        raise ValueError("Too many or excessively long extraction warnings.")
    return result, warnings


def inspect_image(content):
    """Validate image bytes, not only the filename or claimed MIME type."""
    if not content or len(content) > MAX_FILE_BYTES:
        raise ValueError("Choose a non-empty JPG/PNG image of at most 8 MB.")
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format not in {"PNG", "JPEG"}:
                raise ValueError("Only real JPG and PNG images are supported.")
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Use a still image, not an animated or multi-frame image.")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError("Please resize the image to 20 megapixels or less.")
            mime_type = "image/png" if image.format == "PNG" else "image/jpeg"
            image.verify()
        # Decode now so corrupt files cannot fail later in the preview.
        with Image.open(BytesIO(content)) as image:
            oriented = ImageOps.exif_transpose(image).convert("RGBA")
            preview = Image.new("RGB", oriented.size, "white")
            preview.paste(oriented, mask=oriented.getchannel("A"))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("This image cannot be read. Please choose another JPG/PNG.") from error
    return preview, mime_type


def confirmation_errors(event, today=None):
    """UI completeness checks. Part C still owns final calendar validation."""
    errors = []
    if not event["event_name"].strip():
        errors.append("Enter the event name.")
    try:
        raw_date = event["event_date"]
        event_date = date.fromisoformat(raw_date)
        if event_date.isoformat() != raw_date:
            raise ValueError
        today = today or datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
        if event_date < today:
            errors.append("The event date is in the past. Check it before proceeding.")
    except ValueError:
        errors.append("Enter a complete, valid date as YYYY-MM-DD; do not guess the year.")
    if not event["all_day"]:
        try:
            if datetime.strptime(event["start_time"], "%H:%M").strftime("%H:%M") != event["start_time"]:
                raise ValueError
        except ValueError:
            errors.append("Enter a start time as HH:MM (24-hour), or deliberately choose All-day.")
        if event["end_time"]:
            try:
                if datetime.strptime(event["end_time"], "%H:%M").strftime("%H:%M") != event["end_time"]:
                    raise ValueError
                if event["start_time"] and event["end_time"] <= event["start_time"]:
                    errors.append("For this single-day MVP, the end time must be after the start time. "
                                  "Check overnight events with the calendar owner.")
            except ValueError:
                errors.append("Use HH:MM for the end time, or leave it blank if not stated.")
    try:
        parse_deadline(event["registration_deadline"])
    except ValueError:
        errors.append("Use YYYY-MM-DD or YYYY-MM-DD HH:MM for a stated deadline, or leave it blank.")
    return errors


def parse_deadline(value):
    """A printed date without a time must never silently become midnight."""
    if not value:
        return None
    if len(value) == 10:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() == value:
            return parsed
    else:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
        if parsed.strftime("%Y-%m-%d %H:%M") == value:
            return parsed
    raise ValueError("Invalid deadline format.")


def registration_warning(event, now=None):
    """Warn without rejecting an upcoming event just because registration closed."""
    try:
        deadline = parse_deadline(event["registration_deadline"])
    except ValueError:
        return None
    now = now or datetime.now(ZoneInfo("Asia/Hong_Kong"))
    if deadline is None:
        return None
    if not isinstance(deadline, datetime):
        if deadline <= now.date():
            return ("Registration closes today or earlier, but no time is stated. Check with the "
                    "organiser. No possibly expired deadline entry will be exported.")
        return "No registration closing time is stated. The deadline will be a date-only entry, not a guessed time."
    if deadline <= now.replace(tzinfo=None):
        return ("The registration deadline has passed. Adding this event does not secure a place. "
                "Check with the organiser; an expired deadline must not become a new reminder.")
    return None


def review_fingerprint(source_id, event):
    data = json.dumps([source_id, event], sort_keys=True)
    return sha256(data.encode()).hexdigest()


def invalidate_review(state):
    state["reviewed"] = False
    state["approved_fingerprint"] = None
    state["confirmed_event"] = None
    state["calendar_bytes"] = None


def populate_fields(state, event):
    for field in TEXT_FIELDS:
        state["field_" + field] = event.get(field, "")
    state["field_all_day"] = event.get("all_day", False)
    invalidate_review(state)


def replace_source(state, source_id):
    if state.get("source_id") == source_id:
        return
    state["source_id"] = source_id
    state["extraction_warnings"] = []
    state["source_label"] = "Manual entry; no AI result yet"
    state["allow_ai"] = False
    state["preview_image"] = None
    state["preview_mime_type"] = ""
    state["image_error"] = None
    state["extraction_rejected"] = False
    populate_fields(state, empty_event())

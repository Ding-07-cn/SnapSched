"""SnapSched Part B - AI extraction of event details from one poster image.

Public interface (teammates code against this, do not change it):

    extract_event(image_bytes, mime_type, reference_date=None, demo_image_id=None) -> dict

The returned dict always has the keys ``status``, ``mode``, ``fields``, ``warnings``,
``warning_codes``, ``message`` and ``raw_model_output`` (see ``_build_result``).
``warnings`` and ``warning_codes`` are parallel lists: ``warnings[i]`` is the plain-English
text for ``warning_codes[i]``. ``LOW_CONFIDENCE`` appears once per doubtful field, so the
same code can repeat; the matching text names the field.

Design rules
------------
* Never invent data. Anything unreadable, unprinted or invalid becomes ``None``.
* The model is told the poster is untrusted data. We additionally only ever read a fixed set
  of known keys from its reply, so extra "instructions" cannot add fields.
* Nothing sensitive is logged or written to disk. The only thing this module ever writes is
  ``demo_results/<id>.json`` via ``save_demo_result``, and only when a human asks for it.
* All provider-specific code lives in ``_call_vision_model``. To swap providers, rewrite
  that one function (and nothing else).

YEAR POLICY (one approach, used everywhere)
-------------------------------------------
A date is only trusted if its year is PRINTED on the poster. If the poster prints no year,
``date`` is set to ``None``, ``date_has_year_printed`` is ``False`` and the warning
``YEAR_NOT_PRINTED`` is raised. ``reference_date`` is never used to fill in a year; it is
only passed to the model as context and used to flag past events / passed deadlines.
The same rule applies to the registration deadline.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from PIL import Image, ImageOps, UnidentifiedImageError

from prompts import PROMPT_VERSION, build_prompt  # noqa: F401  (PROMPT_VERSION re-exported for logs)

# Load GEMINI_API_KEY etc. from a .env next to this file. Never printed or logged.
load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger("snapsched.extraction")

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------

DEMO_DIR = Path(__file__).resolve().parent / "demo_results"
DEFAULT_MODEL = "gemini-3.5-flash"      # override with SNAPSCHED_MODEL
DEFAULT_TIMEOUT_SECONDS = 60.0          # override with SNAPSCHED_TIMEOUT_SECONDS
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 50_000_000                 # refuse absurdly large images before decoding them
MAX_LONG_SIDE = 1600
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = (1.0, 2.0)
HK_TZ = timezone(timedelta(hours=8))    # Hong Kong has no DST; avoids needing the tzdata package

FIELD_NAMES = (
    "event_name", "date", "date_has_year_printed", "start_time", "end_time", "venue",
    "registration_deadline", "registration_deadline_time", "registration_method",
    "registration_text_raw",
)

WARNING_MESSAGES = {
    "MISSING_EVENT_NAME": "No event name could be read from the poster. Please type it in.",
    "MISSING_DATE": "No event date could be read from the poster. Please enter it yourself.",
    "YEAR_NOT_PRINTED": "A date on the poster has no printed year, so it was left blank "
                        "rather than guessed. Please enter the full date yourself.",
    "AMBIGUOUS_DATE": "The date is written with numbers only (for example 03/11/2026). "
                      "It was read day-first, as is usual in Hong Kong. Please check the day and month.",
    "MISSING_TIME": "No start time could be read from the poster. Please enter it yourself.",
    "MISSING_VENUE": "No venue could be read from the poster. Please enter it yourself.",
    "MISSING_REGISTRATION": "No registration details were found on the poster.",
    "CHECK_ORGANISER_PAGE": "The poster points to a website or link for more details. "
                            "Please check the organiser's page for the missing information.",
    "QR_SCAN_MANUALLY": "A QR code is shown on the poster. SnapSched does not read QR codes - "
                        "please scan it with your phone and check where it leads.",
    "MULTIPLE_EVENTS": "The poster seems to list several events. Only the most prominent one was "
                       "read. Please crop the image to a single event if this is the wrong one.",
    "LOW_CONFIDENCE": "The AI was not sure it read this detail correctly. Please check it carefully.",
    "REGISTRATION_DEADLINE_PASSED": "The registration deadline has already passed.",
    "EVENT_IN_PAST": "The event date is in the past.",
}

# Human-readable names used in LOW_CONFIDENCE messages.
FIELD_LABELS = {
    "event_name": "event name", "date": "date", "start_time": "start time",
    "end_time": "end time", "venue": "venue",
    "registration_deadline": "registration deadline",
    "registration_deadline_time": "registration deadline time",
    "registration_method": "registration method",
    "registration_text_raw": "registration wording",
}

_RETRY_OR_DEMO = " You can try again, or switch to demo mode to use a saved sample poster."
ERROR_MESSAGES = {
    "bad_type": "Only JPG and PNG images are supported. Please upload a .jpg or .png file.",
    "too_large": "That image is larger than 10 MB. Please upload a smaller JPG or PNG.",
    "bad_image": "That file could not be opened as a JPG or PNG image. Please upload a different image.",
    "config": "The AI service is not set up on this computer (missing API key or software)." + _RETRY_OR_DEMO,
    "auth": "The AI service rejected our credentials." + _RETRY_OR_DEMO,
    "rate_limit": "The AI service is busy or its usage limit was reached." + _RETRY_OR_DEMO,
    "timeout": "The AI service took too long to respond." + _RETRY_OR_DEMO,
    "network": "Could not reach the AI service. Please check the internet connection." + _RETRY_OR_DEMO,
    "server": "The AI service had a temporary problem." + _RETRY_OR_DEMO,
    "request": "The AI service could not process this request." + _RETRY_OR_DEMO,
    "empty": "The AI service returned an empty answer." + _RETRY_OR_DEMO,
    "bad_json": "The AI service returned an answer we could not understand." + _RETRY_OR_DEMO,
    "simulated": "Simulated AI error (SNAPSCHED_SIMULATE_API_ERROR is on). No result was produced."
                 + _RETRY_OR_DEMO,
    "demo_missing": "Demo mode only works for the supplied sample posters, and no saved result "
                    "exists for this image. Switch to live mode to read other posters.",
    "unknown": "Something went wrong while reading the poster." + _RETRY_OR_DEMO,
}

NO_EVENT_MESSAGE = ("This image does not look like an event poster, so no event was extracted. "
                    "Please upload a poster that shows an event's name, date and venue.")
DEMO_NOTICE = "Demo mode: this is a saved result for a sample poster, not a live AI reading."


class _ExtractionError(Exception):
    """Internal error carrying a ``kind`` (key of ERROR_MESSAGES). Never shown raw to users."""

    def __init__(self, kind: str, transient: bool = False, raw_output: Optional[str] = None):
        super().__init__(kind)
        self.kind = kind
        self.transient = transient
        self.raw_output = raw_output


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------

def extract_event(image_bytes: bytes, mime_type: str, reference_date: str | None = None,
                  demo_image_id: str | None = None) -> dict:
    """Extract event details from one poster image. See the module docstring.

    ``reference_date`` is "YYYY-MM-DD" (default: today in Asia/Hong_Kong). Pass it explicitly
    in tests so results are reproducible. Never raises; failures come back as ``api_error``.
    """
    started = time.monotonic()
    ref = _resolve_reference_date(reference_date)
    demo_requested = bool(demo_image_id) or os.getenv("SNAPSCHED_DEMO_MODE") == "1"
    mode = "demo" if demo_requested else "live"
    error_kind = None
    try:
        if os.getenv("SNAPSCHED_SIMULATE_API_ERROR") == "1":
            raise _ExtractionError("simulated")
        if demo_requested:
            result = _load_demo_result(demo_image_id, ref)
        else:
            result = _extract_live(image_bytes, mime_type, ref)
    except _ExtractionError as err:
        error_kind = err.kind
        result = _build_result("api_error", mode, message=ERROR_MESSAGES.get(err.kind, ERROR_MESSAGES["unknown"]),
                               raw_model_output=err.raw_output)
    except Exception as err:  # last-resort guard: the UI must never crash on a bad poster
        error_kind = f"unexpected:{type(err).__name__}"
        result = _build_result("api_error", mode, message=ERROR_MESSAGES["unknown"])
    # Only non-sensitive facts are logged: never image data, keys or extracted text.
    logger.info("extract_event status=%s mode=%s latency_ms=%d error=%s prompt=%s",
                result["status"], result["mode"], int((time.monotonic() - started) * 1000),
                error_kind, PROMPT_VERSION)
    return result


def save_demo_result(image_id: str, result: dict) -> Path:
    """Save a live result as demo_results/<image_id>.json. Used only by ``test_extraction.py --save-demo``.

    Only successful live results (``ok`` / ``no_event_found``) are saved. ``raw_model_output``
    is dropped so the file holds exactly what the UI would have shown.
    """
    _check_demo_id(image_id)
    if result.get("mode") != "live" or result.get("status") not in ("ok", "no_event_found"):
        raise ValueError("Only successful live results can be saved as demo results.")
    to_save = {k: v for k, v in result.items() if k != "raw_model_output"}
    DEMO_DIR.mkdir(exist_ok=True)
    path = DEMO_DIR / f"{image_id}.json"
    path.write_text(json.dumps(to_save, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------
# Result construction
# --------------------------------------------------------------------------------------

def _empty_fields() -> dict:
    fields: dict[str, Any] = {name: None for name in FIELD_NAMES}
    fields["date_has_year_printed"] = False
    return fields


def _build_result(status: str, mode: str, fields: Optional[dict] = None,
                  findings: Optional[list] = None, message: Optional[str] = None,
                  raw_model_output: Optional[str] = None) -> dict:
    """Assemble the public result dict. ``findings`` is a list of (code, text) pairs."""
    findings = findings or []
    return {
        "status": status,
        "mode": mode,
        "fields": fields if (status == "ok" and fields is not None) else _empty_fields(),
        "warnings": [text for _, text in findings],
        "warning_codes": [code for code, _ in findings],
        "message": message,
        "raw_model_output": raw_model_output,
    }


def _finding(code: str, suffix: str = "") -> tuple:
    return code, WARNING_MESSAGES[code] + suffix


# --------------------------------------------------------------------------------------
# Live extraction pipeline
# --------------------------------------------------------------------------------------

def _extract_live(image_bytes: bytes, mime_type: str, ref: date) -> dict:
    jpeg_bytes = _prepare_image(image_bytes, mime_type)
    prompt = build_prompt(ref.isoformat())
    raw = _call_with_retry(jpeg_bytes, "image/jpeg", prompt)
    if not isinstance(raw, str) or not raw.strip():
        raise _ExtractionError("empty")
    parsed = _parse_model_json(raw)
    if parsed is None:
        raise _ExtractionError("bad_json", raw_output=raw)

    verdict = _as_bool_or_none(parsed.get("is_event_poster"))
    if verdict is None:
        raise _ExtractionError("bad_json", raw_output=raw)
    if verdict is False:
        return _build_result("no_event_found", "live", message=NO_EVENT_MESSAGE, raw_model_output=raw)

    fields, findings = _interpret(parsed, ref)
    return _build_result("ok", "live", fields, findings, raw_model_output=raw)


def _resolve_reference_date(reference_date: Optional[str]) -> date:
    """Parse the explicit reference date, or fall back to today in Hong Kong."""
    if reference_date:
        try:
            return date.fromisoformat(reference_date.strip())
        except (ValueError, AttributeError):
            logger.warning("invalid reference_date; using today (Asia/Hong_Kong)")
    return datetime.now(HK_TZ).date()


def _prepare_image(image_bytes: bytes, mime_type: str) -> bytes:
    """Validate the upload and return a resized RGB JPEG. Works in memory only."""
    if mime_type not in ALLOWED_MIME_TYPES:
        raise _ExtractionError("bad_type")
    if not image_bytes:
        raise _ExtractionError("bad_image")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise _ExtractionError("too_large")
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.format not in ("JPEG", "PNG"):
                raise _ExtractionError("bad_type")
            if img.width * img.height > MAX_PIXELS:
                raise _ExtractionError("too_large")
            img = ImageOps.exif_transpose(img)  # honour phone-camera rotation
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                rgba = img.convert("RGBA")      # flatten transparency onto white, not black
                flat = Image.new("RGB", rgba.size, "white")
                flat.paste(rgba, mask=rgba.getchannel("A"))
                img = flat
            else:
                img = img.convert("RGB")
            img.thumbnail((MAX_LONG_SIDE, MAX_LONG_SIDE), Image.LANCZOS)  # shrink only, keeps aspect
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=90)
            return out.getvalue()
    except _ExtractionError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise _ExtractionError("bad_image")


# --------------------------------------------------------------------------------------
# Provider call (the ONLY provider-specific code in this project)
# --------------------------------------------------------------------------------------

def _sleep(seconds: float) -> None:
    """Indirection so tests can skip the retry backoff."""
    time.sleep(seconds)


def _call_with_retry(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    """Call the model, retrying up to MAX_RETRIES times on transient errors only."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return _call_vision_model(image_bytes, mime_type, prompt)
        except _ExtractionError as err:
            if not err.transient or attempt == MAX_RETRIES:
                raise
            logger.info("transient error kind=%s; retry %d of %d", err.kind, attempt + 1, MAX_RETRIES)
            _sleep(RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)])
    raise _ExtractionError("unknown")  # unreachable; keeps type checkers happy


def _call_vision_model(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    """Send the image + prompt to the vision model and return its raw text reply.

    Provider: Google Gemini via the ``google-genai`` package.
    Env vars: GEMINI_API_KEY (required), SNAPSCHED_MODEL (default gemini-3.5-flash),
    SNAPSCHED_TIMEOUT_SECONDS (default 60).
    Raises ``_ExtractionError`` with a ``kind`` for every failure; provider exceptions and
    their text never leave this function.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise _ExtractionError("config")
    try:
        from google import genai
        from google.genai import errors as genai_errors
        from google.genai import types
    except ImportError:
        raise _ExtractionError("config")

    model = os.getenv("SNAPSCHED_MODEL") or DEFAULT_MODEL
    try:
        timeout_s = float(os.getenv("SNAPSCHED_TIMEOUT_SECONDS") or DEFAULT_TIMEOUT_SECONDS)
    except ValueError:
        timeout_s = DEFAULT_TIMEOUT_SECONDS

    try:
        client = genai.Client(api_key=api_key,
                              http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))  # ms
        response = client.models.generate_content(
            model=model,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
            config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
        )
        return response.text or ""   # None when the reply was blocked or empty
    except genai_errors.APIError as err:
        code = getattr(err, "code", None)
        text = str(err)
        if code == 429:
            raise _ExtractionError("rate_limit", transient=True)
        if code in (401, 403) or "API key" in text or "API_KEY" in text:
            raise _ExtractionError("auth")
        if code in (408, 504):
            raise _ExtractionError("timeout", transient=True)
        if isinstance(code, int) and code >= 500:
            raise _ExtractionError("server", transient=True)
        raise _ExtractionError("request")
    except Exception as err:
        names = " ".join(cls.__name__.lower() for cls in type(err).__mro__)
        if "timeout" in names:
            raise _ExtractionError("timeout", transient=True)
        if any(word in names for word in ("connect", "transport", "network", "connectionerror", "oserror")):
            raise _ExtractionError("network", transient=True)
        raise _ExtractionError("unknown")


# --------------------------------------------------------------------------------------
# Parsing and validation
# --------------------------------------------------------------------------------------

def _parse_model_json(text: str) -> Optional[dict]:
    """Pull the JSON object out of the model reply, or return None.

    Tolerates code fences and chatter before/after: decoding starts at the first "{" and
    ignores whatever follows the object, so ```json fences need no special handling. The
    object must contain "is_event_poster", which stops us returning a nested object
    (e.g. "confidence") from a broken reply.
    """
    decoder = json.JSONDecoder()
    pos = text.find("{")
    while pos != -1:
        try:
            obj, _ = decoder.raw_decode(text, pos)
        except ValueError:
            obj = None
        if isinstance(obj, dict) and "is_event_poster" in obj:
            return obj
        pos = text.find("{", pos + 1)
    return None


_NULLISH = {"", "null", "none", "n/a", "na", "unknown"}
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Purely numeric day/month/year with a day-first reading, e.g. 03/11/2026, 3.11.26.
_NUMERIC_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4}|\d{2})(?!\d)")


def _as_bool_or_none(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    return None


def _as_bool(value: Any) -> bool:
    return _as_bool_or_none(value) is True


def _clean_str(value: Any, max_len: int = 300, multiline: bool = False) -> tuple:
    """Return (clean string or None, is_valid). Non-strings are invalid; null-ish strings are None."""
    if value is None:
        return None, True
    if not isinstance(value, str):
        return None, False
    text = _CONTROL_CHARS.sub("", value.replace("\r\n", "\n").replace("\r", "\n"))
    text = text.strip() if multiline else " ".join(text.split())
    if text.lower() in _NULLISH:
        return None, True
    return text[:max_len], True


def _clean_date(value: Any) -> tuple:
    """Return (YYYY-MM-DD or None, is_valid)."""
    text, ok = _clean_str(value, 20)
    if text is None:
        return None, ok
    if not _DATE_RE.match(text):
        return None, False
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return None, False
    if not 2000 <= parsed.year <= 2100:
        return None, False
    return text, True


def _clean_time(value: Any) -> tuple:
    """Return (HH:MM or None, is_valid). Accepts H:MM and zero-pads it."""
    text, ok = _clean_str(value, 10)
    if text is None:
        return None, ok
    match = _TIME_RE.match(text)
    if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
        return None, False
    return f"{int(match.group(1)):02d}:{match.group(2)}", True


def _day_first_swap_fix(date_value: str, date_raw: Optional[str]) -> tuple:
    """Enforce Hong Kong day-first reading of numeric dates.

    Returns (possibly corrected date, is_ambiguous). A date is ambiguous when the printed
    text is numeric with day and month both <= 12 and different (03/11/2026). If the model
    read it month-first (a pure day/month swap of the day-first reading) we correct it.
    """
    match = _NUMERIC_DATE_RE.search(date_raw or "")
    if not match:
        return date_value, False
    first, second, year_text = int(match.group(1)), int(match.group(2)), match.group(3)
    if first > 12 or second > 12 or first == second:
        return date_value, False
    year = int(year_text) if len(year_text) == 4 else 2000 + int(year_text)
    model_date = date.fromisoformat(date_value)
    day_first = date(year, second, first)
    if model_date != day_first and model_date == date(year, first, second):
        return day_first.isoformat(), True
    return date_value, True


def _interpret(parsed: dict, ref: date) -> tuple:
    """Validate the model's JSON and turn it into (fields, findings). Never raises."""
    findings: list = []
    codes: set = set()
    low_fields: list = []

    def add(code: str, suffix: str = "") -> None:
        if code == "LOW_CONFIDENCE" or code not in codes:
            codes.add(code)
            findings.append(_finding(code, suffix))

    def mark_low(field: str) -> None:
        if field not in low_fields:
            low_fields.append(field)

    if _as_bool(parsed.get("multiple_events")):
        add("MULTIPLE_EVENTS")

    # --- text fields -------------------------------------------------------------
    event_name, ok = _clean_str(parsed.get("event_name"), 200)
    if not ok:
        mark_low("event_name")
    venue, ok = _clean_str(parsed.get("venue"), 200)
    if not ok:
        mark_low("venue")
    method, ok = _clean_str(parsed.get("registration_method"), 300)
    if not ok:
        mark_low("registration_method")
    reg_text, ok = _clean_str(parsed.get("registration_text_raw"), 1000, multiline=True)
    if not ok:
        mark_low("registration_text_raw")
    date_raw, _ = _clean_str(parsed.get("date_raw"), 100)

    # --- event date (year policy: no printed year -> no date) --------------------------
    model_date, ok = _clean_date(parsed.get("date"))
    date_invalid = not ok
    if date_invalid:
        mark_low("date")
    year_printed = _as_bool(parsed.get("date_has_year_printed"))
    year_missing = (not year_printed) and (model_date is not None
                                           or (date_raw is not None and any(c.isdigit() for c in date_raw)))
    event_date = None if year_missing else model_date
    if event_date is not None:
        event_date, ambiguous = _day_first_swap_fix(event_date, date_raw)
        if ambiguous:
            add("AMBIGUOUS_DATE")

    # --- times ---------------------------------------------------------------------
    start_time, ok = _clean_time(parsed.get("start_time"))
    if not ok:
        mark_low("start_time")
    end_time, ok = _clean_time(parsed.get("end_time"))
    if not ok:
        mark_low("end_time")

    # --- registration deadline (kept strictly separate from the event date) ---------
    deadline, ok = _clean_date(parsed.get("registration_deadline"))
    if not ok:
        mark_low("registration_deadline")
    deadline_time, ok = _clean_time(parsed.get("registration_deadline_time"))
    if not ok:
        mark_low("registration_deadline_time")
    if _as_bool_or_none(parsed.get("registration_deadline_has_year")) is False:
        # Same year policy as the event date. Only warn if registration wording exists, so a
        # poster with no deadline at all does not get a spurious year warning.
        if deadline is not None or reg_text is not None:
            add("YEAR_NOT_PRINTED")
        deadline = None

    # --- QR codes and external pages ----------------------------------------------------
    qr_present = _as_bool(parsed.get("qr_code_present"))
    if qr_present:
        method = f"{method}; QR code shown on poster" if method else "QR code shown on poster"
        add("QR_SCAN_MANUALLY")
    external = _as_bool(parsed.get("refers_to_external_details"))

    # --- missing-field warnings --------------------------------------------------------
    if event_name is None:
        add("MISSING_EVENT_NAME")
    if event_date is None:
        add("YEAR_NOT_PRINTED" if year_missing else "MISSING_DATE")
    if start_time is None:
        add("MISSING_TIME")
    if venue is None and not external:
        add("MISSING_VENUE")
    if method is None and reg_text is None and not external:
        add("MISSING_REGISTRATION")
    if external and (venue is None or method is None):
        add("CHECK_ORGANISER_PAGE")

    fields = {
        "event_name": event_name,
        "date": event_date,
        "date_has_year_printed": event_date is not None,
        "start_time": start_time,
        "end_time": end_time,
        "venue": venue,
        "registration_deadline": deadline,
        "registration_deadline_time": deadline_time,
        "registration_method": method,
        "registration_text_raw": reg_text,
    }

    # --- confidence: model-reported "low" or a value we had to discard -----------------
    confidence = parsed.get("confidence")
    if isinstance(confidence, dict):
        for name, level in confidence.items():
            if name in FIELD_LABELS and isinstance(level, str) and level.strip().lower() == "low" \
                    and fields.get(name) is not None:
                mark_low(name)
    for name in low_fields:
        add("LOW_CONFIDENCE", f" ({FIELD_LABELS[name].capitalize()})")

    for code in _date_relative_codes(fields, ref):
        add(code)
    return fields, findings


def _date_relative_codes(fields: dict, ref: date) -> list:
    """Warnings that compare printed dates with ``ref``. They never change the fields."""
    codes = []
    if fields.get("date") and date.fromisoformat(fields["date"]) < ref:
        codes.append("EVENT_IN_PAST")
    if fields.get("registration_deadline") and date.fromisoformat(fields["registration_deadline"]) < ref:
        codes.append("REGISTRATION_DEADLINE_PASSED")
    return codes


# --------------------------------------------------------------------------------------
# Demo mode
# --------------------------------------------------------------------------------------

_DEMO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def _check_demo_id(image_id: Any) -> None:
    """Only simple names are allowed, so an id can never point outside demo_results/."""
    if not isinstance(image_id, str) or not _DEMO_ID_RE.match(image_id):
        raise _ExtractionError("demo_missing")


def _load_demo_result(demo_image_id: Optional[str], ref: date) -> dict:
    """Return a saved result with mode "demo". Date-relative warnings are recomputed for ``ref``."""
    _check_demo_id(demo_image_id)
    path = DEMO_DIR / f"{demo_image_id}.json"
    if not path.is_file():
        raise _ExtractionError("demo_missing")
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        status = saved["status"]
        if status not in ("ok", "no_event_found"):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        raise _ExtractionError("demo_missing")

    if status == "no_event_found":
        return _build_result("no_event_found", "demo", message=f"{DEMO_NOTICE} {NO_EVENT_MESSAGE}")

    saved_fields = saved.get("fields") if isinstance(saved.get("fields"), dict) else {}
    fields = _sanitize_saved_fields(saved_fields)
    codes, texts = saved.get("warning_codes"), saved.get("warnings")
    if not (isinstance(codes, list) and isinstance(texts, list) and len(codes) == len(texts)):
        codes, texts = [], []
    relative = {"EVENT_IN_PAST", "REGISTRATION_DEADLINE_PASSED"}
    findings = [(c, t) for c, t in zip(codes, texts)
                if isinstance(c, str) and isinstance(t, str) and c not in relative]
    findings += [_finding(code) for code in _date_relative_codes(fields, ref)]
    return _build_result("ok", "demo", fields, findings, message=DEMO_NOTICE)


def _sanitize_saved_fields(saved: dict) -> dict:
    """Re-validate a saved fields dict so a hand-edited demo file cannot feed junk to the UI."""
    fields = _empty_fields()
    for name in ("event_name", "venue", "registration_method"):
        fields[name] = _clean_str(saved.get(name), 300)[0]
    fields["registration_text_raw"] = _clean_str(saved.get("registration_text_raw"), 1000, multiline=True)[0]
    for name in ("date", "registration_deadline"):
        fields[name] = _clean_date(saved.get(name))[0]
    for name in ("start_time", "end_time", "registration_deadline_time"):
        fields[name] = _clean_time(saved.get(name))[0]
    fields["date_has_year_printed"] = fields["date"] is not None
    return fields

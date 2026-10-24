"""Part D only needs to adjust these two adapters if team APIs differ.

Expected B: extraction.extract_event(image_bytes, mime_type) -> dict
            (Part B uses the module name ``extraction``, not ``ai_extraction``.
             The adapter below translates Part B's result into Part A's format.)
Expected C: calendar_export.generate_ics(confirmed_event) -> str or bytes
Neither module is implemented by Part A or required to open the interface.
"""

from dataclasses import dataclass
from importlib import import_module
from typing import Callable, Optional


@dataclass
class Backend:
    status: str
    function: Optional[Callable] = None


def load_backend(module_name, function_name):
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        return Backend("not connected" if error.name == module_name else "setup error")
    except Exception:
        # Do not show provider exception text, which can contain secrets or input.
        return Backend("setup error")
    function = getattr(module, function_name, None)
    return Backend("connected", function) if callable(function) else Backend("setup error")


# ---------------------------------------------------------------------------
# Part A <-> Part B adapter
# ---------------------------------------------------------------------------

def _adapt_extraction(raw_extract):
    """Wrap Part B's ``extract_event`` so its output matches Part A's contract.

    Part B (``extraction.extract_event``) returns::

        {"status": "ok"|"api_error"|"no_event_found",
         "mode": "live"|"demo",
         "fields": {"event_name": ..., "date": ..., ...},
         "warnings": [...], "warning_codes": [...],
         "message": ..., "raw_model_output": ...}

    Part A's ``normalise_event`` expects a flat dict with keys like
    ``event_date`` (not ``date``), ``all_day``, ``timezone``, and a combined
    ``registration_deadline`` of ``"YYYY-MM-DD HH:MM"``.

    This adapter:
    * Unwraps ``result["fields"]`` into a flat payload.
    * Renames ``"date"`` -> ``"event_date"``.
    * Merges ``registration_deadline`` + ``registration_deadline_time``.
    * Adds ``all_day=False`` and ``timezone="Asia/Hong_Kong"``.
    * Raises ``ValueError`` with Part B's safe message when status != "ok".
    """
    def adapted(image_bytes, mime_type):
        result = raw_extract(image_bytes, mime_type)

        # --- error / non-poster: raise so app.py's except block fires ---
        if not isinstance(result, dict) or result.get("status") != "ok":
            message = (result.get("message") if isinstance(result, dict) else None
                       ) or "AI extraction could not finish."
            raise ValueError(message)

        raw_fields = result.get("fields") or {}
        if not isinstance(raw_fields, dict):
            raise ValueError("AI extraction returned an unexpected format.")

        # --- map Part B keys -> Part A keys ---
        adapted_fields = {
            "event_name": raw_fields.get("event_name") or "",
            "event_date": raw_fields.get("date") or "",
            "start_time": raw_fields.get("start_time") or "",
            "end_time": raw_fields.get("end_time") or "",
            "venue": raw_fields.get("venue") or "",
            "registration_method": raw_fields.get("registration_method") or "",
        }

        # Merge separate deadline date + time into "YYYY-MM-DD HH:MM".
        deadline_date = raw_fields.get("registration_deadline")
        deadline_time = raw_fields.get("registration_deadline_time")
        if deadline_date and deadline_time:
            adapted_fields["registration_deadline"] = f"{deadline_date} {deadline_time}"
        elif deadline_date:
            adapted_fields["registration_deadline"] = str(deadline_date)
        else:
            adapted_fields["registration_deadline"] = ""

        # Part B does not produce these; supply sensible defaults.
        adapted_fields["all_day"] = False
        adapted_fields["timezone"] = "Asia/Hong_Kong"

        # Part B warnings are already plain strings, compatible with Part A.
        warnings = result.get("warnings") or []
        adapted_fields["warnings"] = [w for w in warnings if isinstance(w, str)]
        return adapted_fields

    return adapted


def load_ai_backend():
    """Load Part B's extraction module and wrap it for Part A's interface."""
    backend = load_backend("extraction", "extract_event")
    if backend.function is not None:
        return Backend(backend.status, _adapt_extraction(backend.function))
    return backend


# ---------------------------------------------------------------------------
# Calendar export guard (unchanged)
# ---------------------------------------------------------------------------

def calendar_file_bytes(result):
    if isinstance(result, str):
        result = result.encode("utf-8")
    if not isinstance(result, bytes):
        raise ValueError("Calendar output must be text or bytes.")
    if len(result) > 2 * 1024 * 1024:
        raise ValueError("Calendar output is unexpectedly large for one event.")
    try:
        text=result.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Calendar output must be valid UTF-8.") from error
    lines=text.strip().splitlines()
    required={"VERSION:2.0","BEGIN:VEVENT","END:VEVENT"}
    if (not lines or lines[0] != "BEGIN:VCALENDAR" or lines[-1] != "END:VCALENDAR"
            or not required.issubset(lines) or "\x00" in text):
        raise ValueError("The calendar module returned an unexpected file.")
    # A basic download guard only; C still owns full RFC/calendar-import checks.
    return result

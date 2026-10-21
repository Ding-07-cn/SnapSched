"""Part D only needs to adjust these two adapters if team APIs differ.

Expected B: ai_extraction.extract_event(image_bytes, mime_type) -> dict
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

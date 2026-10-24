"""Part C-compatible name using the canonical export backend.

Existing-calendar merging is outside the saved final proposal's MVP. Never
silently discard an old calendar supplied by a caller; reject that extra input.
"""
from calendar_export import generate_ics as _generate_ics


def generate_ics(event_data: dict, existing_ics_str: str | None = None) -> str:
    if existing_ics_str is not None:
        raise ValueError("Existing-calendar merging is outside this MVP. Import the new file in your calendar client.")
    return _generate_ics(event_data).decode("utf-8")

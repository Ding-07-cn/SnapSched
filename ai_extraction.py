"""Connect Aryan's structured result to the existing review form.

Provider code stays in extraction.py. This adapter never invents missing times
and never treats an API failure or an unrelated image as a successful draft.
"""
import extraction
from interface_state import normalise_event


class ExtractionProblem(ValueError):
    def __init__(self, code):
        self.code = code
        messages = {
            "no_event_found": "No event was found. Upload an event poster; nothing was approved or exported.",
            "api_error": "AI extraction could not finish. Check the API setup/connection and retry, "
                         "or switch to the clearly labelled saved sample. No live result was produced.",
            "invalid_result": "The extraction result had an unexpected format. Nothing was approved. "
                              "Retry or enter verified details manually.",
        }
        super().__init__(messages.get(code, messages["invalid_result"]))


def adapt_result(result):
    if not isinstance(result, dict):
        raise ExtractionProblem("invalid_result")
    status = result.get("status")
    if status in {"no_event_found", "api_error"}:
        raise ExtractionProblem(status)
    if status != "ok" or result.get("mode") not in {"live", "demo"}:
        raise ExtractionProblem("invalid_result")
    fields = result.get("fields")
    warnings = result.get("warnings", [])
    if not isinstance(fields, dict) or not isinstance(warnings, list):
        raise ExtractionProblem("invalid_result")
    warnings = list(warnings)
    deadline = fields.get("registration_deadline") or ""
    deadline_time = fields.get("registration_deadline_time") or ""
    if not isinstance(deadline, str) or not isinstance(deadline_time, str):
        raise ExtractionProblem("invalid_result")
    if deadline and deadline_time:
        deadline += " " + deadline_time
    elif deadline:
        warnings.append("The registration deadline has no printed time. Its date is retained; "
                        "no exact time has been guessed.")
    flat = {
        "event_name": fields.get("event_name"),
        "event_date": fields.get("date"),
        "start_time": fields.get("start_time"),
        "end_time": fields.get("end_time"),
        "venue": fields.get("venue"),
        "registration_deadline": deadline,
        "registration_method": fields.get("registration_method"),
        "registration_text_raw": fields.get("registration_text_raw"),
        "all_day": False,  # Never infer all-day from a missing start time.
        "timezone": "Asia/Hong_Kong", "warnings": warnings,
    }
    try:
        event, notes = normalise_event(flat)
    except (ValueError, TypeError):
        raise ExtractionProblem("invalid_result") from None
    return {**event, "warnings": notes, "mode": result["mode"]}


def extract_event(image_bytes, mime_type):
    return adapt_result(extraction.extract_event(image_bytes, mime_type))

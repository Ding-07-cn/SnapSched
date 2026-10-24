"""Teammates' original entrypoint names work without missing imports."""
from datetime import datetime
import unittest
from unittest.mock import patch

from icalendar import Calendar

import generate_calendar
from exceptions import EventValidationError, ICSImportValidationError
from ics_generator import create_event_obj, generate_ics_content, load_existing_ics
from import_validator import validate_import
from interface_state import sample_event
from parser import parse_event_fields, parse_and_convert_time_from_str
from validator import validate_event


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        class RecordedClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 24, 18, 0, tzinfo=tz)
        for target in ["calendar_export.datetime", "interface_state.datetime"]:
            clock = patch(target, RecordedClock); clock.start(); self.addCleanup(clock.stop)

    def test_original_c_generate_entrypoint_calls_canonical_backend(self):
        data = generate_calendar.generate_ics(sample_event())
        self.assertTrue(validate_import(data))
        self.assertEqual(len(load_existing_ics(data)), 2)

    def test_old_calendar_input_is_rejected_not_silently_discarded(self):
        with self.assertRaisesRegex(ValueError, "outside this MVP"):
            generate_calendar.generate_ics(sample_event(), "old-calendar")

    def test_compatibility_helpers_use_installed_library(self):
        event = parse_event_fields(sample_event())
        validate_event(event)
        text = generate_ics_content([create_event_obj(event)])
        self.assertEqual(len(Calendar.from_ical(text).walk("VEVENT")), 1)

    def test_optional_missing_fields_do_not_become_required(self):
        event = {**sample_event(), "venue": "", "registration_method": "", "registration_deadline": "", "end_time": ""}
        validate_event(event)
        self.assertTrue(validate_import(generate_calendar.generate_ics(event)))

    def test_invalid_input_and_date_only_time_are_not_guessed(self):
        with self.assertRaises(EventValidationError):
            validate_event({**sample_event(), "event_date": "invalid"})
        with self.assertRaises(ValueError):
            parse_and_convert_time_from_str("2026-11-03")
        with self.assertRaises(ICSImportValidationError):
            validate_import("not-a-calendar")

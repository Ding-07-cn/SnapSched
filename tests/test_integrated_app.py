"""Real A/B-adapter/C integration; ONLY the external model response is mocked."""
from datetime import datetime
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from icalendar import Calendar
from streamlit.testing.v1 import AppTest

import extraction

ROOT = Path(__file__).resolve().parents[1]
POSTER = (ROOT / "samples/demo_poster.png").read_bytes()
REPLY = {
    "is_event_poster": True, "event_name": "Student Research Skills Workshop (DEMO)",
    "date": "2026-11-05", "date_raw": "5 November 2026", "date_has_year_printed": True,
    "start_time": "15:00", "end_time": "16:00", "venue": "Demo Room 101",
    "registration_deadline": "2026-11-03", "registration_deadline_has_year": True,
    "registration_deadline_time": "18:00", "registration_method": "https://example.com/register",
    "registration_text_raw": "Register by 3 November 2026, 18:00", "confidence": {},
}


class IntegratedTests(unittest.TestCase):
    def setUp(self):
        class RecordedClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 24, 18, 0, tzinfo=tz)
        for target in ["interface_state.datetime", "calendar_export.datetime", "extraction.datetime"]:
            clock = patch(target, RecordedClock); clock.start(); self.addCleanup(clock.stop)
        env = patch.dict("os.environ", {"SNAPSCHED_DEMO_MODE": "0", "SNAPSCHED_SIMULATE_API_ERROR": "0"})
        env.start(); self.addCleanup(env.stop)

    def app(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
        self.assertFalse(app.exception)
        return app

    def upload(self, app):
        app.file_uploader[0].upload("sample.png", POSTER, "image/png").run()
        app.checkbox(key="allow_ai").check().run()

    def confirm(self, app):
        app.checkbox(key="reviewed").check().run()
        app.button(key="confirm_details").click().run()
        self.assertFalse(app.exception)

    def test_real_modules_upload_extract_edit_confirm_export(self):
        with patch("extraction._call_vision_model", return_value=json.dumps(REPLY)) as model:
            app = self.app(); self.upload(app)
            self.assertTrue(app.button(key="create_calendar").disabled)
            app.button(key="extract_ai").click().run()
        model.assert_called_once()
        self.assertEqual(app.text_input(key="field_event_date").value, "2026-11-05")
        self.assertIn("Register by", app.text_area(key="field_registration_text_raw").value)
        self.assertIsNone(app.session_state["confirmed_event"])
        app.text_input(key="field_venue").input("Corrected Room 202").run()
        self.confirm(app)
        app.button(key="create_calendar").click().run()
        self.assertFalse(app.exception)
        events = Calendar.from_ical(app.session_state["calendar_bytes"]).walk("VEVENT")
        self.assertEqual(len(events), 2)
        self.assertEqual(str(events[0]["location"]), "Corrected Room 202")
        app.button(key="edit_details").click().run()
        self.assertIsNone(app.session_state["calendar_bytes"])
        self.assertTrue(app.button(key="create_calendar").disabled)

    def test_unrelated_image_is_refused_even_after_manual_typing(self):
        with patch("extraction._call_vision_model", return_value='{"is_event_poster": false}'):
            app = self.app(); self.upload(app)
            app.button(key="extract_ai").click().run()
        self.assertIn("No event was found", " ".join(x.value for x in app.error))
        app.text_input(key="field_event_name").input("Should not export").run()
        app.text_input(key="field_event_date").input("2026-11-05").run()
        app.checkbox(key="field_all_day").check().run()
        app.checkbox(key="reviewed").check().run()
        self.assertTrue(app.button(key="confirm_details").disabled)
        self.assertTrue(app.button(key="create_calendar").disabled)

    def test_missing_date_blocks_confirmation_until_corrected(self):
        reply = {**REPLY, "date": None, "date_raw": "", "date_has_year_printed": False}
        with patch("extraction._call_vision_model", return_value=json.dumps(reply)):
            app = self.app(); self.upload(app); app.button(key="extract_ai").click().run()
        self.assertEqual(app.text_input(key="field_event_date").value, "")
        app.checkbox(key="reviewed").check().run()
        self.assertTrue(app.button(key="confirm_details").disabled)
        app.text_input(key="field_event_date").input("2026-11-05").run()
        self.confirm(app)
        self.assertFalse(app.button(key="create_calendar").disabled)

    def test_closed_registration_exports_only_future_event(self):
        reply = {**REPLY, "registration_deadline": "2026-10-23"}
        with patch("extraction._call_vision_model", return_value=json.dumps(reply)):
            app = self.app(); self.upload(app); app.button(key="extract_ai").click().run()
        self.assertIn("deadline has passed", " ".join(x.value for x in app.warning))
        self.confirm(app); app.button(key="create_calendar").click().run()
        self.assertEqual(len(Calendar.from_ical(app.session_state["calendar_bytes"]).walk("VEVENT")), 1)

    def test_date_only_deadline_stays_date_only_in_ui_and_calendar(self):
        reply = {**REPLY, "registration_deadline_time": None}
        with patch("extraction._call_vision_model", return_value=json.dumps(reply)):
            app = self.app(); self.upload(app); app.button(key="extract_ai").click().run()
        self.assertEqual(app.text_input(key="field_registration_deadline").value, "2026-11-03")
        self.confirm(app); app.button(key="create_calendar").click().run()
        events = Calendar.from_ical(app.session_state["calendar_bytes"]).walk("VEVENT")
        self.assertEqual(events[1].decoded("dtstart").isoformat(), "2026-11-03")
        self.assertFalse(events[1].subcomponents)

    def test_model_failure_cannot_be_a_live_success(self):
        with patch("extraction._call_vision_model", side_effect=extraction._ExtractionError("auth")):
            app = self.app(); self.upload(app); app.button(key="extract_ai").click().run()
        self.assertIn("No live result", " ".join(x.value for x in app.error))
        self.assertEqual(app.text_input(key="field_event_name").value, "")
        self.assertIsNone(app.session_state["confirmed_event"])
        self.assertTrue(app.button(key="create_calendar").disabled)

    def test_saved_sample_exports_real_calendar_without_api(self):
        with patch("extraction._call_vision_model") as model:
            app = self.app(); app.radio(key="workspace_mode").set_value("Saved sample demo").run()
            app.button(key="load_sample").click().run(); self.confirm(app)
            app.button(key="create_calendar").click().run()
        model.assert_not_called()
        self.assertEqual(len(Calendar.from_ical(app.session_state["calendar_bytes"]).walk("VEVENT")), 2)

    def test_legacy_review_entrypoint_uses_same_working_app(self):
        app = AppTest.from_file(str(ROOT / "review_page.py"), default_timeout=20).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "SnapSched")

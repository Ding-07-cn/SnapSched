"""Interface integration tests. Fake B/C modules below are TEST DOUBLES ONLY."""
from pathlib import Path
from datetime import datetime
from io import BytesIO
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from PIL import Image

from integrations import Backend
from interface_state import sample_event

ROOT = Path(__file__).resolve().parents[1]
POSTER = (ROOT/"samples/demo_poster.png").read_bytes()
CALENDAR_TEST_DOUBLE = (
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//SnapSched UI Test//EN\r\n"
    "BEGIN:VEVENT\r\nUID:ui-test@example.invalid\r\nDTSTAMP:20261021T000000Z\r\n"
    "DTSTART:20261105T070000Z\r\nSUMMARY:UI test double\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
)


class AppTests(unittest.TestCase):
    def setUp(self):
        # Keep the fixed, synthetic November poster usable as a test fixture later.
        class RecordedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026,10,21,12,0,tzinfo=tz)
        self.clock = patch("interface_state.datetime",RecordedDateTime)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def start(self):
        app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=15).run()
        self.assertFalse(app.exception)
        return app

    def demo(self):
        app=self.start()
        app.radio(key="workspace_mode").set_value("Saved sample demo").run()
        app.button(key="load_sample").click().run()
        self.assertFalse(app.exception)
        return app

    def confirm(self,app):
        app.checkbox(key="reviewed").check().run()
        self.assertFalse(app.button(key="confirm_details").disabled)
        app.button(key="confirm_details").click().run()
        self.assertIsNotNone(app.session_state["confirmed_event"])
        self.assertFalse(app.exception)

    def upload(self,app):
        app.file_uploader[0].upload("demo.png",POSTER,"image/png").run()
        self.assertFalse(app.exception)

    def test_initial_empty_interface_blocks_every_export(self):
        app=self.start()
        self.assertTrue(app.button(key="confirm_details").disabled)
        self.assertTrue(app.button(key="create_calendar").disabled)
        self.assertTrue(app.button(key="extract_ai").disabled)
        self.assertEqual(app.text_input(key="field_event_date").value,"")

    def test_saved_sample_is_labelled_not_live_ai(self):
        app=self.demo()
        self.assertIn("not live AI", " ".join(x.value for x in app.warning))
        self.assertIn("SAVED SAMPLE",app.session_state["source_label"])
        self.confirm(app)
        self.assertTrue(app.button(key="create_calendar").disabled)

    def test_confirmation_locks_fields_until_explicit_edit(self):
        app=self.demo(); self.confirm(app)
        self.assertTrue(app.text_input(key="field_venue").disabled)
        self.assertTrue(app.checkbox(key="reviewed").disabled)
        self.assertFalse(app.button(key="edit_details").disabled)
        app.button(key="edit_details").click().run()
        self.assertFalse(app.text_input(key="field_venue").disabled)
        self.assertFalse(app.checkbox(key="reviewed").value)
        self.assertIsNone(app.session_state["confirmed_event"])

    def test_editing_after_confirmation_revokes_approval_and_output(self):
        app=self.demo(); self.confirm(app)
        app.session_state["calendar_bytes"]=b"old calendar"
        app.button(key="edit_details").click().run()
        self.assertIsNone(app.session_state["calendar_bytes"])
        app.text_input(key="field_venue").input("Corrected venue").run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["confirmed_event"])
        self.assertIsNone(app.session_state["calendar_bytes"])
        self.assertFalse(app.checkbox(key="reviewed").value)

    def test_upload_is_not_fake_extraction_and_changing_mode_clears_demo(self):
        app=self.demo(); self.confirm(app)
        app.radio(key="workspace_mode").set_value("Upload a poster").run()
        self.upload(app)
        self.assertEqual(app.text_input(key="field_event_name").value,"")
        self.assertIsNone(app.session_state["confirmed_event"])
        self.assertTrue(app.button(key="extract_ai").disabled)
        self.assertEqual(len(app.file_uploader[0].value.getvalue()),len(POSTER))

    def test_corrupt_upload_is_rejected_with_a_readable_error(self):
        app=self.start()
        app.file_uploader[0].upload("broken.png",b"not a PNG","image/png").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertIsNone(app.session_state["confirmed_event"])

    def test_reset_clears_poster_fields_and_confirmation(self):
        app=self.demo(); self.confirm(app)
        app.button(key="reset_workspace").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input(key="field_event_name").value,"")
        self.assertIsNone(app.session_state["confirmed_event"])

    def test_new_upload_clears_confirmed_fields_consent_and_output(self):
        def fake_loader(module,function):
            return Backend("connected",lambda *args: sample_event()) if module=="ai_extraction" else Backend("not connected")
        with patch("integrations.load_backend",side_effect=fake_loader):
            app=self.start(); self.upload(app)
            app.checkbox(key="allow_ai").check().run()
            app.button(key="extract_ai").click().run(); self.confirm(app)
            app.session_state["calendar_bytes"]=b"old calendar"
            replacement=BytesIO(); Image.new("RGB",(40,40),"blue").save(replacement,format="PNG")
            app.file_uploader[0].set_value(("second.png",replacement.getvalue(),"image/png")).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input(key="field_event_name").value,"")
            self.assertFalse(app.checkbox(key="allow_ai").value)
            self.assertIsNone(app.session_state["confirmed_event"])
            self.assertIsNone(app.session_state["calendar_bytes"])

    def test_reset_really_clears_the_upload_widget(self):
        app=self.start(); self.upload(app)
        app.button(key="reset_workspace").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.file_uploader[0].value)

    def test_session_data_is_not_shared_with_another_viewer(self):
        first=self.demo(); self.confirm(first)
        second=self.start()
        self.assertEqual(second.text_input(key="field_event_name").value,"")
        self.assertIsNone(second.session_state["confirmed_event"])
        self.assertEqual(first.session_state["confirmed_event"]["event_name"],sample_event()["event_name"])

    def test_ai_adapter_requires_consent_and_cannot_confirm_its_own_answer(self):
        received=[]
        def fake_extract(image_bytes,mime_type):
            received.append((len(image_bytes),mime_type)); return sample_event()
        def fake_loader(module,function):
            return Backend("connected",fake_extract) if module=="ai_extraction" else Backend("not connected")
        with patch("integrations.load_backend",side_effect=fake_loader):
            app=self.start(); self.upload(app)
            self.assertTrue(app.button(key="extract_ai").disabled)
            app.checkbox(key="allow_ai").check().run()
            app.button(key="extract_ai").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(received,[(len(POSTER),"image/png")])
            self.assertEqual(app.text_input(key="field_event_name").value,sample_event()["event_name"])
            self.assertIsNone(app.session_state["confirmed_event"])
            self.assertFalse(app.checkbox(key="reviewed").value)

    def test_api_error_does_not_leak_error_text_or_leave_old_results(self):
        def failing_ai(*args): raise RuntimeError("SECRET_API_TOKEN_DO_NOT_PRINT")
        def fake_loader(module,function):
            return Backend("connected",failing_ai) if module=="ai_extraction" else Backend("not connected")
        with patch("integrations.load_backend",side_effect=fake_loader):
            app=self.start(); self.upload(app)
            app.text_input(key="field_event_name").input("Old draft").run()
            app.checkbox(key="allow_ai").check().run()
            app.button(key="extract_ai").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input(key="field_event_name").value,"")
            self.assertIsNone(app.session_state["confirmed_event"])
            self.assertNotIn("SECRET_API_TOKEN",str(app.error))

    def test_calendar_adapter_receives_only_explicitly_confirmed_details(self):
        received=[]
        def fake_calendar(event):
            received.append(event); return CALENDAR_TEST_DOUBLE
        def fake_loader(module,function):
            return Backend("connected",fake_calendar) if module=="calendar_export" else Backend("not connected")
        with patch("integrations.load_backend",side_effect=fake_loader):
            app=self.demo()
            self.assertTrue(app.button(key="create_calendar").disabled)
            self.confirm(app)
            app.button(key="create_calendar").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(received,[sample_event()])
            self.assertIsInstance(app.session_state["calendar_bytes"],bytes)
            app.button(key="edit_details").click().run()
            app.text_input(key="field_event_name").input("Changed event").run()
            self.assertIsNone(app.session_state["calendar_bytes"])
            self.assertTrue(app.button(key="create_calendar").disabled)

    def test_invalid_calendar_result_has_no_download(self):
        def fake_loader(module,function):
            return Backend("connected",lambda event: "provider error") if module=="calendar_export" else Backend("not connected")
        with patch("integrations.load_backend",side_effect=fake_loader):
            app=self.demo(); self.confirm(app)
            app.button(key="create_calendar").click().run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.session_state["calendar_bytes"])
            self.assertTrue(app.error)

    def test_preview_is_decoded_once_and_released_on_reset(self):
        from interface_state import inspect_image
        with patch("interface_state.inspect_image", wraps=inspect_image) as inspect:
            app=self.start(); self.upload(app)
            app.text_input(key="field_event_name").input("First edit").run()
            app.text_input(key="field_venue").input("Second edit").run()
            self.assertEqual(inspect.call_count,1)
            app.button(key="reset_workspace").click().run()
            self.assertIsNone(app.session_state["preview_image"])

    def test_invalid_date_can_be_fixed_without_reuploading(self):
        app=self.demo()
        app.text_input(key="field_event_date").input("2026-02-30").run()
        app.checkbox(key="reviewed").check().run()
        self.assertTrue(app.button(key="confirm_details").disabled)
        app.text_input(key="field_event_date").input("2026-11-05").run()
        self.assertFalse(app.checkbox(key="reviewed").value)
        self.confirm(app)

    def test_all_day_export_does_not_reuse_disabled_time_values(self):
        received=[]
        def fake_calendar(event):
            received.append(event); return CALENDAR_TEST_DOUBLE
        def fake_loader(module,function):
            return Backend("connected",fake_calendar) if module=="calendar_export" else Backend("not connected")
        with patch("integrations.load_backend",side_effect=fake_loader):
            app=self.demo()
            app.checkbox(key="field_all_day").check().run()
            self.assertTrue(app.text_input(key="field_start_time").disabled)
            self.confirm(app)
            app.button(key="create_calendar").click().run()
            self.assertEqual(received[0]["start_time"],"")
            self.assertEqual(received[0]["end_time"],"")

    def test_closed_registration_warns_but_future_event_can_be_reviewed(self):
        app=self.demo()
        app.text_input(key="field_registration_deadline").input("2026-10-20 18:00").run()
        self.assertTrue(any("deadline has passed" in message.value for message in app.warning))
        self.confirm(app)

    def test_backend_setup_error_is_safe_and_distinct_from_missing(self):
        with patch("integrations.load_backend",return_value=Backend("setup error")):
            app=self.start()
            self.assertTrue(app.button(key="extract_ai").disabled)
            self.assertTrue(app.button(key="create_calendar").disabled)
            self.assertFalse(app.exception)

    def test_ai_markup_is_displayed_as_plain_text(self):
        note="![not an image](https://example.com/private-tracker)"
        def fake_loader(module,function):
            payload={**sample_event(),"warnings":[note]}
            return Backend("connected",lambda *args:payload) if module=="ai_extraction" else Backend("not connected")
        with patch("integrations.load_backend",side_effect=fake_loader):
            app=self.start(); self.upload(app)
            app.checkbox(key="allow_ai").check().run()
            app.button(key="extract_ai").click().run()
            self.assertTrue(any(text.value==note for text in app.text))
            self.assertFalse(any(note in item.value for item in app.markdown))


if __name__ == "__main__":
    unittest.main()

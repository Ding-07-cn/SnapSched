from datetime import date, datetime
from io import BytesIO
import unittest
from unittest.mock import patch

from PIL import Image

from integrations import Backend, calendar_file_bytes, load_backend
from interface_state import (
    MAX_FILE_BYTES, confirmation_errors, empty_event, inspect_image, invalidate_review,
    normalise_event, populate_fields, replace_source, registration_warning, review_fingerprint, sample_event,
)


class StateTests(unittest.TestCase):
    def test_empty_event_is_not_prefilled_with_today(self):
        event = empty_event()
        self.assertEqual(event["event_date"], "")
        self.assertGreaterEqual(len(confirmation_errors(event)), 3)

    def test_sample_is_complete_on_recorded_reference_date(self):
        self.assertEqual(confirmation_errors(sample_event(), date(2026, 10, 21)), [])

    def test_invalid_dates_and_past_dates_cannot_be_confirmed(self):
        for value in ["2026-02-30", "2026-1-1", "05/11", "2026-10-20", "20261105"]:
            with self.subTest(value=value):
                event = sample_event(); event["event_date"] = value
                self.assertTrue(confirmation_errors(event, date(2026, 10, 21)))

    def test_missing_time_requires_explicit_all_day_choice(self):
        event = sample_event(); event["start_time"] = ""
        self.assertTrue(confirmation_errors(event, date(2026, 10, 21)))
        event["all_day"] = True
        self.assertFalse(confirmation_errors(event, date(2026, 10, 21)))

    def test_ambiguous_time_is_not_silently_normalised(self):
        for value in ["3pm", "3:00", "25:00"]:
            event = sample_event(); event["start_time"] = value
            self.assertTrue(confirmation_errors(event, date(2026, 10, 21)))

    def test_image_bytes_not_extension_are_validated(self):
        for fmt,mime in [("PNG","image/png"),("JPEG","image/jpeg")]:
            data = BytesIO(); Image.new("RGB",(20,20)).save(data,format=fmt)
            preview,detected = inspect_image(data.getvalue())
            self.assertEqual(detected,mime); self.assertEqual(preview.size,(20,20))
        for content in [b"",b"not an image",b"<html>poster</html>",b"x"*(MAX_FILE_BYTES+1)]:
            with self.subTest(size=len(content)):
                with self.assertRaises(ValueError): inspect_image(content)

    def test_phone_photo_orientation_is_respected(self):
        image=Image.new("RGB",(30,60),"blue")
        exif=image.getexif(); exif[274]=6
        data=BytesIO(); image.save(data,format="JPEG",exif=exif)
        preview,mime=inspect_image(data.getvalue())
        self.assertEqual(preview.size,(60,30))
        self.assertEqual(mime,"image/jpeg")

    def test_invalid_end_time_order_and_deadline_are_not_confirmable(self):
        for field,value in [("end_time","14:00"),("end_time","15:00"),
                            ("registration_deadline","3 Nov"),
                            ("registration_deadline","2026-02-30 18:00")]:
            with self.subTest(field=field,value=value):
                event=sample_event(); event[field]=value
                self.assertTrue(confirmation_errors(event,date(2026,10,21)))

    def test_different_source_erases_previous_answer_and_confirmation(self):
        state = {}; replace_source(state,"one"); populate_fields(state,sample_event())
        state["approved_fingerprint"]="approved"; state["calendar_bytes"]=b"old output"
        replace_source(state,"two")
        self.assertEqual(state["field_event_name"],"")
        self.assertIsNone(state["calendar_bytes"])
        self.assertIsNone(state["confirmed_event"])
        self.assertFalse(state["reviewed"])

    def test_same_source_does_not_erase_edits_on_rerun(self):
        state = {}; replace_source(state,"one"); populate_fields(state,sample_event())
        replace_source(state,"one")
        self.assertEqual(state["field_event_name"],sample_event()["event_name"])

    def test_all_fields_and_source_are_bound_to_confirmation(self):
        event=sample_event(); original=review_fingerprint("source1",event)
        self.assertNotEqual(original,review_fingerprint("source2",event))
        for field in event:
            other=dict(event); other[field]=not other[field] if field=="all_day" else other[field]+" changed"
            self.assertNotEqual(original,review_fingerprint("source1",other))

    def test_normaliser_does_not_invent_missing_values(self):
        event,warnings=normalise_event({"event_name":" Test ","venue":None,"warnings":["Date missing"]})
        self.assertEqual(event["event_name"],"Test"); self.assertEqual(event["venue"],"")
        self.assertEqual(event["event_date"],""); self.assertEqual(warnings,["Date missing"])
        for bad in [None,[],{"event_date":20261105},{"all_day":"false"},{"warnings":"missing"},
                    {"timezone":"UTC"}]:
            with self.assertRaises(ValueError): normalise_event(bad)

    def test_missing_module_different_from_broken_dependency(self):
        self.assertEqual(load_backend("a_missing_team_module","extract_event").status,"not connected")
        with patch("integrations.import_module",side_effect=ModuleNotFoundError(name="missing_dependency")):
            self.assertEqual(load_backend("ai_extraction","extract_event").status,"setup error")

    def test_invalid_calendar_output_cannot_be_offered_as_download(self):
        for invalid in [None,{},b"error: connection failed","not a calendar",
                        "BEGIN:VCALENDAR\r\nEND:VCALENDAR",b"BEGIN:VCALENDAR\r\n\xff\r\nEND:VCALENDAR"]:
            with self.assertRaises(ValueError): calendar_file_bytes(invalid)
        example="BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nSUMMARY:Test\r\nEND:VEVENT\r\nEND:VCALENDAR"
        self.assertIsInstance(calendar_file_bytes(example),bytes)

    def test_gif_and_animated_png_are_rejected(self):
        frames=[Image.new("RGB",(20,20),colour) for colour in ["red","blue"]]
        for fmt in ["GIF","PNG"]:
            data=BytesIO(); frames[0].save(data,format=fmt,save_all=True,append_images=frames[1:],duration=100,loop=0)
            with self.assertRaises(ValueError): inspect_image(data.getvalue())

    def test_large_pixel_dimensions_are_rejected_before_decoding(self):
        image=Image.new("RGB",(4500,4500),"white")
        data=BytesIO(); image.save(data,format="PNG")
        with self.assertRaisesRegex(ValueError,"20 megapixels"): inspect_image(data.getvalue())

    def test_unbounded_backend_strings_are_rejected_not_silently_truncated(self):
        for payload in [{"venue":"x"*301},{"warnings":["x"*501]},
                        {"warnings":["warning"]*31}]:
            with self.assertRaises(ValueError): normalise_event(payload)

    def test_closed_registration_is_warning_not_event_rejection(self):
        event=sample_event(); event["registration_deadline"]="2026-10-20 18:00"
        self.assertIsNotNone(registration_warning(event,datetime(2026,10,21)))
        self.assertFalse(confirmation_errors(event,date(2026,10,21)))
        self.assertIsNone(registration_warning(sample_event(),datetime(2026,10,21)))
        event["registration_deadline"]=""
        self.assertIsNone(registration_warning(event,datetime(2026,10,21)))


if __name__ == "__main__":
    unittest.main()

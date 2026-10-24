import copy
import unittest
from unittest.mock import MagicMock, patch

import extraction
from ai_extraction import ExtractionProblem, adapt_result, extract_event
from runtime_config import setting


def b_result(**changes):
    result = {"status": "ok", "mode": "live", "warnings": [], "fields": {
        "event_name": "Career Talk", "date": "2026-11-12", "date_has_year_printed": True,
        "start_time": "18:00", "end_time": "20:00", "venue": "MB 123",
        "registration_deadline": "2026-11-05", "registration_deadline_time": "17:30",
        "registration_method": "https://example.com/register", "registration_text_raw": "Scan QR to join",
    }, "raw_model_output": "Never display this"}
    result["fields"].update(changes)
    return result


class AdapterTests(unittest.TestCase):
    def test_maps_real_b_contract_without_leaking_raw_output(self):
        output = adapt_result(b_result())
        self.assertEqual(output["event_date"], "2026-11-12")
        self.assertEqual(output["registration_deadline"], "2026-11-05 17:30")
        self.assertEqual(output["registration_text_raw"], "Scan QR to join")
        self.assertNotIn("raw_model_output", output)
        self.assertFalse(output["all_day"])

    def test_missing_deadline_time_is_retained_as_date_only(self):
        output = adapt_result(b_result(registration_deadline_time=None))
        self.assertEqual(output["registration_deadline"], "2026-11-05")
        self.assertIn("no printed time", " ".join(output["warnings"]))

    def test_missing_event_time_is_not_assumed_all_day(self):
        output = adapt_result(b_result(start_time=None))
        self.assertEqual(output["start_time"], "")
        self.assertFalse(output["all_day"])

    def test_api_errors_and_unrelated_images_are_not_successes(self):
        for status in ["api_error", "no_event_found"]:
            result = b_result(); result["status"] = status
            with self.subTest(status=status), self.assertRaises(ExtractionProblem) as raised:
                adapt_result(result)
            self.assertEqual(raised.exception.code, status)

    def test_malformed_payloads_are_rejected(self):
        for result in [None, [], {}, {"status": "ok", "mode": "live", "fields": []},
                       {**b_result(), "mode": "unknown"}, b_result(event_name=123)]:
            with self.subTest(result=result), self.assertRaises(ExtractionProblem):
                adapt_result(result)

    def test_input_and_provider_result_are_not_mutated(self):
        result = b_result(); original = copy.deepcopy(result)
        with patch("extraction.extract_event", return_value=result) as backend:
            output = extract_event(b"test-image", "image/png")
        backend.assert_called_once_with(b"test-image", "image/png")
        self.assertEqual(result, original)
        self.assertEqual(output["event_name"], "Career Talk")

    def test_demo_mode_stays_explicitly_labelled(self):
        result = b_result(); result["mode"] = "demo"
        self.assertEqual(adapt_result(result)["mode"], "demo")

    def test_streamlit_secrets_and_environment_are_supported(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "environment-test-value"}):
            self.assertEqual(setting("GEMINI_API_KEY"), "environment-test-value")
        with patch.dict("os.environ", {}, clear=True), patch("pathlib.Path.read_text",
                return_value='GEMINI_API_KEY = "file-test-value"'):
            self.assertEqual(setting("GEMINI_API_KEY"), "file-test-value")
        with patch.dict("os.environ", {}, clear=True), patch("pathlib.Path.read_text",
                side_effect=OSError("missing")):
            self.assertEqual(setting("GEMINI_API_KEY"), "")

    def test_provider_configuration_is_bounded_and_client_closed(self):
        from google import genai
        client = MagicMock()
        client.__enter__.return_value = client
        client.models.generate_content.return_value.text = '{"is_event_poster":false}'
        values = {"GEMINI_API_KEY": "test-key-not-real", "SNAPSCHED_MODEL": "gemini-3.5-flash",
                  "SNAPSCHED_TIMEOUT_SECONDS": "-1"}
        with patch("extraction.setting", side_effect=lambda key, default="": values.get(key, default)), \
                patch.object(genai, "Client", return_value=client) as factory:
            extraction._call_vision_model(b"test", "image/png", "test prompt")
        options = factory.call_args.kwargs["http_options"]
        self.assertEqual(options.retry_options.attempts, 1)
        self.assertEqual(options.timeout, 60000)
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertFalse(config.automatic_continuation)
        self.assertEqual(config.max_output_tokens, 4096)
        client.__exit__.assert_called_once()

"""Evaluation tooling must distinguish fixtures, mocks and actual live results."""
import contextlib
import io
from unittest.mock import patch
import unittest

from scripts import evaluate_live


class EvaluationTests(unittest.TestCase):
    def result(self):
        return {"status": "ok", "mode": "live", "warning_codes": [],
                "fields": {"registration_deadline_time": "17:00"}}

    def test_deadline_time_is_scored_not_only_date(self):
        self.assertEqual(evaluate_live.compare_result(self.result(), {"registration_deadline_time": "17:00"}), "match")
        self.assertIn("registration_deadline_time", evaluate_live.compare_result(self.result(), {"registration_deadline_time": "18:00"}))

    def test_saved_demo_can_never_be_a_live_match(self):
        self.assertIn("NOT a live result", evaluate_live.compare_result({**self.result(), "mode": "demo"}, {"status": "ok"}))

    def test_required_warnings_are_checked(self):
        self.assertIn("missing warning", evaluate_live.compare_result(self.result(), {"required_warning_codes": ["QR_SCAN_MANUALLY"]}))

    def test_no_key_does_not_call_provider_or_write_scores(self):
        with patch("sys.argv", ["evaluate_live.py", "--live"]), patch.dict("os.environ", {"SNAPSCHED_DEMO_MODE": "0", "SNAPSCHED_SIMULATE_API_ERROR": "0"}), patch("scripts.evaluate_live.ai_configured", return_value=False), patch("scripts.evaluate_live.extraction.extract_event") as call, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluate_live.main(), 2)
            call.assert_not_called()

    def test_opt_in_required_even_with_a_key(self):
        with patch("sys.argv", ["evaluate_live.py"]), patch("scripts.evaluate_live.ai_configured", return_value=True), patch("scripts.evaluate_live.extraction.extract_event") as call, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluate_live.main(), 2)
            call.assert_not_called()

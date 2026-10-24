import unittest

from review_logic import (
    ensure_standard_event,
    find_missing_required_fields,
    get_by_path,
    review_fingerprint,
    set_by_path,
)


class TestReviewLogic(unittest.TestCase):
    def test_path_get_set(self):
        d = {}
        set_by_path(d, "reg_method.value", "https://x.com")
        self.assertEqual(get_by_path(d, "reg_method.value"), "https://x.com")
        self.assertIsNone(get_by_path(d, "reg_method.type"))

    def test_ensure_standard_event(self):
        e = ensure_standard_event({"name": "A"})
        self.assertIn("reg_method", e)
        self.assertIsNone(get_by_path(e, "venue"))

    def test_missing(self):
        e = ensure_standard_event({
            "name": "A",
            "venue": None,
            "start_dt": "2026-01-01 10:00",
            "end_dt": None,
            "reg_deadline_dt": None,
            "reg_method": {"type": "url", "value": None},
        })
        missing = find_missing_required_fields(e)
        self.assertIn("venue", missing)
        self.assertIn("reg_method.value", missing)

    def test_fingerprint_changes(self):
        f1 = review_fingerprint("src", {"name": "A"})
        f2 = review_fingerprint("src", {"name": "B"})
        self.assertNotEqual(f1, f2)


if __name__ == "__main__":
    unittest.main()

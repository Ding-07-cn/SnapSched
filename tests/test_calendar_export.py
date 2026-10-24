from datetime import date, datetime, timezone
import unittest

from icalendar import Calendar

from calendar_export import generate_ics
from interface_state import sample_event

NOW = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)


class CalendarTests(unittest.TestCase):
    def export(self, **changes):
        event = {**sample_event(), **changes}
        data = generate_ics(event, now=NOW)
        return data, Calendar.from_ical(data).walk("VEVENT")

    def test_timed_event_and_registration_are_distinct(self):
        data, events = self.export()
        self.assertEqual(len(events), 2)
        main, deadline = events
        self.assertEqual(main.decoded("dtstart"), datetime(2026, 11, 5, 7, tzinfo=timezone.utc))
        self.assertEqual(main.decoded("dtend"), datetime(2026, 11, 5, 8, tzinfo=timezone.utc))
        self.assertEqual(deadline.decoded("dtstart"), datetime(2026, 11, 3, 10, tzinfo=timezone.utc))
        self.assertIn("Registration deadline:", str(deadline["summary"]))
        self.assertEqual(str(main["location"]), sample_event()["venue"])
        self.assertEqual(deadline.walk("VALARM")[0].decoded("trigger").total_seconds(), 0)
        self.assertIn(b"DTSTART:20261105T070000Z", data)
        self.assertNotIn(b"METHOD:REQUEST", data)  # Never an invitation/registration.

    def test_expired_deadline_is_omitted(self):
        _, events = self.export(registration_deadline="2026-10-24 17:59")
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0].walk("VALARM"))

    def test_deadline_equal_to_now_is_omitted(self):
        _, events = self.export(registration_deadline="2026-10-24 18:00")
        self.assertEqual(len(events), 1)

    def test_no_deadline_does_not_create_one(self):
        _, events = self.export(registration_deadline="")
        self.assertEqual(len(events), 1)

    def test_date_only_deadline_does_not_invent_a_time(self):
        data, events = self.export(registration_deadline="2026-11-03")
        self.assertEqual(events[1].decoded("dtstart"), date(2026, 11, 3))
        self.assertIn(b"DTSTART;VALUE=DATE:20261103", data)
        self.assertFalse(events[1].walk("VALARM"))

    def test_date_only_deadline_today_is_not_assumed_still_open(self):
        _, events = self.export(registration_deadline="2026-10-24")
        self.assertEqual(len(events), 1)

    def test_all_day_end_is_exclusive_and_disabled_times_ignored(self):
        _, events = self.export(all_day=True)
        self.assertEqual(events[0].decoded("dtstart"), date(2026, 11, 5))
        self.assertEqual(events[0].decoded("dtend"), date(2026, 11, 6))

    def test_unprinted_end_time_is_not_invented(self):
        _, events = self.export(end_time="", registration_deadline="")
        self.assertNotIn("dtend", events[0])
        self.assertNotIn("duration", events[0])

    def test_uids_are_stable_distinct_and_not_personal_addresses(self):
        _, first = self.export()
        _, second = self.export()
        self.assertEqual([str(x["uid"]) for x in first], [str(x["uid"]) for x in second])
        self.assertNotEqual(str(first[0]["uid"]), str(first[1]["uid"]))
        self.assertTrue(str(first[0]["uid"]).endswith("@snapsched.invalid"))

    def test_text_unicode_escaping_and_folding_round_trip(self):
        title = "研究会; discussion, \\ practice\nBEGIN:VEVENT" + "x" * 100
        _, events = self.export(event_name=title, registration_text_raw="Email office@example.org\nBring ID")
        self.assertEqual(len(events), 2)
        self.assertEqual(str(events[0]["summary"]), title)
        self.assertIn("Bring ID", str(events[0]["description"]))

    def test_unsafe_or_incomplete_events_fail_before_serialization(self):
        for change in [{"event_name": ""}, {"event_date": "2026-02-30"},
                       {"event_date": "2026-10-23"}, {"start_time": "25:00"},
                       {"end_time": "14:00"}, {"registration_deadline": "Nov 3"},
                       {"timezone": "UTC"}, {"event_name": "invalid\x00text"}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.export(**change)

    def test_started_event_today_is_refused(self):
        with self.assertRaises(ValueError):
            self.export(event_date="2026-10-24", start_time="17:00", end_time="19:00")

    def test_reference_time_must_be_aware(self):
        with self.assertRaises(ValueError):
            generate_ics(sample_event(), now=datetime(2026, 10, 24))

    def test_optional_fields_are_not_fabricated(self):
        _, events = self.export(venue="", registration_method="", registration_deadline="")
        self.assertNotIn("location", events[0])
        self.assertNotIn("Registration:", str(events[0]["description"]))

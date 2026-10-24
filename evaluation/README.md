# Evaluation pack — prepared, not yet a live result

The saved revised proposal requires eight ordinary examples and four special
cases. `posters/` contains 12 **team-created synthetic** images; `expected.json`
is their hand-authored ground truth. They are not real HKU announcements or
measured extraction results. Their consistent design makes this a baseline,
not evidence of performance on every real-world layout.

An independent teammate must check each poster against `expected.json` before
signing off. Add varied public posters later if permitted; record the source and
avoid private material. Do not replace difficult examples just to raise a score.

## Test cases

| Cases | Purpose |
| --- | --- |
| ordinary_01–02 | Full event fields, distinct registration deadline dates/times and exact URLs |
| ordinary_03_qr | QR present; tell the user to scan manually, do not invent a decoded URL |
| ordinary_04–08 | Vary printed date/time notation and venue, include an email method |
| special_09_no_date | Date missing: no invented year/date; confirmation remains blocked |
| special_10_closed | Registration closed, event in future: warn, omit expired reminder |
| special_11_hidden_venue | Venue on organiser's page: warn and do not invent it |
| special_12_unrelated | Not an event: refuse extraction/export |

## Run and record honestly

1. Securely configure the Google key; disable demo/error-simulation modes.
2. Run `python scripts/evaluate_live.py --live --reference-date 2026-10-24`.
   Twelve images are sent to Gemini, with up to three attempts per image on
   transient failures. Quotas or charges may apply. No opt-in/key means no run.
3. Inspect `results/live_fields.csv` and `results/live_summary.json`. Nonzero exit
   means a target failed; do not relabel the run successful. Model/prompt/reference
   date are recorded. Missing values are not correct guesses.
4. Independently check source vs result. Record corrections and a named reviewer
   in the CSV. Deadline **times**, not just dates, are checked in `mismatch`.
5. Export at least three reviewed `.ics` files in the actual UI and import them
   into a real calendar client. Check HK-equivalent times, title/venue, the separate
   deadline, alarm behaviour, date-only cases and no expired reminders. Record
   client/version, pass/fail and observations in `export_import_result`.
   Parser tests alone do not count as real calendar-client imports.
6. Test the four special cases through the actual UI, not only the CLI; record
   blocked confirmation, missing-information warnings and safe failure.

Automatic extraction targets are at least 7/8 correct name/date and 7/8 correct
time/venue, both deadline/URL examples exact, and the specified safety/QR checks.
Full evaluation also needs the independent review and real UI/import checks.
The script deliberately leaves `full_evaluation_complete` false; complete the
human evidence separately. No live scores are included in this initial pack.

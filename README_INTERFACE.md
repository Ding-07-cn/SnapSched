# SnapSched - Part A interface handoff

Owner: GE Jiayu. Prepared 21 October 2026.

This is the Streamlit interface component, **not the complete AI application**.
It runs without a paid API key. The team README's roles are preserved; its setup
section has only been corrected and linked to this guide.

## Run it

Use Python 3.11 or newer (locally tested with Python 3.12.14). In this project folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

On Windows, use `.venv\Scripts\activate` instead of the `source` line.
Open the Local URL shown in the terminal, normally http://localhost:8501.
Do not share a localhost URL as a public deployment: it works on your own computer only.

`requirements-ui.txt` pins the two direct dependencies actually used and tested by A.
`requirements.txt` currently includes those UI dependencies. B/C/D should merge their
dependencies during integration, rather than overwrite another member's requirements
with a freeze from an unrelated/global environment.

## What works now

- Upload one real JPG/PNG, check its bytes and size, and display its preview.
- Edit the event name, date, times, venue, deadline and registration method.
- Warn about missing details; never infer a date/year from today's date.
- Require review acknowledgement and an explicit confirmation.
- Lock reviewed fields after confirmation. **Edit details** clears approval and
  previous output before unlocking the form; a replacement image also clears both.
- Reject impossible dates, malformed deadlines and non-increasing same-day times.
- Correct phone-photo preview orientation and reject animated images.
- Reset app-held data and the upload widget.
- Load a **labelled saved sample** for UI review without calling an AI service.
- Detect optional B/C modules and display their connection status.
- Pass confirmed details to C and enable download only after C returns a calendar file.
- Catch integration errors without displaying raw exception text or API credentials.

## What is deliberately not implemented by A

There is no real vision/LLM call and no `.ics` generator in this delivery.
The corresponding buttons stay disabled until B/C are connected.
The saved sample is not image recognition, and test doubles in `tests/` are not
production implementations. **Do not use the saved sample alone as evidence of a
working AI input -> processing -> output workflow for the Mid-Term Check.**

Other limits: one event per image; Hong Kong time; no automatic link opening, QR
decoding, website scraping, mailbox/calendar-account syncing or notifications.
C owns final calendar validation, deadline/reminder semantics and calendar contents.
A checks dates, same-day time order and deadline format, and gates export behind review.
An expired registration deadline is a warning, not an invented new reminder.

## Quick interface walkthrough

1. Open the app. In the sidebar choose **Saved sample demo**.
2. The synthetic poster appears; the form remains empty until you click
   **Load saved sample fields**. A warning explicitly labels this as saved data.
3. Compare the source and fields; correct a venue or time if needed.
4. Tick the review acknowledgement and click **Confirm reviewed details**.
5. Confirm that C is shown as not connected and no fake calendar can be downloaded.
6. Choose **Edit details**: approval and old output must be cleared before any
   field becomes editable. Changes require a fresh review and confirmation.
7. Switch to **Upload a poster** and choose `samples/demo_poster.png`.
   The source appears, but fields must not be filled with the saved demo answer.

For the real AI workflow, B must be connected, an image must be uploaded and live
extraction consent given; review the returned draft, then connect C for export.
Before using a live provider, D/B should document that provider's retention policy
and key setup. Local preview is not a claim of provider-side deletion.

## Integration contract (B and C)

These function names are a proposed handoff contract, not an instruction to
overwrite teammates' code. If teammates already use other names, change only
`integrations.py` / the two loader calls in `app.py` to adapt.

### B: `ai_extraction.py`

```python
def extract_event(image_bytes: bytes, mime_type: str) -> dict:
    # Return the fields below after a real extraction.
    # Use empty strings or null for absent/unreadable text; do not guess.
    ...
```

Example shape (all values are synthetic examples, not an implemented result):

```json
{
  "event_name": "Workshop",
  "event_date": "2026-11-05",
  "start_time": "15:00",
  "end_time": "16:00",
  "venue": "Room 101",
  "registration_deadline": "2026-11-03 18:00",
  "registration_method": "https://example.com/register",
  "timezone": "Asia/Hong_Kong",
  "all_day": false,
  "warnings": ["Check the organiser's details if a field is missing."]
}
```

Dates/times are plain strings for easy debugging. `all_day` must be a boolean;
`warnings` is optional and must be a list of strings. The adapter deliberately
rejects a non-Hong-Kong timezone rather than silently converting it incorrectly.

### C: `calendar_export.py`

```python
def generate_ics(confirmed_event: dict) -> str | bytes:
    # Validate the reviewed event and return the calendar file contents.
    # Raise an exception if the event cannot be exported safely.
    ...
```

The confirmed event has the same fields except `warnings`. For an all-day event,
the UI passes blank start/end times. `registration_deadline` is distinct from the
event date. Blank optional fields remain blank. A checks UTF-8, size and basic
VCALENDAR/VEVENT structure before download; C must validate the actual calendar
properties and test real import. This guard is not a full calendar parser.

## Tests

```sh
python -m unittest discover -s tests -v
```

See `docs/PART_A_TEST_REPORT.md` for tested scope and limitations. Tests make no
network/API calls. Tests involving B/C use temporary in-process test doubles.
They verify the interface boundary, not the accuracy of B or correctness of C.

## Files to merge into the team repository

- `app.py`, `interface_state.py`, `integrations.py`
- `requirements.txt`, `requirements-ui.txt`, `.gitignore`
- `.streamlit/config.toml`, `.github/workflows/ui-tests.yml`
- `samples/demo_poster.png`, `scripts/create_sample_poster.py`
- `tests/`, `README_INTERFACE.md`, `docs/PART_A_TEST_REPORT.md`

`docs/GE_JIAYU_CONTRIBUTION.md` contains factual contribution notes for the
official status sheet/weekly report. It is not an official submission.

## Hosting

This is a Python/Streamlit app, not a static GitHub Pages site. For Streamlit
Community Cloud, select `Ding-07-cn/SnapSched`, branch `main`, entrypoint `app.py`,
and Python 3.12. Install from the root `requirements.txt`. No API secret is
required for Part A. B should document its own secret names before live extraction
is enabled. Never commit keys; use the hosting service's secrets settings.

The labelled sample has a fixed event date, 5 November 2026. After that date it
will correctly fail the past-date check. Update the synthetic poster and matching
`sample_event()` together if retaining the demo later. Do not bypass validation.

Do not upload `.venv`, private posters, API keys, logs, or `.git`. This is a local
working copy of **Ding-07-cn/SnapSched**, not the earlier personal prototype repo.

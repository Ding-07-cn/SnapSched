# SnapSched

HKU event poster → reviewed calendar file. A small AILT9019 team application,
not an automatic calendar account manager.

## Current implementation — 24 October 2026

The A/B/C code is integrated: upload one JPG/PNG, consent to AI processing,
extract event fields through Gemini, edit them next to the poster, explicitly
confirm, and download a real `.ics` file. A future registration deadline becomes
a separate entry. The original Part B and C branch histories are preserved.

The concurrent Part A–B adapter and latest Part C helper files are also included.
Their original import names delegate to the same validated implementation;
there is no second UI or second calendar library to configure.
Local verification currently passes 79 regression tests and 55 Part B offline
self-checks; these counts do not represent live AI accuracy.
Clean Ubuntu CI also passes on Python 3.11/3.12
([verified run](https://github.com/Ding-07-cn/SnapSched/actions/runs/40088278623)).
`samples/reviewed_demo.ics` is an actual browser download from the clearly
labelled saved sample, not an AI-extracted result or client-import certificate.

**Verification boundary:** automated integration tests replace only the external
model response; they do not measure AI accuracy. Real API extraction, the full
12-image evaluation, independent teammate review and three calendar-client
imports still need to be recorded. A configured key is required for live AI.
See [test report](docs/INTEGRATION_TEST_REPORT.md) for completed/pending checks.

## Run locally

Use Python 3.11 or 3.12 (3.12 recommended). In this project folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

On Windows, activate with `.venv\Scripts\activate` instead of `source`.
Open the Local URL printed in the terminal. `localhost` is only accessible on
your computer; it is not the group's public website.

### Set up live AI safely

Create `.streamlit/secrets.toml` locally, using
[the example](.streamlit/secrets.toml.example). Set `GEMINI_API_KEY` to your own
key. Environment variables or a root `.env` file are also supported; environment
values take priority. Restart after changing settings.

```toml
GEMINI_API_KEY = "replace-with-your-key"
SNAPSCHED_MODEL = "gemini-3.5-flash"
SNAPSCHED_TIMEOUT_SECONDS = "30"
```

Do not commit real keys, send them to the group, or put them in a poster.
The default model follows Part B's chosen Gemini 3.5 Flash. Availability,
region, quotas and billing depend on the actual Google account; a model name
alone is not proof that a key can use it. Requests have bounded retries
(at most three attempts for temporary errors), no training or agent workflow.

Without a key, **Saved sample demo** still supports review, confirmation and
real calendar export. It is clearly labelled saved data, not live AI recognition.
The fixed sample is dated 5 November 2026; refresh both its poster and data after
that date rather than disabling date checks.

## What the user does

1. Upload one clear poster; JPG/PNG, at most 8 MB and 20 megapixels.
2. Use only public or synthetic material. Agree to external AI processing.
3. Click **Extract details with AI** and wait for either a draft or a safe error.
4. Check the source, especially date/year, venue, registration link and deadline.
   Missing information stays missing. Open an organiser's details yourself;
   the app does not follow links or decode QR codes automatically.
5. Correct the fields, acknowledge review, then click **Confirm reviewed details**.
6. Click **Create calendar file**, then **Download .ics**. Import it into your
   chosen calendar yourself. This does not register you for the event.

Editing or replacing the poster clears old approval and output. API failures
never silently become successful demo results. Images classified as unrelated
cannot be exported through the AI review flow; choose a different image or retry.

## Calendar rules and deliberate limits

- One event per image, one calendar download; Hong Kong time only. Check any
  source using another timezone manually. Timed entries are serialized as UTC,
  so a client displays the equivalent time in its own configured timezone.
- Unknown event times are not automatically marked all-day. A user must
  deliberately select all-day when appropriate. No printed end time means no
  guessed duration. Overnight/multi-day events are outside this single-day MVP.
- A future date-only registration deadline stays an all-day entry, without an
  invented closing time or alarm. If it is today or earlier, no deadline entry
  is generated because its exact closing time is unknown.
- A future timed deadline receives a separate entry and an alarm at that time.
  Past deadlines are omitted from reminders but retained in the description.
  Calendar clients control whether imported alarms appear or fire.
- Stable IDs help identify repeated exports, but import/deduplication behaviour
  depends on the calendar client. Check before importing the same event twice.
- No login system, mailbox access, server calendar storage, automatic sync,
  old-calendar merging, push notifications, scraping or direct account writes.
  Existing-calendar merging is not a requirement in the saved final proposal.

## Public hosting

This is a Python app, so **GitHub Pages cannot run it**. Use Streamlit Community
Cloud (or another Python host). The repository owner/deployer should select:

| Setting | Value |
| --- | --- |
| Repository | `Ding-07-cn/SnapSched` |
| Branch | `main` after the integration is merged |
| Main file | `app.py` |
| Python | `3.12` |
| Dependencies | root `requirements.txt` |
| Secrets | paste the TOML settings above into the app's deployment secrets |

Do not include the key in GitHub files. If you lack repository admin/deployment
permissions, ask the current owner to deploy/configure the app; do not change
repository visibility just to bypass access errors. Keep existing access settings.
After deployment, test the public `.streamlit.app` URL on a second device and
record a live upload-to-download attempt. A working local preview does not prove
that the public deployment or API works. No unverified public URL is listed here.

## Privacy and responsible use

The application does not intentionally persist uploaded posters or extracted
details to its own database/files, and calendar generation happens in memory.
Streamlit sessions and hosting infrastructure still handle the data. **Clear
session data** removes the app's current state; it cannot erase downloaded
files, provider records, browser history or platform logs.

Live extraction sends a compressed image to Google. Under the
[Gemini API terms](https://ai.google.dev/gemini-api/terms), unpaid-service content
may be used for product improvement and human review; paid services have
different data-use terms but still include limited abuse-monitoring retention.
This is **not zero-retention or offline AI**. Check current terms, applicable
account/region/age rules and quota before deployment. Policy reviewed 24 October
2026. Use synthetic/public posters only; do not upload confidential emails,
student IDs, faces or private information. This course prototype is not affiliated
with or endorsed by HKU.

## Tests, evaluation and handoff

```sh
python -m unittest discover -s tests -v
python test_extraction.py --selftest
python -m pip check
```

To regenerate synthetic evaluation fixtures (not measured AI results):

```sh
python -m pip install -r requirements-dev.txt
python scripts/create_evaluation_posters.py
```

After independent fixture checking and secure key setup, explicitly opt into
12 real API calls (retry/quota/cost limits still apply):

```sh
python scripts/evaluate_live.py --live --reference-date 2026-10-24
```

The reference date is fixed to make these dated fixtures reproducible; it does
not change the UI's actual current-date checks. The script refuses missing keys
or demo/error-simulation mode and never creates pretend scores. Review the
generated `evaluation/results/` files; log corrections and actual imports manually.
See [evaluation instructions](evaluation/README.md),
[demo guide](docs/DEMO_GUIDE.md), and [interface/module contract](README_INTERFACE.md).

Create a clean source handoff (not a complete Moodle submission):

```sh
python scripts/package_project.py
```

## Team contributions

- **GE Jiayu:** Part A interface, review/state handling; integration of existing
  modules, missing calendar backend, regression tests, setup and handoff updates.
- **Aryan / Part B:** Gemini extraction, prompts, field checks and CLI self-tests;
  integrated with small configuration and request-bound fixes.
- **Nicole / Part C:** calendar review and backend/helper drafts; integration
  repaired their missing imports and aligned optional-field/deadline rules.
  Her latest branch history is preserved alongside the completed implementation.
- **Ding Siqi / Part D:** team repository, collaboration and deployment coordination.

[GE Jiayu's factual contribution notes](docs/GE_JIAYU_CONTRIBUTION.md) are a writing
reference, not the official Moodle form or proof of other members' contribution.

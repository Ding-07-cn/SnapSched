# Integration verification — 24 October 2026

## Completed locally

- Python 3.12.14: **79/79** unit/interface/integration tests passed (4.451 s),
  rerun after incorporating the concurrent team changes.
- Part B offline CLI self-tests: **55/55** passed. They use mocked responses,
  not a live AI service, including the prompt-injection response checks.
- Dependency compatibility: `pip check` passed; whitespace/diff check passed.
- Actual browser: uploaded a synthetic PNG, gave processing consent and attempted
  extraction without a key. A clear safe error appeared, no successful AI answer.
- Actual browser: labelled saved sample → explicit review → confirmation → real
  calendar generation → browser download. Downloaded bytes parsed as two UTC
  events: 5 November 15:00–16:00 HKT and 3 November 18:00 HKT registration deadline.
  The deadline has an at-time display alarm. This is a **saved-data** check.
- Actual browser: **Edit details** unlocked the form and disabled/cleared the
  previous export. Phone-size (390×844) export controls checked without overflow.
  `integrated-mobile.png` is saved-data UI evidence, not live AI evidence.
- Twelve synthetic 1200×1200 baseline posters and field truth prepared. Selected
  rendered fixtures visually checked, including a real synthetic QR code. This
  is not an independent teammate check or measured extraction accuracy.

## Code and risk review

The original B/C branch histories are merged rather than rewritten. The adapter
keeps source wording and separates API errors/unrelated images from events.
The calendar backend was completed with `icalendar`, including escaping,
UTC times, all-day exclusive end, optional fields, stable IDs and future-only
deadline reminders. Date-only deadlines never become guessed midnight alarms.
The live evaluation script rejects demo/error-simulation mode and missing keys;
it explicitly scores deadline times and leaves human checks pending.

Concurrent changes were incorporated before publication: main's Part A–B adapter
(`d2d7e98`) and the latest C helpers (`aff21df`). C's missing config/import references,
duplicate library dependency and overly strict optional-field requirements were
replaced by compatibility wrappers around the canonical implementation. Five
compatibility tests verify old entrypoint names and reject unsupported old-calendar
input explicitly. Unexpected provider exception text is never shown in the UI.

Scope was checked against the locally saved **SnapSched_Project_Proposal_Revised_Final.pdf**
(9 October revision). Existing-calendar merging and automatic retention are not
required. They are deliberately absent; no accounts, database or calendar sync
were added. See README for current provider policy and limitations.

## Not yet verified / not claimed

| Check | Status / next action |
| --- | --- |
| Real Gemini extraction | NOT RUN: no local key; configure securely, then test account/model access |
| 12-poster live accuracy | NOT RUN: run the opt-in tool; no invented scores |
| Independent fixture/result review | PENDING: another teammate checks source vs fields |
| Three calendar-client imports | PENDING: actual client checks, not parser round-trips |
| Public deployment and live workflow | NOT VERIFIED: owner must provide actual URL and configure secrets |
| Current integration CI | Awaiting publication; local success is not a remote CI claim |
| Official midterm package/video/status sheet | Not complete; source ZIP is a code handoff only |

The application's clear/reset action does not prove deletion at the provider or
hosting layer. Stable calendar IDs do not guarantee every client deduplicates.
Alarm behaviour varies by client; import tests are still necessary.

## Reproduce

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python test_extraction.py --selftest
python -m pip check
python scripts/evaluate_live.py --live --reference-date 2026-10-24
```

The final command must exit `2` without a configured key and must not write
pretend results. See `evaluation/README.md` for scoring and independent checks.

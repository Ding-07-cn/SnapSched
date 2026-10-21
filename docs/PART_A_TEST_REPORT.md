# Part A verification - 21 October 2026

## Result

38 automated checks passed using `python -m unittest discover -s tests -q`.
Tests cover pure helpers, optional-module adapters and simulated Streamlit flows.
The tests were rerun after adding regression cases, not merely before changes.

Environment: macOS ARM64, Python 3.12.14, Streamlit 1.66.0, Pillow 12.3.0.
The AppTest clock is fixed at 21 October 2026 for the dated synthetic poster;
the actual app uses the real current date in Asia/Hong_Kong.

The app was also started as a real local Streamlit server. Its health check
returned `ok`; the browser loaded the sample poster/fields, the review checkbox
enabled confirmation, and confirmed inputs became disabled while C remained
disabled. Explicit editing releases the lock and clears previous approval.
The final page showed the 8 MB upload limit and readable consent/review labels.
`part-a-interface.jpg` is a browser screenshot of this
local, clearly labelled sample mode, not a claim of live AI extraction.

Responsive browser check: at a 390 x 844 viewport the sidebar collapses and the
two main columns stack. Input widths were 356 px and the document width equalled
the 390 px viewport (no horizontal page overflow). `part-a-mobile.jpg` records
the initial upload screen. This is browser emulation, not a physical-phone test.

## Covered

- Empty form cannot be confirmed; no default date/year is invented.
- Valid sample can be reviewed and confirmed, but not exported without C.
- Saved sample is explicitly labelled, not presented as live extraction.
- Uploaded files are checked as real PNG/JPEG bytes, with an 8 MB limit.
- Corrupt, empty, non-image and oversized inputs are refused.
- Missing/invalid/past dates and ambiguous times block UI confirmation.
- All-day events require an explicit all-day choice.
- Source changes clear fields, consent, confirmation and prior export bytes.
- Same-source reruns retain the user's edits.
- Confirmed fields are locked; choosing Edit details clears approval and stale
  output before editing. All-day export does not reuse disabled time values.
- Non-increasing end times and malformed/impossible deadlines are refused.
- Closed registration warns without rejecting an otherwise upcoming event.
- Phone EXIF orientation is corrected; GIF and animated PNG are refused.
- Preview decoding is reused per session and released on reset/source change.
- Excessive model fields/warnings are rejected; model notes display as plain text.
- Reset clears the form and confirmation.
- Reset also clears the real upload widget; separate viewer sessions do not share data.
- Live extraction button requires consent and a connected B module.
- B adapter output is validated; missing fields stay empty.
- API failure clears previous drafts and never displays raw error text/secrets.
- C receives only a copy of explicitly confirmed details.
- C failure or a non-calendar result cannot leave a downloadable stale file.
- Calendar output must be UTF-8, bounded in size and contain basic event structure.

## Review and reproduction

The first regression run reproduced unlocked confirmed inputs, invalid time order,
bad deadline acceptance and incorrect phone orientation. These were fixed and the
38-test suite then passed. The production server was restarted after shared
Python imports changed; the fresh process was checked in the browser. This avoids
mistaking an old hot-reload process for a clean deployment.

GitHub Actions run 39564068373 completed successfully on Linux for Python 3.11
and 3.12, including dependency installation, the test suite and compilation.
Verified code commit: `8b5d8c0de7192b3831f80167d5ee7483cb61e5cc`.
Result: https://github.com/Ding-07-cn/SnapSched/actions/runs/39564068373

## Publication and hosting

Part A is published in https://github.com/Ding-07-cn/SnapSched/pull/1 .
The Streamlit hosting entrypoint https://share.streamlit.io returned
`source IP address not allowed` in both the in-app browser and Chrome on this
machine. Hosting is therefore blocked before sign-in/deployment; this delivery
does not claim a live public URL. The localhost preview works on this machine only.
From a connection that can access the service, use the hosting settings in
README_INTERFACE.md. Do not replace this Python app with a static Pages upload.

## Not demonstrated or claimed

This does not prove AI extraction quality, QR decoding, a real calendar import,
the full 12-poster team evaluation, teammate installation on a second machine,
public deployment, or completion of the team Mid-Term Check. B/C integration
tests use temporary test doubles, not hidden production implementations.

## Remaining integration work

1. B owner: connect real image extraction and document API/privacy setup.
2. Nicole/C: connect calendar generation and final validation; check real import.
3. Kylie/D: combine the modules, merge dependencies, reproduce from a clean
   environment, and prepare genuine end-to-end evidence and submission files.
4. Confirm real team dates/owners before completing the official one-page sheet.

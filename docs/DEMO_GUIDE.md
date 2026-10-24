# Demo and remaining handoff

Use the current app with a securely configured key. Test the exact deployment
before recording; do not show a secret in the recording or screen share.

## A genuine workflow in at most 60 seconds

- 0–8s: show SnapSched and upload `evaluation/posters/ordinary_01.png`.
- 8–12s: explain consent and click **Extract details with AI**.
- 12–35s: show the actual model result next to the poster. Check date, time,
  venue, registration link and deadline. Correct one field only if it needs it.
- 35–45s: acknowledge source checking and **Confirm reviewed details**.
- 45–55s: create and download `.ics`; show the event and registration entry in
  a calendar client if already verified and quick enough.
- 55–60s: say that users must review AI output and register with the organiser.

These times are a recording plan, not measured provider latency. If extraction
takes longer, prepare a clearly labelled captured real response or choose a
permitted editing approach under the assignment rules; never replace it with
the saved sample and claim it was live. Do not speed up a failure into a success.

## Quick safety checks before the recording

- Missing date: confirmation blocked until a verified complete date is entered.
- Closed registration: future event still exportable; no old deadline alarm.
- Unrelated image: no successful event, no export.
- Wrong key/network/quota: clear error, no old answer carried forward.
- Edit confirmed fields: old approval/download cleared.
- Optional-field omissions: organiser-page reminder, no invented venue/link.

## What still requires team input/evidence

1. Kylie/deployer: configure `GEMINI_API_KEY` in existing deployment secrets,
   confirm the selected model works for the account, and share the actual public
   URL. Do not paste the key into WhatsApp or GitHub.
2. Run the supplied 12-image live evaluation and have another teammate verify it.
3. Record three real calendar imports. Client import behaviour cannot be inferred
   from Python parser tests. Adding events does not register a place.
4. Record the real workflow video and complete the official one-page team status
   sheet with each member's actual contribution. Include `repository_link.txt`.

The source ZIP produced by `scripts/package_project.py` is a clean code handoff,
not a claim that the full Moodle submission is ready. The saved course reminders
were checked on 21 October: Week 8 individual report due 25 October 23:59 HKT;
midterm due 26 October 23:59 HKT. Recheck the assignment for any later changes.

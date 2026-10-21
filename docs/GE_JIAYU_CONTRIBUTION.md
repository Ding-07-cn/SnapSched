# GE Jiayu - completed contribution as of 21 October 2026

These are factual notes for the team status sheet / individual weekly report.
Use the official Moodle form or companion template when submitting.

## Completed

I implemented Part A, the Streamlit interface, in a local working copy of the
new team repository, Ding-07-cn/SnapSched. It supports one JPG/PNG upload and
preview, side-by-side editable event details, missing-information prompts,
review acknowledgement and explicit confirmation before calendar export.

I added state handling so a replacement image or edited field invalidates
previous confirmation and calendar data. Uploads are checked by actual image
content and limited to 8 MB / 20 megapixels. Live extraction requires a privacy
consent checkbox. The interface exposes adapters for B's extraction module and
C's calendar module; missing modules are clearly labelled and their actions
are disabled rather than faked.

I prepared a synthetic poster, a clearly labelled saved-data demonstration,
setup instructions and the proposed B/C data contract. I ran 38 automated
checks and checked the actual local browser review/confirmation flow. A second
review added explicit edit/unlock handling, phone-photo orientation correction,
per-session preview reuse, date/time/deadline checks and safer adapter output
handling. GitHub Actions is configured for Python 3.11 and 3.12.

## Current limitations and next action

This delivery does not implement a real LLM call or calendar generation.
The saved-data demo does not constitute the real end-to-end AI workflow.
The full 12-poster team evaluation and a real calendar import are not yet done.

Write access for gejiayu202509-maker was verified on 21 October. The code is
published at https://github.com/Ding-07-cn/SnapSched/pull/1, with a shareable ZIP
as a separate handoff. Linux CI passed on Python 3.11 and 3.12 (run 39564068373).
Public hosting remains blocked because share.streamlit.io returns
`source IP address not allowed` in both available browsers on this machine.
No live public deployment is claimed.

After B/C are connected, I can verify that the live extraction result fills
the interface correctly and that only explicitly confirmed details reach C.
The integration owner should then record the real workflow and complete the
official team status sheet with every member's actual contribution.

## Upcoming course reminders

The Moodle project page sidebar was checked on 21 October 2026:
- Week 8 individual weekly project report: Sunday 25 October, 23:59 HKT.
- Midterm: Monday 26 October, 23:59 HKT.

The locally saved midterm requirements specify one team ZIP up to 100 MB,
containing a running-workflow video of at most 60 seconds, repository_link.txt,
and the official one-page status sheet. Check the assignment itself and the
current companion template before final submission. Do not submit this notes
file as a substitute for that template.

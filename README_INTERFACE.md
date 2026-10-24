# Interface and integration contract

Updated 24 October 2026. This replaces the old Part A-only handoff.
The current entrypoint is **app.py**. B and C are now connected.
See [README.md](README.md) for setup, secrets, privacy, hosting and limitations.

## Keep the architecture small

| File | Responsibility |
| --- | --- |
| `app.py` | Streamlit upload, preview, consent, edit, confirm and download |
| `interface_state.py` | Image/field validation, state invalidation, deadline parsing |
| `integrations.py` | Load B/C and guard their return types |
| `extraction.py`, `prompts.py` | Aryan's Gemini request, parsing and field warnings |
| `ai_extraction.py` | Convert B's existing response to the flat review fields |
| `calendar_export.py` | Validate confirmed fields and create real `.ics` bytes |
| `runtime_config.py` | Environment / Streamlit-secret lookup without displaying keys |
| `review_page.py` | Compatibility entrypoint opening the same app, not a second UI |

## B contract

The interface calls `ai_extraction.extract_event(image_bytes, mime_type)`.
This adapter calls the real Part B `extraction.extract_event` and converts:

- B `fields.date` → UI `event_date`.
- B `registration_deadline` + `registration_deadline_time` → either
  `YYYY-MM-DD HH:MM` or date-only `YYYY-MM-DD` (never guessed midnight).
- Preserves printed registration wording, exact registration method/link and
  warning text. Drops raw model output from the UI payload.
- `api_error` and `no_event_found` become safe local errors, not fake events.
- Missing times stay blank; the adapter does not assume an all-day event.

The resulting flat dictionary contains `event_name`, `event_date`, `start_time`,
`end_time`, `venue`, `registration_deadline`, `registration_method`,
`registration_text_raw`, `timezone="Asia/Hong_Kong"`, `all_day=False`, `warnings`
and `mode`. Null text becomes blank. Invalid types, non-Hong-Kong timezone,
oversized strings and unsupported control characters are rejected.

An external response never confirms itself. When extracting again, replacing
the source or editing fields, previous approval and calendar bytes are cleared.
Fields are locked after confirmation; **Edit details** unlocks and invalidates.

## C contract

`calendar_export.generate_ics(confirmed_event)` returns UTF-8 calendar bytes.
It does not take an old calendar, credentials, an upload path or a storage target.
Confirmed details have the flat fields above without warning metadata.

The generator revalidates real date/time values and rejects already-started timed
events. Timed entries use UTC; all-day entries use a date and an exclusive next-day
end. A missing end time remains omitted. Future stated deadlines become separate
entries; expired ones do not. A date-only deadline on the current date is not
assumed to remain open. Only future timed deadlines have an explicit at-time alarm.

Calendar output is parsed back and checked before it is offered for download.
Editing confirmed details clears both the approved snapshot and old bytes. No
database, mailbox/calendar account integration or server calendar retention exists.

## Verification

- `tests/test_app.py`: isolated interface/adapter boundary cases.
- `tests/test_integrated_app.py`: real A/B parser/adapter/C, with only the external
  model response mocked. Verifies actual generated calendar properties.
- `tests/test_calendar_export.py`: serialization, timezone, date-only deadlines,
  escaping, deterministic IDs and invalid/expired-event cases.
- `tests/test_ai_adapter.py`: B response contract and provider configuration.
- `tests/test_evaluation.py`: live evaluation opt-in and honest scoring boundaries.
- `test_extraction.py --selftest`: Part B's offline checks, not AI accuracy.

See [current test report](docs/INTEGRATION_TEST_REPORT.md). The old
`docs/PART_A_TEST_REPORT.md` and Part A screenshots are historical, not current
end-to-end evidence. Real model accuracy and real calendar imports must be
recorded separately. The saved sample alone is not a live AI demonstration.

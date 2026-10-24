# demo_results

The `.json` files here are **saved results** for the supplied sample posters. They are **not live AI output**:
demo mode (`SNAPSCHED_DEMO_MODE=1`, or `demo_image_id` passed to `extract_event`) simply replays them,
and the returned dict says `"mode": "demo"`.

- File name = image id (`<image_id>.json`), e.g. `sample_poster_1.json`.
- Created only on request: `python test_extraction.py sample_posters --reference-date 2026-10-23 --save-demo`.
- Demo mode only works for posters that have a saved file here; any other image gets an `api_error` message saying so.
- Files contain only the fields, warnings and message the UI would show. The raw model output is never saved.
- "Event in the past" and "deadline passed" warnings are recomputed from the reference date each time.

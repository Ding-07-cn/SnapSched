"""Explicitly opt in to sending ONLY the supplied synthetic posters to Gemini.

This measures live field extraction, never the mocked integration tests. It does
not claim calendar-client import or independent human review. No default API call.
"""
import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extraction
from runtime_config import ai_configured
from test_extraction import build_row, compare_to_expected, CSV_COLUMNS


def compare_result(result, wanted):
    differences = compare_to_expected(result, wanted)
    extras = []
    missing = set(wanted.get("required_warning_codes", [])) - set(result["warning_codes"])
    if missing:
        extras.append("missing warning codes: " + ",".join(sorted(missing)))
    field = "registration_deadline_time"
    if field in wanted and result["fields"].get(field) != wanted[field]:
        extras.append(f"{field}: expected {wanted[field]!r} got {result['fields'].get(field)!r}")
    if result.get("mode") != "live":
        extras.append("NOT a live result")
    return "; ".join(([differences] if differences != "match" else []) + extras) or "match"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Send 12 synthetic images; API charges/quotas may apply")
    parser.add_argument("--reference-date", default="2026-10-24")
    args = parser.parse_args()
    if not args.live:
        print("NOT RUN. Add --live to explicitly send the synthetic test set to Gemini.")
        return 2
    if any(os.getenv(name) == "1" for name in ("SNAPSCHED_DEMO_MODE", "SNAPSCHED_SIMULATE_API_ERROR")):
        print("NOT RUN: disable demo/simulated mode before measuring live extraction.")
        return 2
    if not ai_configured():
        print("NOT RUN: GEMINI_API_KEY is not configured. No score or successful AI result is claimed.")
        return 2
    expected = json.loads((ROOT / "evaluation/expected.json").read_text())
    rows, outcomes = [], {}
    for ident, wanted in expected.items():
        image = (ROOT / "evaluation/posters" / f"{ident}.png").read_bytes()
        result = extraction.extract_event(image, "image/png", reference_date=args.reference_date)
        row = build_row(ident, args.reference_date, result, wanted)
        differences = compare_result(result, wanted)
        row["mismatch"] = differences
        row["reviewer_check"] = "PENDING independent teammate check; deadline time checked in mismatch column"
        row["export_import_result"] = "NOT TESTED in a calendar client"
        rows.append(row)
        fields = result["fields"]
        outcomes[ident] = {
            "status": result["status"], "warning_codes": result["warning_codes"],
            "name_date_correct": result["status"] == "ok" and
                all(fields.get(k) == wanted.get(k) for k in ["event_name", "date"]),
            "time_venue_correct": result["status"] == "ok" and
                all(fields.get(k) == wanted.get(k) for k in ["start_time", "end_time", "venue"]),
            "all_expected_fields_match": differences == "match",
        }
        print(f"{ident}: {result['status']}; {differences}")
    ordinary = [value for key, value in outcomes.items() if key.startswith("ordinary_")]
    name_date = sum(x["name_date_correct"] for x in ordinary)
    time_venue = sum(x["time_venue_correct"] for x in ordinary)
    exact_cases = ["ordinary_01", "ordinary_02", "ordinary_03_qr", "special_09_no_date",
                   "special_10_closed", "special_11_hidden_venue", "special_12_unrelated"]
    targets_met = (name_date >= 7 and time_venue >= 7 and
                   all(outcomes[key]["all_expected_fields_match"] for key in exact_cases))
    summary = {
        "executed_at_hkt": datetime.now(ZoneInfo("Asia/Hong_Kong")).isoformat(),
        "reference_date": args.reference_date, "model": extraction.setting("SNAPSCHED_MODEL", extraction.DEFAULT_MODEL),
        "prompt_version": extraction.PROMPT_VERSION,
        "ordinary_name_date_correct": name_date,
        "ordinary_time_venue_correct": time_venue,
        "automated_extraction_targets_met": targets_met,
        "full_evaluation_complete": False,
        "ordinary_case_count": len(ordinary), "cases": outcomes,
        "independent_review": "PENDING", "real_calendar_import": "PENDING",
        "note": "Field extraction only. Missing values and API errors are not correct guesses.",
    }
    out = ROOT / "evaluation/results"
    out.mkdir(exist_ok=True)
    with (out / "live_fields.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader(); writer.writerows(rows)
    (out / "live_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("Written evaluation/results. Independent review and real calendar imports still pending.")
    return 0 if targets_met else 1


if __name__ == "__main__":
    raise SystemExit(main())

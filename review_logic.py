from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

HK_TZ = ZoneInfo("Asia/Hong_Kong")
SAVE_DIR = Path("review_outputs")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_PATHS = [
    "name",
    "venue",
    "start_dt",
    "end_dt",
    "reg_deadline_dt",
    "reg_method.type",
    "reg_method.value",
]

FIELD_LABELS = {
    "name": "Event name",
    "venue": "Venue",
    "start_dt": "Start datetime (YYYY-MM-DD HH:MM)",
    "end_dt": "End datetime (YYYY-MM-DD HH:MM)",
    "reg_deadline_dt": "Registration deadline (YYYY-MM-DD HH:MM)",
    "reg_method.type": "Registration method type (url / qr_image / text)",
    "reg_method.value": "Registration method value",
}


def get_by_path(data: dict, path: str) -> Any:
    cur = data
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def set_by_path(data: dict, path: str, value: Any) -> None:
    keys = path.split(".")
    cur = data
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value


def ensure_standard_event(event: dict) -> dict:
    output = dict(event or {})
    if "reg_method" not in output or not isinstance(output.get("reg_method"), dict):
        output["reg_method"] = {}

    for p in REQUIRED_PATHS:
        if get_by_path(output, p) is None and p not in flatten_paths(output):
            set_by_path(output, p, None)
    return output


def flatten_paths(data: Any, prefix: str = "") -> set[str]:
    paths = set()
    if isinstance(data, dict):
        for k, v in data.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.add(p)
            paths |= flatten_paths(v, p)
    return paths


def find_missing_required_fields(event: dict) -> list[str]:
    return [p for p in REQUIRED_PATHS if get_by_path(event, p) is None]


def review_fingerprint(source_id: str, event: dict) -> str:
    payload = json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return sha256(source_id.encode("utf-8") + b"|" + payload).hexdigest()


def parse_hk_datetime(dt_text: str) -> Optional[datetime]:
    if not dt_text:
        return None
    try:
        dt = datetime.strptime(dt_text.strip(), "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=HK_TZ)
    except ValueError:
        return None


def save_event_json(event: dict, source_id: str) -> Path:
    now = datetime.now(tz=HK_TZ).strftime("%Y%m%d_%H%M%S")
    file_path = SAVE_DIR / f"review_{now}_{source_id[:10]}.json"
    file_path.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


def source_id_from_bytes(source_name: str, image_bytes: bytes | None) -> str:
    return sha256((source_name or "").encode("utf-8") + (image_bytes or b"")).hexdigest()

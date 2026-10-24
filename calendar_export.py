from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo

HK = ZoneInfo("Asia/Hong_Kong")


def _escape_text(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def _fmt_local(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def generate_ics(confirmed_event: dict) -> str:
    """
    按约定接口：
      calendar_export.generate_ics(confirmed_event) -> str | bytes
    """
    name = confirmed_event.get("name") or ""
    venue = confirmed_event.get("venue") or ""
    start_s = confirmed_event.get("start_dt") or ""
    end_s = confirmed_event.get("end_dt") or ""
    ddl = confirmed_event.get("reg_deadline_dt") or ""
    rm = confirmed_event.get("reg_method", {}) or {}
    reg_type = rm.get("type") or ""
    reg_value = rm.get("value") or ""

    # 解析本地时区时间
    start_dt = datetime.strptime(start_s, "%Y-%m-%d %H:%M").replace(tzinfo=HK)
    end_dt = datetime.strptime(end_s, "%Y-%m-%d %H:%M").replace(tzinfo=HK)

    uid_seed = f"{name}|{start_s}|{venue}|{reg_value}"
    uid = sha256(uid_seed.encode("utf-8")).hexdigest()[:24] + "@snapsched"
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    desc = f"Registration deadline: {ddl}\\nRegistration method: {reg_type} {reg_value}"

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//SnapSched//Event Review//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{dtstamp}\r\n"
        f"DTSTART;TZID=Asia/Hong_Kong:{_fmt_local(start_dt)}\r\n"
        f"DTEND;TZID=Asia/Hong_Kong:{_fmt_local(end_dt)}\r\n"
        f"SUMMARY:{_escape_text(name)}\r\n"
        f"LOCATION:{_escape_text(venue)}\r\n"
        f"DESCRIPTION:{_escape_text(desc)}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    return ics

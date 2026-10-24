"""Create the proposal's 8 ordinary + 4 special synthetic test images.

Expected fields are fixture ground truth, NOT measured AI results. An independent
teammate must compare the rendered posters and expected JSON before live scoring.
Run from the repository root with requirements-dev.txt installed.
"""
import json
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont
import qrcode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation" / "posters"
OUT.mkdir(parents=True, exist_ok=True)


def font(size):
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


# id, title, printed date, ISO date, printed time, start, end, venue, deadline, URL/email
cases = [
    ("ordinary_01", "Career Skills Talk", "8 Nov 2026", "2026-11-08", "6-8pm", "18:00", "20:00", "MB 123", "2026-11-05 17:00", "https://example.com/register-A"),
    ("ordinary_02", "Research Lab Workshop", "09/11/2026", "2026-11-09", "14:30-16:00", "14:30", "16:00", "CPD-LG.01", "2026-11-06 18:00", "https://example.com/Join?event=Lab2"),
    ("ordinary_03_qr", "Student Design Meetup", "10.11.2026", "2026-11-10", "10:00-11:00", "10:00", "11:00", "KKL 101", "", "QR code shown on poster"),
    ("ordinary_04", "Public Speaking Practice", "Nov 11 2026", "2026-11-11", "11:00am-12:30pm", "11:00", "12:30", "CC 101", "", "clubs@example.org"),
    ("ordinary_05", "Student Film Discussion", "12 November 2026", "2026-11-12", "6-8pm", "18:00", "20:00", "CPD-3.04", "", ""),
    ("ordinary_06", "Careers Q and A", "13/11/2026", "2026-11-13", "12:00-13:00", "12:00", "13:00", "Auditorium LG1", "", ""),
    ("ordinary_07", "Study Skills Workshop", "14 Nov 2026", "2026-11-14", "09:00-10:00", "09:00", "10:00", "CPD-2.58", "", ""),
    ("ordinary_08", "Campus Photography Talk", "15.11.2026", "2026-11-15", "4pm-5pm", "16:00", "17:00", "MB G07", "", ""),
    ("special_09_no_date", "Workshop - Date Pending", "To be confirmed", "", "15:00-16:00", "15:00", "16:00", "MB 123", "", ""),
    ("special_10_closed", "Upcoming Research Talk", "20 Nov 2026", "2026-11-20", "15:00-16:00", "15:00", "16:00", "MB 123", "2026-10-20 18:00", "https://example.com/closed"),
    ("special_11_hidden_venue", "Society Workshop", "21 Nov 2026", "2026-11-21", "18:00-19:00", "18:00", "19:00", "", "", "https://example.com/details"),
]
expected = {}
for case in cases:
    ident, title, printed_date, iso, printed_time, start, end, venue, deadline, method = case
    image = Image.new("RGB", (1200, 1200), "#F1F5F9")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1200, 160), fill="#16324F")
    draw.text((60, 50), "SnapSched | TEAM-CREATED TEST", font=font(38), fill="white")
    y = 215
    lines = textwrap.wrap(title, 35) + ["", "DATE: " + printed_date, "TIME: " + printed_time,
             "VENUE: " + (venue or "View details on the organiser's page")]
    if deadline:
        lines += ["REGISTER BY: " + deadline]
    if method and not ident.endswith("_qr"):
        lines += ["REGISTER: " + method]
    if not venue:
        lines += ["Venue details: https://example.com/details"]
    if ident.endswith("_qr"):
        lines += ["Scan the QR code to register"]
    for line in lines:
        for part in textwrap.wrap(line, 52) or [""]:
            draw.text((60, y), part, font=font(31), fill="#16324F")
            y += 52
    if ident.endswith("_qr"):
        qr = qrcode.make("https://example.com/synthetic-qr").convert("RGB").resize((250, 250))
        image.paste(qr, (850, 830))
    draw.text((60, 1120), "Synthetic fixture only. Not an official HKU announcement.", font=font(25), fill="#087F8C")
    image.save(OUT / f"{ident}.png")
    entry = {"status": "ok", "event_name": title, "date": iso or None, "start_time": start,
             "end_time": end, "venue": venue or None, "registration_method": method or None,
             "registration_deadline": deadline[:10] or None,
             "registration_deadline_time": deadline[11:] or None}
    if ident == "special_09_no_date":
        entry["required_warning_codes"] = ["MISSING_DATE"]
    if ident == "special_10_closed":
        entry["required_warning_codes"] = ["REGISTRATION_DEADLINE_PASSED"]
    if ident == "special_11_hidden_venue":
        entry["required_warning_codes"] = ["CHECK_ORGANISER_PAGE"]
    if ident.endswith("_qr"):
        entry["required_warning_codes"] = ["QR_SCAN_MANUALLY"]
    expected[ident] = entry

image = Image.new("RGB", (1200, 1200), "#F1F5F9")
draw = ImageDraw.Draw(image)
draw.ellipse((200, 200, 900, 900), fill="#087F8C")
draw.text((150, 1020), "Colour study. No event information.", font=font(40), fill="#16324F")
image.save(OUT / "special_12_unrelated.png")
expected["special_12_unrelated"] = {"status": "no_event_found"}
(OUT.parent / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
print("Prepared 12 synthetic posters and fixture ground truth. Live AI evaluation has NOT run.")

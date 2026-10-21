"""Create a public, synthetic fixture. No copyrighted poster or personal data."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
def font(size):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)

image = Image.new("RGB", (1050, 1300), "#f4f7fb")
draw = ImageDraw.Draw(image)
draw.rectangle((0, 0, 1050, 215), fill="#173b53")
draw.text((65, 55), "SNAPSCHED / TEAM-CREATED DEMO", font=font(34), fill="white")
draw.text((65, 125), "SAMPLE POSTER - NOT A REAL EVENT", font=font(27), fill="#b6e4d8")
lines = [
    (295, "Student Research", 64), (380, "Skills Workshop", 64), (495, "(DEMO)", 36),
    (635, "EVENT DATE     5 November 2026", 36),
    (710, "TIME                   15:00 - 16:00 (HKT)", 34),
    (785, "VENUE                Demo Room 101", 34),
    (835, "                              (sample location)", 28),
    (935, "REGISTER BY    3 November 2026, 18:00", 32),
    (1010, "REGISTRATION  https://example.com/register", 29),
    (1160, "For UI testing only. Saved sample data is not AI output.", 26),
    (1210, "This poster is not an official HKU announcement.", 26),
]
for y,text,size in lines:
    draw.text((65, y), text, font=font(size), fill="#173b53")
(ROOT / "samples").mkdir(exist_ok=True)
image.save(ROOT / "samples/demo_poster.png")
print(ROOT / "samples/demo_poster.png")

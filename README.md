# SnapSched 📅✨

## 🚀 What is SnapSched?
HKU students receive posters through chats, emails, and course pages. Manually copying dates, venues, and registration deadlines takes time and leads to missed opportunities. **SnapSched** streamlines this workflow into one place:
1. **Upload** a poster (JPG/PNG).
2. **Extract** event details automatically using a vision-capable AI model.
3. **Review & Edit** extracted details side-by-side with the poster.
4. **Export** a verified `.ics` calendar file (with separate registration deadline reminders).


## 🛠️ Team Division
- **GE Jiayu**: Streamlit interface (upload/preview, side-by-side editable event details, confirmation workflow).
- **Member B**: AI extraction (vision-capable LLM integration, prompt design, and field-checking logic).
- **Member C**: Calendar export & validation (generating `.ics` files, separate registration deadlines, safe-failure warnings).
- **Ding Siqi**: Repository setup, integration, end-to-end testing, and documentation (`README.md` & demo).


## 📦 Quick Start Guide

### 1. Prerequisites
Make sure you have **Python 3.10+** installed on your computer.

### 2. Install Dependencies
Open your terminal inside the project folder and run:
```bash
pip install -r requirements.txt

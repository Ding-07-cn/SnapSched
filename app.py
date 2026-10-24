"""SnapSched: poster extraction, human review and verified calendar export."""

from hashlib import sha256
from pathlib import Path

import streamlit as st

from integrations import calendar_file_bytes, load_backend
from ai_extraction import ExtractionProblem
from runtime_config import ai_configured
from interface_state import (
    FIELD_LIMITS, TEXT_FIELDS, confirmation_errors, empty_event, inspect_image,
    invalidate_review, normalise_event, populate_fields, replace_source,
    registration_warning, review_fingerprint, sample_event,
)

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="SnapSched | Poster to Calendar", page_icon="📅", layout="wide")


def clear_confirmation():
    invalidate_review(st.session_state)


def load_saved_sample():
    populate_fields(st.session_state, sample_event())
    st.session_state.source_label = "SAVED SAMPLE - not an AI extraction"
    st.session_state.extraction_warnings = []


def reset_workspace():
    st.session_state.upload_generation = st.session_state.get("upload_generation", 0) + 1
    st.session_state.source_id = None
    populate_fields(st.session_state, empty_event())
    st.session_state.extraction_warnings = []
    st.session_state.allow_ai = False
    st.session_state.preview_image = None
    st.session_state.preview_mime_type = ""
    st.session_state.image_error = None
    st.session_state.extraction_rejected = False


if "upload_generation" not in st.session_state:
    st.session_state.upload_generation = 0
    st.session_state.source_id = None
    populate_fields(st.session_state, empty_event())
    st.session_state.extraction_warnings = []
    st.session_state.source_label = "Manual entry; no AI result yet"

ai = load_backend("ai_extraction", "extract_event")
calendar = load_backend("calendar_export", "generate_ics")

st.title("SnapSched")
st.caption("HKU Event to Calendar · One poster. One careful review. Your next event, organised.")
with st.sidebar:
    st.subheader("Your workspace")
    mode = st.radio("Mode", ["Upload a poster", "Saved sample demo"], key="workspace_mode")
    st.button("Clear this session", on_click=reset_workspace, key="reset_workspace")
    st.divider()
    st.caption("TEAM MODULES")
    st.write("A · Interface: ready")
    st.write(f"B · AI extraction: {ai.status}")
    st.write(f"C · Calendar export: {calendar.status}")
    st.caption("Live AI key: configured" if ai_configured() else
               "Live AI key: not configured. Saved sample and manual review still work.")
    st.caption("No HKU login, mailbox connection, account system or model training.")

if mode == "Saved sample demo":
    st.warning("UI DEMO ONLY: the sample fields are saved examples, not live AI output. "
               "This alone is not the full working AI workflow for the Mid-Term Check.")

left, right = st.columns([1, 1.15], gap="large")
with left:
    st.subheader("1. Add a poster")
    st.info("Use a public poster or a team-created sample. Remove private chats, faces and "
            "student numbers. The app does not intentionally save uploads to disk.")
    content = None
    if mode == "Saved sample demo":
        source_name = "demo_poster.png"
        try:
            content = (ROOT / "samples" / source_name).read_bytes()
        except OSError:
            replace_source(st.session_state, "missing-sample")
            st.error("The sample poster is missing from this installation. Switch to Upload a poster "
                     "and use a public JPG/PNG, or ask the team to restore samples/demo_poster.png.")
            st.stop()
    else:
        uploaded = st.file_uploader("Choose one JPG or PNG", type=["jpg", "jpeg", "png"],
                                    key=f"poster_upload_{st.session_state.upload_generation}",
                                    max_upload_size=8,
                                    help="One event per image. Maximum 8 MB / 20 megapixels.")
        source_name = uploaded.name if uploaded else ""
        if uploaded is not None:
            content = uploaded.getvalue()
    source_id = sha256(mode.encode() + (content or b"")).hexdigest()
    replace_source(st.session_state, source_id)
    preview = None
    mime_type = ""
    if content is not None:
        # Keep only a per-session preview, never a shared/global upload cache.
        # This avoids decoding a large image again on every field edit.
        if st.session_state.preview_image is None and not st.session_state.image_error:
            try:
                st.session_state.preview_image, st.session_state.preview_mime_type = inspect_image(content)
            except ValueError as error:
                st.session_state.image_error = str(error)
        if st.session_state.image_error:
            st.error(st.session_state.image_error)
            st.stop()
        preview, mime_type = st.session_state.preview_image, st.session_state.preview_mime_type
        st.image(preview, caption="Original poster - compare every field with this source",
                 width="stretch")
        st.text(f"Selected image: {source_name}")
    else:
        st.caption("Your poster preview will appear here. You can also try the saved sample in the sidebar.")

    if mode == "Saved sample demo":
        st.button("Load saved sample fields", on_click=load_saved_sample, key="load_sample")
        st.caption("This copies the sample answer into the review form. It does not call any AI service.")
    else:
        st.caption("Live extraction sends the image to an external AI provider. Remove private information first.")
        consent = st.checkbox("I agree to send this image to the AI provider.", key="allow_ai")
        if st.button("Extract details with AI", key="extract_ai", type="primary",
                     disabled=not (content and consent and ai.function)):
            # A failed new extraction must never leave an old answer approved.
            populate_fields(st.session_state, empty_event())
            st.session_state.extraction_warnings = []
            st.session_state.source_label = "Extraction incomplete; enter details manually or retry"
            st.session_state.extraction_rejected = False
            try:
                with st.spinner("Reading the poster..."):
                    payload = ai.function(content, mime_type)
                    fields, warnings = normalise_event(payload)
                populate_fields(st.session_state, fields)
                st.session_state.extraction_warnings = warnings
                st.session_state.source_label = ("SAVED SAMPLE - not a live AI extraction"
                    if payload.get("mode") == "demo" else "AI draft - verify against the original")
            except ExtractionProblem as error:
                st.session_state.extraction_rejected = error.code == "no_event_found"
                st.error(str(error))
            except Exception:
                st.error("AI extraction could not finish. No result has been confirmed. "
                         "Retry, enter the fields manually, or use the labelled sample demo.")
        if not ai.function:
            st.caption("AI extraction is not connected yet. Manual review works now; the B owner "
                       "can connect the extraction module later.")

with right:
    st.subheader("2. Review and edit")
    st.caption(st.session_state.source_label)
    st.caption("All dates and times below use Asia/Hong_Kong. Check the year; do not guess hidden details.")
    for warning in st.session_state.extraction_warnings:
        st.warning("AI note - verify against the source")
        st.text(warning)  # Plain text: model notes must not embed remote Markdown images/links.
    confirmed = st.session_state.confirmed_event
    locked = bool(confirmed and st.session_state.reviewed and
                  st.session_state.approved_fingerprint == review_fingerprint(source_id, confirmed))
    if locked:
        st.success("Details locked after confirmation. Choose Edit details to make changes safely.")
        st.button("Edit details", key="edit_details", on_click=clear_confirmation)
    event_name = st.text_input("Event name", key="field_event_name", on_change=clear_confirmation,
                               disabled=locked, max_chars=FIELD_LIMITS["event_name"])
    event_date = st.text_input("Event date (YYYY-MM-DD)", placeholder="2026-11-05",
                               key="field_event_date", on_change=clear_confirmation,
                               disabled=locked, max_chars=FIELD_LIMITS["event_date"])
    all_day = st.checkbox("All-day event (only if appropriate)", key="field_all_day",
                          on_change=clear_confirmation, disabled=locked)
    time_left, time_right = st.columns(2)
    with time_left:
        start_time = st.text_input("Start time (HH:MM)", placeholder="15:00",
                                   key="field_start_time", disabled=locked or all_day,
                                   max_chars=FIELD_LIMITS["start_time"], on_change=clear_confirmation)
    with time_right:
        end_time = st.text_input("End time (HH:MM, optional)", placeholder="16:00",
                                 key="field_end_time", disabled=locked or all_day,
                                 max_chars=FIELD_LIMITS["end_time"], on_change=clear_confirmation)
    venue = st.text_input("Venue", key="field_venue", on_change=clear_confirmation,
                          disabled=locked, max_chars=FIELD_LIMITS["venue"],
                          placeholder="Keep abbreviations exactly as printed")
    registration_deadline = st.text_input("Registration deadline (YYYY-MM-DD [HH:MM], optional)",
                                          key="field_registration_deadline", on_change=clear_confirmation,
                                          disabled=locked, max_chars=FIELD_LIMITS["registration_deadline"])
    registration_method = st.text_input("Registration method / link (optional)",
                                        key="field_registration_method", on_change=clear_confirmation,
                                        disabled=locked, max_chars=FIELD_LIMITS["registration_method"],
                                        placeholder="Printed URL/email, or note that a QR code needs scanning")
    st.text_area("Registration wording (as printed, optional)", key="field_registration_text_raw",
                 disabled=locked, max_chars=FIELD_LIMITS["registration_text_raw"],
                 on_change=clear_confirmation,
                 help="Keep visible instructions from the poster; links are not opened automatically.")
    if not venue or not registration_method:
        st.warning("Venue or registration details are missing. Check the organiser's 'view details' "
                   "page or scan the original QR code. If genuinely not stated/not required, leave "
                   "the field blank and acknowledge that when confirming.")
    st.caption("A calendar entry does not register you for the event. Links are not verified or opened automatically.")
    event = {field: st.session_state["field_" + field].strip() for field in TEXT_FIELDS}
    event.update(all_day=all_day, timezone="Asia/Hong_Kong")
    if all_day:
        event["start_time"] = event["end_time"] = ""
    errors = confirmation_errors(event)
    if st.session_state.extraction_rejected:
        errors.append("No event was found in this image. Upload an event poster or retry extraction.")
    deadline_warning = registration_warning(event)
    if deadline_warning:
        st.warning(deadline_warning)
    if content and errors:
        for error in errors:
            st.caption("To confirm: " + error)
    st.caption("Before confirming, check the poster/organiser and acknowledge any information genuinely not stated.")
    reviewed = st.checkbox("I checked the poster and missing details.", key="reviewed", disabled=locked)
    if st.button("Confirm reviewed details", type="primary", key="confirm_details",
                 disabled=locked or not (content and reviewed and not errors)):
        st.session_state.confirmed_event = dict(event)
        st.session_state.approved_fingerprint = review_fingerprint(source_id, event)
        st.session_state.calendar_bytes = None
        st.rerun()  # Lock the inputs before exposing the next-step actions.

    approved = bool(content and reviewed and not errors and
                    st.session_state.approved_fingerprint == review_fingerprint(source_id, event))
    st.divider()
    st.subheader("3. Calendar export")
    if approved:
        st.success("Reviewed details confirmed. Changing a field or poster will require confirmation again.")
    else:
        st.caption("Check the source, complete the required fields and confirm before exporting.")
    if not calendar.function:
        st.info("Calendar export is not connected yet. This interface is ready for Part C; "
                "it does not generate a pretend .ics file.")
    if st.button("Create calendar file", key="create_calendar", disabled=not (approved and calendar.function)):
        st.session_state.calendar_bytes = None
        try:
            st.session_state.calendar_bytes = calendar_file_bytes(calendar.function(dict(st.session_state.confirmed_event)))
        except Exception:
            st.error("The calendar file could not be created. Nothing has been added to your calendar. "
                     "Check the details and ask the team to check the calendar module.")
    output = st.session_state.calendar_bytes if approved else None
    st.download_button("Download .ics", data=output or b"", file_name="snapsched-event.ics",
                       mime="text/calendar", disabled=not bool(output), key="download_calendar")

st.divider()
st.caption("SnapSched · Public/team-created posters only · Human confirmation required · "
           "No automatic registration or account access")

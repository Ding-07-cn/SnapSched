from __future__ import annotations

import io
from pathlib import Path

import streamlit as st
from PIL import Image

from integrations import calendar_file_bytes, load_backend
from review_logic import (
    FIELD_LABELS,
    REQUIRED_PATHS,
    ensure_standard_event,
    find_missing_required_fields,
    get_by_path,
    parse_hk_datetime,
    review_fingerprint,
    save_event_json,
    set_by_path,
    source_id_from_bytes,
)

st.set_page_config(page_title="Event Review", page_icon="📌", layout="wide")
st.title("Event Review Interface")

# Plugin loading (dynamic import)
ai_backend = load_backend("ai_extraction", "extract_event")
calendar_backend = load_backend("calendar_export", "generate_ics")

# Session initialization
defaults = {
    "event_data": ensure_standard_event({}),
    "saved_path": None,
    "confirmed_event": None,
    "last_fingerprint": None,
    "calendar_bytes": None,
    "source_label": "Manual entry; no AI result yet",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

left, right = st.columns([1, 1.2], gap="large")

with left:
    st.subheader("1) Original poster")
    upload = st.file_uploader("Upload poster image (JPG/PNG)", type=["jpg", "jpeg", "png"])
    image_bytes = upload.getvalue() if upload else None
    source_name = upload.name if upload else "no-image"

    mime_type = ""
    if upload is not None:
        ext = Path(upload.name).suffix.lower()
        mime_type = "image/png" if ext == ".png" else "image/jpeg"

    if image_bytes:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            st.image(image, caption="Original uploaded poster", use_container_width=True)
        except Exception:
            st.error("Cannot open this image. Please upload a valid JPG/PNG.")
            st.stop()
    else:
        st.info("Please upload an original poster image for side-by-side verification.")

    st.caption(f"AI extraction backend: {ai_backend.status}")
    if st.button("Extract details with AI", disabled=not (image_bytes and ai_backend.function)):
        try:
            payload = ai_backend.function(image_bytes, mime_type)  # dict
            st.session_state.event_data = ensure_standard_event(payload)
            st.session_state.source_label = "AI draft - verify against the original"
            st.session_state.confirmed_event = None
            st.session_state.calendar_bytes = None
            st.success("AI data loaded. Please verify and edit on the right panel.")
        except Exception as e:
            st.error(f"AI extraction failed: {e}")

with right:
    st.subheader("2) Review and edit")
    st.info("Please verify whether all extracted information is accurate and complete.")
    st.caption(st.session_state.source_label)

    # 表单渲染（None -> 空字符串）
    for path in REQUIRED_PATHS:
        current = get_by_path(st.session_state.event_data, path)
        label = FIELD_LABELS[path]
        value = "" if current is None else str(current)
        new_text = st.text_input(label, value=value, key=f"input_{path}")
        set_by_path(
            st.session_state.event_data,
            path,
            new_text.strip() if new_text.strip() else None
        )

    # Submit（save，then check None）
    submit_col_left, submit_col_right = st.columns([4, 1])
    with submit_col_right:
        submit_clicked = st.button("Submit", type="primary", use_container_width=True)

    if submit_clicked:
        sid = source_id_from_bytes(source_name, image_bytes)

        # 1) save
        saved = save_event_json(st.session_state.event_data, sid)
        st.session_state.saved_path = str(saved)

        # 2) check missing 
        missing = find_missing_required_fields(st.session_state.event_data)
        if missing:
            readable = [FIELD_LABELS[p] for p in missing]
            st.warning(
                "Some required information is still missing. "
                "Please complete all required fields before continuing."
            )
            st.write("Missing fields:")
            for x in readable:
                st.write(f"- {x}")
        else:
            st.success("Information saved successfully.")
            st.session_state.confirmed_event = dict(st.session_state.event_data)
            st.session_state.last_fingerprint = review_fingerprint(sid, st.session_state.confirmed_event)
            st.session_state.calendar_bytes = None

    if st.session_state.saved_path:
        st.caption(f"Last saved file: {st.session_state.saved_path}")

    # Time format
    bad_time_fields = []
    for p in ["start_dt", "end_dt", "reg_deadline_dt"]:
        v = get_by_path(st.session_state.event_data, p)
        if v is not None and parse_hk_datetime(v) is None:
            bad_time_fields.append(FIELD_LABELS[p])
    if bad_time_fields:
        st.caption("Format reminder (not blocking in this step):")
        for f in bad_time_fields:
            st.caption(f"- {f} should follow YYYY-MM-DD HH:MM")

    # Preview + ICS export
    st.divider()
    st.subheader("3) Schedule output")

    if st.session_state.confirmed_event is None:
        st.caption("Please submit complete information first.")
    else:
        event = st.session_state.confirmed_event
        st.write("Confirmed event preview:")
        st.table({
            "Name": [event.get("name")],
            "DateTime": [f"{event.get('start_dt')} ~ {event.get('end_dt')}"],
            "Venue": [event.get("venue")],
            "Registration Deadline": [event.get("reg_deadline_dt")],
            "Registration Method": [f"{event.get('reg_method', {}).get('type')} / {event.get('reg_method', {}).get('value')}"],
        })

        st.caption(f"Calendar export backend: {calendar_backend.status}")

        if not calendar_backend.function:
            st.warning("calendar_export.generate_ics is not connected yet.")
        else:
            if st.button("Create .ics file", type="secondary"):
                try:
                    raw_ics = calendar_backend.function(dict(st.session_state.confirmed_event))
                    st.session_state.calendar_bytes = calendar_file_bytes(raw_ics)
                    st.success("ICS file created.")
                except Exception as e:
                    st.session_state.calendar_bytes = None
                    st.error(f"Failed to create ICS file: {e}")

            st.download_button(
                "Download .ics",
                data=st.session_state.calendar_bytes or b"",
                file_name="event.ics",
                mime="text/calendar",
                disabled=not bool(st.session_state.calendar_bytes),
            )

st.divider()
st.caption("Workflow scope: receive AI dict -> user review/edit -> submit check -> schedule preview -> export .ics")

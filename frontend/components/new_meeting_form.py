"""
MeetMind AI — New Meeting Form Component.

Provides a form-first interface for submitting meeting metadata and transcripts.
Supports 3 input formats:
  1. Direct text pasting
  2. TXT file upload
  3. PDF file upload (parsed via pypdf)

Coordinates with the backend:
  - Registers the submitting user if not already registered (POST /api/v1/users/register)
  - Creates the meeting entity and submitter participant (POST /api/v1/meetings/)
"""

from datetime import date, datetime
import io
import re
from typing import Callable, Optional
import pypdf
import streamlit as st

from services.api_client import APIError, api


EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts text content from a PDF file buffer."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n\n".join(text_parts).strip()


def render_new_meeting_form(on_success: Optional[Callable[[dict], None]] = None) -> None:
    """
    Renders the meeting creation form with full metadata and multi-format transcript upload.

    Args:
        on_success: Optional callback invoked with the created meeting payload.
    """
    st.markdown(
        """
        <div class="meetmind-card" style="margin-bottom:1.25rem;">
            <div style="font-weight:700; color:#FFFFFE; font-size:1.15rem; margin-bottom:0.25rem;">
                ➕ Create New Meeting
            </div>
            <div style="color:#94A3B8; font-size:0.85rem;">
                Fill in the meeting context and submit your transcript. MeetMind will ingest, identify participants, and extract action items.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("new_meeting_form", clear_on_submit=False):
        st.markdown("##### 👤 Submitter Identity")
        col_u1, col_u2, col_u3 = st.columns(3)
        with col_u1:
            user_name = st.text_input(
                "Your Name *",
                value=st.session_state.get("user_name", ""),
                placeholder="e.g. Alex Rivera",
                help="Your full display name in the transcript",
            )
        with col_u2:
            user_email = st.text_input(
                "Your Email *",
                value=st.session_state.get("user_email", ""),
                placeholder="e.g. alex@example.com",
                help="Unique identifier used for your workspace profile",
            )
        with col_u3:
            user_role = st.text_input(
                "Your Role / Title",
                value="Product Lead",
                placeholder="e.g. Tech Lead, PM, Designer",
                help="Your role in this meeting",
            )

        st.markdown("##### 📋 Meeting Information")
        col_m1, col_m2, col_m3, col_m4 = st.columns([2, 1.5, 1, 1])
        with col_m1:
            meeting_title = st.text_input(
                "Meeting Title (Optional)",
                placeholder="e.g. Q3 Sprint Planning (or leave blank to auto-detect)",
            )
        with col_m2:
            organization = st.text_input(
                "Organization / Team",
                value="Engineering",
                placeholder="e.g. Engineering, Sales, Product",
            )
        with col_m3:
            meeting_date = st.date_input("Date *", value=date.today())
        with col_m4:
            meeting_time = st.text_input(
                "Time",
                value="10:00",
                placeholder="HH:MM",
                help="24-hour format e.g. 14:30",
            )

        st.markdown("##### 📝 Meeting Transcript")
        input_mode = st.radio(
            "Submission Method",
            ["Paste Text", "Upload TXT", "Upload PDF"],
            horizontal=True,
        )

        transcript_text = ""
        input_format = "text"

        if input_mode == "Paste Text":
            transcript_text = st.text_area(
                "Transcript Content *",
                height=220,
                placeholder="Alex Rivera: Let's discuss the Q3 roadmap...\nSarah Chen: The backend APIs are frozen.",
                help="Paste the speaker-attributed dialogue transcript here.",
            )
            input_format = "text"

        elif input_mode == "Upload TXT":
            uploaded_file = st.file_uploader("Choose a plain text (.txt) file", type=["txt"])
            if uploaded_file is not None:
                try:
                    transcript_text = uploaded_file.getvalue().decode("utf-8")
                    st.success(f"Loaded {uploaded_file.name} ({len(transcript_text):,} characters)")
                except Exception as exc:
                    st.error(f"Failed to read text file: {exc}")
            input_format = "txt"

        elif input_mode == "Upload PDF":
            uploaded_pdf = st.file_uploader("Choose a PDF document (.pdf)", type=["pdf"])
            if uploaded_pdf is not None:
                try:
                    transcript_text = extract_text_from_pdf(uploaded_pdf.getvalue())
                    if transcript_text:
                        st.success(f"Parsed {uploaded_pdf.name} ({len(transcript_text):,} characters extracted)")
                    else:
                        st.warning("No readable text found in PDF. Ensure the PDF contains text rather than scanned images.")
                except Exception as exc:
                    st.error(f"Failed to parse PDF document: {exc}")
            input_format = "pdf"

        # Action Buttons
        col_submit, col_cancel = st.columns([1, 4])
        with col_submit:
            submitted = st.form_submit_button("🚀 Submit Meeting", type="primary", use_container_width=True)

    if submitted:
        # ── Form Validation ──────────────────────────────────────────────
        errors = []
        if not user_name.strip():
            errors.append("Submitter name is required.")
        if not user_email.strip() or not re.match(EMAIL_REGEX, user_email.strip()):
            errors.append("A valid submitter email address is required.")
        if not transcript_text.strip() or len(transcript_text.strip()) < 10:
            errors.append("A valid transcript with at least 10 characters is required.")

        if errors:
            for err in errors:
                st.error(f"⚠️ {err}")
            return

        with st.spinner("Processing user profile and creating meeting..."):
            try:
                # ── 1. Ensure User Registration ──────────────────────────
                user_id = st.session_state.get("user_id")
                cached_email = st.session_state.get("user_email")

                if not user_id or cached_email != user_email.strip():
                    try:
                        reg_resp = api.post(
                            "/users/register",
                            json={"name": user_name.strip(), "email": user_email.strip()},
                        )
                        user_id = reg_resp.get("id")
                    except APIError as api_err:
                        # If user with email already exists in DB (status 409),
                        # reuse existing user_id if already set, or report cleanly
                        if api_err.status_code == 409 and user_id:
                            pass
                        else:
                            st.warning(f"Note: {api_err.message}")

                # Update session state with identity
                if user_id:
                    st.session_state["user_id"] = user_id
                st.session_state["user_name"] = user_name.strip()
                st.session_state["user_email"] = user_email.strip()

                if not user_id:
                    st.error("Could not obtain a valid user identifier. Please check backend connection.")
                    return

                # ── 2. Create Meeting Entity ─────────────────────────────
                meeting_payload = {
                    "user_id": user_id,
                    "title": meeting_title.strip() if meeting_title.strip() else None,
                    "organization": organization.strip() if organization.strip() else None,
                    "meeting_date": str(meeting_date),
                    "meeting_time": meeting_time.strip() if meeting_time.strip() else None,
                    "input_format": input_format,
                    "raw_transcript": transcript_text.strip(),
                }

                params = {
                    "submitter_name": user_name.strip(),
                    "submitter_role": user_role.strip() if user_role.strip() else None,
                }

                created_meeting = api.post("/meetings/", json=meeting_payload, params=params)

                meeting_id = created_meeting.get("id")
                st.session_state["active_meeting_id"] = meeting_id
                st.session_state["show_new_meeting_form"] = False

                st.success(f"✅ Meeting '{created_meeting.get('title')}' created successfully!")

                if on_success:
                    on_success(created_meeting)

                st.rerun()

            except APIError as exc:
                st.error(f"❌ Failed to create meeting: {exc.message}")
                if exc.details:
                    st.caption(f"Details: {exc.details}")
            except Exception as exc:
                st.error(f"❌ Unexpected error creating meeting: {exc}")

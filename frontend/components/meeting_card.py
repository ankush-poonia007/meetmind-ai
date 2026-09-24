"""
MeetMind AI — Meeting Card Component.

Renders an individual meeting item in the workspace meeting list,
with metadata, status badges, and action triggers (view details, run extraction, delete).
"""

from typing import Any, Callable, Optional
import streamlit as st

from services.api_client import APIError, api


def render_meeting_card(
    meeting: dict[str, Any],
    on_select: Optional[Callable[[str], None]] = None,
    on_delete: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Renders a meeting card with metadata and action buttons.

    Args:
        meeting: Meeting dictionary payload from API.
        on_select: Callback when user opens the meeting detail / Q&A.
        on_delete: Callback when user deletes the meeting.
    """
    meeting_id = str(meeting.get("id"))
    title = meeting.get("title") or "Untitled Meeting"
    org = meeting.get("organization") or "General"
    m_date = meeting.get("meeting_date") or "N/A"
    m_time = meeting.get("meeting_time") or ""
    fmt = (meeting.get("input_format") or "text").upper()

    date_display = f"{m_date} · {m_time}" if m_time else str(m_date)

    st.markdown(
        f"""
        <div class="meetmind-card" style="margin-bottom:0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.4rem;">
                <div>
                    <span style="font-weight:700; color:#FFFFFE; font-size:1.05rem;">{title}</span>
                    <span class="badge badge-medium" style="margin-left:8px; font-size:0.7rem;">{fmt}</span>
                </div>
                <div style="color:#94A3B8; font-size:0.8rem; font-weight:500;">
                    🏢 {org}
                </div>
            </div>
            <div style="color:#64748B; font-size:0.8rem; margin-bottom:0.5rem;">
                📅 {date_display}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_view, col_extract, col_delete, col_spacer = st.columns([1.2, 1.2, 0.8, 2])
    with col_view:
        if st.button("🔍 Open Workspace", key=f"btn_view_{meeting_id}", use_container_width=True):
            st.session_state["active_meeting_id"] = meeting_id
            if on_select:
                on_select(meeting_id)
            st.rerun()

    with col_extract:
        if st.button("⚡ Extract Tasks", key=f"btn_extract_{meeting_id}", use_container_width=True):
            st.session_state["active_meeting_id"] = meeting_id
            st.session_state["trigger_extraction"] = meeting_id
            st.rerun()

    with col_delete:
        if st.button("🗑️ Delete", key=f"btn_del_{meeting_id}", use_container_width=True):
            try:
                api.delete(f"/meetings/{meeting_id}")
                st.success("Meeting deleted.")
                if st.session_state.get("active_meeting_id") == meeting_id:
                    st.session_state["active_meeting_id"] = None
                if on_delete:
                    on_delete(meeting_id)
                st.rerun()
            except APIError as exc:
                st.error(f"Failed to delete meeting: {exc.message}")

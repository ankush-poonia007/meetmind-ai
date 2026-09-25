"""
MeetMind AI — Workspace Page.

Orchestrates the 3 core workspace tabs:
  1. 📊 Dashboard: Summary metrics, meeting count, task stats, and quick overview.
  2. 📋 Meetings: Meeting list, creation form, meeting detail view,
                 identity resolution, task extraction preview, HITL confirmation,
                 and meeting-scoped Q&A chat.
  3. 🎯 Tasks: Unified cross-meeting task list with status toggle and multi-parameter filters.
"""

from typing import Any, Optional
from uuid import UUID
import streamlit as st

from components.chat_bubble import render_meeting_chat
from components.highlight_card import render_highlight_card
from components.layout import render_footer, render_page_header, render_section_divider
from components.meeting_card import render_meeting_card
from components.new_meeting_form import render_new_meeting_form
from components.state_displays import render_empty_state
from components.task_card import render_task_card
from components.task_filter import render_task_filter
from services.api_client import APIError, api


# ── Helper: Safe Data Fetchers ───────────────────────────────────────────────

def _fetch_user_meetings(user_id: str) -> list[dict[str, Any]]:
    """Fetches meetings belonging to the user."""
    try:
        data = api.get(f"/meetings/{user_id}")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _fetch_user_tasks(user_id: str, filter_params: Optional[dict] = None) -> list[dict[str, Any]]:
    """Fetches user tasks, optionally filtered."""
    try:
        if filter_params:
            data = api.get(f"/tasks/{user_id}/filter", params=filter_params)
        else:
            data = api.get(f"/tasks/{user_id}")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _fetch_meeting_detail(meeting_id: str) -> Optional[dict[str, Any]]:
    """Fetches full meeting detail including detected participants."""
    try:
        return api.get(f"/meetings/{meeting_id}/detail")
    except Exception:
        return None


def _fetch_meeting_tasks(user_id: str, meeting_id: str) -> list[dict[str, Any]]:
    """Fetches confirmed tasks for a specific meeting."""
    try:
        data = api.get(f"/tasks/{user_id}/meeting/{meeting_id}")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _fetch_meeting_highlights(user_id: str, meeting_id: str) -> list[dict[str, Any]]:
    """Fetches confirmed highlights for a specific meeting."""
    try:
        data = api.get(f"/highlights/{user_id}/meeting/{meeting_id}")
        if isinstance(data, dict):
            return data.get("highlights", [])
        return []
    except Exception:
        return []


# ── 1. Dashboard Tab ─────────────────────────────────────────────────────────

def _render_dashboard_tab() -> None:
    """Renders high-level metrics and recent activity overview."""
    user_id = st.session_state.get("user_id")

    meetings = _fetch_user_meetings(user_id) if user_id else []
    tasks = _fetch_user_tasks(user_id) if user_id else []

    pending_tasks = [t for t in tasks if t.get("status") == "pending"]
    completed_tasks = [t for t in tasks if t.get("status") == "complete"]

    # Calculate highlights across meetings
    total_highlights_count = 0
    if user_id and meetings:
        for m in meetings:
            hl = _fetch_meeting_highlights(user_id, str(m.get("id")))
            total_highlights_count += len(hl)

    # ── Summary Stats ────────────────────────────────────────────────────
    stat_cols = st.columns(4)
    stats = [
        (str(len(meetings)), "Meetings", "📋"),
        (str(len(pending_tasks)), "Active Tasks", "🎯"),
        (str(len(completed_tasks)), "Completed", "✅"),
        (str(total_highlights_count), "Highlights", "💡"),
    ]

    for col, (value, label, icon) in zip(stat_cols, stats):
        with col:
            st.markdown(
                f"""
                <div class="stat-card">
                    <div style="font-size:1.25rem; margin-bottom:0.25rem;">{icon}</div>
                    <div class="stat-value">{value}</div>
                    <div class="stat-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_section_divider()

    # ── Recent Activity / Quick Actions ──────────────────────────────────
    st.markdown('<div class="section-header">📌 Recent Activity</div>', unsafe_allow_html=True)

    if not meetings:
        render_empty_state(
            icon="🏠",
            title="Welcome to MeetMind",
            description="Submit your first meeting transcript to see your personalized dashboard populate with tasks, highlights, and actionable insights.",
        )
        col_c1, col_c2, col_c3 = st.columns([1.5, 1, 1.5])
        with col_c2:
            if st.button("➕ Create Meeting Now", type="primary", use_container_width=True):
                st.session_state["show_new_meeting_form"] = True
                st.session_state["workspace_tab"] = "meetings"
                st.rerun()
    else:
        st.markdown(f"Showing overview for **{len(meetings)} meeting(s)** and **{len(tasks)} task(s)**.")
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("##### 📋 Recent Meetings")
            for m in meetings[:3]:
                st.markdown(
                    f"""
                    <div style="background:rgba(26,26,46,0.6); border:1px solid rgba(108,92,231,0.15); border-radius:10px; padding:0.6rem 0.85rem; margin-bottom:0.4rem;">
                        <div style="font-weight:600; color:#FFFFFE;">{m.get('title')}</div>
                        <div style="font-size:0.75rem; color:#94A3B8;">📅 {m.get('meeting_date')} · 🏢 {m.get('organization') or 'General'}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with c_right:
            st.markdown("##### 🎯 Active Tasks")
            if pending_tasks:
                for t in pending_tasks[:3]:
                    st.markdown(
                        f"""
                        <div style="background:rgba(26,26,46,0.6); border:1px solid rgba(108,92,231,0.15); border-radius:10px; padding:0.6rem 0.85rem; margin-bottom:0.4rem;">
                            <div style="font-weight:600; color:#FFFFFE;">{t.get('title')}</div>
                            <div style="font-size:0.75rem; color:#FDCB6E;">⏳ Due: {t.get('deadline') or 'None'} · Priority: {(t.get('priority') or 'medium').upper()}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No pending tasks. You are all caught up!")


# ── 2. Meeting Detail & Extraction Sub-View ──────────────────────────────────

def _render_meeting_detail_view(meeting_id: str, user_id: str) -> None:
    """Renders complete meeting detail: metadata, identity, HITL extraction, highlights, tasks, and Q&A."""
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("⬅️ All Meetings", use_container_width=True):
            st.session_state["active_meeting_id"] = None
            st.rerun()

    meeting = _fetch_meeting_detail(meeting_id)
    if not meeting:
        st.error("Failed to load meeting details.")
        return

    title = meeting.get("title") or "Meeting Details"
    org = meeting.get("organization") or "General"
    m_date = meeting.get("meeting_date") or ""
    m_time = meeting.get("meeting_time") or ""
    participants = meeting.get("participants", [])

    st.markdown(
        f"""
        <div class="meetmind-card" style="margin-top:0.5rem; margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <div style="font-size:1.4rem; font-weight:800; color:#FFFFFE; margin-bottom:0.25rem;">{title}</div>
                    <div style="color:#94A3B8; font-size:0.85rem;">📅 {m_date} {m_time} · 🏢 {org}</div>
                </div>
                <div>
                    <span class="badge badge-medium">{(meeting.get('input_format') or 'text').upper()}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Identity Resolution & Detected Participants ───────────────────────
    st.markdown('<div class="section-header" style="font-size:1.1rem;">👥 Detected Meeting Participants</div>', unsafe_allow_html=True)
    if participants:
        p_cols = st.columns(min(len(participants), 4))
        for idx, p in enumerate(participants):
            with p_cols[idx % 4]:
                is_you = p.get("is_current_user", False)
                card_border = "border:1px solid #00B894;" if is_you else "border:1px solid rgba(108,92,231,0.15);"
                st.markdown(
                    f"""
                    <div style="background:rgba(26,26,46,0.8); {card_border} border-radius:10px; padding:0.6rem 0.8rem; margin-bottom:0.5rem;">
                        <div style="font-weight:700; color:#FFFFFE; font-size:0.85rem;">{p.get('name')}</div>
                        <div style="font-size:0.75rem; color:#94A3B8;">{p.get('role') or 'Participant'}</div>
                        {f'<span class="badge badge-complete" style="font-size:0.65rem; margin-top:4px;">YOU (IDENTIFIED)</span>' if is_you else ''}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.caption("No participants detected yet.")

    render_section_divider()

    # ── Human-in-the-Loop Extraction & Confirmation ───────────────────────
    st.markdown('<div class="section-header" style="font-size:1.1rem;">⚡ Task Extraction & Human Confirmation</div>', unsafe_allow_html=True)

    # Check if we should trigger extraction or if preview is available
    preview_key = f"preview_{meeting_id}"
    auto_trigger = st.session_state.pop("trigger_extraction", None) == meeting_id

    col_btn_extract, col_extract_info = st.columns([1.5, 3])
    with col_btn_extract:
        run_extract = st.button("🚀 Run Multi-Agent Extraction", type="primary", use_container_width=True, key=f"run_ext_{meeting_id}")

    if run_extract or auto_trigger:
        with st.spinner("Multi-agent pipeline running: Ingesting → Identifying User → Extracting Tasks & Highlights..."):
            try:
                run_res = api.post(
                    f"/extraction/{meeting_id}/run",
                    json={"meeting_id": meeting_id, "user_id": user_id},
                )
                st.session_state[preview_key] = run_res
                st.success("Extraction complete! Review extracted items below for confirmation.")
            except APIError as exc:
                st.error(f"Extraction failed: {exc.message}")

    # Fetch preview if not cached
    if preview_key not in st.session_state:
        try:
            prev = api.get(f"/extraction/{meeting_id}/preview", params={"user_id": user_id})
            if prev and prev.get("task_count", 0) > 0:
                st.session_state[preview_key] = prev
        except Exception:
            pass

    preview = st.session_state.get(preview_key)
    if preview and preview.get("tasks"):
        st.info("Human-in-the-Loop Review: Confirm which tasks should be saved to your dashboard.")
        extracted_tasks = preview.get("tasks", [])
        extracted_highlights = preview.get("highlights", [])

        st.markdown(f"**Found {len(extracted_tasks)} Task(s) for your role:**")

        selected_tasks = []
        for idx, t in enumerate(extracted_tasks):
            t_title = t.get("title", f"Task {idx+1}")
            t_desc = t.get("description", "")
            t_prio = (t.get("priority") or "medium").upper()
            t_due = t.get("deadline") or "None"

            chk = st.checkbox(
                f"**{t_title}** [{t_prio}] · Due: {t_due}",
                value=True,
                key=f"chk_task_{meeting_id}_{idx}",
            )
            if t_desc:
                st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;{t_desc}")

            if chk:
                selected_tasks.append(t_title)

        st.markdown("")
        col_c_yes, col_c_partial, col_c_no = st.columns(3)
        with col_c_yes:
            if st.button("✅ Accept All Tasks", type="primary", use_container_width=True, key=f"conf_yes_{meeting_id}"):
                with st.spinner("Committing all tasks..."):
                    try:
                        res = api.post(
                            f"/extraction/{meeting_id}/confirm",
                            json={
                                "meeting_id": meeting_id,
                                "user_id": user_id,
                                "user_confirmation": "yes",
                                "confirmed_task_ids": [],
                            },
                        )
                        st.success(f"Confirmed: {res.get('saved_tasks')} tasks saved to database!")
                        st.session_state.pop(preview_key, None)
                        st.rerun()
                    except APIError as exc:
                        st.error(f"Confirmation error: {exc.message}")

        with col_c_partial:
            if st.button("☑️ Confirm Selected", use_container_width=True, key=f"conf_part_{meeting_id}"):
                if not selected_tasks:
                    st.warning("Please check at least one task or choose 'Reject All'.")
                else:
                    with st.spinner("Committing selected tasks..."):
                        try:
                            res = api.post(
                                f"/extraction/{meeting_id}/confirm",
                                json={
                                    "meeting_id": meeting_id,
                                    "user_id": user_id,
                                    "user_confirmation": "partial",
                                    "confirmed_task_ids": selected_tasks,
                                },
                            )
                            st.success(f"Saved {res.get('saved_tasks')} selected task(s) to database!")
                            st.session_state.pop(preview_key, None)
                            st.rerun()
                        except APIError as exc:
                            st.error(f"Confirmation error: {exc.message}")

        with col_c_no:
            if st.button("❌ Reject All", use_container_width=True, key=f"conf_no_{meeting_id}"):
                with st.spinner("Discarding extracted tasks..."):
                    try:
                        res = api.post(
                            f"/extraction/{meeting_id}/confirm",
                            json={
                                "meeting_id": meeting_id,
                                "user_id": user_id,
                                "user_confirmation": "no",
                                "confirmed_task_ids": [],
                            },
                        )
                        st.warning("Extracted tasks discarded.")
                        st.session_state.pop(preview_key, None)
                        st.rerun()
                    except APIError as exc:
                        st.error(f"Confirmation error: {exc.message}")

    render_section_divider()

    # ── Meeting Highlights & Confirmed Tasks ──────────────────────────────
    c_hl, c_tk = st.columns(2)
    with c_hl:
        st.markdown('<div class="section-header" style="font-size:1.1rem;">💡 Meeting Highlights</div>', unsafe_allow_html=True)
        highlights = _fetch_meeting_highlights(user_id, meeting_id)
        if highlights:
            for h in highlights:
                render_highlight_card(h)
        else:
            st.caption("No confirmed highlights yet. Run extraction to generate highlights.")

    with c_tk:
        st.markdown('<div class="section-header" style="font-size:1.1rem;">🎯 Meeting Tasks</div>', unsafe_allow_html=True)
        tasks = _fetch_meeting_tasks(user_id, meeting_id)
        if tasks:
            for idx, t in enumerate(tasks):
                render_task_card(t, key_prefix=f"meeting_{meeting_id}", index=idx)
        else:
            st.caption("No confirmed tasks for this meeting yet.")

    render_section_divider()

    # ── Meeting-Scoped Q&A Chat ───────────────────────────────────────────
    render_meeting_chat(meeting_id=meeting_id, user_id=user_id)


# ── 3. Meetings Tab ──────────────────────────────────────────────────────────

def _render_meetings_tab() -> None:
    """Renders the meetings list, creation form trigger, and meeting detail view."""
    user_id = st.session_state.get("user_id")

    # If an active meeting is selected, render its full dashboard
    active_meeting_id = st.session_state.get("active_meeting_id")
    if active_meeting_id and user_id:
        _render_meeting_detail_view(meeting_id=active_meeting_id, user_id=user_id)
        return

    # Action Row
    action_col, spacer_col = st.columns([1.2, 3])
    with action_col:
        show_form = st.session_state.get("show_new_meeting_form", False)
        btn_label = "✖️ Close Form" if show_form else "➕ New Meeting"
        if st.button(btn_label, use_container_width=True, type="primary"):
            st.session_state["show_new_meeting_form"] = not show_form
            st.rerun()

    # Render Meeting Creation Form if toggled
    if st.session_state.get("show_new_meeting_form", False):
        render_new_meeting_form()

    render_section_divider()

    # ── Meeting List ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📋 Your Meetings</div>', unsafe_allow_html=True)

    if not user_id:
        render_empty_state(
            icon="📝",
            title="No meetings found",
            description="Create your first meeting above to register your user profile and ingest meeting transcripts.",
        )
        return

    meetings = _fetch_user_meetings(user_id)
    if not meetings:
        render_empty_state(
            icon="📝",
            title="No meetings yet",
            description="Click '➕ New Meeting' above to submit your first transcript (PDF, TXT, or pasted text).",
        )
    else:
        for meeting in meetings:
            render_meeting_card(
                meeting=meeting,
                on_select=lambda mid: st.session_state.update({"active_meeting_id": mid}),
            )


# ── 4. Tasks Tab (Unified Task Dashboard) ────────────────────────────────────

def _render_tasks_tab() -> None:
    """Renders the unified cross-meeting task dashboard with interactive filters."""
    user_id = st.session_state.get("user_id")

    if not user_id:
        render_empty_state(
            icon="✨",
            title="No tasks yet",
            description="Create a meeting and confirm extracted tasks to populate your unified task dashboard.",
        )
        return

    # Filter Controls
    filters = render_task_filter()

    render_section_divider()

    # Fetch tasks
    tasks = _fetch_user_tasks(user_id, filter_params=filters)

    st.markdown(
        f'<div class="section-header">🎯 Confirmed Tasks ({len(tasks)})</div>',
        unsafe_allow_html=True,
    )

    if not tasks:
        render_empty_state(
            icon="🔍",
            title="No tasks found",
            description="No tasks match the active filter criteria. Try adjusting the status or priority filters.",
        )
    else:
        for idx, task in enumerate(tasks):
            render_task_card(task, key_prefix="tasks_tab", index=idx)


# ── Page Dispatcher ──────────────────────────────────────────────────────────

def render_workspace_page() -> None:
    """Renders the workspace page with tabbed sub-navigation."""
    render_page_header(
        "Workspace",
        subtitle="Manage meetings, monitor task progress, and review action items",
        icon="💼",
    )

    tab_keys = ["📊  Dashboard", "📋  Meetings", "🎯  Tasks"]
    tab_dashboard, tab_meetings, tab_tasks = st.tabs(tab_keys)

    with tab_dashboard:
        _render_dashboard_tab()

    with tab_meetings:
        _render_meetings_tab()

    with tab_tasks:
        _render_tasks_tab()

    render_footer()

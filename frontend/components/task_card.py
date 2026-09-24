"""
MeetMind AI — Task Card Component.

Renders an individual task with priority badge, status indicator,
deadline, description, and an inline status toggle button.
"""

from typing import Any, Callable, Optional
import streamlit as st

from services.api_client import APIError, api


def render_task_card(
    task: dict[str, Any],
    on_status_change: Optional[Callable[[str, str], None]] = None,
) -> None:
    """
    Renders a task item with interactive status toggle.

    Args:
        task: Task data dictionary from API.
        on_status_change: Optional callback when task status toggles.
    """
    task_id = str(task.get("id"))
    title = task.get("title", "Untitled Task")
    description = task.get("description") or ""
    priority = (task.get("priority") or "medium").lower()
    status = (task.get("status") or "pending").lower()
    deadline = task.get("deadline") or "No deadline set"

    is_complete = status == "complete"

    # Status badge style
    badge_class = f"badge-{priority}"
    status_label = "✅ Complete" if is_complete else "⏳ Pending"
    status_badge_class = "badge-complete" if is_complete else "badge-pending"

    title_style = "text-decoration: line-through; color: #64748B;" if is_complete else "color: #FFFFFE;"

    st.markdown(
        f"""
        <div class="meetmind-card" style="margin-bottom:0.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.4rem;">
                <div style="flex:1;">
                    <span style="font-weight:700; font-size:1rem; {title_style}">{title}</span>
                </div>
                <div style="display:flex; gap:6px;">
                    <span class="badge {badge_class}">{priority.upper()}</span>
                    <span class="badge {status_badge_class}">{status_label}</span>
                </div>
            </div>
            {f'<div style="color:#94A3B8; font-size:0.85rem; margin-bottom:0.4rem; line-height:1.45;">{description}</div>' if description else ''}
            <div style="display:flex; justify-content:space-between; align-items:center; color:#64748B; font-size:0.78rem;">
                <span>📅 Deadline: {deadline}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_btn, col_spacer = st.columns([1.5, 3.5])
    with col_btn:
        toggle_label = "↩️ Mark Pending" if is_complete else "✅ Mark Complete"
        new_status = "pending" if is_complete else "complete"

        if st.button(toggle_label, key=f"toggle_task_{task_id}", use_container_width=True):
            try:
                api.put(f"/tasks/{task_id}/status", json={"status": new_status})
                st.success(f"Task marked as {new_status}.")
                if on_status_change:
                    on_status_change(task_id, new_status)
                st.rerun()
            except APIError as exc:
                st.error(f"Failed to update task: {exc.message}")

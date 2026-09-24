"""
MeetMind AI — Task Filter Component.

Provides interactive filtering controls for the unified task dashboard:
  - Status (All, Pending, Complete)
  - Priority (All, High, Medium, Low)
  - Deadline window (Due After, Due Before)
"""

from datetime import date
from typing import Any, Optional
import streamlit as st


def render_task_filter() -> dict[str, Any]:
    """
    Renders filter controls and returns dictionary of active filter criteria.

    Returns:
        dict containing 'status', 'priority', 'deadline_after', 'deadline_before'
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_option = st.selectbox(
            "Status",
            ["All", "Pending", "Complete"],
            index=0,
            key="filter_status",
        )

    with col2:
        priority_option = st.selectbox(
            "Priority",
            ["All", "High", "Medium", "Low"],
            index=0,
            key="filter_priority",
        )

    with col3:
        due_after = st.date_input(
            "Due After",
            value=None,
            key="filter_due_after",
        )

    with col4:
        due_before = st.date_input(
            "Due Before",
            value=None,
            key="filter_due_before",
        )

    filters: dict[str, Any] = {}

    if status_option != "All":
        filters["status"] = status_option.lower()

    if priority_option != "All":
        filters["priority"] = priority_option.lower()

    if due_after is not None:
        filters["deadline_after"] = str(due_after)

    if due_before is not None:
        filters["deadline_before"] = str(due_before)

    return filters

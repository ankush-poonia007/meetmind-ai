"""
MeetMind AI — State Display Components.

Provides reusable loading, error, and empty-state presentation
for consistent UX across all pages.
"""

import streamlit as st


def render_loading_state(message: str = "Loading...") -> None:
    """Renders a centered loading indicator with a message."""
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-icon">⏳</div>
            <div class="empty-state-title">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(
    icon: str = "📭",
    title: str = "Nothing here yet",
    description: str = "",
) -> None:
    """
    Renders a styled empty-state placeholder.

    Args:
        icon: Large emoji icon.
        title: Short heading.
        description: Supporting description text.
    """
    desc_html = f'<div class="empty-state-desc">{description}</div>' if description else ""
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-icon">{icon}</div>
            <div class="empty-state-title">{title}</div>
            {desc_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_error_state(
    message: str = "Something went wrong",
    details: str = "",
) -> None:
    """
    Renders a styled error state with optional details.

    Args:
        message: Primary error message.
        details: Optional technical details for debugging.
    """
    st.error(f"⚠️ {message}")
    if details:
        with st.expander("Error Details"):
            st.code(details, language="text")

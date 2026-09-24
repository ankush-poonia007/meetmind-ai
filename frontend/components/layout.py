"""
MeetMind AI — Shared Layout Components.

Provides reusable layout elements: brand header, page headers, and footer.
Used across all pages for visual consistency.
"""

import streamlit as st


def render_brand_header() -> None:
    """Renders the MeetMind AI brand header with logo, title, and subtitle."""
    st.markdown(
        """
        <div class="brand-header">
            <div class="brand-logo">🧠</div>
            <div>
                <div class="brand-title">MeetMind AI</div>
                <div class="brand-subtitle">Agentic Meeting Intelligence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """
    Renders a consistent page header with optional icon and subtitle.

    Args:
        title: Page title text.
        subtitle: Optional description below the title.
        icon: Optional emoji icon prefix.
    """
    header_text = f"{icon} {title}" if icon else title
    st.markdown(
        f'<div class="section-header">{header_text}</div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.caption(subtitle)


def render_section_divider() -> None:
    """Renders a styled horizontal divider between sections."""
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


def render_footer() -> None:
    """Renders the application footer with project attribution."""
    st.markdown(
        """
        <div class="app-footer">
            MeetMind AI · Domain Verse 1.0 · Built with Streamlit + FastAPI + LangGraph
        </div>
        """,
        unsafe_allow_html=True,
    )

"""
MeetMind AI — Streamlit Application Entry Point.

Configures the Streamlit page, loads styles, initializes session state,
renders the sidebar navigation, the top navigation shell, and dispatches to the active page.

Launch:
    cd frontend
    streamlit run app.py
"""

import os
import sys

import streamlit as st

# ── Ensure frontend root is on sys.path for relative imports ─────────────────
_FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _FRONTEND_DIR not in sys.path:
    sys.path.insert(0, _FRONTEND_DIR)

from components.layout import render_brand_header
from components.sidebar import render_sidebar
from pages.documentation import render_documentation_page
from pages.landing import render_landing_page
from pages.workspace import render_workspace_page
from utils.session_state import init_session_state

# ── Page Configuration ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="MeetMind AI — Agentic Meeting Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load Global Styles ───────────────────────────────────────────────────────

_STYLES_PATH = os.path.join(_FRONTEND_DIR, "assets", "styles.css")
if os.path.exists(_STYLES_PATH):
    with open(_STYLES_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Initialize Session State ────────────────────────────────────────────────

init_session_state()

# ── Main Navigation Shell ───────────────────────────────────────────────────


def _render_navigation() -> None:
    """Renders the top-level navigation bar with page routing."""
    col_brand, col_nav = st.columns([1.2, 1], vertical_alignment="center")

    with col_brand:
        render_brand_header()

    with col_nav:
        current_page = st.session_state.get("current_page", "landing")
        nav_cols = st.columns(3)
        pages = [
            ("landing", "🏠 Home"),
            ("workspace", "💼 Workspace"),
            ("documentation", "📖 Docs"),
        ]

        for col, (page_key, label) in zip(nav_cols, pages):
            with col:
                is_active = current_page == page_key
                button_type = "primary" if is_active else "secondary"
                if st.button(label, use_container_width=True, type=button_type, key=f"nav_{page_key}"):
                    st.session_state["current_page"] = page_key
                    st.rerun()

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


def _render_active_page() -> None:
    """Dispatches rendering to the currently active page."""
    current_page = st.session_state.get("current_page", "landing")

    if current_page == "landing":
        render_landing_page()
    elif current_page == "workspace":
        render_workspace_page()
    elif current_page == "documentation":
        render_documentation_page()
    else:
        render_landing_page()


# ── Application Entry ───────────────────────────────────────────────────────

def main() -> None:
    """Main application entry point."""
    render_sidebar()
    _render_navigation()
    _render_active_page()


if __name__ == "__main__":
    main()
else:
    # Streamlit invokes the module directly, not via __main__
    main()

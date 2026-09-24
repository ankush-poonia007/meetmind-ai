"""
MeetMind AI — Streamlit Session State Manager.

Centralizes initialization and access to Streamlit session state variables.
Prevents duplication and ensures consistent defaults across all pages.
"""

import streamlit as st


# ── Default State Values ─────────────────────────────────────────────────────

_DEFAULTS = {
    # Navigation
    "current_page": "landing",
    "workspace_tab": "dashboard",

    # User session (no authentication — form-first identity)
    "user_id": None,
    "user_name": "",
    "user_email": "",

    # Active meeting context
    "active_meeting_id": None,

    # UI state
    "show_new_meeting_form": False,

    # API connection status
    "api_connected": None,
}

# Public alias for inspection and testing
DEFAULTS = _DEFAULTS


def init_session_state() -> None:
    """
    Initializes all required session state keys with defaults.
    Skips keys that have already been set to preserve user-driven state changes.
    """
    for key, default_value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def get_state(key: str, default=None):
    """Safely retrieves a session state value with an optional fallback."""
    return st.session_state.get(key, default)


def set_state(key: str, value) -> None:
    """Sets a session state value."""
    st.session_state[key] = value


def reset_session() -> None:
    """Resets all managed session state values to their defaults."""
    for key, default_value in _DEFAULTS.items():
        st.session_state[key] = default_value

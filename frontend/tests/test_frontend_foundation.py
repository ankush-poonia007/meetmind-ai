"""
MeetMind AI — Frontend Foundation Test Suite.

Verifies:
- Session state manager initialization and defaults
- API client construction, URL handling, error wrapping, and methods
- Component and page module imports
- Design system stylesheet presence and core rule existence
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure frontend root is on sys.path
FRONTEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)


# ── Session State Tests ──────────────────────────────────────────────────────


class TestSessionState:
    """Tests for utils.session_state."""

    def test_session_state_defaults(self):
        """Verifies session state is initialized with all expected keys and defaults."""
        from utils.session_state import DEFAULTS

        expected_keys = {
            "current_page",
            "workspace_tab",
            "user_id",
            "user_name",
            "user_email",
            "active_meeting_id",
            "show_new_meeting_form",
            "api_connected",
        }
        for key in expected_keys:
            assert key in DEFAULTS, f"Missing key in DEFAULTS: {key}"

        assert DEFAULTS["current_page"] == "landing"
        assert DEFAULTS["user_id"] is None
        assert DEFAULTS["active_meeting_id"] is None
        assert DEFAULTS["show_new_meeting_form"] is False

    @patch("utils.session_state.st")
    def test_init_session_state(self, mock_st):
        """Verifies init_session_state populates st.session_state when empty."""
        mock_state = {}
        mock_st.session_state = mock_state

        from utils.session_state import init_session_state

        init_session_state()

        assert mock_state["current_page"] == "landing"
        assert mock_state["user_id"] is None
        assert mock_state["active_meeting_id"] is None
        assert mock_state["workspace_tab"] == "dashboard"

    @patch("utils.session_state.st")
    def test_get_and_set_state(self, mock_st):
        """Verifies get_state and set_state helper functions."""
        mock_state = {"current_page": "landing"}
        mock_st.session_state = mock_state

        from utils.session_state import get_state, set_state

        assert get_state("current_page") == "landing"
        assert get_state("non_existent", "default_val") == "default_val"

        set_state("current_page", "workspace")
        assert mock_state["current_page"] == "workspace"
        assert get_state("current_page") == "workspace"

    @patch("utils.session_state.st")
    def test_reset_session(self, mock_st):
        """Verifies reset_session re-applies the default state values."""
        mock_state = {
            "current_page": "workspace",
            "user_id": "usr-1234",
            "active_meeting_id": "meet-5678",
        }
        mock_st.session_state = mock_state

        from utils.session_state import reset_session

        reset_session()

        assert mock_state["current_page"] == "landing"
        assert mock_state["user_id"] is None
        assert mock_state["active_meeting_id"] is None


# ── API Client Tests ─────────────────────────────────────────────────────────


class TestAPIClient:
    """Tests for services.api_client."""

    def test_api_client_initialization(self):
        """Verifies MeetMindAPIClient initializes with base URL and default timeout."""
        from services.api_client import MeetMindAPIClient

        client = MeetMindAPIClient(base_url="http://custom:9000/api/v1", timeout=15.0)
        assert client.base_url == "http://custom:9000/api/v1"
        assert client.timeout == 15.0

    def test_api_error_attributes(self):
        """Verifies APIError exception carries status_code and details."""
        from services.api_client import APIError

        err = APIError(message="Not found", status_code=404, details={"error": "Meeting missing"})
        assert str(err) == "Not found"
        assert err.status_code == 404
        assert err.details == {"error": "Meeting missing"}

    @patch("services.api_client.httpx.Client")
    def test_api_client_get_success(self, mock_client_cls):
        """Verifies successful GET request parsing."""
        from services.api_client import MeetMindAPIClient

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "healthy"}
        mock_resp.raise_for_status = MagicMock()

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_resp
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = False
        mock_client_cls.return_value = mock_instance

        client = MeetMindAPIClient(base_url="http://localhost:8000/api/v1")
        result = client.get("/health")

        assert result == {"status": "healthy"}
        mock_instance.get.assert_called_once_with(
            "http://localhost:8000/api/v1/health",
            params=None,
        )

    @patch("services.api_client.httpx.Client")
    def test_api_client_connection_error_handling(self, mock_client_cls):
        """Verifies connection failure raises wrapped APIError gracefully without crashing."""
        import httpx
        from services.api_client import APIError, MeetMindAPIClient

        mock_instance = MagicMock()
        mock_instance.get.side_effect = httpx.ConnectError("Connection refused")
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = False
        mock_client_cls.return_value = mock_instance

        client = MeetMindAPIClient(base_url="http://localhost:8000/api/v1")

        with pytest.raises(APIError) as exc_info:
            client.get("/health")

        assert exc_info.value.status_code == 0
        assert "Unable to connect" in str(exc_info.value)

    def test_singleton_api_instance(self):
        """Verifies shared singleton client instance is exposed."""
        from services.api_client import api, MeetMindAPIClient

        assert isinstance(api, MeetMindAPIClient)


# ── Module Import and Structure Tests ─────────────────────────────────────────


class TestFrontendStructure:
    """Verifies all required frontend modules and components import cleanly."""

    def test_component_imports(self):
        """Verifies layout and state display components exist and are callable."""
        from components.layout import (
            render_brand_header,
            render_footer,
            render_page_header,
            render_section_divider,
        )
        from components.state_displays import (
            render_empty_state,
            render_error_state,
            render_loading_state,
        )

        assert callable(render_brand_header)
        assert callable(render_footer)
        assert callable(render_page_header)
        assert callable(render_section_divider)
        assert callable(render_empty_state)
        assert callable(render_error_state)
        assert callable(render_loading_state)

    def test_page_imports(self):
        """Verifies page entry functions exist and are callable."""
        from pages.documentation import render_documentation_page
        from pages.landing import render_landing_page
        from pages.workspace import render_workspace_page

        assert callable(render_landing_page)
        assert callable(render_workspace_page)
        assert callable(render_documentation_page)

    def test_design_system_stylesheet(self):
        """Verifies styles.css exists and contains critical design tokens."""
        css_path = os.path.join(FRONTEND_DIR, "assets", "styles.css")
        assert os.path.isfile(css_path), f"styles.css not found at {css_path}"

        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        assert len(css_content) > 500, "styles.css is suspiciously small"
        # Core styling tokens and classes
        assert ".brand-header" in css_content
        assert ".hero-section" in css_content
        assert ".feature-card" in css_content
        assert ".stat-card" in css_content
        assert ".empty-state" in css_content
        assert ".section-divider" in css_content
        assert ".block-container" in css_content

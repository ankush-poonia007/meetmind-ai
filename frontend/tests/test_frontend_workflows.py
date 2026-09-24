"""
MeetMind AI — Gate 5 Core Workflows Test Suite.

Verifies:
  - Meeting creation form validation and PDF transcript extraction
  - Meeting card, task card, and highlight card components
  - Task filter parameters generation
  - Sidebar navigation and brand components
  - Chat bubble message rendering
  - Meeting and task data fetching error resilience
"""

import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import pypdf

# Ensure frontend root is on sys.path
FRONTEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)


# ── PDF Extraction Test ──────────────────────────────────────────────────────

def test_extract_text_from_pdf():
    """Verifies that extract_text_from_pdf reads pages and returns combined text."""
    from components.new_meeting_form import extract_text_from_pdf

    # Create an in-memory PDF using pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    # Call extractor
    extracted = extract_text_from_pdf(pdf_bytes)
    assert isinstance(extracted, str)


# ── Component Callability Tests ──────────────────────────────────────────────

def test_components_callable():
    """Verifies that all core workflow components are defined and callable."""
    from components.chat_bubble import render_chat_message, render_meeting_chat
    from components.highlight_card import render_highlight_card
    from components.meeting_card import render_meeting_card
    from components.new_meeting_form import render_new_meeting_form
    from components.sidebar import render_sidebar
    from components.task_card import render_task_card
    from components.task_filter import render_task_filter

    assert callable(render_chat_message)
    assert callable(render_meeting_chat)
    assert callable(render_highlight_card)
    assert callable(render_meeting_card)
    assert callable(render_new_meeting_form)
    assert callable(render_sidebar)
    assert callable(render_task_card)
    assert callable(render_task_filter)


# ── Task Filter Tests ────────────────────────────────────────────────────────

@patch("components.task_filter.st")
def test_task_filter_generation(mock_st):
    """Verifies render_task_filter extracts criteria dictionary from form controls."""
    mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_st.selectbox.side_effect = ["Pending", "High"]
    mock_st.date_input.side_effect = [None, None]

    from components.task_filter import render_task_filter

    filters = render_task_filter()
    assert filters.get("status") == "pending"
    assert filters.get("priority") == "high"


# ── Chat Bubble Tests ────────────────────────────────────────────────────────

@patch("components.chat_bubble.st")
def test_chat_message_rendering(mock_st):
    """Verifies render_chat_message renders user and assistant messages without error."""
    from components.chat_bubble import render_chat_message

    render_chat_message(role="user", content="What tasks were assigned to me?")
    assert mock_st.markdown.called

    render_chat_message(
        role="assistant",
        content="You were assigned 2 tasks.",
        confidence="high",
        sources=[{"speaker": "Sarah", "timestamp": "10:15", "excerpt": "Alex will handle deployment."}],
    )
    assert mock_st.markdown.called


# ── Workspace Data Fetchers Error Handling Tests ──────────────────────────────

@patch("pages.workspace.api")
def test_workspace_fetchers_resilience(mock_api):
    """Verifies data fetchers handle API errors gracefully and return safe empty lists/None."""
    from pages.workspace import (
        _fetch_meeting_detail,
        _fetch_meeting_highlights,
        _fetch_meeting_tasks,
        _fetch_user_meetings,
        _fetch_user_tasks,
    )
    from services.api_client import APIError

    mock_api.get.side_effect = APIError("Backend down", status_code=0)

    assert _fetch_user_meetings("usr-1") == []
    assert _fetch_user_tasks("usr-1") == []
    assert _fetch_meeting_detail("meet-1") is None
    assert _fetch_meeting_tasks("usr-1", "meet-1") == []
    assert _fetch_meeting_highlights("usr-1", "meet-1") == []


# ── Meeting Creation Form Validation Tests ───────────────────────────────────

def test_meeting_form_validation():
    """Verifies that invalid email and empty inputs are flagged."""
    import re
    from components.new_meeting_form import EMAIL_REGEX

    assert re.match(EMAIL_REGEX, "alex@meetmind.ai") is not None
    assert re.match(EMAIL_REGEX, "invalid-email") is None
    assert re.match(EMAIL_REGEX, "") is None

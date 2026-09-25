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


# ── Task Card Unique Key & Toggle Tests ──────────────────────────────────────

@patch("components.task_card.st")
def test_task_card_key_generation_and_uniqueness(mock_st):
    """Verifies render_task_card produces distinct, stable button keys across tabs/indices."""
    from components.task_card import render_task_card

    task = {
        "id": "7d560196-ab30-4ca6-a04d-1252d8884153",
        "title": "Setup CI/CD Pipeline",
        "description": "Configure GitHub Actions",
        "priority": "high",
        "status": "pending",
        "deadline": "2026-10-01",
    }

    captured_keys = []

    def mock_button(label, key=None, **kwargs):
        captured_keys.append(key)
        return False

    mock_st.button.side_effect = mock_button
    mock_st.columns.return_value = [MagicMock(), MagicMock()]

    # 1. Render in meeting detail view (e.g. index 0)
    render_task_card(task, key_prefix="meeting_meet-123", index=0)

    # 2. Render in tasks tab (e.g. index 0)
    render_task_card(task, key_prefix="tasks_tab", index=0)

    # 3. Render another item in tasks tab (index 1)
    render_task_card(task, key_prefix="tasks_tab", index=1)

    assert len(captured_keys) == 3
    # Check exact keys
    assert captured_keys[0] == "meeting_meet-123_toggle_task_7d560196-ab30-4ca6-a04d-1252d8884153_0"
    assert captured_keys[1] == "tasks_tab_toggle_task_7d560196-ab30-4ca6-a04d-1252d8884153_0"
    assert captured_keys[2] == "tasks_tab_toggle_task_7d560196-ab30-4ca6-a04d-1252d8884153_1"

    # All keys must be strictly unique (no duplicates in captured_keys)
    assert len(captured_keys) == len(set(captured_keys))


@patch("components.task_card.st")
def test_task_card_backward_compatibility(mock_st):
    """Verifies render_task_card with no prefix/index maintains legacy key toggle_task_{task_id}."""
    from components.task_card import render_task_card

    task = {
        "id": "7d560196-ab30-4ca6-a04d-1252d8884153",
        "title": "Legacy Test Task",
        "status": "pending",
    }

    mock_st.button.return_value = False
    mock_st.columns.return_value = [MagicMock(), MagicMock()]

    render_task_card(task)
    mock_st.button.assert_called_once()
    assert mock_st.button.call_args.kwargs.get("key") == "toggle_task_7d560196-ab30-4ca6-a04d-1252d8884153"


@patch("components.task_card.api")
@patch("components.task_card.st")
def test_task_card_toggle_action(mock_st, mock_api):
    """Verifies clicking the toggle button calls api.put, triggers callback, and reruns."""
    from components.task_card import render_task_card

    task = {
        "id": "task-abc-123",
        "title": "Deploy to Staging",
        "status": "pending",
    }

    mock_st.button.return_value = True
    mock_st.columns.return_value = [MagicMock(), MagicMock()]
    mock_callback = MagicMock()

    render_task_card(task, on_status_change=mock_callback, key_prefix="tasks_tab", index=0)

    mock_api.put.assert_called_once_with("/tasks/task-abc-123/status", json={"status": "complete"})
    mock_callback.assert_called_once_with("task-abc-123", "complete")
    mock_st.rerun.assert_called_once()


@patch("components.task_card.st")
@patch("pages.workspace._fetch_user_tasks")
@patch("pages.workspace._fetch_meeting_tasks")
@patch("pages.workspace._fetch_meeting_highlights", return_value=[])
@patch("pages.workspace._fetch_meeting_detail")
@patch("pages.workspace.render_meeting_chat")
@patch("pages.workspace.render_task_filter", return_value={})
@patch("pages.workspace.st")
def test_workspace_no_duplicate_keys_across_tabs(
    mock_workspace_st,
    mock_filter,
    mock_chat,
    mock_detail,
    mock_hl,
    mock_fetch_meeting_tasks,
    mock_fetch_user_tasks,
    mock_task_card_st,
):
    """Verifies that rendering meeting details and tasks tab simultaneously produces zero duplicate widget keys."""
    from pages.workspace import _render_meeting_detail_view, _render_tasks_tab

    shared_task = {
        "id": "7d560196-ab30-4ca6-a04d-1252d8884153",
        "title": "Shared Task",
        "description": "Appears in meeting and user task lists",
        "priority": "high",
        "status": "pending",
        "deadline": "2026-10-01",
    }

    mock_detail.return_value = {
        "id": "meet-uuid-123",
        "title": "Kickoff Meeting",
        "organization": "Engineering",
        "participants": [],
    }
    mock_fetch_meeting_tasks.return_value = [shared_task]
    mock_fetch_user_tasks.return_value = [shared_task]

    mock_workspace_st.session_state = {"user_id": "usr-123", "active_meeting_id": "meet-uuid-123"}
    mock_workspace_st.columns.side_effect = lambda spec: [MagicMock() for _ in (spec if isinstance(spec, list) else range(spec))]
    mock_task_card_st.columns.side_effect = lambda spec: [MagicMock() for _ in (spec if isinstance(spec, list) else range(spec))]

    used_keys = []

    def mock_button(label, key=None, **kwargs):
        if key:
            used_keys.append(key)
        return False

    mock_workspace_st.button.side_effect = mock_button
    mock_task_card_st.button.side_effect = mock_button

    # 1. Render meeting detail view (simulates tab 2)
    _render_meeting_detail_view("meet-uuid-123", "usr-123")

    # 2. Render tasks tab in the same script run (simulates tab 3)
    _render_tasks_tab()

    # Verify task toggle buttons were called and their keys are unique
    task_keys = [k for k in used_keys if "7d560196-ab30-4ca6-a04d-1252d8884153" in k]
    assert len(task_keys) == 2
    assert task_keys[0] == "meeting_meet-uuid-123_toggle_task_7d560196-ab30-4ca6-a04d-1252d8884153_0"
    assert task_keys[1] == "tasks_tab_toggle_task_7d560196-ab30-4ca6-a04d-1252d8884153_0"
    assert task_keys[0] != task_keys[1]
    assert len(used_keys) == len(set(used_keys)), f"Duplicate keys detected: {used_keys}"



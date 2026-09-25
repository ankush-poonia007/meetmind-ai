"""
MeetMind AI — Gate 6, Batch 1: End-to-End API Pipeline Verification
Validates the complete user journey by communicating with the running FastAPI backend over HTTP.
"""

import os
import uuid
from datetime import date
import pytest
import httpx

BASE_URL = os.getenv("MEETMIND_TEST_BASE_URL", "http://localhost:8000")
API_V1 = f"{BASE_URL}/api/v1"

# Load sample transcript for realistic testing
TRANSCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "sample_transcripts", "transcript_emergency_bug.txt"
)


@pytest.fixture(scope="module")
def http_client():
    """Shared HTTP client with timeout configured for agent LLM pipelines."""
    with httpx.Client(base_url=BASE_URL, timeout=90.0) as client:
        # Pre-check health before running pipeline
        r = client.get("/health")
        assert r.status_code == 200, f"Backend not running at {BASE_URL}: {r.text}"
        yield client


@pytest.fixture(scope="module")
def sample_transcript():
    """Load emergency bug transcript text."""
    if os.path.exists(TRANSCRIPT_PATH):
        with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return (
        "Alex (Engineering Lead): We had a critical Redis cache outage affecting checkout.\n"
        "Sarah (Backend): I will add an automated circuit breaker to prevent cascade failures by Friday.\n"
        "Alex: Please also update the runbook documentation."
    )


class TestEndToEndPipeline:
    """Sequential end-to-end integration test validating the complete user journey."""

    user_id = None
    user_email = None
    user_name = "Dev"
    user_role = "Documentation Lead"
    meeting_id = None
    task_id = None

    def test_step1_user_registration_and_retrieval(self, http_client):
        """STEP 1: Register test user and verify profile retrieval."""
        TestEndToEndPipeline.user_email = f"e2e_pipeline_{uuid.uuid4().hex[:8]}@meetmind.ai"
        payload = {
            "name": TestEndToEndPipeline.user_name,
            "email": TestEndToEndPipeline.user_email,
        }
        res = http_client.post("/api/v1/users/register", json=payload)
        assert res.status_code in [200, 201], f"Registration failed: {res.text}"
        data = res.json()
        assert "id" in data
        assert data["email"] == TestEndToEndPipeline.user_email
        assert data["name"] == TestEndToEndPipeline.user_name
        TestEndToEndPipeline.user_id = data["id"]

        # Verify retrieval by ID
        get_res = http_client.get(f"/api/v1/users/{TestEndToEndPipeline.user_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == TestEndToEndPipeline.user_id
        assert get_data["email"] == TestEndToEndPipeline.user_email

    def test_step2_meeting_creation_and_ingestion(self, http_client, sample_transcript):
        """STEP 2: Create a meeting, ingest transcript, and associate with user."""
        assert TestEndToEndPipeline.user_id is not None
        payload = {
            "user_id": TestEndToEndPipeline.user_id,
            "title": "Emergency Production Post-Mortem",
            "organization": "Platform Reliability",
            "meeting_date": str(date.today()),
            "meeting_time": "14:30",
            "input_format": "text",
            "raw_transcript": sample_transcript,
        }
        params = {
            "submitter_name": TestEndToEndPipeline.user_name,
            "submitter_role": TestEndToEndPipeline.user_role,
        }
        res = http_client.post("/api/v1/meetings/", json=payload, params=params)
        assert res.status_code in [200, 201], f"Meeting creation failed: {res.text}"
        data = res.json()
        assert "id" in data
        assert data["user_id"] == TestEndToEndPipeline.user_id
        assert data["title"] == "Emergency Production Post-Mortem"
        TestEndToEndPipeline.meeting_id = data["id"]

    def test_step3_participant_identity_verification(self, http_client):
        """STEP 3: Verify meeting detail and submitter identity resolution."""
        assert TestEndToEndPipeline.meeting_id is not None
        res = http_client.get(f"/api/v1/meetings/{TestEndToEndPipeline.meeting_id}/detail")
        assert res.status_code == 200, f"Detail retrieval failed: {res.text}"
        data = res.json()
        assert data["id"] == TestEndToEndPipeline.meeting_id
        assert len(data.get("participants", [])) >= 1

        submitter = next((p for p in data["participants"] if p.get("is_current_user")), None)
        assert submitter is not None, "Submitter participant with is_current_user=True not found"
        assert submitter["name"] == TestEndToEndPipeline.user_name

    def test_step4_ai_task_extraction(self, http_client):
        """STEP 4: Trigger extraction pipeline and verify preview output."""
        assert TestEndToEndPipeline.meeting_id is not None
        payload = {
            "meeting_id": TestEndToEndPipeline.meeting_id,
            "user_id": TestEndToEndPipeline.user_id,
        }
        res = http_client.post(
            f"/api/v1/extraction/{TestEndToEndPipeline.meeting_id}/run", json=payload
        )
        assert res.status_code == 200, f"Extraction failed: {res.text}"
        data = res.json()
        assert data["meeting_id"] == TestEndToEndPipeline.meeting_id
        assert data.get("extraction_complete") is True
        assert "tasks" in data
        assert "highlights" in data
        assert isinstance(data["tasks"], list)
        assert isinstance(data["highlights"], list)

    def test_step5_human_confirmation_partial(self, http_client):
        """STEP 5: Submit human-in-the-loop partial confirmation."""
        assert TestEndToEndPipeline.meeting_id is not None
        # Retrieve preview first to get current candidate tasks
        preview_res = http_client.get(
            f"/api/v1/extraction/{TestEndToEndPipeline.meeting_id}/preview",
            params={"user_id": TestEndToEndPipeline.user_id},
        )
        assert preview_res.status_code == 200
        preview = preview_res.json()

        # If preview has tasks, confirm the first task by index ["0"]
        confirmed_ids = ["0"] if preview.get("tasks") else []

        confirm_payload = {
            "meeting_id": TestEndToEndPipeline.meeting_id,
            "user_id": TestEndToEndPipeline.user_id,
            "user_confirmation": "partial",
            "confirmed_task_ids": confirmed_ids,
        }
        res = http_client.post(
            f"/api/v1/extraction/{TestEndToEndPipeline.meeting_id}/confirm",
            json=confirm_payload,
        )
        assert res.status_code == 200, f"Confirmation failed: {res.text}"
        data = res.json()
        assert data["meeting_id"] == TestEndToEndPipeline.meeting_id
        assert data["confirmation_complete"] is True
        assert data["dashboard_ready"] is True
        if confirmed_ids:
            assert data["saved_tasks"] >= 1

    def test_step6_confirmed_task_and_highlight_retrieval(self, http_client):
        """STEP 6: Retrieve confirmed tasks and persisted highlights."""
        assert TestEndToEndPipeline.user_id is not None
        # Tasks retrieval
        tasks_res = http_client.get(f"/api/v1/tasks/{TestEndToEndPipeline.user_id}")
        assert tasks_res.status_code == 200, f"Task retrieval failed: {tasks_res.text}"
        tasks = tasks_res.json()
        assert isinstance(tasks, list)
        if tasks:
            TestEndToEndPipeline.task_id = tasks[0]["id"]
            assert tasks[0]["user_id"] == TestEndToEndPipeline.user_id
            assert tasks[0]["meeting_id"] == TestEndToEndPipeline.meeting_id

        # Highlights retrieval
        hl_res = http_client.get(
            f"/api/v1/highlights/{TestEndToEndPipeline.user_id}/meeting/{TestEndToEndPipeline.meeting_id}"
        )
        assert hl_res.status_code == 200, f"Highlights retrieval failed: {hl_res.text}"
        hl_data = hl_res.json()
        assert "highlights" in hl_data
        assert isinstance(hl_data["highlights"], list)

    def test_step7_meeting_scoped_qa(self, http_client):
        """STEP 7: Submit question to meeting-scoped Q&A chat."""
        assert TestEndToEndPipeline.meeting_id is not None
        chat_payload = {
            "question": "What caused the checkout failure and what action was decided?",
            "user_id": TestEndToEndPipeline.user_id,
        }
        res = http_client.post(
            f"/api/v1/chat/{TestEndToEndPipeline.meeting_id}/message", json=chat_payload
        )
        assert res.status_code == 200, f"Chat Q&A failed: {res.text}"
        data = res.json()
        assert data["meeting_id"] == TestEndToEndPipeline.meeting_id
        assert "answer" in data
        assert len(data["answer"]) > 0
        assert "sources" in data
        assert isinstance(data["sources"], list)

    def test_step8_task_status_update(self, http_client):
        """STEP 8: Update task status to complete and verify persistence."""
        if not TestEndToEndPipeline.task_id:
            pytest.skip("No task was confirmed in earlier step to update status.")

        update_payload = {"status": "complete"}
        res = http_client.put(
            f"/api/v1/tasks/{TestEndToEndPipeline.task_id}/status", json=update_payload
        )
        assert res.status_code == 200, f"Task status update failed: {res.text}"
        data = res.json()
        assert data["id"] == TestEndToEndPipeline.task_id
        assert data["status"] == "complete"

        # Re-fetch task list to confirm persistence
        tasks_res = http_client.get(f"/api/v1/tasks/{TestEndToEndPipeline.user_id}")
        assert tasks_res.status_code == 200
        tasks = tasks_res.json()
        matching = next((t for t in tasks if t["id"] == TestEndToEndPipeline.task_id), None)
        assert matching is not None
        assert matching["status"] == "complete"

    def test_step9_final_persistence_verification(self, http_client):
        """STEP 9: Re-query meeting and verify final state consistency."""
        assert TestEndToEndPipeline.meeting_id is not None
        detail_res = http_client.get(
            f"/api/v1/meetings/{TestEndToEndPipeline.meeting_id}/detail"
        )
        assert detail_res.status_code == 200
        meeting = detail_res.json()
        assert meeting["id"] == TestEndToEndPipeline.meeting_id
        assert meeting["user_id"] == TestEndToEndPipeline.user_id

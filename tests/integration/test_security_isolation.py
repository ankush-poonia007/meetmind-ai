"""
MeetMind AI — Gate 6, Batch 2: Security Boundaries, Data Isolation & Database Integrity
Validates:
1. Cross-meeting Q&A isolation (zero leakage between distinct meetings).
2. User ownership boundaries (strict data scoping across separate user profiles).
3. Meeting deletion with cascading database integrity.
4. Duplicate user registration conflict handling.
"""

import os
import uuid
from datetime import date
import pytest
import httpx

BASE_URL = os.getenv("MEETMIND_TEST_BASE_URL", "http://localhost:8000")
API_V1 = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def http_client():
    """Shared HTTP client for security and boundary tests."""
    with httpx.Client(base_url=BASE_URL, timeout=90.0) as client:
        r = client.get("/health")
        assert r.status_code == 200, f"Backend not running at {BASE_URL}"
        yield client


class TestSecurityAndDataIsolation:
    """Tests cross-meeting isolation, user ownership boundaries, and database integrity."""

    # User A records
    user_a_id = None
    user_a_email = None
    meeting_a_id = None

    # User B records
    user_b_id = None
    user_b_email = None
    meeting_b_id = None

    def test_setup_users_and_meetings(self, http_client):
        """Setup User A and User B with distinct meetings, ingested transcripts, and extracted entities."""
        # 1. Register User A
        TestSecurityAndDataIsolation.user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@meetmind.ai"
        res_a = http_client.post(
            "/api/v1/users/register",
            json={"name": "Alice Armstrong", "email": TestSecurityAndDataIsolation.user_a_email},
        )
        assert res_a.status_code in [200, 201]
        TestSecurityAndDataIsolation.user_a_id = res_a.json()["id"]

        # 2. Register User B
        TestSecurityAndDataIsolation.user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@meetmind.ai"
        res_b = http_client.post(
            "/api/v1/users/register",
            json={"name": "Bob Babbage", "email": TestSecurityAndDataIsolation.user_b_email},
        )
        assert res_b.status_code in [200, 201]
        TestSecurityAndDataIsolation.user_b_id = res_b.json()["id"]

        # 3. Create Meeting A for User A with unique facts (Project Apollo, Rust migration, Project Redstone)
        transcript_a = (
            "[10:00] Alice (Tech Lead): Welcome everyone to the Project Apollo architecture alignment.\n"
            "[10:02] Dave (Principal Architect): We evaluated Go and Rust for the core search rewrite. "
            "Given our latency SLAs of sub-five milliseconds, we formally approved migrating our entire data engine to Rust.\n"
            "[10:05] Alice: Confirmed. The internal secret codename for this Rust migration initiative is Project Redstone. "
            "Please ensure all commit messages reference Redstone.\n"
            "[10:08] Dave: Understood. I will prepare the initial Rust prototype repository by next Monday morning."
        )
        res_m_a = http_client.post(
            "/api/v1/meetings/",
            params={"submitter_name": "Alice Armstrong", "submitter_role": "Tech Lead"},
            json={
                "user_id": TestSecurityAndDataIsolation.user_a_id,
                "title": "Project Apollo Architecture Review",
                "organization": "Apollo Systems",
                "meeting_date": str(date.today()),
                "meeting_time": "10:00",
                "input_format": "text",
                "raw_transcript": transcript_a,
            },
        )
        assert res_m_a.status_code in [200, 201]
        TestSecurityAndDataIsolation.meeting_a_id = res_m_a.json()["id"]

        # 4. Ingest and extract Meeting A to populate Pinecone namespace meeting_{id} and PostgreSQL chunks
        ex_a = http_client.post(
            f"/api/v1/extraction/{TestSecurityAndDataIsolation.meeting_a_id}/run",
            json={"meeting_id": TestSecurityAndDataIsolation.meeting_a_id, "user_id": TestSecurityAndDataIsolation.user_a_id},
        )
        assert ex_a.status_code == 200

        # 5. Create Meeting B for User B with unique facts (Project Nebula, Japan expansion, Project BlueSky)
        transcript_b = (
            "[11:00] Bob (Managing Director): Welcome team to the Project Nebula executive strategy session.\n"
            "[11:03] Sarah (VP Expansion): The international expansion committee completed its market analysis. "
            "The executive board has officially decided on full market expansion into Tokyo, Japan by Q4.\n"
            "[11:06] Bob: Excellent news. The internal secret codename for this Japan regional expansion is Project BlueSky. "
            "We will begin hiring 50 engineers in Tokyo immediately.\n"
            "[11:09] Sarah: I will start the recruitment process with our Tokyo agency by Wednesday."
        )
        res_m_b = http_client.post(
            "/api/v1/meetings/",
            params={"submitter_name": "Bob Babbage", "submitter_role": "Managing Director"},
            json={
                "user_id": TestSecurityAndDataIsolation.user_b_id,
                "title": "Project Nebula Executive Strategy",
                "organization": "Nebula Global",
                "meeting_date": str(date.today()),
                "meeting_time": "11:00",
                "input_format": "text",
                "raw_transcript": transcript_b,
            },
        )
        assert res_m_b.status_code in [200, 201]
        TestSecurityAndDataIsolation.meeting_b_id = res_m_b.json()["id"]

        # 6. Ingest and extract Meeting B to populate Pinecone namespace meeting_{id} and PostgreSQL chunks
        ex_b = http_client.post(
            f"/api/v1/extraction/{TestSecurityAndDataIsolation.meeting_b_id}/run",
            json={"meeting_id": TestSecurityAndDataIsolation.meeting_b_id, "user_id": TestSecurityAndDataIsolation.user_b_id},
        )
        assert ex_b.status_code == 200

    # ── Task B1: Cross-Meeting Q&A Isolation ─────────────────────────────────────

    def test_cross_meeting_qa_isolation_meeting_a(self, http_client):
        """Verify Meeting A Q&A retrieves only Meeting A content and never Meeting B content."""
        assert TestSecurityAndDataIsolation.meeting_a_id is not None
        req = {
            "question": "What is the secret codename and language chosen for Project Apollo?",
            "user_id": TestSecurityAndDataIsolation.user_a_id,
        }
        res = http_client.post(
            f"/api/v1/chat/{TestSecurityAndDataIsolation.meeting_a_id}/message", json=req
        )
        assert res.status_code == 200
        data = res.json()
        answer = data.get("answer", "").lower()

        # Must find Meeting A facts (Rust or Redstone)
        assert "rust" in answer or "redstone" in answer, f"Expected Meeting A content in answer: {data['answer']}"
        # Must NOT contain Meeting B facts (Japan or BlueSky)
        assert "japan" not in answer and "bluesky" not in answer, (
            f"Cross-meeting leakage detected: Meeting B data found in Meeting A response: {data['answer']}"
        )

    def test_cross_meeting_qa_isolation_meeting_b(self, http_client):
        """Verify Meeting B Q&A retrieves only Meeting B content and never Meeting A content."""
        assert TestSecurityAndDataIsolation.meeting_b_id is not None
        req = {
            "question": "What is the secret codename and country expansion for Project Nebula?",
            "user_id": TestSecurityAndDataIsolation.user_b_id,
        }
        res = http_client.post(
            f"/api/v1/chat/{TestSecurityAndDataIsolation.meeting_b_id}/message", json=req
        )
        assert res.status_code == 200
        data = res.json()
        answer = data.get("answer", "").lower()

        # Must find Meeting B facts (Japan, Tokyo, or BlueSky)
        assert "japan" in answer or "bluesky" in answer or "tokyo" in answer, (
            f"Expected Meeting B content in answer: {data['answer']}"
        )
        # Must NOT contain Meeting A facts (Rust or Redstone)
        assert "rust" not in answer and "redstone" not in answer, (
            f"Cross-meeting leakage detected: Meeting A data found in Meeting B response: {data['answer']}"
        )

    # ── Task B2: User Ownership Boundaries ───────────────────────────────────────

    def test_user_ownership_meeting_listings(self, http_client):
        """Verify meeting listings are strictly scoped to the requesting user."""
        res_a = http_client.get(f"/api/v1/meetings/{TestSecurityAndDataIsolation.user_a_id}")
        assert res_a.status_code == 200
        meetings_a = res_a.json()
        ids_a = [m["id"] for m in meetings_a]
        assert TestSecurityAndDataIsolation.meeting_a_id in ids_a
        assert TestSecurityAndDataIsolation.meeting_b_id not in ids_a

        res_b = http_client.get(f"/api/v1/meetings/{TestSecurityAndDataIsolation.user_b_id}")
        assert res_b.status_code == 200
        meetings_b = res_b.json()
        ids_b = [m["id"] for m in meetings_b]
        assert TestSecurityAndDataIsolation.meeting_b_id in ids_b
        assert TestSecurityAndDataIsolation.meeting_a_id not in ids_b

    def test_user_ownership_extraction_preview_boundary(self, http_client):
        """Verify requesting extraction preview for another user's meeting is rejected with 404."""
        # User A attempts to view extraction preview for Meeting B (owned by User B)
        res = http_client.get(
            f"/api/v1/extraction/{TestSecurityAndDataIsolation.meeting_b_id}/preview",
            params={"user_id": TestSecurityAndDataIsolation.user_a_id},
        )
        assert res.status_code == 404, f"Expected 404 ownership violation, got {res.status_code}: {res.text}"
        error_data = res.json()
        assert error_data.get("error") == "InvalidOwnershipError"

    def test_user_ownership_task_isolation(self, http_client):
        """Verify task listings for User A do not expose User B tasks."""
        tasks_a = http_client.get(f"/api/v1/tasks/{TestSecurityAndDataIsolation.user_a_id}").json()
        tasks_b = http_client.get(f"/api/v1/tasks/{TestSecurityAndDataIsolation.user_b_id}").json()

        user_a_task_ids = {t["id"] for t in tasks_a}
        user_b_task_ids = {t["id"] for t in tasks_b}

        # Sets of task IDs must be strictly disjoint
        assert user_a_task_ids.isdisjoint(user_b_task_ids), "User A and User B tasks overlapped!"

    # ── Task B3: Meeting Deletion and Cascade Integrity ──────────────────────────

    def test_meeting_cascade_deletion(self, http_client):
        """Create a dedicated meeting with artifacts, delete it via API, and verify full cascade cleanup."""
        # 1. Create Meeting C
        res = http_client.post(
            "/api/v1/meetings/",
            params={"submitter_name": "Charlie", "submitter_role": "QA"},
            json={
                "user_id": TestSecurityAndDataIsolation.user_a_id,
                "title": "Meeting to be Deleted",
                "organization": "QA Sandbox",
                "meeting_date": str(date.today()),
                "meeting_time": "12:00",
                "input_format": "text",
                "raw_transcript": "[12:00] Charlie (QA): This meeting will be deleted to test foreign-key cascades.",
            },
        )
        assert res.status_code in [200, 201]
        m_id = res.json()["id"]

        # 2. Add a chat message to ensure child records exist
        chat_res = http_client.post(
            f"/api/v1/chat/{m_id}/message",
            json={"question": "Will this be deleted?", "user_id": TestSecurityAndDataIsolation.user_a_id},
        )
        assert chat_res.status_code == 200

        # 3. Delete the meeting
        del_res = http_client.delete(f"/api/v1/meetings/{m_id}")
        assert del_res.status_code == 204, f"Deletion failed: {del_res.status_code}"

        # 4. Verify meeting is gone via API
        detail_res = http_client.get(f"/api/v1/meetings/{m_id}/detail")
        assert detail_res.status_code == 404

        # 5. Verify chat history for the deleted meeting returns 404
        chat_hist = http_client.get(f"/api/v1/chat/{m_id}/history")
        assert chat_hist.status_code == 404

        # 6. Verify meeting list for user does not include the deleted meeting
        user_meetings = http_client.get(f"/api/v1/meetings/{TestSecurityAndDataIsolation.user_a_id}").json()
        assert m_id not in [m["id"] for m in user_meetings]

        # 7. Verify Meeting A and Meeting B remain intact
        assert http_client.get(f"/api/v1/meetings/{TestSecurityAndDataIsolation.meeting_a_id}/detail").status_code == 200
        assert http_client.get(f"/api/v1/meetings/{TestSecurityAndDataIsolation.meeting_b_id}/detail").status_code == 200

    # ── Task B4: Duplicate Registration ─────────────────────────────────────────

    def test_duplicate_user_registration_conflict(self, http_client):
        """Verify registering with an existing email returns 409 Conflict without leaking secrets."""
        test_email = f"conflict_{uuid.uuid4().hex[:8]}@meetmind.ai"

        # First registration -> 201 Created
        r1 = http_client.post("/api/v1/users/register", json={"name": "Primary User", "email": test_email})
        assert r1.status_code in [200, 201]

        # Duplicate registration -> 409 Conflict
        r2 = http_client.post("/api/v1/users/register", json={"name": "Duplicate User", "email": test_email})
        assert r2.status_code == 409, f"Expected 409 Conflict, got {r2.status_code}: {r2.text}"

        err_body = r2.json()
        assert err_body.get("error") == "DuplicateUserError"
        assert "already exists" in err_body.get("message", "")
        # Ensure no SQL or database credentials exposed in details
        assert "password" not in str(err_body).lower()
        assert "postgresql://" not in str(err_body).lower()

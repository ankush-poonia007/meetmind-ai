"""
Automated test suite for Gate 6 Backend Integration Fixes:
1. Fix 1 — Explicit Participant-Specific Extraction
2. Fix 2 — Persist Edited Task Details (Descriptions & Deadlines)

Covers all 18 required cases:
PARTICIPANT EXTRACTION:
1. Valid explicit participant name.
2. Empty participant name.
3. Whitespace-only participant name.
4. Participant with matching transcript identity.
5. Participant with no matching transcript identity.
6. Ambiguous participant identity.
7. Ensure another participant's tasks are not returned.
8. Ensure the logged-in user's name is not substituted.

TASK CONFIRMATION:
1. Confirm all selected tasks.
2. Confirm only a subset of tasks.
3. Persist edited descriptions.
4. Persist edited deadlines.
5. Preserve excluded tasks.
6. Reject invalid task IDs.
7. Reject tasks belonging to another meeting.
8. Reject unauthorized confirmation.
9. Reject invalid deadlines.
10. Verify transaction consistency.

INTEGRATION:
- End-to-end extraction and confirmation pipeline.
- Database persistence validation.
- Backward compatibility for requests omitting person_name / modified_tasks.
"""

import sys
import unittest
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.constants import TaskPriority, UserConfirmation
from app.db.base import Base
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.db.models.transcript_chunk import TranscriptChunk, TranscriptChunkType
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.services.extraction_service import ExtractionService


class BaseExtractionTestCase(unittest.TestCase):
    """Base test case with isolated in-memory SQLite and FastAPI TestClient."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

        def _override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override_get_db
        self.client = TestClient(app)
        self.db: Session = self.SessionLocal()

        self.user = self.create_user(name="Alice LoggedIn", email="alice@meetmind.ai")
        self.meeting = self.create_meeting(
            user=self.user,
            title="Sprint Planning Meeting",
            transcript=(
                "Alice: Let's start the meeting.\n"
                "Bob: I will prepare the database migration script by tomorrow.\n"
                "Charlie: I will review the API specifications.\n"
                "Alice: Please make sure the documentation is updated."
            ),
        )

        self.embed_patcher = patch("app.rag.embedder.TranscriptEmbedder.embed_and_store", return_value=None)
        self.mock_embed = self.embed_patcher.start()

        self.gw_patcher = patch("app.agents.extraction.get_provider_gateway")
        self.mock_gw = self.gw_patcher.start()
        self.mock_gw.return_value.execute.side_effect = Exception("Offline test mode")

    def tearDown(self) -> None:
        self.gw_patcher.stop()
        self.embed_patcher.stop()
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def create_user(self, name: str = "Test User", email: str = "test@example.com") -> User:
        user = User(id=uuid.uuid4(), name=name, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_meeting(
        self,
        user: User,
        title: str = "Test Meeting",
        transcript: str = "Alice: Hello world. Bob: Hi there.",
    ) -> Meeting:
        meeting = Meeting(
            id=uuid.uuid4(),
            user_id=user.id,
            title=title,
            organization="QA Org",
            meeting_date=date(2026, 9, 24),
            meeting_time="09:00",
            raw_transcript=transcript,
            input_format="text",
        )
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PARTICIPANT EXTRACTION TESTS (Cases 1 - 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestParticipantExtraction(BaseExtractionTestCase):
    """Verifies Fix 1: Participant-specific task extraction using explicit name."""

    def test_01_valid_explicit_participant_name(self) -> None:
        """Case 1: Valid explicit participant name triggers pipeline and returns 200."""
        # Add Bob as participant
        p = MeetingParticipant(
            id=uuid.uuid4(),
            meeting_id=self.meeting.id,
            name="Bob Smith",
            role="Backend Engineer",
        )
        self.db.add(p)
        self.db.commit()

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "person_name": "Bob",
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["meeting_id"], str(self.meeting.id))
        self.assertTrue(data["extraction_complete"])

    def test_02_empty_participant_name(self) -> None:
        """Case 2: Empty participant name is rejected with 422 Unprocessable Entity."""
        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "person_name": "",
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_03_whitespace_only_participant_name(self) -> None:
        """Case 3: Whitespace-only participant name is rejected with 422 Unprocessable Entity."""
        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "person_name": "     \t \n ",
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_04_participant_with_matching_transcript_identity(self) -> None:
        """Case 4: Participant with matching transcript identity extracts their tasks."""
        transcript = (
            "Alice: We need to set up the infrastructure.\n"
            "Bob: Action item: I will prepare the database migration script.\n"
            "Charlie: Let's sync tomorrow."
        )
        meeting = self.create_meeting(self.user, title="Dev Sync", transcript=transcript)

        payload = {
            "meeting_id": str(meeting.id),
            "user_id": str(self.user.id),
            "person_name": "Bob",
        }
        res = self.client.post(f"/api/v1/extraction/{meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data["tasks"]), 1)
        # Task title / description should reflect Bob's action item
        task = data["tasks"][0]
        self.assertTrue(
            "migration" in task["title"].lower() or "migration" in (task.get("description") or "").lower()
        )

    def test_05_participant_with_no_matching_transcript_identity(self) -> None:
        """Case 5: Participant with no matching identity returns 0 tasks and clear structured highlight."""
        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "person_name": "Zaphod Beeblebrox",
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["tasks"]), 0)
        self.assertEqual(data["task_count"], 0)
        self.assertGreaterEqual(len(data["highlights"]), 1)
        self.assertIn("not found", data["highlights"][0]["content"].lower())

    def test_06_ambiguous_participant_identity(self) -> None:
        """Case 6: Ambiguous participant identity (multiple candidates) returns clear structured response."""
        p1 = MeetingParticipant(id=uuid.uuid4(), meeting_id=self.meeting.id, name="Alex Johnson")
        p2 = MeetingParticipant(id=uuid.uuid4(), meeting_id=self.meeting.id, name="Alex Morgan")
        self.db.add_all([p1, p2])
        self.db.commit()

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "person_name": "Alex",
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["tasks"]), 0)
        self.assertGreaterEqual(len(data["highlights"]), 1)
        self.assertIn("ambiguous", data["highlights"][0]["content"].lower())

    def test_07_ensure_another_participants_tasks_not_returned(self) -> None:
        """Case 7: Ensure another participant's tasks are NOT returned."""
        transcript = (
            "Bob: Action item: I will configure the firewall security rules.\n"
            "Alice: Action item: I will prepare the financial quarterly slides.\n"
        )
        meeting = self.create_meeting(self.user, title="Security & Finance", transcript=transcript)

        payload = {
            "meeting_id": str(meeting.id),
            "user_id": str(self.user.id),
            "person_name": "Alice",
        }
        res = self.client.post(f"/api/v1/extraction/{meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for task in data["tasks"]:
            combined = (task["title"] + " " + (task.get("description") or "")).lower()
            self.assertNotIn("firewall", combined)

    def test_08_ensure_logged_in_user_name_not_substituted(self) -> None:
        """Case 8: Ensure the logged-in user's profile is NOT substituted for explicit participant."""
        # Logged-in user is 'Alice LoggedIn'
        transcript = (
            "Alice: I need to book the conference venue.\n"
            "David: Action item: I will prepare the hardware inventory list.\n"
        )
        meeting = self.create_meeting(self.user, title="Inventory Sync", transcript=transcript)

        payload = {
            "meeting_id": str(meeting.id),
            "user_id": str(self.user.id),
            "person_name": "David",
        }
        res = self.client.post(f"/api/v1/extraction/{meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data["tasks"]), 1)
        task = data["tasks"][0]
        combined = (task["title"] + " " + (task.get("description") or "")).lower()
        self.assertIn("inventory", combined)
        self.assertNotIn("venue", combined)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TASK CONFIRMATION & PERSISTENCE TESTS (Cases 9 - 18)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskConfirmationPersistence(BaseExtractionTestCase):
    """Verifies Fix 2: Persistence of edited task descriptions and deadlines during confirmation."""

    def test_09_confirm_all_selected_tasks(self) -> None:
        """Case 1: Confirm all selected tasks persists all tasks to the database."""
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[
                {"id": "0", "title": "Task One", "priority": "high"},
                {"id": "1", "title": "Task Two", "priority": "medium"},
            ],
            highlights=[{"content": "Highlight One"}],
        )

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "yes",
            "confirmed_task_ids": ["0", "1"],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["saved_tasks"], 2)
        self.assertEqual(data["discarded_tasks"], 0)

        # Check DB records
        tasks_in_db = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(tasks_in_db), 2)
        titles = {t.title for t in tasks_in_db}
        self.assertIn("Task One", titles)
        self.assertIn("Task Two", titles)

    def test_10_confirm_only_a_subset_of_tasks(self) -> None:
        """Case 2: Confirm only a subset of tasks (partial) saves only confirmed IDs."""
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[
                {"id": "0", "title": "Keep Me", "priority": "high"},
                {"id": "1", "title": "Drop Me", "priority": "low"},
            ],
            highlights=[],
        )

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "partial",
            "confirmed_task_ids": ["0"],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["saved_tasks"], 1)
        self.assertEqual(data["discarded_tasks"], 1)

        tasks_in_db = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(tasks_in_db), 1)
        self.assertEqual(tasks_in_db[0].title, "Keep Me")

    def test_11_persist_edited_descriptions(self) -> None:
        """Case 3: Persist edited descriptions submitted during confirmation."""
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[{"id": "0", "title": "Design Mockups", "description": "Original raw description"}],
            highlights=[],
        )

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "yes",
            "confirmed_task_ids": ["0"],
            "modified_tasks": [
                {
                    "id": "0",
                    "title": "Design Mockups",
                    "description": "User edited high-priority mockups for mobile checkout.",
                }
            ],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 200)

        task_in_db = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).first()
        self.assertIsNotNone(task_in_db)
        self.assertEqual(task_in_db.description, "User edited high-priority mockups for mobile checkout.")

    def test_12_persist_edited_deadlines(self) -> None:
        """Case 4: Persist edited deadlines submitted during confirmation."""
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[{"id": "0", "title": "Deploy Service", "deadline": None}],
            highlights=[],
        )

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "yes",
            "confirmed_task_ids": ["0"],
            "modified_tasks": [
                {
                    "id": "0",
                    "title": "Deploy Service",
                    "deadline": "2026-11-15",
                }
            ],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 200)

        task_in_db = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).first()
        self.assertIsNotNone(task_in_db)
        self.assertIsNotNone(task_in_db.deadline)
        self.assertEqual(task_in_db.deadline.date(), date(2026, 11, 15))

    def test_13_preserve_excluded_tasks(self) -> None:
        """Case 5: Preserve excluded tasks without accidentally confirming them."""
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[
                {"id": "0", "title": "Included Task", "priority": "high"},
                {"id": "1", "title": "Excluded Task A", "priority": "medium"},
                {"id": "2", "title": "Excluded Task B", "priority": "low"},
            ],
            highlights=[],
        )

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "partial",
            "confirmed_task_ids": ["0"],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["saved_tasks"], 1)
        self.assertEqual(data["discarded_tasks"], 2)

        tasks_in_db = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(tasks_in_db), 1)
        self.assertEqual(tasks_in_db[0].title, "Included Task")

    def test_14_reject_invalid_task_ids(self) -> None:
        """Case 6: Reject invalid task IDs not in the extraction preview."""
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[{"id": "0", "title": "Valid Task"}],
            highlights=[],
        )

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "partial",
            "confirmed_task_ids": ["non_existent_id"],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        # Expected: 404 (InvalidOwnershipError)
        self.assertIn(res.status_code, [400, 404])

    def test_15_reject_tasks_belonging_to_another_meeting(self) -> None:
        """Case 7: Reject confirmation attempt with mismatched meeting ID in body."""
        other_meeting = self.create_meeting(self.user, title="Other Meeting")

        payload = {
            "meeting_id": str(other_meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "yes",
            "confirmed_task_ids": [],
        }
        # Post to meeting 1 endpoint but with meeting 2 ID in body
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 404)

    def test_16_reject_unauthorized_confirmation(self) -> None:
        """Case 8: Reject confirmation when user does not own the meeting."""
        other_user = self.create_user(name="Intruder", email="intruder@test.com")

        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[{"id": "0", "title": "Private Task"}],
            highlights=[],
        )

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(other_user.id),
            "user_confirmation": "yes",
            "confirmed_task_ids": [],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 404)

    def test_17_reject_invalid_deadlines(self) -> None:
        """Case 9: Reject invalid deadline format in confirmation payload with 422."""
        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "yes",
            "confirmed_task_ids": ["0"],
            "modified_tasks": [
                {
                    "id": "0",
                    "title": "Task",
                    "deadline": "not-a-valid-date",
                }
            ],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_18_verify_transaction_consistency(self) -> None:
        """Case 10: Verify transactional rollback on persistence failure."""
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[{"id": "0", "title": "Atomic Task"}],
            highlights=[{"content": "Highlight"}],
        )

        # Patch db.commit to raise an exception during confirmation persistence
        client_no_raise = TestClient(app, raise_server_exceptions=False)
        with patch.object(Session, "commit", side_effect=RuntimeError("Simulated DB Disk Failure")):
            payload = {
                "meeting_id": str(self.meeting.id),
                "user_id": str(self.user.id),
                "user_confirmation": "yes",
                "confirmed_task_ids": ["0"],
            }
            res = client_no_raise.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
            self.assertEqual(res.status_code, 500)

        # Ensure no tasks were committed
        tasks_in_db = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(tasks_in_db), 0)

    def test_19_duplicate_task_ids_rejected(self) -> None:
        """Rejects duplicate task IDs in confirmed_task_ids."""
        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "partial",
            "confirmed_task_ids": ["0", "0"],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_20_backward_compatibility_omitted_fields(self) -> None:
        """Verifies backward compatibility when person_name and modified_tasks are omitted."""
        # 1. Run extraction without person_name
        run_payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
        }
        res_run = self.client.post(f"/api/v1/extraction/{self.meeting.id}/run", json=run_payload)
        self.assertEqual(res_run.status_code, 200)

        # 2. Confirm without modified_tasks
        confirm_payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "yes",
            "confirmed_task_ids": [],
        }
        res_confirm = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=confirm_payload)
        self.assertEqual(res_confirm.status_code, 200)
        self.assertTrue(res_confirm.json()["confirmation_complete"])

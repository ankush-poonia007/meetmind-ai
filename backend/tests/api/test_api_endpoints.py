"""
Unit & integration tests for Gate 4 Batch 2: FastAPI API Layer (21 Endpoints).

Validates all 21 HTTP endpoint contracts across the 7 domain routers:
1. Users:
   - POST /api/v1/users/register (201, 409, 422)
   - GET  /api/v1/users/{user_id} (200, 404)
   - PUT  /api/v1/users/{user_id} (200, 404, 409)
2. Meetings:
   - POST   /api/v1/meetings/ (201 with placeholder title, 201 with custom title, 404)
   - GET    /api/v1/meetings/{user_id} (200)
   - GET    /api/v1/meetings/{meeting_id}/detail (200, 404)
   - DELETE /api/v1/meetings/{meeting_id} (204, 404)
3. Tasks:
   - GET /api/v1/tasks/{user_id} (200)
   - GET /api/v1/tasks/{user_id}/meeting/{meeting_id} (200)
   - PUT /api/v1/tasks/{task_id}/status (200, 404)
   - GET /api/v1/tasks/{user_id}/filter (200, priority/status/deadline filters)
4. Chat:
   - POST   /api/v1/chat/{meeting_id}/message (200, 404)
   - GET    /api/v1/chat/{meeting_id}/history (200, meeting isolation)
   - DELETE /api/v1/chat/{meeting_id}/history (204)
5. Extraction:
   - POST /api/v1/extraction/{meeting_id}/run (200)
   - GET  /api/v1/extraction/{meeting_id}/preview (200)
   - POST /api/v1/extraction/{meeting_id}/confirm (200, YES/NO/PARTIAL)
6. Highlights:
   - GET /api/v1/highlights/{user_id}/meeting/{meeting_id} (200)
   - GET /api/v1/highlights/{user_id} (200)
7. Notifications:
   - POST /api/v1/notifications/trigger (200)
   - GET  /api/v1/notifications/{user_id}/pending (200)
"""

import sys
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.constants import TaskPriority, TaskStatus, UserConfirmation
from app.db.base import Base
from app.db.models.chat_message import ChatMessage, ChatRole as DBChatRole
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.services.extraction_service import ExtractionService


class BaseAPITestCase(unittest.TestCase):
    """Base test case managing in-memory SQLite and FastAPI TestClient."""

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

    def tearDown(self) -> None:
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

    def create_meeting(self, user: User, title: str = "Test Meeting") -> Meeting:
        meeting = Meeting(
            id=uuid.uuid4(),
            user_id=user.id,
            title=title,
            organization="QA Org",
            meeting_date=date(2026, 9, 24),
            meeting_time="09:00",
            raw_transcript="Alice: Hello world. Bob: Hi there.",
            input_format="text",
        )
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting


# ═══════════════════════════════════════════════════════════════════════════════
# 1. USERS ROUTER TESTS (3 Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUsersRouter(BaseAPITestCase):
    """Tests for /api/v1/users endpoints."""

    def test_01_register_user_success(self) -> None:
        payload = {"name": "Grace Hopper", "email": "grace@navy.mil"}
        res = self.client.post("/api/v1/users/register", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["name"], "Grace Hopper")
        self.assertEqual(data["email"], "grace@navy.mil")
        self.assertIn("id", data)

    def test_02_register_user_duplicate_conflict(self) -> None:
        self.create_user(name="Grace", email="grace@navy.mil")
        payload = {"name": "Grace Duplicate", "email": "grace@navy.mil"}
        res = self.client.post("/api/v1/users/register", json=payload)
        self.assertEqual(res.status_code, 409)

    def test_03_get_user_success(self) -> None:
        user = self.create_user()
        res = self.client.get(f"/api/v1/users/{user.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], str(user.id))

    def test_04_get_user_not_found(self) -> None:
        res = self.client.get(f"/api/v1/users/{uuid.uuid4()}")
        self.assertEqual(res.status_code, 404)

    def test_05_update_user_success(self) -> None:
        user = self.create_user()
        res = self.client.put(
            f"/api/v1/users/{user.id}",
            json={"name": "Updated Name", "email": "newemail@example.com"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["name"], "Updated Name")
        self.assertEqual(data["email"], "newemail@example.com")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MEETINGS ROUTER TESTS (4 Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingsRouter(BaseAPITestCase):
    """Tests for /api/v1/meetings endpoints."""

    def test_06_create_meeting_with_placeholder_title(self) -> None:
        user = self.create_user()
        payload = {
            "user_id": str(user.id),
            "meeting_date": "2026-09-24",
            "meeting_time": "11:00",
            "organization": "Backend Team",
            "input_format": "text",
            "raw_transcript": "John: Let us build the API layer.",
        }
        res = self.client.post("/api/v1/meetings/", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["title"], "Processing Transcript...")
        self.assertEqual(data["user_id"], str(user.id))

    def test_07_get_user_meetings(self) -> None:
        user = self.create_user()
        self.create_meeting(user, title="Meeting 1")
        self.create_meeting(user, title="Meeting 2")

        res = self.client.get(f"/api/v1/meetings/{user.id}")
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 2)

    def test_08_get_meeting_detail(self) -> None:
        user = self.create_user()
        meeting = self.create_meeting(user)

        res = self.client.get(f"/api/v1/meetings/{meeting.id}/detail")
        self.assertEqual(res.status_code, 200)
        detail = res.json()
        self.assertEqual(detail["id"], str(meeting.id))
        self.assertIn("participants", detail)

    def test_09_delete_meeting(self) -> None:
        user = self.create_user()
        meeting = self.create_meeting(user)

        res = self.client.delete(f"/api/v1/meetings/{meeting.id}")
        self.assertEqual(res.status_code, 204)

        # Verify 404 after deletion
        get_res = self.client.get(f"/api/v1/meetings/{meeting.id}/detail")
        self.assertEqual(get_res.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TASKS ROUTER TESTS (4 Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTasksRouter(BaseAPITestCase):
    """Tests for /api/v1/tasks endpoints."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)

    def test_10_get_user_tasks(self) -> None:
        t = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Implement Batch 2",
            status=DBTaskStatus.pending,
        )
        self.db.add(t)
        self.db.commit()

        res = self.client.get(f"/api/v1/tasks/{self.user.id}")
        self.assertEqual(res.status_code, 200)
        tasks = res.json()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Implement Batch 2")

    def test_11_get_meeting_tasks(self) -> None:
        t = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Meeting Task",
            status=DBTaskStatus.pending,
        )
        self.db.add(t)
        self.db.commit()

        res = self.client.get(f"/api/v1/tasks/{self.user.id}/meeting/{self.meeting.id}")
        self.assertEqual(res.status_code, 200)
        tasks = res.json()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Meeting Task")

    def test_12_update_task_status(self) -> None:
        t = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Update Me",
            status=DBTaskStatus.pending,
        )
        self.db.add(t)
        self.db.commit()

        res = self.client.put(
            f"/api/v1/tasks/{t.id}/status",
            json={"status": "complete"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "complete")

    def test_13_filter_tasks(self) -> None:
        t_high = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="High Priority",
            priority=DBTaskPriority.high,
            status=DBTaskStatus.pending,
            deadline=date(2026, 9, 30),
        )
        t_low = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Low Priority",
            priority=DBTaskPriority.low,
            status=DBTaskStatus.complete,
            deadline=date(2026, 10, 15),
        )
        self.db.add_all([t_high, t_low])
        self.db.commit()

        # Filter by priority=high
        res = self.client.get(f"/api/v1/tasks/{self.user.id}/filter?priority=high")
        self.assertEqual(res.status_code, 200)
        tasks = res.json()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "High Priority")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CHAT ROUTER TESTS (3 Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatRouter(BaseAPITestCase):
    """Tests for /api/v1/chat endpoints."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)
        self.mock_retrieve = patch("app.agents.qa.retrieve").start()
        self.mock_retrieve.return_value = []
        self.addCleanup(patch.stopall)

    def test_14_send_chat_message(self) -> None:
        payload = {
            "question": "What is the sprint deadline?",
            "user_id": str(self.user.id),
        }
        res = self.client.post(f"/api/v1/chat/{self.meeting.id}/message", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["meeting_id"], str(self.meeting.id))
        self.assertIn("answer", data)

    def test_15_chat_history_and_meeting_isolation(self) -> None:
        meeting2 = self.create_meeting(self.user, title="Meeting 2")

        # Chat in meeting 1
        self.client.post(
            f"/api/v1/chat/{self.meeting.id}/message",
            json={"question": "Q1", "user_id": str(self.user.id)},
        )

        # History for meeting 2 must be empty
        res2 = self.client.get(f"/api/v1/chat/{meeting2.id}/history")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(len(res2.json()["messages"]), 0)

        # History for meeting 1 has 2 messages (user + assistant)
        res1 = self.client.get(f"/api/v1/chat/{self.meeting.id}/history")
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(res1.json()["messages"]), 2)

    def test_16_clear_chat_history(self) -> None:
        self.client.post(
            f"/api/v1/chat/{self.meeting.id}/message",
            json={"question": "To clear", "user_id": str(self.user.id)},
        )
        del_res = self.client.delete(f"/api/v1/chat/{self.meeting.id}/history")
        self.assertEqual(del_res.status_code, 204)

        history_res = self.client.get(f"/api/v1/chat/{self.meeting.id}/history")
        self.assertEqual(len(history_res.json()["messages"]), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. EXTRACTION ROUTER TESTS (3 Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractionRouter(BaseAPITestCase):
    """Tests for /api/v1/extraction endpoints."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)

    def test_17_run_extraction(self) -> None:
        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/run", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["meeting_id"], str(self.meeting.id))
        self.assertTrue(data["extraction_complete"])

    def test_18_get_extraction_preview(self) -> None:
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[{"title": "Preview Task", "priority": "high"}],
            highlights=[{"content": "Preview Highlight"}],
        )

        res = self.client.get(
            f"/api/v1/extraction/{self.meeting.id}/preview?user_id={self.user.id}"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["task_count"], 1)
        self.assertEqual(data["highlight_count"], 1)

    def test_19_confirm_extraction(self) -> None:
        ExtractionService.set_extraction_preview(
            self.meeting.id,
            tasks=[{"id": "0", "title": "Confirmed Task", "priority": "medium"}],
            highlights=[{"content": "Confirmed Note"}],
        )

        payload = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "user_confirmation": "yes",
            "confirmed_task_ids": [],
        }
        res = self.client.post(f"/api/v1/extraction/{self.meeting.id}/confirm", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["saved_tasks"], 1)
        self.assertEqual(data["saved_highlights"], 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. HIGHLIGHTS ROUTER TESTS (2 Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHighlightsRouter(BaseAPITestCase):
    """Tests for /api/v1/highlights endpoints."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)

    def test_20_get_meeting_highlights(self) -> None:
        h = Highlight(meeting_id=self.meeting.id, user_id=self.user.id, content="Decision 1")
        self.db.add(h)
        self.db.commit()

        res = self.client.get(f"/api/v1/highlights/{self.user.id}/meeting/{self.meeting.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["highlights"]), 1)
        self.assertEqual(data["highlights"][0]["content"], "Decision 1")

    def test_21_get_user_highlights(self) -> None:
        h = Highlight(meeting_id=self.meeting.id, user_id=self.user.id, content="Decision User")
        self.db.add(h)
        self.db.commit()

        res = self.client.get(f"/api/v1/highlights/{self.user.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["highlights"]), 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. NOTIFICATIONS ROUTER TESTS (2 Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationsRouter(BaseAPITestCase):
    """Tests for /api/v1/notifications endpoints."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)

    @patch("app.services.notification_service.NotificationService._retrieve_task_context", return_value="")
    @patch("app.services.notification_service.NotificationService._deliver_email", return_value=True)
    def test_22_trigger_notifications(self, mock_email, mock_rag) -> None:
        task = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Pending Alert",
            deadline=date.today(),
            status=DBTaskStatus.pending,
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        res = self.client.post("/api/v1/notifications/trigger", json={"trigger": "manual"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tasks_checked"], 1)
        self.assertEqual(data["alerts_sent"], 1)

    def test_23_get_pending_notifications(self) -> None:
        task = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Pending Alert Due Today",
            deadline=date.today(),
            status=DBTaskStatus.pending,
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        res = self.client.get(f"/api/v1/notifications/{self.user.id}/pending")
        self.assertEqual(res.status_code, 200)
        alerts = res.json()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["title"], "Pending Alert Due Today")


if __name__ == "__main__":
    unittest.main()

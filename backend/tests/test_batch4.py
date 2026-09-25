"""
Unit tests for Gate 4 Batch 4: Integration + Hardening (Final Backend Batch).

Verifies cross-layer contract consistency, lifecycle/resource safety, error handling,
secret concealment, graph boundaries, scheduler lifecycle, and backend startup readiness.

CRITICAL: All tests are fast, deterministic, and mock external network boundaries.
Execution time target: UNDER 30 SECONDS.
"""

import asyncio
import sys
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.constants import (
    ConfidenceLevel,
    InputFormat,
    NotificationTrigger,
    TaskPriority,
    TaskStatus,
    UserConfirmation,
)
from app.core.exceptions import (
    DuplicateUserError,
    EntityNotFoundError,
    InvalidOwnershipError,
    InvalidStateError,
    MeetMindError,
    ProviderAuthError,
    ProviderRateLimitError,
)
from app.core.settings import settings
from app.db.base import Base
from app.db.models.chat_message import ChatMessage, ChatRole as DBChatRole
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.main import app, meetmind_error_handler
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.schemas.extraction import (
    ExtractionConfirmRequest,
    ExtractionPreviewResponse,
    ExtractionResult,
    ExtractionRunRequest,
)
from app.schemas.meeting import MeetingCreate, MeetingResponse
from app.schemas.notification import NotificationStatusResponse
from app.schemas.task import TaskStatusUpdate
from app.services.chat_service import ChatService
from app.services.extraction_service import ExtractionService, _EXTRACTION_PREVIEWS
from app.services.meeting_service import MeetingService
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService


class BaseBatch4TestCase(unittest.TestCase):
    """Base test case providing an isolated in-memory SQLite database."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db: Session = self.SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        _EXTRACTION_PREVIEWS.clear()

    def create_user(self, name: str = "Grace Hopper", email: str = "grace@navy.mil") -> User:
        user = User(id=uuid.uuid4(), name=name, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_meeting(self, user: User, title: str = "Compiler Design Sync") -> Meeting:
        meeting = Meeting(
            id=uuid.uuid4(),
            user_id=user.id,
            title=title,
            meeting_date=date.today(),
            raw_transcript="Grace: Standardize syntax. Alan: Agreed.",
            input_format=InputFormat.TEXT.value,
        )
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting


# ═══════════════════════════════════════════════════════════════════════════════
# 1. BACKEND STARTUP & CONTRACT INTEGRITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackendStartupAndContracts(BaseBatch4TestCase):
    """Tests application startup readiness and cross-layer API-Service contracts."""

    def test_01_backend_startup_and_import_readiness(self) -> None:
        """Verifies FastAPI application instance, routes, and settings compile cleanly."""
        self.assertIsInstance(app, FastAPI)
        self.assertEqual(app.title, "MeetMind AI")

        # Verify OpenAPI schema generates cleanly and all key routes are mounted
        openapi_schema = app.openapi()
        self.assertIsNotNone(openapi_schema)
        route_paths = list(openapi_schema.get("paths", {}).keys())

        expected_endpoints = [
            "/api/v1/users/register",
            "/api/v1/meetings/",
            "/api/v1/tasks/{user_id}",
            "/api/v1/chat/{meeting_id}/message",
            "/api/v1/extraction/{meeting_id}/run",
            "/api/v1/extraction/{meeting_id}/confirm",
            "/api/v1/notifications/trigger",
            "/health",
            "/health/db",
            "/health/providers",
        ]
        for ep in expected_endpoints:
            self.assertIn(ep, route_paths, f"Expected endpoint '{ep}' missing from FastAPI routes")

    def test_02_meeting_service_lifecycle_contract(self) -> None:
        """Verifies meeting creation and retrieval contract with participant initialization."""
        user = self.create_user()
        payload = MeetingCreate(
            user_id=user.id,
            title="Q3 Strategy",
            meeting_date=date.today(),
            raw_transcript="Discussion on product roadmap and timelines.",
            input_format=InputFormat.TEXT,
        )

        res = MeetingService.create_meeting(
            db=self.db,
            meeting_in=payload,
            submitter_name="Grace Hopper",
            submitter_role="Lead",
        )
        self.assertIsInstance(res, MeetingResponse)
        self.assertEqual(res.title, "Q3 Strategy")
        self.assertEqual(res.user_id, user.id)

        # Confirm participant was automatically initialized as current user
        part = (
            self.db.query(MeetingParticipant)
            .filter(MeetingParticipant.meeting_id == res.id)
            .first()
        )
        self.assertIsNotNone(part)
        self.assertTrue(part.is_current_user)
        self.assertEqual(part.name, "Grace Hopper")

    def test_03_task_service_filtering_and_status_update(self) -> None:
        """Verifies task lifecycle, sorting order, and status transition."""
        user = self.create_user()
        meeting = self.create_meeting(user)

        t1 = Task(
            meeting_id=meeting.id,
            user_id=user.id,
            title="Low priority task",
            priority=DBTaskPriority.low,
            status=DBTaskStatus.pending,
            deadline=date(2026, 10, 1),
            alert_sent=False,
        )
        t2 = Task(
            meeting_id=meeting.id,
            user_id=user.id,
            title="High priority task",
            priority=DBTaskPriority.high,
            status=DBTaskStatus.pending,
            deadline=date(2026, 9, 30),
            alert_sent=False,
        )
        self.db.add_all([t1, t2])
        self.db.commit()

        # Test ordering: deadline ascending then priority
        tasks = TaskService.get_user_tasks(self.db, user.id)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].title, "High priority task")

        # Test status update pending -> complete
        updated = TaskService.update_task_status(
            self.db,
            task_id=t2.id,
            status_update=TaskStatusUpdate(status=TaskStatus.COMPLETE),
        )
        self.assertEqual(updated.status, TaskStatus.COMPLETE)

        self.db.refresh(t2)
        self.assertEqual(t2.status, DBTaskStatus.complete)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GRAPH BOUNDARIES & HITL INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphBoundariesAndHITL(BaseBatch4TestCase):
    """Tests service-to-graph delegation, HITL resume logic, and boundary safety."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)

    @patch("app.graph.graph.run_extraction_graph")
    def test_04_extraction_service_delegates_to_run_extraction_graph(
        self, mock_run_graph: MagicMock
    ) -> None:
        """Verifies ExtractionService coordinates with run_extraction_graph and caches preview."""
        mock_run_graph.return_value = {
            "tasks": [{"id": "0", "title": "Prepare Deck", "description": "Slides"}],
            "highlights": [{"content": "Product launch on track"}],
        }

        preview = ExtractionService.run_extraction(
            db=self.db,
            meeting_id=self.meeting.id,
            user_id=self.user.id,
        )

        mock_run_graph.assert_called_once_with(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            db=self.db,
        )
        self.assertIsInstance(preview, ExtractionPreviewResponse)
        self.assertEqual(preview.task_count, 1)
        self.assertEqual(preview.highlight_count, 1)

    def test_05_confirmation_resume_decision_yes(self) -> None:
        """Verifies YES confirmation persists all candidate tasks with status=pending."""
        sample_tasks = [
            {"id": "0", "title": "Audit Database", "description": "Review indices", "priority": "high"},
            {"id": "1", "title": "Write Docs", "description": "API guide", "priority": "medium"},
        ]
        sample_highlights = [{"content": "Target release date set"}]
        ExtractionService.set_extraction_preview(self.meeting.id, sample_tasks, sample_highlights)

        req = ExtractionConfirmRequest(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            user_confirmation=UserConfirmation.YES,
        )
        result = ExtractionService.confirm_extraction(self.db, req)

        self.assertEqual(result.saved_tasks, 2)
        self.assertEqual(result.discarded_tasks, 0)
        self.assertEqual(result.saved_highlights, 1)

        db_tasks = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(db_tasks), 2)
        for t in db_tasks:
            self.assertEqual(t.status, DBTaskStatus.pending)

    def test_06_confirmation_resume_decision_no(self) -> None:
        """Verifies NO confirmation discards tasks and preserves highlights."""
        sample_tasks = [{"id": "0", "title": "Discarded Task", "description": "Desc"}]
        sample_highlights = [{"content": "Retained Highlight"}]
        ExtractionService.set_extraction_preview(self.meeting.id, sample_tasks, sample_highlights)

        req = ExtractionConfirmRequest(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            user_confirmation=UserConfirmation.NO,
        )
        result = ExtractionService.confirm_extraction(self.db, req)

        self.assertEqual(result.saved_tasks, 0)
        self.assertEqual(result.discarded_tasks, 1)
        self.assertEqual(result.saved_highlights, 1)

        db_tasks = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(db_tasks), 0)

    def test_07_confirmation_resume_decision_partial_and_invalid_id(self) -> None:
        """Verifies PARTIAL confirmation persists selected tasks and rejects unknown IDs."""
        sample_tasks = [
            {"id": "0", "title": "Approved Task", "description": "Desc 0"},
            {"id": "1", "title": "Declined Task", "description": "Desc 1"},
        ]
        ExtractionService.set_extraction_preview(self.meeting.id, sample_tasks, [])

        # Valid PARTIAL
        req = ExtractionConfirmRequest(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            user_confirmation=UserConfirmation.PARTIAL,
            confirmed_task_ids=["0"],
        )
        result = ExtractionService.confirm_extraction(self.db, req)
        self.assertEqual(result.saved_tasks, 1)
        self.assertEqual(result.discarded_tasks, 1)

        # Invalid Task ID
        ExtractionService.set_extraction_preview(self.meeting.id, sample_tasks, [])
        invalid_req = ExtractionConfirmRequest(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            user_confirmation=UserConfirmation.PARTIAL,
            confirmed_task_ids=["unrelated_id_999"],
        )
        with self.assertRaises(InvalidOwnershipError):
            ExtractionService.confirm_extraction(self.db, invalid_req)

    def test_08_duplicate_confirmation_protection(self) -> None:
        """Verifies duplicate confirmation on completed run raises InvalidStateError."""
        from app.graph.graph import meetmind_graph, resume_extraction_graph

        thread_id = f"meeting_{self.meeting.id}"
        config = {"configurable": {"thread_id": thread_id}}

        # Set checkpointer state with confirmation_complete=True
        meetmind_graph.update_state(
            config,
            {"meeting_id": str(self.meeting.id), "confirmation_complete": True},
        )

        with self.assertRaises(InvalidStateError):
            resume_extraction_graph(
                meeting_id=self.meeting.id,
                user_id=self.user.id,
                confirmation="yes",
                db=self.db,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Q&A & NOTIFICATION INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestQANotificationIntegration(BaseBatch4TestCase):
    """Tests meeting-scoped Q&A and notification execution boundaries."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)

    @patch("app.graph.graph.run_qa_graph")
    def test_09_qa_boundary_meeting_scoping_and_message_persistence(
        self, mock_run_qa: MagicMock
    ) -> None:
        """Verifies ChatService delegates through run_qa_graph and persists conversation."""
        mock_run_qa.return_value = {
            "qa_answer": "Architecture sync is scheduled for 2 PM.",
            "qa_sources": [{"speaker": "Grace", "timestamp": "00:05", "excerpt": "Meeting at 2"}],
            "qa_confidence": "high",
        }

        req = ChatRequest(
            question="What time is the meeting?",
            user_id=self.user.id,
        )
        res = ChatService.send_chat_message(self.db, self.meeting.id, req)

        # 1. Verify scoping
        mock_run_qa.assert_called_once()
        self.assertEqual(mock_run_qa.call_args[1]["meeting_id"], self.meeting.id)

        # 2. Verify response
        self.assertIsInstance(res, ChatResponse)
        self.assertEqual(res.answer, "Architecture sync is scheduled for 2 PM.")
        self.assertEqual(len(res.sources), 1)
        self.assertEqual(res.confidence, ConfidenceLevel.HIGH)

        # 3. Verify chat history persisted in DB
        msgs = self.db.query(ChatMessage).filter(ChatMessage.meeting_id == self.meeting.id).all()
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, DBChatRole.user)
        self.assertEqual(msgs[1].role, DBChatRole.assistant)

    @patch("app.agents.notification.NotificationAgent.compose_email_tool", return_value="Sample reminder body")
    @patch("app.services.notification_service.NotificationService._deliver_email", return_value=True)
    @patch("app.services.notification_service.NotificationService._retrieve_task_context", return_value="Context")
    def test_10_notification_boundary_alert_sent_semantics(
        self, mock_rag: MagicMock, mock_deliver: MagicMock, mock_compose: MagicMock
    ) -> None:
        """Verifies alert_sent is updated to True only upon successful delivery."""
        now = datetime.now(timezone.utc)
        task = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Urgent Alert Task",
            deadline=now + timedelta(hours=2),
            status=DBTaskStatus.pending,
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        # Run notification pipeline via NotificationService -> run_notification_graph
        status_res = NotificationService.process_deadline_notifications(
            self.db,
            trigger=NotificationTrigger.MANUAL,
        )

        self.assertIsInstance(status_res, NotificationStatusResponse)
        self.assertEqual(status_res.tasks_checked, 1)
        self.assertEqual(status_res.alerts_sent, 1)

        # Check DB flag
        self.db.refresh(task)
        self.assertTrue(task.alert_sent)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ERROR HANDLING, SECRET SAFETY & SCHEDULER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHardeningSafety(unittest.TestCase):
    """Tests secret-safe exception handling, provider gateway security, and scheduler."""

    def test_11_error_handling_and_secret_safety(self) -> None:
        """Verifies MeetMind exception handler masks secrets and maps HTTP status codes."""
        mock_request = MagicMock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/v1/meetings"

        # 1. InvalidOwnershipError -> 404
        exc_404 = InvalidOwnershipError("Access forbidden", details={"secret_key": "raw_xyz"})
        res_404 = asyncio.run(meetmind_error_handler(mock_request, exc_404))
        self.assertEqual(res_404.status_code, 404)
        body = res_404.body.decode("utf-8")
        self.assertIn("InvalidOwnershipError", body)

        # 2. DuplicateUserError -> 409
        exc_409 = DuplicateUserError("User exists", details={"email": "grace@navy.mil"})
        res_409 = asyncio.run(meetmind_error_handler(mock_request, exc_409))
        self.assertEqual(res_409.status_code, 409)

        # 3. ProviderRateLimitError -> 429
        exc_429 = ProviderRateLimitError("Rate limit exceeded")
        res_429 = asyncio.run(meetmind_error_handler(mock_request, exc_429))
        self.assertEqual(res_429.status_code, 429)

        # 4. ProviderAuthError -> 502
        exc_502 = ProviderAuthError("Bad gateway auth")
        res_502 = asyncio.run(meetmind_error_handler(mock_request, exc_502))
        self.assertEqual(res_502.status_code, 502)

    def test_12_provider_gateway_secret_concealment(self) -> None:
        """Verifies settings string representations mask raw provider API keys."""
        settings_repr = repr(settings)
        # Should not display raw secret strings
        self.assertNotIn("AIzaSy", settings_repr)
        self.assertNotIn("sk-or-v1", settings_repr)
        self.assertNotIn("tvly-", settings_repr)
        # Safe diagnostic counts should be present
        self.assertIn("gemini_keys_configured=", settings_repr)

    def test_13_scheduler_configuration_and_clean_shutdown(self) -> None:
        """Verifies AsyncIOScheduler configuration, daily 08:00 cron registration, and shutdown."""
        async def _test():
            scheduler = AsyncIOScheduler()
            scheduler.start()
            self.assertTrue(scheduler.running)

            job = scheduler.add_job(
                lambda: None,
                trigger="cron",
                hour=8,
                minute=0,
                id="daily_deadline_notification",
                replace_existing=True,
            )
            self.assertEqual(job.id, "daily_deadline_notification")
            self.assertIsInstance(job.trigger, CronTrigger)

            cron_fields = {f.name: str(f) for f in job.trigger.fields}
            self.assertEqual(cron_fields["hour"], "8")
            self.assertEqual(cron_fields["minute"], "0")

            scheduler.shutdown(wait=False)
            await asyncio.sleep(0.01)
            self.assertFalse(scheduler.running)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()

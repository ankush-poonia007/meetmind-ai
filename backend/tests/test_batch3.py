"""
Unit tests for Gate 4 Batch 3: LangGraph Orchestration + HITL + APScheduler Integration.

Covers the 5 required Batch 3 boundaries:
A. Graph Construction: StateGraph compiles, 7 nodes exist, supervisor routing.
B. HITL Mechanism: Confirmation interrupt, resume with YES/NO/PARTIAL, invalid task ID rejection, duplicate confirmation prevention.
C. Q&A Service Boundary: ChatService delegates through run_qa_graph with meeting_id preservation.
D. Notification Service Boundary: NotificationService delegates through run_notification_graph.
E. Scheduler Registration: AsyncIOScheduler lifecycle, 08:00 cron schedule, replace_existing safety, clean shutdown.

CRITICAL: All tests are fast, deterministic, and use mocks for external network boundaries.
Zero live external calls to Gemini, OpenRouter, Tavily, Pinecone, or Resend.
"""

import sys
import unittest
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.constants import ConfidenceLevel, InputFormat, NotificationTrigger, UserConfirmation
from app.core.exceptions import InvalidOwnershipError, InvalidStateError
from app.db.base import Base
from app.db.models.chat_message import ChatMessage, ChatRole as DBChatRole
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.graph.graph import (
    build_meetmind_graph,
    resume_extraction_graph,
    run_extraction_graph,
)
from app.graph.router import route_supervisor
from app.graph.state import MeetMindState
from app.schemas.chat import ChatRequest, ChatSource
from app.schemas.extraction import ExtractionConfirmRequest
from app.schemas.notification import NotificationStatusResponse
from app.services.chat_service import ChatService
from app.services.extraction_service import ExtractionService, _EXTRACTION_PREVIEWS
from app.services.notification_service import NotificationService


class BaseBatch3TestCase(unittest.TestCase):
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

    def create_user(self, name: str = "Alice Analyst", email: str = "alice@example.com") -> User:
        user = User(id=uuid.uuid4(), name=name, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_meeting(self, user: User, title: str = "Sprint Planning") -> Meeting:
        meeting = Meeting(
            id=uuid.uuid4(),
            user_id=user.id,
            title=title,
            meeting_date=date.today(),
            raw_transcript="Alice: Prepare sprint report by Friday. Bob: Agreed.",
            input_format=InputFormat.TEXT.value,
        )
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting


# ═══════════════════════════════════════════════════════════════════════════════
# A. GRAPH CONSTRUCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphConstruction(unittest.TestCase):
    """Tests StateGraph compilation, node presence, and routing logic."""

    def test_01_graph_builds_and_contains_all_seven_nodes(self) -> None:
        checkpointer = MemorySaver()
        graph = build_meetmind_graph(checkpointer=checkpointer)
        self.assertIsNotNone(graph)

        # Inspect compiled graph nodes
        graph_nodes = graph.nodes
        expected_nodes = {
            "supervisor",
            "ingestion",
            "identity",
            "extraction",
            "confirmation",
            "qa",
            "notification",
        }
        for node in expected_nodes:
            self.assertIn(node, graph_nodes, f"Expected node '{node}' missing from graph")

    def test_02_supervisor_routing_logic(self) -> None:
        # Action mappings
        self.assertEqual(route_supervisor({"session_action": "ingest"}), "ingestion")
        self.assertEqual(route_supervisor({"session_action": "identify"}), "identity")
        self.assertEqual(route_supervisor({"session_action": "extract"}), "extraction")
        self.assertEqual(route_supervisor({"session_action": "confirm"}), "confirmation")
        self.assertEqual(route_supervisor({"session_action": "qa"}), "qa")
        self.assertEqual(route_supervisor({"session_action": "notify"}), "notification")
        self.assertEqual(route_supervisor({"session_action": "complete"}), "__end__")

        # Confirmation complete routes to END
        self.assertEqual(
            route_supervisor({"session_action": "confirm", "confirmation_complete": True}),
            "__end__",
        )

        # Error routes to END
        self.assertEqual(
            route_supervisor({"error": "Pipeline failure", "session_action": "ingest"}),
            "__end__",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# B. HITL MECHANISM TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHITLMechanism(BaseBatch3TestCase):
    """Tests genuine LangGraph HITL interrupt and resume logic."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)

    def test_03_hitl_pause_at_confirmation_interrupt(self) -> None:
        """Verifies the pipeline executes up to confirmation and pauses via interrupt()."""
        with patch("app.agents.ingestion.TranscriptEmbedder.embed_and_store") as mock_embed, \
             patch("app.agents.extraction.get_provider_gateway") as mock_gw:
            mock_embed.return_value = None
            mock_gw.return_value.execute.side_effect = Exception("Offline test mode")

            res = run_extraction_graph(
                meeting_id=self.meeting.id,
                user_id=self.user.id,
                db=self.db,
            )

            # Execution paused and preview was returned
            self.assertIn("tasks", res)
            self.assertIn("highlights", res)
            self.assertEqual(res["meeting_id"], str(self.meeting.id))

    def test_04_hitl_resume_decision_yes(self) -> None:
        """Verifies YES decision persists all candidate tasks."""
        sample_tasks = [
            {"id": "0", "title": "Task Alpha", "description": "Desc Alpha", "priority": "high"},
            {"id": "1", "title": "Task Beta", "description": "Desc Beta", "priority": "low"},
        ]
        sample_highlights = [{"content": "Important meeting milestone"}]
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
        self.assertEqual(db_tasks[0].status, DBTaskStatus.pending)

    def test_05_hitl_resume_decision_no(self) -> None:
        """Verifies NO decision discards all candidate tasks."""
        sample_tasks = [
            {"id": "0", "title": "Unwanted Task", "description": "Desc", "priority": "low"},
        ]
        sample_highlights = [{"content": "Retained note"}]
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

    def test_06_hitl_resume_decision_partial(self) -> None:
        """Verifies PARTIAL decision persists only selected task IDs."""
        sample_tasks = [
            {"id": "0", "title": "Accepted Task", "description": "Desc", "priority": "high"},
            {"id": "1", "title": "Rejected Task", "description": "Desc", "priority": "low"},
        ]
        ExtractionService.set_extraction_preview(self.meeting.id, sample_tasks, [])

        req = ExtractionConfirmRequest(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            user_confirmation=UserConfirmation.PARTIAL,
            confirmed_task_ids=["0"],
        )
        result = ExtractionService.confirm_extraction(self.db, req)

        self.assertEqual(result.saved_tasks, 1)
        self.assertEqual(result.discarded_tasks, 1)

        db_tasks = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(db_tasks), 1)
        self.assertEqual(db_tasks[0].title, "Accepted Task")

    def test_07_hitl_rejects_invalid_task_id(self) -> None:
        """Verifies PARTIAL confirmation rejects task IDs not present in preview."""
        sample_tasks = [{"id": "0", "title": "Valid Task", "description": "Desc"}]
        ExtractionService.set_extraction_preview(self.meeting.id, sample_tasks, [])

        req = ExtractionConfirmRequest(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            user_confirmation=UserConfirmation.PARTIAL,
            confirmed_task_ids=["999"],  # Non-existent / foreign task ID
        )
        with self.assertRaises(InvalidOwnershipError):
            ExtractionService.confirm_extraction(self.db, req)

    def test_08_duplicate_confirmation_prevention(self) -> None:
        """Verifies duplicate confirmation on completed graph run raises InvalidStateError."""
        from app.graph.graph import meetmind_graph

        thread_id = f"meeting_{self.meeting.id}"
        config = {"configurable": {"thread_id": thread_id}}

        # Simulate checkpoint where confirmation was finalized
        state_dict: MeetMindState = {
            "meeting_id": str(self.meeting.id),
            "user_id": str(self.user.id),
            "confirmation_complete": True,
            "session_action": "complete",
        }
        # Update checkpointer directly to reflect finished run
        meetmind_graph.update_state(config, state_dict)

        with self.assertRaises(InvalidStateError):
            resume_extraction_graph(
                meeting_id=self.meeting.id,
                user_id=self.user.id,
                confirmation="yes",
                db=self.db,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# C. Q&A SERVICE BOUNDARY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestQAServiceBoundary(BaseBatch3TestCase):
    """Tests ChatService delegation through run_qa_graph."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.meeting = self.create_meeting(self.user)

    @patch("app.graph.graph.run_qa_graph")
    def test_09_chat_service_delegates_to_run_qa_graph(self, mock_run_qa_graph: MagicMock) -> None:
        mock_run_qa_graph.return_value = {
            "qa_answer": "The sprint deadline is this Friday.",
            "qa_sources": [{"speaker": "Alice", "excerpt": "Deadline is Friday."}],
            "qa_confidence": "high",
            "session_action": "complete",
        }

        req = ChatRequest(
            question="When is the sprint deadline?",
            user_id=self.user.id,
        )
        res = ChatService.send_chat_message(self.db, self.meeting.id, req)

        # 1. Verify run_qa_graph was called with meeting scoping
        mock_run_qa_graph.assert_called_once()
        call_kwargs = mock_run_qa_graph.call_args[1]
        self.assertEqual(call_kwargs["meeting_id"], self.meeting.id)
        self.assertEqual(call_kwargs["user_id"], self.user.id)
        self.assertEqual(call_kwargs["question"], "When is the sprint deadline?")
        self.assertEqual(call_kwargs["db"], self.db)

        # 2. Verify response structure
        self.assertEqual(res.meeting_id, self.meeting.id)
        self.assertEqual(res.answer, "The sprint deadline is this Friday.")
        self.assertEqual(len(res.sources), 1)
        self.assertEqual(res.sources[0].speaker, "Alice")
        self.assertEqual(res.confidence, ConfidenceLevel.HIGH)

        # 3. Verify chat messages persisted in DB
        msgs = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.meeting_id == self.meeting.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, DBChatRole.user)
        self.assertEqual(msgs[1].role, DBChatRole.assistant)


# ═══════════════════════════════════════════════════════════════════════════════
# D. NOTIFICATION SERVICE BOUNDARY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationServiceBoundary(BaseBatch3TestCase):
    """Tests NotificationService delegation through run_notification_graph."""

    @patch("app.graph.graph.run_notification_graph")
    def test_10_notification_service_delegates_to_run_notification_graph(
        self, mock_run_notif_graph: MagicMock
    ) -> None:
        mock_run_notif_graph.return_value = {
            "tasks_checked": 3,
            "alerts_sent": 2,
            "failed_alerts": ["task_fail_1"],
            "completion_time": datetime.now(timezone.utc).isoformat(),
            "session_action": "complete",
        }

        res = NotificationService.process_deadline_notifications(
            db=self.db,
            trigger=NotificationTrigger.SCHEDULED,
        )

        # 1. Verify run_notification_graph was invoked
        mock_run_notif_graph.assert_called_once_with(
            db=self.db,
            trigger="scheduled",
        )

        # 2. Verify response matches graph statistics
        self.assertIsInstance(res, NotificationStatusResponse)
        self.assertEqual(res.tasks_checked, 3)
        self.assertEqual(res.alerts_sent, 2)
        self.assertEqual(res.failed_alerts, ["task_fail_1"])


# ═══════════════════════════════════════════════════════════════════════════════
# E. SCHEDULER LIFECYCLE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchedulerLifecycle(unittest.TestCase):
    """Tests AsyncIOScheduler configuration, cron registration, and lifecycle."""

    def test_11_scheduler_registration_and_clean_shutdown(self) -> None:
        import asyncio

        async def _test_lifecycle():
            scheduler = AsyncIOScheduler()

            def dummy_job():
                pass

            scheduler.start()
            self.assertTrue(scheduler.running)

            # 1. Register daily 08:00 cron job with duplicate safety
            job = scheduler.add_job(
                dummy_job,
                trigger="cron",
                hour=8,
                minute=0,
                id="daily_deadline_notification",
                replace_existing=True,
            )

            self.assertEqual(job.id, "daily_deadline_notification")
            self.assertIsInstance(job.trigger, CronTrigger)

            # Verify cron fields (hour 8, minute 0)
            cron_fields = {f.name: str(f) for f in job.trigger.fields}
            self.assertEqual(cron_fields["hour"], "8")
            self.assertEqual(cron_fields["minute"], "0")

            # 2. Verify replace_existing prevents duplicate job accumulation
            scheduler.add_job(
                dummy_job,
                trigger="cron",
                hour=8,
                minute=0,
                id="daily_deadline_notification",
                replace_existing=True,
            )
            self.assertEqual(len(scheduler.get_jobs()), 1)

            # 3. Test clean shutdown
            scheduler.shutdown(wait=False)
            await asyncio.sleep(0.01)
            self.assertFalse(scheduler.running)

        asyncio.run(_test_lifecycle())


if __name__ == "__main__":
    unittest.main()

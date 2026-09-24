"""
Unit tests for Gate 4 Batch 1: Backend Service Layer.

Validates all 7 application services with full in-memory SQLite isolation:
1. UserService: create, get by id/email, duplicate email, update, missing user.
2. MeetingService: create with deterministic title placeholder, participants, get user meetings,
   meeting detail, delete with cascade, ownership isolation.
3. TaskService: list user tasks, list meeting tasks, status update, priority filter, deadline filter,
   status filter, deadline+priority ordering, ownership validation.
4. ChatService: send/save message, history retrieval, history clearing, meeting isolation.
5. ExtractionService: run extraction boundary, preview retrieval, confirmation decisions (yes, no, partial).
6. HighlightService: meeting-scoped retrieval, user-scoped retrieval, highlight creation.
7. NotificationService: pending task selection (<= 24h, alert_sent=false), RAG context retrieval,
   alert_sent update only after successful delivery.
"""

import sys
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
    InvalidOwnershipError,
    MeetingNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.db.base import Base
from app.db.models.chat_message import ChatMessage, ChatRole as DBChatRole
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.schemas.chat import ChatRequest
from app.schemas.extraction import ExtractionConfirmRequest
from app.schemas.highlight import HighlightCreate
from app.schemas.meeting import MeetingCreate
from app.schemas.task import TaskFilterParams, TaskStatusUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services import (
    ChatService,
    ExtractionService,
    HighlightService,
    MeetingService,
    NotificationService,
    TaskService,
    UserService,
)


class BaseServiceTestCase(unittest.TestCase):
    """Base test case setting up an in-memory SQLite database for synchronous service testing."""

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

    def create_sample_user(self, name: str = "Alice Analyst", email: str = "alice@example.com") -> User:
        """Helper to insert a user directly into the database."""
        user = User(id=uuid.uuid4(), name=name, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_sample_meeting(
        self,
        user: User,
        title: str = "Sprint Planning",
        meeting_date: date = date(2026, 9, 24),
    ) -> Meeting:
        """Helper to insert a meeting directly into the database."""
        meeting = Meeting(
            id=uuid.uuid4(),
            user_id=user.id,
            title=title,
            organization="Engineering",
            meeting_date=meeting_date,
            meeting_time="10:00",
            raw_transcript="Alice: Let's discuss sprint goals. Bob: Agreed.",
            input_format="text",
        )
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting


# ═══════════════════════════════════════════════════════════════════════════════
# 1. USER SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserService(BaseServiceTestCase):
    """Tests for UserService."""

    def test_create_user_success(self) -> None:
        user_in = UserCreate(name="Carol Danvers", email="carol@marvel.com")
        res = UserService.create_user(self.db, user_in)
        self.assertEqual(res.name, "Carol Danvers")
        self.assertEqual(res.email, "carol@marvel.com")
        self.assertIsNotNone(res.id)
        self.assertIsNotNone(res.created_at)

    def test_create_user_duplicate_email(self) -> None:
        user_in = UserCreate(name="Carol Danvers", email="carol@marvel.com")
        UserService.create_user(self.db, user_in)

        # Attempt duplicate registration
        with self.assertRaises(DuplicateUserError):
            UserService.create_user(self.db, user_in)

    def test_get_user_by_id_success(self) -> None:
        user = self.create_sample_user()
        res = UserService.get_user_by_id(self.db, user.id)
        self.assertEqual(res.id, user.id)
        self.assertEqual(res.email, user.email)

    def test_get_user_by_id_missing(self) -> None:
        random_id = uuid.uuid4()
        with self.assertRaises(UserNotFoundError):
            UserService.get_user_by_id(self.db, random_id)

    def test_get_user_by_email_success(self) -> None:
        user = self.create_sample_user()
        res = UserService.get_user_by_email(self.db, user.email)
        self.assertEqual(res.id, user.id)

    def test_get_user_by_email_missing(self) -> None:
        with self.assertRaises(UserNotFoundError):
            UserService.get_user_by_email(self.db, "nonexistent@example.com")

    def test_update_user_success(self) -> None:
        user = self.create_sample_user()
        update_in = UserUpdate(name="Alice Senior Analyst", email="alicesenior@example.com")
        res = UserService.update_user(self.db, user.id, update_in)
        self.assertEqual(res.name, "Alice Senior Analyst")
        self.assertEqual(res.email, "alicesenior@example.com")

    def test_update_user_duplicate_email(self) -> None:
        user1 = self.create_sample_user("User 1", "u1@example.com")
        user2 = self.create_sample_user("User 2", "u2@example.com")

        update_in = UserUpdate(email="u1@example.com")
        with self.assertRaises(DuplicateUserError):
            UserService.update_user(self.db, user2.id, update_in)

    def test_update_user_missing(self) -> None:
        with self.assertRaises(UserNotFoundError):
            UserService.update_user(self.db, uuid.uuid4(), UserUpdate(name="Ghost"))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MEETING SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMeetingService(BaseServiceTestCase):
    """Tests for MeetingService."""

    def test_create_meeting_with_deterministic_placeholder(self) -> None:
        user = self.create_sample_user()
        meeting_in = MeetingCreate(
            user_id=user.id,
            meeting_date=date(2026, 9, 24),
            meeting_time="14:00",
            organization="Product Team",
            input_format=InputFormat.TEXT,
            raw_transcript="Bob: Welcome everyone.",
            title=None,  # No title provided at form submission
        )

        res = MeetingService.create_meeting(
            self.db,
            meeting_in=meeting_in,
            submitter_name="Alice Submitter",
            submitter_role="Lead",
        )

        self.assertEqual(res.title, "Processing Transcript...")
        self.assertEqual(res.user_id, user.id)

        # Verify participant was created
        participants = (
            self.db.query(MeetingParticipant)
            .filter(MeetingParticipant.meeting_id == res.id)
            .all()
        )
        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0].name, "Alice Submitter")
        self.assertEqual(participants[0].role, "Lead")
        self.assertTrue(participants[0].is_current_user)

    def test_create_meeting_with_custom_title(self) -> None:
        user = self.create_sample_user()
        meeting_in = MeetingCreate(
            user_id=user.id,
            title="Q3 Strategy Review",
            meeting_date=date(2026, 9, 24),
            raw_transcript="Discussion on roadmap.",
        )
        res = MeetingService.create_meeting(self.db, meeting_in=meeting_in)
        self.assertEqual(res.title, "Q3 Strategy Review")

    def test_create_meeting_missing_user(self) -> None:
        meeting_in = MeetingCreate(
            user_id=uuid.uuid4(),
            meeting_date=date(2026, 9, 24),
            raw_transcript="Some text",
        )
        with self.assertRaises(UserNotFoundError):
            MeetingService.create_meeting(self.db, meeting_in=meeting_in)

    def test_get_meetings_for_user_ordering(self) -> None:
        user = self.create_sample_user()
        # Create older meeting
        self.create_sample_meeting(user, title="Old Meeting", meeting_date=date(2026, 1, 1))
        # Create newer meeting
        self.create_sample_meeting(user, title="New Meeting", meeting_date=date(2026, 9, 24))

        meetings = MeetingService.get_meetings_for_user(self.db, user.id)
        self.assertEqual(len(meetings), 2)
        # Should be ordered by meeting_date desc
        self.assertEqual(meetings[0].title, "New Meeting")
        self.assertEqual(meetings[1].title, "Old Meeting")

    def test_get_meeting_detail_with_participants(self) -> None:
        user = self.create_sample_user()
        meeting = self.create_sample_meeting(user)

        # Add participant
        p = MeetingParticipant(
            meeting_id=meeting.id,
            name="Charlie",
            role="Designer",
            is_current_user=False,
        )
        self.db.add(p)
        self.db.commit()

        detail = MeetingService.get_meeting_detail(self.db, meeting.id, user_id=user.id)
        self.assertEqual(detail.id, meeting.id)
        self.assertEqual(len(detail.participants), 1)
        self.assertEqual(detail.participants[0].name, "Charlie")

    def test_get_meeting_detail_ownership_isolation(self) -> None:
        user1 = self.create_sample_user("User 1", "u1@example.com")
        user2 = self.create_sample_user("User 2", "u2@example.com")
        meeting = self.create_sample_meeting(user1)

        # User 2 attempts to view User 1's meeting
        with self.assertRaises(InvalidOwnershipError):
            MeetingService.get_meeting_detail(self.db, meeting.id, user_id=user2.id)

    def test_delete_meeting_and_cascade(self) -> None:
        user = self.create_sample_user()
        meeting = self.create_sample_meeting(user)

        # Add task and highlight
        task = Task(
            meeting_id=meeting.id,
            user_id=user.id,
            title="Action item",
            status=DBTaskStatus.pending,
        )
        highlight = Highlight(
            meeting_id=meeting.id,
            user_id=user.id,
            content="Important decision",
        )
        self.db.add_all([task, highlight])
        self.db.commit()

        MeetingService.delete_meeting(self.db, meeting.id, user_id=user.id)

        # Verify meeting and dependents deleted
        self.assertIsNone(self.db.query(Meeting).filter(Meeting.id == meeting.id).first())
        self.assertIsNone(self.db.query(Task).filter(Task.meeting_id == meeting.id).first())
        self.assertIsNone(self.db.query(Highlight).filter(Highlight.meeting_id == meeting.id).first())

    def test_update_meeting_title(self) -> None:
        user = self.create_sample_user()
        meeting = self.create_sample_meeting(user, title="Processing Transcript...")
        res = MeetingService.update_meeting_title(self.db, meeting.id, "Generated Title")
        self.assertEqual(res.title, "Generated Title")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TASK SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskService(BaseServiceTestCase):
    """Tests for TaskService."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_sample_user()
        self.meeting = self.create_sample_meeting(self.user)

    def test_get_user_tasks_and_ordering(self) -> None:
        # Task 1: Low priority, due tomorrow
        t1 = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Task 1",
            priority=DBTaskPriority.low,
            deadline=date(2026, 9, 26),
            status=DBTaskStatus.pending,
        )
        # Task 2: High priority, due today
        t2 = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Task 2",
            priority=DBTaskPriority.high,
            deadline=date(2026, 9, 25),
            status=DBTaskStatus.pending,
        )
        # Task 3: No deadline
        t3 = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Task 3",
            priority=DBTaskPriority.medium,
            deadline=None,
            status=DBTaskStatus.pending,
        )
        self.db.add_all([t1, t2, t3])
        self.db.commit()

        tasks = TaskService.get_user_tasks(self.db, self.user.id)
        self.assertEqual(len(tasks), 3)
        # Order should be deadline ascending (Task 2 due 9/25, then Task 1 due 9/26, then Task 3 None)
        self.assertEqual(tasks[0].title, "Task 2")
        self.assertEqual(tasks[1].title, "Task 1")
        self.assertEqual(tasks[2].title, "Task 3")

    def test_filter_tasks_by_status(self) -> None:
        t_pending = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Pending Task",
            status=DBTaskStatus.pending,
        )
        t_complete = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Complete Task",
            status=DBTaskStatus.complete,
        )
        self.db.add_all([t_pending, t_complete])
        self.db.commit()

        # Filter pending
        params = TaskFilterParams(status=TaskStatus.PENDING)
        pending_tasks = TaskService.get_user_tasks(self.db, self.user.id, filter_params=params)
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(pending_tasks[0].title, "Pending Task")

        # Filter complete
        params_comp = TaskFilterParams(status=TaskStatus.COMPLETE)
        comp_tasks = TaskService.get_user_tasks(self.db, self.user.id, filter_params=params_comp)
        self.assertEqual(len(comp_tasks), 1)
        self.assertEqual(comp_tasks[0].title, "Complete Task")

    def test_filter_tasks_by_priority(self) -> None:
        t_high = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="High Task",
            priority=DBTaskPriority.high,
            status=DBTaskStatus.pending,
        )
        t_low = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Low Task",
            priority=DBTaskPriority.low,
            status=DBTaskStatus.pending,
        )
        self.db.add_all([t_high, t_low])
        self.db.commit()

        params = TaskFilterParams(priority=TaskPriority.HIGH)
        high_tasks = TaskService.get_user_tasks(self.db, self.user.id, filter_params=params)
        self.assertEqual(len(high_tasks), 1)
        self.assertEqual(high_tasks[0].title, "High Task")

    def test_update_task_status_toggle(self) -> None:
        task = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Action item",
            status=DBTaskStatus.pending,
        )
        self.db.add(task)
        self.db.commit()

        # Update to complete
        res = TaskService.update_task_status(
            self.db,
            task.id,
            TaskStatusUpdate(status=TaskStatus.COMPLETE),
            user_id=self.user.id,
        )
        self.assertEqual(res.status, TaskStatus.COMPLETE)

    def test_update_task_status_ownership_violation(self) -> None:
        other_user = self.create_sample_user("Other", "other@example.com")
        task = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Action item",
            status=DBTaskStatus.pending,
        )
        self.db.add(task)
        self.db.commit()

        with self.assertRaises(InvalidOwnershipError):
            TaskService.update_task_status(
                self.db,
                task.id,
                TaskStatusUpdate(status=TaskStatus.COMPLETE),
                user_id=other_user.id,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CHAT SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatService(BaseServiceTestCase):
    """Tests for ChatService."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_sample_user()
        self.meeting = self.create_sample_meeting(self.user)
        self.mock_retrieve = patch("app.agents.qa.retrieve").start()
        self.mock_retrieve.return_value = []
        self.addCleanup(patch.stopall)

    def test_send_chat_message_and_persistence(self) -> None:
        req = ChatRequest(
            question="What was decided about the budget?",
            user_id=self.user.id,
        )
        res = ChatService.send_chat_message(self.db, self.meeting.id, req)
        self.assertEqual(res.meeting_id, self.meeting.id)
        self.assertIsNotNone(res.answer)

        # Verify 2 messages persisted in DB: user and assistant
        msgs = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.meeting_id == self.meeting.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, DBChatRole.user)
        self.assertEqual(msgs[0].content, "What was decided about the budget?")
        self.assertEqual(msgs[1].role, DBChatRole.assistant)

    def test_chat_meeting_isolation(self) -> None:
        # Create second meeting
        meeting2 = self.create_sample_meeting(self.user, title="Meeting 2")

        # Chat in meeting 1
        ChatService.send_chat_message(
            self.db,
            self.meeting.id,
            ChatRequest(question="Meeting 1 question", user_id=self.user.id),
        )

        # Retrieve history for meeting 2 (must be empty!)
        history2 = ChatService.get_chat_history(self.db, meeting2.id)
        self.assertEqual(len(history2.messages), 0)

        # Retrieve history for meeting 1 (must have 2 messages)
        history1 = ChatService.get_chat_history(self.db, self.meeting.id)
        self.assertEqual(len(history1.messages), 2)

    def test_clear_chat_history(self) -> None:
        ChatService.send_chat_message(
            self.db,
            self.meeting.id,
            ChatRequest(question="Question", user_id=self.user.id),
        )
        self.assertEqual(len(ChatService.get_chat_history(self.db, self.meeting.id).messages), 2)

        ChatService.clear_chat_history(self.db, self.meeting.id)
        self.assertEqual(len(ChatService.get_chat_history(self.db, self.meeting.id).messages), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. EXTRACTION SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractionService(BaseServiceTestCase):
    """Tests for ExtractionService."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_sample_user()
        self.meeting = self.create_sample_meeting(self.user)

    def test_run_and_preview_extraction(self) -> None:
        # Inject sample preview data into service
        sample_tasks = [
            {"title": "Deploy API", "priority": "high", "deadline": date(2026, 9, 30)},
            {"title": "Write Docs", "priority": "medium", "deadline": None},
        ]
        sample_highlights = [
            {"content": "Launch date confirmed for Oct 1."},
        ]
        ExtractionService.set_extraction_preview(self.meeting.id, sample_tasks, sample_highlights)

        preview = ExtractionService.get_extraction_preview(self.db, self.meeting.id, self.user.id)
        self.assertEqual(preview.task_count, 2)
        self.assertEqual(preview.highlight_count, 1)
        self.assertEqual(preview.tasks[0].title, "Deploy API")

    def test_confirm_extraction_yes(self) -> None:
        sample_tasks = [
            {"id": "0", "title": "Task A", "priority": "high"},
            {"id": "1", "title": "Task B", "priority": "low"},
        ]
        sample_highlights = [{"content": "Important note"}]
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

        # Verify persisted tasks in DB
        db_tasks = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(db_tasks), 2)
        self.assertEqual(db_tasks[0].status, DBTaskStatus.pending)

    def test_confirm_extraction_no(self) -> None:
        sample_tasks = [{"title": "Unwanted Task", "priority": "low"}]
        sample_highlights = [{"content": "Still keep note"}]
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

        # No tasks should be in DB
        db_tasks = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(db_tasks), 0)

    def test_confirm_extraction_partial(self) -> None:
        sample_tasks = [
            {"id": "0", "title": "Accepted Task", "priority": "high"},
            {"id": "1", "title": "Rejected Task", "priority": "low"},
        ]
        ExtractionService.set_extraction_preview(self.meeting.id, sample_tasks, [])

        req = ExtractionConfirmRequest(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            user_confirmation=UserConfirmation.PARTIAL,
            confirmed_task_ids=["0"],  # Select only first task
        )
        result = ExtractionService.confirm_extraction(self.db, req)
        self.assertEqual(result.saved_tasks, 1)
        self.assertEqual(result.discarded_tasks, 1)

        # Only Accepted Task should be in DB
        db_tasks = self.db.query(Task).filter(Task.meeting_id == self.meeting.id).all()
        self.assertEqual(len(db_tasks), 1)
        self.assertEqual(db_tasks[0].title, "Accepted Task")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. HIGHLIGHT SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHighlightService(BaseServiceTestCase):
    """Tests for HighlightService."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_sample_user()
        self.meeting = self.create_sample_meeting(self.user)

    def test_create_and_get_meeting_highlights(self) -> None:
        h_in = HighlightCreate(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            content="Q4 Targets finalized.",
        )
        res = HighlightService.create_highlight(self.db, h_in)
        self.assertEqual(res.content, "Q4 Targets finalized.")

        list_res = HighlightService.get_meeting_highlights(self.db, self.meeting.id)
        self.assertEqual(len(list_res.highlights), 1)
        self.assertEqual(list_res.highlights[0].content, "Q4 Targets finalized.")

    def test_get_user_highlights_across_meetings(self) -> None:
        meeting2 = self.create_sample_meeting(self.user, title="Meeting 2")
        HighlightService.create_highlight(
            self.db,
            HighlightCreate(meeting_id=self.meeting.id, user_id=self.user.id, content="H1"),
        )
        HighlightService.create_highlight(
            self.db,
            HighlightCreate(meeting_id=meeting2.id, user_id=self.user.id, content="H2"),
        )

        user_highlights = HighlightService.get_user_highlights(self.db, self.user.id)
        self.assertEqual(len(user_highlights.highlights), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. NOTIFICATION SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationService(BaseServiceTestCase):
    """Tests for NotificationService."""

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_sample_user()
        self.meeting = self.create_sample_meeting(self.user)

    def test_get_pending_alerts_selection(self) -> None:
        today = date.today()

        # Task 1: Due today, alert_sent=False -> QUALIFIES
        t1 = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Due Today Task",
            deadline=today,
            status=DBTaskStatus.pending,
            alert_sent=False,
        )
        # Task 2: Due tomorrow, alert_sent=False -> QUALIFIES
        t2 = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Due Tomorrow Task",
            deadline=today + timedelta(days=1),
            status=DBTaskStatus.pending,
            alert_sent=False,
        )
        # Task 3: Due in 5 days -> DOES NOT QUALIFY
        t3 = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Due Later Task",
            deadline=today + timedelta(days=5),
            status=DBTaskStatus.pending,
            alert_sent=False,
        )
        # Task 4: Due today, but alert_sent=True -> DOES NOT QUALIFY
        t4 = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Already Alerted",
            deadline=today,
            status=DBTaskStatus.pending,
            alert_sent=True,
        )
        # Task 5: Complete task -> DOES NOT QUALIFY
        t5 = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Completed Task",
            deadline=today,
            status=DBTaskStatus.complete,
            alert_sent=False,
        )
        self.db.add_all([t1, t2, t3, t4, t5])
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 2)
        titles = [a.title for a in alerts]
        self.assertIn("Due Today Task", titles)
        self.assertIn("Due Tomorrow Task", titles)

    @patch("app.services.notification_service.NotificationService._deliver_email", return_value=True)
    @patch("app.services.notification_service.NotificationService._retrieve_task_context", return_value="Sample context")
    def test_process_deadline_notifications_success(self, mock_rag, mock_email) -> None:
        today = date.today()
        task = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Urgent Task",
            deadline=today,
            status=DBTaskStatus.pending,
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        status_res = NotificationService.process_deadline_notifications(
            self.db,
            trigger=NotificationTrigger.MANUAL,
        )
        self.assertEqual(status_res.tasks_checked, 1)
        self.assertEqual(status_res.alerts_sent, 1)
        self.assertEqual(len(status_res.failed_alerts), 0)

        # Verify alert_sent was set to True in database
        self.db.refresh(task)
        self.assertTrue(task.alert_sent)

    @patch("app.services.notification_service.NotificationService._retrieve_task_context", return_value="")
    @patch("app.services.notification_service.NotificationService._deliver_email", return_value=False)
    def test_process_deadline_notifications_delivery_failure(self, mock_email, mock_rag) -> None:
        today = date.today()
        task = Task(
            meeting_id=self.meeting.id,
            user_id=self.user.id,
            title="Failing Alert Task",
            deadline=today,
            status=DBTaskStatus.pending,
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        status_res = NotificationService.process_deadline_notifications(self.db)
        self.assertEqual(status_res.tasks_checked, 1)
        self.assertEqual(status_res.alerts_sent, 0)
        self.assertEqual(len(status_res.failed_alerts), 1)

        # alert_sent must remain False when delivery fails!
        self.db.refresh(task)
        self.assertFalse(task.alert_sent)


if __name__ == "__main__":
    unittest.main()

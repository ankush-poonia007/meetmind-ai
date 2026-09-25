"""
Unit and regression tests for Phase 7 Batch 6: Canonical Deadline Semantics and Filtering.

Covers:
- Part 5.A: Date-only conversion and timestamp normalization (M-01)
- Part 5.B: Deadline filter range semantics and half-open boundary (M-02)
- Part 5.C: Frozen notification eligibility rules (NOW < deadline <= NOW + 24h)
"""

import sys
import unittest
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.constants import TaskPriority, TaskStatus
from app.core.utils import normalize_deadline, parse_filter_bound
from app.db.base import Base
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.schemas.task import TaskBase, TaskCreate, TaskFilterParams, TaskUpdate
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService


class TestDeadlineNormalizationSemantics(unittest.TestCase):
    """Validates Part 5.A: Date-only conversion and timestamp preservation."""

    def test_date_only_date_object(self):
        """Date-only Python date object resolves to end of that UTC calendar day (23:59:59.999999)."""
        d = date(2026, 9, 25)
        res = normalize_deadline(d)
        expected = datetime(2026, 9, 25, 23, 59, 59, 999999, tzinfo=timezone.utc)
        self.assertEqual(res, expected)

    def test_date_only_string(self):
        """Date-only 'YYYY-MM-DD' string resolves to end of that UTC calendar day."""
        res = normalize_deadline("2026-09-25")
        expected = datetime(2026, 9, 25, 23, 59, 59, 999999, tzinfo=timezone.utc)
        self.assertEqual(res, expected)

    def test_explicit_utc_timestamp_preserved(self):
        """Explicit UTC timestamp retains its exact instant."""
        res = normalize_deadline("2026-09-25T14:30:00Z")
        expected = datetime(2026, 9, 25, 14, 30, 0, tzinfo=timezone.utc)
        self.assertEqual(res, expected)

    def test_explicit_timestamp_with_offset_normalized(self):
        """Explicit timestamp with timezone offset normalizes to UTC instant."""
        # 14:30 in UTC+5:30 is 09:00 UTC
        res = normalize_deadline("2026-09-25T14:30:00+05:30")
        expected = datetime(2026, 9, 25, 9, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(res, expected)

    def test_naive_datetime_assigned_utc(self):
        """Naive datetime is assigned UTC without altering hours/minutes."""
        naive_dt = datetime(2026, 9, 25, 14, 30, 0)
        res = normalize_deadline(naive_dt)
        expected = datetime(2026, 9, 25, 14, 30, 0, tzinfo=timezone.utc)
        self.assertEqual(res, expected)

    def test_null_deadline_remains_null(self):
        """None and empty strings resolve to None."""
        self.assertIsNone(normalize_deadline(None))
        self.assertIsNone(normalize_deadline(""))
        self.assertIsNone(normalize_deadline("   "))

    def test_task_orm_model_assignment(self):
        """ORM Task model assignment normalizes date and timestamp inputs consistently."""
        t1 = Task(id=uuid.uuid4(), title="Date Task", deadline=date(2026, 9, 25))
        self.assertEqual(t1.deadline, datetime(2026, 9, 25, 23, 59, 59, 999999, tzinfo=timezone.utc))

        t2 = Task(id=uuid.uuid4(), title="Explicit TS Task", deadline="2026-09-25T14:30:00Z")
        self.assertEqual(t2.deadline, datetime(2026, 9, 25, 14, 30, 0, tzinfo=timezone.utc))

        t3 = Task(id=uuid.uuid4(), title="Null Task", deadline=None)
        self.assertIsNone(t3.deadline)

    def test_task_schema_validation(self):
        """Pydantic schemas normalize date-only and explicit timestamp inputs."""
        tb = TaskBase(title="Schema Task", deadline="2026-09-25")
        self.assertEqual(tb.deadline, datetime(2026, 9, 25, 23, 59, 59, 999999, tzinfo=timezone.utc))

        tu = TaskUpdate(deadline="2026-09-25T14:30:00Z")
        self.assertEqual(tu.deadline, datetime(2026, 9, 25, 14, 30, 0, tzinfo=timezone.utc))


class TestDeadlineFilteringSemantics(unittest.TestCase):
    """Validates Part 5.B: Date-based filtering with half-open intervals."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

    def setUp(self):
        self.db: Session = self.SessionLocal()
        self.user = User(
            id=uuid.uuid4(),
            name="Filter Tester",
            email=f"tester_{uuid.uuid4().hex[:8]}@meetmind.ai",
        )
        self.db.add(self.user)
        self.meeting = Meeting(
            id=uuid.uuid4(),
            user_id=self.user.id,
            title="Filter Test Meeting",
            meeting_date=date(2026, 9, 25),
            input_format="text",
            raw_transcript="Discussion transcript for filter test.",
        )
        self.db.add(self.meeting)
        self.db.commit()

        # Seed test tasks around calendar date 2026-09-25
        self.t_midnight = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Midnight",
            priority=DBTaskPriority.high,
            status=DBTaskStatus.pending,
            deadline=datetime(2026, 9, 25, 0, 0, 0, tzinfo=timezone.utc),
        )
        self.t_noon = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Noon",
            priority=DBTaskPriority.medium,
            status=DBTaskStatus.pending,
            deadline=datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc),
        )
        self.t_end_of_day = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task End Of Day",
            priority=DBTaskPriority.low,
            status=DBTaskStatus.pending,
            deadline=datetime(2026, 9, 25, 23, 59, 59, 999999, tzinfo=timezone.utc),
        )
        self.t_next_day = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Next Day Midnight",
            priority=DBTaskPriority.medium,
            status=DBTaskStatus.pending,
            deadline=datetime(2026, 9, 26, 0, 0, 0, tzinfo=timezone.utc),
        )
        self.t_null = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Without Deadline",
            priority=DBTaskPriority.low,
            status=DBTaskStatus.pending,
            deadline=None,
        )
        self.db.add_all([
            self.t_midnight,
            self.t_noon,
            self.t_end_of_day,
            self.t_next_day,
            self.t_null,
        ])
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_filter_deadline_before_includes_entire_date(self):
        """B.1, B.2, B.3: Tasks due at midnight, noon, and end of requested date are included."""
        params = TaskFilterParams(deadline_before=date(2026, 9, 25))
        tasks = TaskService.get_user_tasks(self.db, self.user.id, params)
        titles = {t.title for t in tasks}

        self.assertIn("Task Midnight", titles)
        self.assertIn("Task Noon", titles)
        self.assertIn("Task End Of Day", titles)

    def test_filter_deadline_before_excludes_following_day(self):
        """B.4: Task due at midnight on the following date is excluded."""
        params = TaskFilterParams(deadline_before=date(2026, 9, 25))
        tasks = TaskService.get_user_tasks(self.db, self.user.id, params)
        titles = {t.title for t in tasks}

        self.assertNotIn("Task Next Day Midnight", titles)

    def test_filter_deadline_before_excludes_null(self):
        """B.5: Task with NULL deadline follows existing filter behavior (excluded)."""
        params = TaskFilterParams(deadline_before=date(2026, 9, 25))
        tasks = TaskService.get_user_tasks(self.db, self.user.id, params)
        titles = {t.title for t in tasks}

        self.assertNotIn("Task Without Deadline", titles)

    def test_filter_explicit_timestamp_remains_precise(self):
        """B.6: Explicit timestamp filtering remains precise to the instant."""
        params = TaskFilterParams(deadline_before="2026-09-25T12:00:00Z")
        tasks = TaskService.get_user_tasks(self.db, self.user.id, params)
        titles = {t.title for t in tasks}

        self.assertIn("Task Midnight", titles)
        self.assertIn("Task Noon", titles)
        self.assertNotIn("Task End Of Day", titles)
        self.assertNotIn("Task Next Day Midnight", titles)

    def test_filter_status_and_ordering_preserved(self):
        """B.7: Status filtering and deadline+priority ordering continue to function."""
        # Mark noon task complete
        self.t_noon.status = DBTaskStatus.complete
        self.db.commit()

        params = TaskFilterParams(status=TaskStatus.PENDING)
        tasks = TaskService.get_user_tasks(self.db, self.user.id, params)
        titles = [t.title for t in tasks]

        self.assertIn("Task Midnight", titles)
        self.assertNotIn("Task Noon", titles)
        self.assertIn("Task End Of Day", titles)


class TestFrozenNotificationEligibilityRules(unittest.TestCase):
    """Validates Part 5.C: Frozen notification eligibility rules."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

    def setUp(self):
        self.db: Session = self.SessionLocal()
        self.user = User(
            id=uuid.uuid4(),
            name="Eligibility User",
            email=f"elig_{uuid.uuid4().hex[:8]}@meetmind.ai",
        )
        self.db.add(self.user)
        self.meeting = Meeting(
            id=uuid.uuid4(),
            user_id=self.user.id,
            title="Eligibility Meeting",
            meeting_date=date(2026, 9, 25),
            input_format="text",
            raw_transcript="Discussion transcript for eligibility test.",
        )
        self.db.add(self.meeting)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_c1_pending_task_due_in_1_hour_eligible(self):
        """C.1: Pending task due in 1 hour -> ELIGIBLE."""
        now = datetime.now(timezone.utc)
        t = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Due in 1 hour",
            status=DBTaskStatus.pending,
            alert_sent=False,
            deadline=now + timedelta(hours=1),
        )
        self.db.add(t)
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].task_id, t.id)

    def test_c2_pending_task_due_exactly_now_ineligible(self):
        """C.2: Pending task due exactly now -> INELIGIBLE (NOW < deadline fails)."""
        now = datetime.now(timezone.utc)
        t = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Due exactly now",
            status=DBTaskStatus.pending,
            alert_sent=False,
            deadline=now,
        )
        self.db.add(t)
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_c3_pending_task_due_1_hour_ago_ineligible(self):
        """C.3: Pending task due 1 hour ago -> INELIGIBLE (overdue)."""
        now = datetime.now(timezone.utc)
        t = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Due 1 hour ago",
            status=DBTaskStatus.pending,
            alert_sent=False,
            deadline=now - timedelta(hours=1),
        )
        self.db.add(t)
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_c4_pending_task_due_in_24_hours_eligible(self):
        """C.4: Pending task due in exactly 24 hours -> ELIGIBLE."""
        now = datetime.now(timezone.utc)
        t = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Due in 24 hours",
            status=DBTaskStatus.pending,
            alert_sent=False,
            deadline=now + timedelta(hours=24),
        )
        self.db.add(t)
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].task_id, t.id)

    def test_c5_pending_task_due_in_25_hours_ineligible(self):
        """C.5: Pending task due in 25 hours -> INELIGIBLE."""
        now = datetime.now(timezone.utc)
        t = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Due in 25 hours",
            status=DBTaskStatus.pending,
            alert_sent=False,
            deadline=now + timedelta(hours=25),
        )
        self.db.add(t)
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_c6_completed_task_due_in_1_hour_ineligible(self):
        """C.6: Completed task due in 1 hour -> INELIGIBLE."""
        now = datetime.now(timezone.utc)
        t = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Completed task",
            status=DBTaskStatus.complete,
            alert_sent=False,
            deadline=now + timedelta(hours=1),
        )
        self.db.add(t)
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_c7_alert_already_sent_ineligible(self):
        """C.7: Task with alert_sent = True -> INELIGIBLE."""
        now = datetime.now(timezone.utc)
        t = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Alert sent task",
            status=DBTaskStatus.pending,
            alert_sent=True,
            deadline=now + timedelta(hours=1),
        )
        self.db.add(t)
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_c8_null_deadline_ineligible(self):
        """C.8: Task with NULL deadline -> INELIGIBLE."""
        t = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="No deadline task",
            status=DBTaskStatus.pending,
            alert_sent=False,
            deadline=None,
        )
        self.db.add(t)
        self.db.commit()

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)


if __name__ == "__main__":
    unittest.main()

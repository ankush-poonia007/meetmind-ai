"""
Unit and integration tests for Batch 6 Notification Rules and Eligibility.

Validates the 12 required scenarios under the frozen notification eligibility rule:
NOW < task.due_at <= NOW + 24 HOURS, status=PENDING, alert_sent=FALSE.

Scenarios:
1. Pending task due in 1 hour -> ELIGIBLE.
2. Pending task due in 12 hours -> ELIGIBLE.
3. Pending task due in exactly 24 hours -> ELIGIBLE.
4. Pending task due in 25 hours -> NOT ELIGIBLE.
5. Pending overdue task -> NOT ELIGIBLE.
6. Pending task due at the current time -> NOT ELIGIBLE.
7. Completed task due in 2 hours -> NOT ELIGIBLE.
8. Pending task due in 2 hours with alert_sent=true -> NOT ELIGIBLE.
9. Successful email delivery marks alert_sent=true.
10. Failed email delivery does not mark alert_sent=true.
11. Ineligible tasks are never sent to the email provider.
12. Existing notification behavior remains intact.
"""

import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.agents.notification import NotificationAgent
from app.core.constants import NotificationTrigger
from app.db.base import Base
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.services.notification_service import NotificationService


class TestBatch6NotificationRules(unittest.TestCase):
    """Rigorous validation of the frozen notification eligibility rule and delivery behavior."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

    def setUp(self):
        self.db: Session = self.SessionLocal()
        self.user = User(
            id=uuid.uuid4(),
            name="Test User",
            email="testuser@meetmind.ai",
        )
        self.meeting = Meeting(
            id=uuid.uuid4(),
            user_id=self.user.id,
            title="Batch 6 Sprint Review",
            meeting_date=datetime.now(timezone.utc).date(),
            raw_transcript="Discussion regarding upcoming task deadlines.",
            input_format="txt",
        )
        self.db.add(self.user)
        self.db.add(self.meeting)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()
        self.db.close()

    # ── ELIGIBILITY TESTS (Scenarios 1–8) ────────────────────────────────────────

    def test_01_pending_task_due_in_1_hour_is_eligible(self):
        """Scenario 1: Pending task due in 1 hour -> ELIGIBLE."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Due in 1h",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=1),
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        # Both agent check_deadline_tool and service get_pending_alerts_for_user
        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 1)
        self.assertEqual(qualifying[0].id, task.id)

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].task_id, task.id)

    def test_02_pending_task_due_in_12_hours_is_eligible(self):
        """Scenario 2: Pending task due in 12 hours -> ELIGIBLE."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Due in 12h",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=12),
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 1)
        self.assertEqual(qualifying[0].id, task.id)

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].task_id, task.id)

    def test_03_pending_task_due_in_exactly_24_hours_is_eligible(self):
        """Scenario 3: Pending task due in exactly 24 hours -> ELIGIBLE."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Due in 24h",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=24),
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 1)
        self.assertEqual(qualifying[0].id, task.id)

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].task_id, task.id)

    def test_04_pending_task_due_in_25_hours_is_not_eligible(self):
        """Scenario 4: Pending task due in 25 hours -> NOT ELIGIBLE."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Due in 25h",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=25),
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 0)

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_05_pending_overdue_task_is_not_eligible(self):
        """Scenario 5: Pending overdue task -> NOT ELIGIBLE."""
        now = datetime.now(timezone.utc)
        # Task due 2 hours ago
        task_past_hours = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Overdue by 2h",
            status=DBTaskStatus.pending,
            deadline=now - timedelta(hours=2),
            alert_sent=False,
        )
        # Task due yesterday
        task_past_days = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Overdue by 1 day",
            status=DBTaskStatus.pending,
            deadline=now - timedelta(days=1),
            alert_sent=False,
        )
        self.db.add_all([task_past_hours, task_past_days])
        self.db.commit()

        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 0)

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_06_pending_task_due_at_current_time_is_not_eligible(self):
        """Scenario 6: Pending task due at the current time -> NOT ELIGIBLE (strict inequality NOW < task.deadline)."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Task Due Right Now",
            status=DBTaskStatus.pending,
            deadline=now,
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 0)

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_07_completed_task_due_in_2_hours_is_not_eligible(self):
        """Scenario 7: Completed task due in 2 hours -> NOT ELIGIBLE."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Completed Task Due in 2h",
            status=DBTaskStatus.complete,
            deadline=now + timedelta(hours=2),
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 0)

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    def test_08_pending_task_due_in_2_hours_with_alert_sent_true_is_not_eligible(self):
        """Scenario 8: Pending task due in 2 hours with alert_sent=true -> NOT ELIGIBLE."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Already Alerted Task Due in 2h",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=2),
            alert_sent=True,
        )
        self.db.add(task)
        self.db.commit()

        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 0)

        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 0)

    # ── DELIVERY TESTS (Scenarios 9–12) ──────────────────────────────────────────

    @patch("app.agents.notification.NotificationAgent.compose_email_tool", return_value="Test Reminder Body")
    @patch("app.agents.notification.NotificationAgent.retrieve_task_context_tool", return_value="Excerpt")
    @patch("app.agents.notification.NotificationAgent.send_email_tool", return_value=True)
    def test_09_successful_email_delivery_marks_alert_sent_true(self, mock_send, mock_context, mock_compose):
        """Scenario 9: Successful email delivery marks alert_sent=true in database."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Deliver Presentation",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=3),
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        res = NotificationAgent.run_notification_run(self.db, trigger=NotificationTrigger.SCHEDULED)
        self.assertEqual(res["tasks_checked"], 1)
        self.assertEqual(res["alerts_sent"], 1)
        self.assertEqual(len(res["failed_alerts"]), 0)

        self.db.refresh(task)
        self.assertTrue(task.alert_sent)
        mock_send.assert_called_once()

    @patch("app.agents.notification.NotificationAgent.compose_email_tool", return_value="Test Reminder Body")
    @patch("app.agents.notification.NotificationAgent.retrieve_task_context_tool", return_value="Excerpt")
    @patch("app.agents.notification.NotificationAgent.send_email_tool", return_value=False)
    def test_10_failed_email_delivery_does_not_mark_alert_sent_true(self, mock_send, mock_context, mock_compose):
        """Scenario 10: Failed email delivery rolls back transaction and does NOT mark alert_sent=true."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Network Flaky Task",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=3),
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        res = NotificationAgent.run_notification_run(self.db, trigger=NotificationTrigger.SCHEDULED)
        self.assertEqual(res["tasks_checked"], 1)
        self.assertEqual(res["alerts_sent"], 0)
        self.assertIn(str(task.id), res["failed_alerts"])

        self.db.refresh(task)
        self.assertFalse(task.alert_sent)
        mock_send.assert_called_once()

    @patch("app.agents.notification.NotificationAgent.send_email_tool")
    def test_11_ineligible_tasks_are_never_sent_to_email_provider(self, mock_send):
        """Scenario 11: Ineligible tasks (overdue, completed, >24h, alert_sent=True) are never sent to email provider."""
        now = datetime.now(timezone.utc)
        ineligible_tasks = [
            # 1. Overdue
            Task(id=uuid.uuid4(), user_id=self.user.id, meeting_id=self.meeting.id, title="Overdue Task", status=DBTaskStatus.pending, deadline=now - timedelta(hours=1), alert_sent=False),
            # 2. Beyond 24h
            Task(id=uuid.uuid4(), user_id=self.user.id, meeting_id=self.meeting.id, title="Future Task", status=DBTaskStatus.pending, deadline=now + timedelta(hours=48), alert_sent=False),
            # 3. Completed
            Task(id=uuid.uuid4(), user_id=self.user.id, meeting_id=self.meeting.id, title="Complete Task", status=DBTaskStatus.complete, deadline=now + timedelta(hours=4), alert_sent=False),
            # 4. Already Alerted
            Task(id=uuid.uuid4(), user_id=self.user.id, meeting_id=self.meeting.id, title="Alerted Task", status=DBTaskStatus.pending, deadline=now + timedelta(hours=4), alert_sent=True),
            # 5. Due right now
            Task(id=uuid.uuid4(), user_id=self.user.id, meeting_id=self.meeting.id, title="Current Time Task", status=DBTaskStatus.pending, deadline=now, alert_sent=False),
            # 6. No deadline
            Task(id=uuid.uuid4(), user_id=self.user.id, meeting_id=self.meeting.id, title="No Deadline Task", status=DBTaskStatus.pending, deadline=None, alert_sent=False),
        ]
        self.db.add_all(ineligible_tasks)
        self.db.commit()

        res = NotificationAgent.run_notification_run(self.db, trigger=NotificationTrigger.SCHEDULED)
        self.assertEqual(res["tasks_checked"], 0)
        self.assertEqual(res["alerts_sent"], 0)
        self.assertEqual(len(res["failed_alerts"]), 0)
        mock_send.assert_not_called()

    @patch("app.services.notification_service.NotificationService._retrieve_task_context", return_value="Context lines")
    @patch("app.services.notification_service.NotificationService._deliver_email", return_value=True)
    def test_12_existing_notification_behavior_remains_intact(self, mock_email, mock_rag):
        """Scenario 12: NotificationService.process_deadline_notifications executes end-to-end through graph boundary."""
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="E2E Notification Flow Task",
            deadline=now + timedelta(hours=6),
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

        self.db.refresh(task)
        self.assertTrue(task.alert_sent)
        self.assertTrue(task.due_at is not None)


if __name__ == "__main__":
    unittest.main()

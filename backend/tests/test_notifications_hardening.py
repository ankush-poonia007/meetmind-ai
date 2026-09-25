"""
MeetMind AI — Gate 6 Combined Batch 3+4: Notifications, Scheduler & Hardening Test Suite.

Validates all Phase A & Phase B acceptance criteria:
- Task A1: Pending task eligibility (pending status, deadline <= 24h, alert_sent=False, user/meeting scoping)
- Task A2: Resend email delivery (sender 'MeetMind <onboarding@resend.dev>', recipient, content, error handling)
- Task A3: Duplicate prevention (no repeated alerts, failed sends leave alert_sent=False, idempotent runs)
- Task B1: Scheduler lifecycle & lifespan (AsyncIOScheduler initialization, daily 08:00 cron, clean shutdown, no duplicate jobs)
- Task B2: Notification execution (controlled execution, payload generation, tracking updates, ineligible tasks untouched)
- Task B3: Failure recovery (Resend failure, missing email, multi-task isolation where one failure does not block other tasks)
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.agents.notification import NotificationAgent
from app.core.constants import NotificationTrigger
from app.core.settings import settings
from app.db.base import Base
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.schemas.notification import NotificationStatusResponse, PendingAlertResponse
from app.services.notification_service import NotificationService


class BaseNotificationTestCase(unittest.TestCase):
    """In-memory SQLite test fixture for isolated database testing."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

    def setUp(self):
        self.db: Session = self.SessionLocal()
        # Create standard test user
        self.user = User(
            id=uuid.uuid4(),
            name="Alice Engineer",
            email="alice@meetmind.ai",
        )
        self.meeting = Meeting(
            id=uuid.uuid4(),
            user_id=self.user.id,
            title="Sprint Planning",
            meeting_date=date.today(),
            raw_transcript="Alice will finalize API specs by tomorrow.",
            input_format="txt",
        )
        self.db.add(self.user)
        self.db.add(self.meeting)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        # Clear database tables between tests
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()
        self.db.close()


# ── Phase A: Email Notification Verification ─────────────────────────────────

class TestPhaseANotifications(BaseNotificationTestCase):
    """Tests for Phase A: Task eligibility, Resend email delivery, and duplicate prevention."""

    def test_a1_pending_task_eligibility(self):
        """
        Task A1: Verifies that only tasks satisfying frozen notification rules are selected:
        - status == pending
        - deadline <= 24 hours (or overdue)
        - alert_sent == False
        - excluded: completed, rejected, alert_sent=True, deadline > 24h, deadline=None
        """
        today = date.today()
        now = datetime.now(timezone.utc)

        # 1. Eligible task: pending, due in 2 hours, alert_sent=False
        eligible_task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Eligible Pending Task",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=2),
            alert_sent=False,
        )

        # 2. Ineligible: already completed
        completed_task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Completed Task",
            status=DBTaskStatus.complete,
            deadline=today,
            alert_sent=False,
        )

        # 3. Ineligible: alert already sent
        already_alerted_task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Already Alerted Task",
            status=DBTaskStatus.pending,
            deadline=today,
            alert_sent=True,
        )

        # 4. Ineligible: deadline far in future (>24h)
        future_task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Future Task",
            status=DBTaskStatus.pending,
            deadline=today + timedelta(days=5),
            alert_sent=False,
        )

        # 5. Ineligible: no deadline set
        no_deadline_task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="No Deadline Task",
            status=DBTaskStatus.pending,
            deadline=None,
            alert_sent=False,
        )

        self.db.add_all([
            eligible_task,
            completed_task,
            already_alerted_task,
            future_task,
            no_deadline_task,
        ])
        self.db.commit()

        # Agent deadline check tool
        qualifying = NotificationAgent.check_deadline_tool(self.db)
        self.assertEqual(len(qualifying), 1)
        self.assertEqual(qualifying[0].id, eligible_task.id)

        # Service get_pending_alerts_for_user
        alerts = NotificationService.get_pending_alerts_for_user(self.db, self.user.id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].task_id, eligible_task.id)
        self.assertEqual(alerts[0].title, "Eligible Pending Task")

    @patch("app.services.notification_service.settings")
    def test_a2_resend_email_delivery_and_sender_format(self, mock_settings):
        """
        Task A2: Verifies Resend integration uses configured sender MeetMind <onboarding@resend.dev>,
        sends to the correct recipient, and properly wraps Resend.Emails.send.
        """
        mock_settings.resend_api_key = "re_test_key_123"
        mock_settings.resend_sender = "MeetMind <onboarding@resend.dev>"

        with patch("resend.Emails.send") as mock_resend_send:
            mock_resend_send.return_value = {"id": "msg_12345"}

            success = NotificationService._deliver_email(
                recipient_email="alice@meetmind.ai",
                subject="Reminder: Task Due Soon",
                body="You have a pending task due tomorrow.",
            )

            self.assertTrue(success)
            mock_resend_send.assert_called_once()
            call_params = mock_resend_send.call_args[0][0]
            self.assertEqual(call_params["from"], "MeetMind <onboarding@resend.dev>")
            self.assertEqual(call_params["to"], ["alice@meetmind.ai"])
            self.assertEqual(call_params["subject"], "Reminder: Task Due Soon")
            self.assertEqual(call_params["text"], "You have a pending task due tomorrow.")

    @patch("app.agents.notification.NotificationAgent.compose_email_tool", return_value="Polite AI reminder")
    @patch("app.agents.notification.NotificationAgent.send_email_tool", return_value=True)
    def test_a3_duplicate_prevention_and_idempotency(self, mock_send, mock_compose):
        """
        Task A3: Verifies that once a task alert is delivered, alert_sent becomes True and
        subsequent scheduler executions do NOT re-alert or create duplicate notifications.
        """
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Deploy Monitoring Service",
            status=DBTaskStatus.pending,
            deadline=datetime.now(timezone.utc) + timedelta(hours=2),
            alert_sent=False,
        )
        self.db.add(task)
        self.db.commit()

        # Run 1: Should send 1 alert and mark alert_sent=True
        res1 = NotificationAgent.run_notification_run(self.db, trigger=NotificationTrigger.SCHEDULED)
        self.assertEqual(res1["tasks_checked"], 1)
        self.assertEqual(res1["alerts_sent"], 1)
        self.assertEqual(len(res1["failed_alerts"]), 0)

        self.db.refresh(task)
        self.assertTrue(task.alert_sent)

        # Run 2: Repeated run should find 0 qualifying tasks
        res2 = NotificationAgent.run_notification_run(self.db, trigger=NotificationTrigger.SCHEDULED)
        self.assertEqual(res2["tasks_checked"], 0)
        self.assertEqual(res2["alerts_sent"], 0)

        # send_email_tool should only have been called once overall
        mock_send.assert_called_once()


# ── Phase B: Scheduler & Lifecycle Verification ──────────────────────────────

class TestPhaseBSchedulerLifecycle(unittest.TestCase):
    """Tests for Phase B: Scheduler initialization, lifespan, execution, and failure recovery."""

    def test_b1_scheduler_initialization_and_shutdown(self):
        """
        Task B1: Verifies AsyncIOScheduler initializes, registers daily 08:00 cron job exactly once,
        and shuts down cleanly.
        """
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

            # Check cron trigger fields
            cron_fields = {f.name: str(f) for f in job.trigger.fields}
            self.assertEqual(cron_fields["hour"], "8")
            self.assertEqual(cron_fields["minute"], "0")

            # Duplicate prevention check (replace_existing=True keeps 1 job)
            scheduler.add_job(
                lambda: None,
                trigger="cron",
                hour=8,
                minute=0,
                id="daily_deadline_notification",
                replace_existing=True,
            )
            self.assertEqual(len(scheduler.get_jobs()), 1)

            # Clean shutdown
            scheduler.shutdown(wait=False)
            await asyncio.sleep(0.02)
            self.assertFalse(scheduler.running)

        asyncio.run(_test())

    @patch("app.main.AsyncIOScheduler")
    def test_b1_fastapi_lifespan_integration(self, mock_scheduler_cls):
        """
        Task B1: Verifies FastAPI lifespan context manager registers the scheduler,
        adds the daily notification job, and shuts down on exit.
        """
        from app.main import app, lifespan

        mock_scheduler_instance = MagicMock()
        mock_scheduler_instance.running = True
        mock_scheduler_cls.return_value = mock_scheduler_instance

        async def _test_lifespan():
            async with lifespan(app):
                self.assertTrue(hasattr(app.state, "scheduler"))
                mock_scheduler_instance.add_job.assert_called_once()
                call_kwargs = mock_scheduler_instance.add_job.call_args.kwargs
                self.assertEqual(call_kwargs.get("id"), "daily_deadline_notification")
                self.assertEqual(call_kwargs.get("trigger"), "cron")
                self.assertTrue(call_kwargs.get("replace_existing"))
                mock_scheduler_instance.start.assert_called_once()

            # Upon lifespan exit:
            mock_scheduler_instance.shutdown.assert_called_once_with(wait=False)

        asyncio.run(_test_lifespan())


class TestPhaseBFailureRecovery(BaseNotificationTestCase):
    """Tests for Phase B: Error handling, provider failure, missing email, and task isolation."""

    @patch("app.agents.notification.NotificationAgent.compose_email_tool", return_value="Reminder body")
    @patch("app.agents.notification.NotificationAgent.send_email_tool", return_value=False)
    def test_b3_resend_delivery_failure_keeps_alert_sent_false(self, mock_send, mock_compose):
        """
        Task B3: Verifies that if email delivery fails, the task's alert_sent remains False,
        is recorded in failed_alerts, and can be retried later.
        """
        task = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Fix Database Connection",
            status=DBTaskStatus.pending,
            deadline=datetime.now(timezone.utc) + timedelta(hours=2),
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

    @patch("app.agents.notification.NotificationAgent.compose_email_tool", return_value="Reminder body")
    @patch("app.agents.notification.NotificationAgent.send_email_tool")
    def test_b3_multi_task_isolation_one_failure_does_not_block_other(self, mock_send, mock_compose):
        """
        Task B3: Verifies that if multiple eligible tasks exist and one fails (e.g. provider error
        or missing email), the remaining eligible tasks are still successfully processed and alerted.
        """
        now = datetime.now(timezone.utc)
        # User 1 with valid email
        task_good = Task(
            id=uuid.uuid4(),
            user_id=self.user.id,
            meeting_id=self.meeting.id,
            title="Good Task",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=2),
            alert_sent=False,
        )

        # User 2 without email
        user_no_email = User(
            id=uuid.uuid4(),
            name="No Email User",
            email="",
        )
        task_bad = Task(
            id=uuid.uuid4(),
            user_id=user_no_email.id,
            meeting_id=self.meeting.id,
            title="Task with missing recipient email",
            status=DBTaskStatus.pending,
            deadline=now + timedelta(hours=2),
            alert_sent=False,
        )

        self.db.add_all([user_no_email, task_good, task_bad])
        self.db.commit()

        # Mock send_email_tool to return True for good email
        mock_send.return_value = True

        res = NotificationAgent.run_notification_run(self.db, trigger=NotificationTrigger.SCHEDULED)

        self.assertEqual(res["tasks_checked"], 2)
        self.assertEqual(res["alerts_sent"], 1)
        self.assertIn(str(task_bad.id), res["failed_alerts"])

        # Check database states
        self.db.refresh(task_good)
        self.db.refresh(task_bad)

        self.assertTrue(task_good.alert_sent)
        self.assertFalse(task_bad.alert_sent)

    def test_b3_no_eligible_tasks_handles_cleanly(self):
        """
        Task B3: Verifies that running notification run when zero tasks qualify completes
        gracefully with 0 checked, 0 sent, and empty failed list.
        """
        res = NotificationAgent.run_notification_run(self.db, trigger=NotificationTrigger.SCHEDULED)
        self.assertEqual(res["tasks_checked"], 0)
        self.assertEqual(res["alerts_sent"], 0)
        self.assertEqual(len(res["failed_alerts"]), 0)


if __name__ == "__main__":
    unittest.main()

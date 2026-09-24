"""
Notification service for MeetMind AI.

Handles identification of pending tasks nearing deadlines (within 24 hours),
retrieves transcript context via Gate 3 RAG, coordinates AI email composition,
delivers alerts via Resend, and marks alert_sent=True only after successful send.
Scheduler wiring is deferred to Batch 3.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.constants import NotificationTrigger
from app.core.exceptions import NotificationError, UserNotFoundError
from app.core.logging import get_logger
from app.core.settings import settings
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.schemas.notification import (
    NotificationStatusResponse,
    PendingAlertResponse,
)

logger = get_logger(__name__)


class NotificationService:
    """Service layer managing deadline notifications and alerting pipeline."""

    @staticmethod
    def get_pending_alerts_for_user(
        db: Session,
        user_id: UUID,
    ) -> list[PendingAlertResponse]:
        """
        Retrieves pending tasks assigned to a user with deadlines within the next 24 hours
        (or already overdue) that have not yet had alerts sent.

        Args:
            db: Active synchronous database session.
            user_id: Target user UUID.

        Returns:
            List of PendingAlertResponse schemas.

        Raises:
            UserNotFoundError: If user does not exist.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"Get pending alerts failed: user {user_id} not found")
            raise UserNotFoundError(
                f"User with id '{user_id}' not found.",
                details={"user_id": str(user_id)},
            )

        today = date.today()
        deadline_threshold = today + timedelta(days=1)

        tasks = (
            db.query(Task)
            .filter(
                Task.user_id == user_id,
                Task.status == DBTaskStatus.pending,
                Task.alert_sent.is_(False),
                Task.deadline.isnot(None),
                Task.deadline <= deadline_threshold,
            )
            .order_by(Task.deadline.asc())
            .all()
        )

        results: list[PendingAlertResponse] = []
        for t in tasks:
            days_until = (t.deadline - today).days if t.deadline else None
            results.append(
                PendingAlertResponse(
                    task_id=t.id,
                    meeting_id=t.meeting_id,
                    user_id=t.user_id,
                    title=t.title,
                    deadline=t.deadline,
                    days_until_due=days_until,
                )
            )

        return results

    @staticmethod
    def process_deadline_notifications(
        db: Session,
        trigger: NotificationTrigger = NotificationTrigger.MANUAL,
    ) -> NotificationStatusResponse:
        """
        Executes the deadline notification run through the LangGraph boundary:
        APScheduler / API -> NotificationService -> run_notification_graph() -> NotificationAgent.

        Args:
            db: Active synchronous database session.
            trigger: Trigger source (SCHEDULED or MANUAL).

        Returns:
            NotificationStatusResponse summarizing run statistics.
        """
        trigger_name = trigger.value if hasattr(trigger, "value") else str(trigger)
        logger.info(f"Starting deadline notification run via graph boundary (trigger={trigger_name})")

        from app.graph.graph import run_notification_graph

        graph_res = run_notification_graph(db=db, trigger=trigger_name)

        tasks_checked = graph_res.get("tasks_checked", 0)
        alerts_sent = graph_res.get("alerts_sent", 0)
        failed_alerts = graph_res.get("failed_alerts", [])
        raw_completion = graph_res.get("completion_time")

        if isinstance(raw_completion, str) and raw_completion:
            try:
                comp_dt = datetime.fromisoformat(raw_completion)
            except ValueError:
                comp_dt = datetime.now(timezone.utc)
        elif isinstance(raw_completion, datetime):
            comp_dt = raw_completion
        else:
            comp_dt = datetime.now(timezone.utc)

        return NotificationStatusResponse(
            tasks_checked=tasks_checked,
            alerts_sent=alerts_sent,
            failed_alerts=failed_alerts,
            completion_time=comp_dt,
        )

    @staticmethod
    def _retrieve_task_context(
        meeting_id: UUID,
        task_title: str,
        db: Session,
    ) -> str:
        """
        Helper method to retrieve transcript context via Gate 3 RAG.
        Preserved as static method on NotificationService for compatibility and delegation.
        """
        try:
            from app.rag import retrieve
            chunks = retrieve(meeting_id=meeting_id, query=task_title, db_session=db)
            if chunks:
                from app.core.config import NOTIFICATION_CONTEXT_CHUNKS
                return "\n".join([f"- {c.content}" for c in chunks[:NOTIFICATION_CONTEXT_CHUNKS]])
        except Exception as exc:
            logger.warning(f"RAG context retrieval skipped for task '{task_title}': {exc}")
        return ""

    @staticmethod
    def _deliver_email(
        recipient_email: str,
        subject: str,
        body: str,
    ) -> bool:
        """
        Helper method to deliver email via Resend API.
        Preserved as static method on NotificationService for compatibility and delegation.
        """
        if not settings.resend_api_key or settings.resend_api_key.strip() in ("", "mock", "dummy"):
            logger.info(f"[SIMULATED EMAIL] To: {recipient_email} | Subject: {subject}")
            return True

        try:
            import resend
            resend.api_key = settings.resend_api_key
            params = {
                "from": settings.resend_sender or "onboarding@resend.dev",
                "to": [recipient_email],
                "subject": subject,
                "text": body,
            }
            resend.Emails.send(params)
            return True
        except Exception as exc:
            logger.error(f"Resend email delivery failed for {recipient_email}: {exc}")
            return False


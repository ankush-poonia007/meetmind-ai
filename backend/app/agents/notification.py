"""
Notification Agent for MeetMind AI.

Pattern: ReAct
Model: gemini-3.5-flash-lite (via ProviderGateway with use_case="sub_agent")

Responsibilities:
- Independent execution path for scheduled (08:00 AM) or manual deadline alerting.
- Queries PostgreSQL for tasks where status=pending, deadline <= next 24h, alert_sent=false.
- Retrieves transcript context for each task via Gate 3 RAG (top 3 chunks).
- Composes personalized alert emails using AI (gemini-3.5-flash-lite).
- Delivers emails via Resend API.
- Updates tasks.alert_sent = True ONLY upon verified successful delivery.
- Does NOT trigger meeting ingestion, identity, or confirmation pipelines.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.core.config import NOTIFICATION_CONTEXT_CHUNKS, SUB_AGENT_MODEL
from app.core.constants import NotificationTrigger
from app.core.logging import get_logger
from app.core.providers import get_provider_gateway
from app.core.settings import settings
from app.db.models.task import Task, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.graph.state import MeetMindState

logger = get_logger(__name__)


class NotificationAgent:
    """
    Notification Agent managing deadline checks, AI email composition, and alert dispatch.
    """

    model_name: str = SUB_AGENT_MODEL

    @classmethod
    def check_deadline_tool(cls, db: Session) -> list[Task]:
        """
        Queries PostgreSQL for all pending tasks due within the next 24 hours
        (or already overdue) that have not yet had an alert sent.
        """
        now = datetime.now(timezone.utc)
        deadline_threshold = now + timedelta(hours=24)

        return (
            db.query(Task)
            .filter(
                Task.status == DBTaskStatus.pending,
                Task.alert_sent.is_(False),
                Task.deadline.isnot(None),
                Task.deadline > now,
                Task.deadline <= deadline_threshold,
            )
            .order_by(Task.deadline.asc())
            .all()
        )

    @classmethod
    def retrieve_task_context_tool(cls, db: Session, meeting_id: Any, task_title: str) -> str:
        """
        Retrieves transcript context chunks via Gate 3 RAG for grounding email composition.
        Delegates through NotificationService._retrieve_task_context.
        """
        from app.services.notification_service import NotificationService
        return NotificationService._retrieve_task_context(meeting_id=meeting_id, task_title=task_title, db=db)

    @classmethod
    def compose_email_tool(
        cls,
        recipient_name: str,
        task_title: str,
        deadline: Optional[date],
        rag_context: str,
    ) -> str:
        """
        Composes an informative, context-aware notification email body.
        """
        prompt = f"""Compose a polite, concise professional reminder email for a task deadline.

Recipient: {recipient_name}
Task: {task_title}
Deadline: {deadline.isoformat() if deadline else 'Immediate'}
Meeting Transcript Context:
{rag_context if rag_context else 'No specific transcript excerpt available.'}

Keep the tone helpful and actionable. Include the task title, deadline, and a brief summary of what was discussed."""

        try:
            gateway = get_provider_gateway()

            def _call_gemini_compose(api_key: str, model_str: Optional[str]) -> str:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_str or cls.model_name)
                return model.generate_content(prompt).text.strip()

            return gateway.execute("sub_agent", _call_gemini_compose)
        except Exception as exc:
            logger.info(f"AI email composition skipped ({exc}); using templated text")
            body = (
                f"Hello {recipient_name},\n\n"
                f"This is a reminder that your task is due soon:\n"
                f"Task: {task_title}\n"
                f"Deadline: {deadline.isoformat() if deadline else 'N/A'}\n\n"
            )
            if rag_context:
                body += f"Meeting Context:\n{rag_context}\n\n"
            body += "Best regards,\nMeetMind AI Assistant"
            return body

    @classmethod
    def send_email_tool(cls, recipient_email: str, subject: str, body: str) -> bool:
        """
        Delivers composed email via Resend API or simulates if key is not configured.
        Delegates through NotificationService._deliver_email.
        """
        from app.services.notification_service import NotificationService
        return NotificationService._deliver_email(recipient_email=recipient_email, subject=subject, body=body)

    @classmethod
    def run_notification_run(
        cls,
        db: Session,
        trigger: NotificationTrigger = NotificationTrigger.SCHEDULED,
    ) -> dict[str, Any]:
        """
        Full notification execution loop:
        1. Checks deadlines for pending tasks.
        2. Retrieves RAG context per task.
        3. Composes and delivers emails.
        4. Updates alert_sent = True only upon delivery success.
        """
        trigger_name = trigger.value if hasattr(trigger, "value") else str(trigger)
        logger.info(f"NotificationAgent initiating run (trigger={trigger_name})")

        qualifying_tasks = cls.check_deadline_tool(db)
        tasks_checked = len(qualifying_tasks)
        alerts_sent = 0
        failed_alerts: list[str] = []

        logger.info(f"NotificationAgent found {tasks_checked} qualifying tasks")

        for task in qualifying_tasks:
            task_id_str = str(task.id)
            try:
                recipient = db.query(User).filter(User.id == task.user_id).first()
                if not recipient or not recipient.email:
                    logger.warning(f"Task {task_id_str}: missing recipient email; skipping")
                    failed_alerts.append(task_id_str)
                    continue

                rag_context = cls.retrieve_task_context_tool(
                    db=db,
                    meeting_id=task.meeting_id,
                    task_title=task.title,
                )

                email_body = cls.compose_email_tool(
                    recipient_name=recipient.name,
                    task_title=task.title,
                    deadline=task.deadline,
                    rag_context=rag_context,
                )

                subject = f"Reminder: Task Due Soon - {task.title}"
                success = cls.send_email_tool(
                    recipient_email=recipient.email,
                    subject=subject,
                    body=email_body,
                )

                if success:
                    task.alert_sent = True
                    db.commit()
                    alerts_sent += 1
                    logger.info(f"Notification successfully sent for task {task_id_str}")
                else:
                    db.rollback()
                    failed_alerts.append(task_id_str)
                    logger.warning(f"Failed to send email for task {task_id_str}")

            except Exception as exc:
                db.rollback()
                failed_alerts.append(task_id_str)
                logger.error(f"Error processing notification for task {task_id_str}: {exc}")

        return {
            "tasks_checked": tasks_checked,
            "alerts_sent": alerts_sent,
            "failed_alerts": failed_alerts,
            "completion_time": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def run(cls, state: MeetMindState, db: Optional[Session] = None) -> dict[str, Any]:
        """
        LangGraph node entry point for notification pipeline.
        """
        if not db:
            from app.db.session import SessionLocal
            db_session = SessionLocal()
            try:
                result = cls.run_notification_run(db=db_session, trigger=NotificationTrigger.MANUAL)
            finally:
                db_session.close()
        else:
            result = cls.run_notification_run(db=db, trigger=NotificationTrigger.MANUAL)

        return {
            "tasks_due_soon": [{"id": tid} for tid in result["failed_alerts"]],
            "tasks_checked": result.get("tasks_checked", 0),
            "alerts_sent": result.get("alerts_sent", 0),
            "failed_alerts": result.get("failed_alerts", []),
            "completion_time": result.get("completion_time", ""),
            "current_stage": "notification",
            "session_action": "complete",
        }


# Module level convenience export
run_notification_agent = NotificationAgent.run_notification_run

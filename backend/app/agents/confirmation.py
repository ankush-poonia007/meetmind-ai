"""
Confirmation Agent for MeetMind AI.

Pattern: ReAct with Human-in-the-Loop (HITL) Interrupt/Resume
Model: gemini-3.5-flash-lite (via ProviderGateway with use_case="sub_agent")

Responsibilities:
- Sole agent interacting directly with the user.
- Formats and presents the task preview containing TITLE and DESCRIPTION only.
- Pauses execution using LangGraph `interrupt(...)` awaiting human confirmation.
- Resumes execution upon receiving decision: YES, NO, or PARTIAL.
- Validates confirmed task IDs against current meeting extraction context.
- Discards unconfirmed or rejected tasks.
- Persists confirmed tasks and highlights to PostgreSQL database.
- Marks confirmation_complete = True and session_action = "complete".
- Enforces duplicate confirmation protection.
"""

import uuid
from typing import Any, Optional
from langgraph.types import interrupt
from sqlalchemy.orm import Session

from app.core.config import SUB_AGENT_MODEL
from app.core.constants import TaskPriority as AppTaskPriority, UserConfirmation
from app.core.exceptions import InvalidOwnershipError, InvalidStateError
from app.core.logging import get_logger
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.graph.state import MeetMindState

logger = get_logger(__name__)


class ConfirmationAgent:
    """
    Confirmation Agent mediating HITL review and persisting approved tasks.
    """

    model_name: str = SUB_AGENT_MODEL

    @classmethod
    def present_tasks_tool(cls, extracted_tasks: list[dict[str, Any]]) -> list[dict[str, str]]:
        """
        Formats confirmation preview: title + description only.
        Does NOT expose deadline or priority in the presentation.
        """
        preview_list: list[dict[str, str]] = []
        for idx, task in enumerate(extracted_tasks):
            t_id = str(task.get("id", idx))
            preview_list.append({
                "id": t_id,
                "title": task.get("title", f"Task {idx + 1}"),
                "description": task.get("description", ""),
            })
        return preview_list

    @classmethod
    def run(cls, state: MeetMindState, db: Optional[Session] = None) -> dict[str, Any]:
        """
        Executes Confirmation Agent logic:
        1. If user confirmation is missing, pauses execution via interrupt().
        2. When resumed, validates the confirmation decision.
        3. Persists approved tasks and highlights to the database.
        4. Updates state and marks confirmation complete.
        """
        meeting_id_str = state.get("meeting_id", "")
        user_id_str = state.get("user_id", "")
        extracted_tasks = state.get("extracted_tasks", [])
        extracted_highlights = state.get("extracted_highlights", [])

        logger.info(f"ConfirmationAgent processing meeting {meeting_id_str}")

        # Guard against duplicate confirmation if already completed
        if state.get("confirmation_complete", False):
            logger.warning(f"Confirmation already completed for meeting {meeting_id_str}")
            return {
                "current_stage": "confirmation",
                "session_action": "complete",
            }

        # 1. HITL Interrupt: Pause if user confirmation is not yet in state
        confirmation_decision = state.get("user_confirmation")
        confirmed_task_ids = state.get("confirmed_task_ids", [])

        if not confirmation_decision:
            preview = cls.present_tasks_tool(extracted_tasks)
            logger.info(
                f"Pausing execution via LangGraph interrupt for meeting {meeting_id_str} "
                f"with {len(preview)} candidate tasks"
            )

            # LangGraph interrupt: Pauses graph and awaits external resume command
            resume_data = interrupt({
                "type": "human_confirmation_required",
                "meeting_id": meeting_id_str,
                "user_id": user_id_str,
                "tasks": preview,
            })

            # Resumed: unpack decision and confirmed_task_ids from resume_data
            if isinstance(resume_data, dict):
                confirmation_decision = resume_data.get("user_confirmation", "no")
                confirmed_task_ids = resume_data.get("confirmed_task_ids", [])
            elif isinstance(resume_data, str):
                confirmation_decision = resume_data
                confirmed_task_ids = []
            else:
                confirmation_decision = "no"
                confirmed_task_ids = []

        # Normalize decision string
        decision_val = (
            confirmation_decision.value.lower()
            if hasattr(confirmation_decision, "value")
            else str(confirmation_decision).lower().strip()
        )

        logger.info(
            f"ConfirmationAgent resumed with decision: '{decision_val}' "
            f"for meeting {meeting_id_str}"
        )

        valid_decisions = [c.value for c in UserConfirmation]
        if decision_val not in valid_decisions:
            raise InvalidStateError(
                f"Invalid confirmation decision '{decision_val}'. "
                f"Expected one of: {valid_decisions}"
            )

        # 2. Process tasks according to decision
        saved_tasks_count = 0
        discarded_tasks_count = 0
        confirmed_ids_set = {str(cid) for cid in confirmed_task_ids}

        # Validate that confirmed_task_ids belong to current extraction context
        available_ids = {str(t.get("id", idx)) for idx, t in enumerate(extracted_tasks)}
        available_titles = {t.get("title", "") for t in extracted_tasks}

        if decision_val == UserConfirmation.PARTIAL.value:
            for cid in confirmed_ids_set:
                if cid not in available_ids and cid not in available_titles:
                    raise InvalidOwnershipError(
                        f"Task ID '{cid}' does not exist in extraction preview for meeting '{meeting_id_str}'.",
                        details={"meeting_id": meeting_id_str, "task_id": cid},
                    )

        # 3. Persist to DB if session provided and meeting exists
        meeting_uuid = uuid.UUID(meeting_id_str) if meeting_id_str else None
        user_uuid = uuid.UUID(user_id_str) if user_id_str else None

        meeting_exists = False
        if db and meeting_uuid:
            try:
                meeting_exists = db.query(Meeting).filter(Meeting.id == meeting_uuid).first() is not None
            except Exception as exc:
                logger.warning(f"meeting_exists check failed: {exc}")
                meeting_exists = False

        if db and meeting_uuid and user_uuid and meeting_exists:
            if decision_val == UserConfirmation.NO.value:
                discarded_tasks_count = len(extracted_tasks)
            else:
                for idx, t_data in enumerate(extracted_tasks):
                    task_id = str(t_data.get("id", idx))
                    task_title = t_data.get("title", "")

                    should_save = False
                    if decision_val == UserConfirmation.YES.value:
                        should_save = True
                    elif decision_val == UserConfirmation.PARTIAL.value:
                        if task_id in confirmed_ids_set or str(idx) in confirmed_ids_set or task_title in confirmed_ids_set:
                            should_save = True

                    if should_save:
                        raw_prio = t_data.get("priority", "medium")
                        prio_str = raw_prio.value if hasattr(raw_prio, "value") else str(raw_prio).lower()
                        try:
                            prio_enum = DBTaskPriority(prio_str)
                        except ValueError:
                            prio_enum = DBTaskPriority.medium

                        db_task = Task(
                            meeting_id=meeting_uuid,
                            user_id=user_uuid,
                            title=task_title,
                            description=t_data.get("description"),
                            priority=prio_enum,
                            deadline=t_data.get("deadline"),
                            status=DBTaskStatus.pending,
                            alert_sent=False,
                        )
                        db.add(db_task)
                        saved_tasks_count += 1
                    else:
                        discarded_tasks_count += 1

            # Save highlights
            saved_highlights_count = 0
            for h_data in extracted_highlights:
                content = h_data.get("content", "").strip()
                if content:
                    db_highlight = Highlight(
                        meeting_id=meeting_uuid,
                        user_id=user_uuid,
                        content=content,
                    )
                    db.add(db_highlight)
                    saved_highlights_count += 1

            try:
                db.commit()
                logger.info(
                    f"Confirmed items persisted to DB: {saved_tasks_count} tasks, "
                    f"{saved_highlights_count} highlights"
                )
            except Exception as exc:
                db.rollback()
                logger.error(f"Failed to persist confirmed items: {exc}")
                raise
        else:
            # DB-less / testing calculation
            saved_highlights_count = len(extracted_highlights)
            if decision_val == UserConfirmation.YES.value:
                saved_tasks_count = len(extracted_tasks)
            elif decision_val == UserConfirmation.PARTIAL.value:
                saved_tasks_count = len(confirmed_ids_set)
                discarded_tasks_count = len(extracted_tasks) - saved_tasks_count
            else:
                discarded_tasks_count = len(extracted_tasks)

        # Clear preview cache
        from app.services.extraction_service import _EXTRACTION_PREVIEWS
        _EXTRACTION_PREVIEWS.pop(meeting_id_str, None)

        return {
            "user_confirmation": decision_val,
            "confirmed_task_ids": list(confirmed_ids_set),
            "saved_tasks": saved_tasks_count,
            "discarded_tasks": discarded_tasks_count,
            "saved_highlights": saved_highlights_count,
            "confirmation_complete": True,
            "current_stage": "confirmation",
            "session_action": "complete",
        }

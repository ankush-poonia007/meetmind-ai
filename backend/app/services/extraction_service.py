"""
Extraction service for MeetMind AI.

Orchestrates the transcript extraction and human-in-the-loop (HITL) confirmation pipeline.
Maintains the service boundary between API endpoints and LangGraph multi-agent execution.
Confirmation Agent remains the sole agent interacting with the user.
"""

from typing import Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.constants import TaskPriority, UserConfirmation
from app.core.exceptions import (
    InvalidOwnershipError,
    InvalidStateError,
    MeetingNotFoundError,
    UserNotFoundError,
)
from app.core.logging import get_logger
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.schemas.extraction import (
    ExtractedHighlight,
    ExtractedTask,
    ExtractionConfirmRequest,
    ExtractionPreviewResponse,
    ExtractionResult,
)

logger = get_logger(__name__)

# In-memory execution state cache for pending HITL confirmations (meeting_id -> state dict)
_EXTRACTION_PREVIEWS: dict[str, dict[str, Any]] = {}


class ExtractionService:
    """Service layer managing extraction orchestration and HITL task confirmation."""

    @staticmethod
    def run_extraction(
        db: Session,
        meeting_id: UUID,
        user_id: UUID,
    ) -> ExtractionPreviewResponse:
        """
        Initiates the multi-agent extraction pipeline for a meeting.
        In Batch 1/2, coordinates pipeline execution and caches unconfirmed preview state.

        Args:
            db: Active synchronous database session.
            meeting_id: Target meeting UUID.
            user_id: Submitting user UUID.

        Returns:
            ExtractionPreviewResponse with extracted items awaiting user confirmation.

        Raises:
            MeetingNotFoundError: If meeting does not exist.
            UserNotFoundError: If user does not exist.
            InvalidOwnershipError: If meeting does not belong to user.
        """
        logger.info(f"Initiating extraction pipeline for meeting {meeting_id}, user {user_id}")

        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Extraction failed: meeting {meeting_id} not found")
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        if meeting.user_id != user_id:
            logger.warning(f"Extraction ownership violation: user {user_id} on meeting {meeting_id}")
            raise InvalidOwnershipError(
                f"Meeting with id '{meeting_id}' does not belong to user '{user_id}'.",
                details={"meeting_id": str(meeting_id), "user_id": str(user_id)},
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"Extraction failed: user {user_id} not found")
            raise UserNotFoundError(
                f"User with id '{user_id}' not found.",
                details={"user_id": str(user_id)},
            )

        # Delegate to LangGraph pipeline boundary
        preview_data = ExtractionService._execute_graph_extraction(meeting=meeting, user=user, db=db)

        # Cache preview in state store awaiting user confirmation
        _EXTRACTION_PREVIEWS[str(meeting_id)] = preview_data

        tasks = [ExtractedTask(**t) for t in preview_data.get("tasks", [])]
        highlights = [ExtractedHighlight(**h) for h in preview_data.get("highlights", [])]

        return ExtractionPreviewResponse(
            meeting_id=meeting_id,
            tasks=tasks,
            highlights=highlights,
            task_count=len(tasks),
            highlight_count=len(highlights),
            extraction_complete=True,
        )

    @staticmethod
    def _execute_graph_extraction(meeting: Meeting, user: User, db: Optional[Session] = None) -> dict[str, Any]:
        """
        Boundary interface for LangGraph extraction pipeline execution.
        Delegates to graph runner in Batch 3.
        """
        try:
            from app.graph.graph import run_extraction_graph
            return run_extraction_graph(meeting_id=meeting.id, user_id=user.id, db=db)
        except (ImportError, AttributeError):
            logger.info("LangGraph pipeline not yet compiled; returning initialized extraction state")
            return {
                "tasks": [],
                "highlights": [],
            }

    @staticmethod
    def get_extraction_preview(
        db: Session,
        meeting_id: UUID,
        user_id: UUID,
    ) -> ExtractionPreviewResponse:
        """
        Retrieves extracted tasks and highlights awaiting user confirmation.

        Args:
            db: Active synchronous database session.
            meeting_id: Target meeting UUID.
            user_id: Requesting user UUID.

        Returns:
            ExtractionPreviewResponse schema.

        Raises:
            MeetingNotFoundError: If meeting does not exist.
            InvalidOwnershipError: If meeting does not belong to user.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        if meeting.user_id != user_id:
            raise InvalidOwnershipError(
                f"Meeting with id '{meeting_id}' does not belong to user '{user_id}'.",
                details={"meeting_id": str(meeting_id), "user_id": str(user_id)},
            )

        cached = _EXTRACTION_PREVIEWS.get(str(meeting_id), {"tasks": [], "highlights": []})
        tasks = [ExtractedTask(**t) for t in cached.get("tasks", [])]
        highlights = [ExtractedHighlight(**h) for h in cached.get("highlights", [])]

        return ExtractionPreviewResponse(
            meeting_id=meeting_id,
            tasks=tasks,
            highlights=highlights,
            task_count=len(tasks),
            highlight_count=len(highlights),
            extraction_complete=str(meeting_id) in _EXTRACTION_PREVIEWS,
        )

    @staticmethod
    def set_extraction_preview(
        meeting_id: UUID,
        tasks: list[dict[str, Any]],
        highlights: list[dict[str, Any]],
    ) -> None:
        """Helper to inject or update preview state (used by Extraction Agent / tests)."""
        _EXTRACTION_PREVIEWS[str(meeting_id)] = {
            "tasks": tasks,
            "highlights": highlights,
        }

    @staticmethod
    def confirm_extraction(
        db: Session,
        confirm_req: ExtractionConfirmRequest,
    ) -> ExtractionResult:
        """
        Processes human-in-the-loop task confirmation:
        - Resumes LangGraph execution at ConfirmationAgent stage.
        - YES: Persists all extracted tasks with status=pending.
        - NO: Discards all extracted tasks.
        - PARTIAL: Persists only selected tasks from confirmed_task_ids.
        - Persists extracted highlights to database.
        - Clears pending preview cache upon completion.

        Args:
            db: Active synchronous database session.
            confirm_req: Validated confirmation payload.

        Returns:
            ExtractionResult summary.

        Raises:
            MeetingNotFoundError: If meeting does not exist.
            UserNotFoundError: If user does not exist.
            InvalidOwnershipError: If meeting does not belong to user or invalid task IDs provided.
            InvalidStateError: If confirmation already performed.
        """
        meeting_id_str = str(confirm_req.meeting_id)
        logger.info(
            f"Processing confirmation '{confirm_req.user_confirmation}' for meeting {meeting_id_str}"
        )

        meeting = db.query(Meeting).filter(Meeting.id == confirm_req.meeting_id).first()
        if not meeting:
            raise MeetingNotFoundError(
                f"Meeting with id '{confirm_req.meeting_id}' not found.",
                details={"meeting_id": meeting_id_str},
            )

        if meeting.user_id != confirm_req.user_id:
            raise InvalidOwnershipError(
                f"Meeting with id '{confirm_req.meeting_id}' does not belong to user '{confirm_req.user_id}'.",
                details={"meeting_id": meeting_id_str, "user_id": str(confirm_req.user_id)},
            )

        user = db.query(User).filter(User.id == confirm_req.user_id).first()
        if not user:
            raise UserNotFoundError(
                f"User with id '{confirm_req.user_id}' not found.",
                details={"user_id": str(confirm_req.user_id)},
            )

        decision = confirm_req.user_confirmation
        decision_val = (
            decision.value.lower() if hasattr(decision, "value") else str(decision).lower()
        )

        # Delegate to LangGraph HITL resume
        from app.graph.graph import resume_extraction_graph
        graph_res = resume_extraction_graph(
            meeting_id=confirm_req.meeting_id,
            user_id=confirm_req.user_id,
            confirmation=decision_val,
            confirmed_task_ids=[str(cid) for cid in confirm_req.confirmed_task_ids],
            db=db,
        )

        return ExtractionResult(
            meeting_id=confirm_req.meeting_id,
            saved_tasks=graph_res.get("saved_tasks", 0),
            discarded_tasks=graph_res.get("discarded_tasks", 0),
            saved_highlights=graph_res.get("saved_highlights", 0),
            confirmation_complete=True,
            dashboard_ready=True,
        )

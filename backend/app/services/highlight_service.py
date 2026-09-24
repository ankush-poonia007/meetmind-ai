"""
Highlight service for MeetMind AI.

Handles retrieval of meeting-scoped and user-scoped highlights (decisions,
announcements, key context). Enforces data scoping and relationship integrity.
Highlight generation remains the responsibility of the Extraction Agent.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.exceptions import HighlightNotFoundError, MeetingNotFoundError, UserNotFoundError
from app.core.logging import get_logger
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.user import User
from app.schemas.highlight import HighlightCreate, HighlightListResponse, HighlightResponse

logger = get_logger(__name__)


class HighlightService:
    """Service layer managing Highlight domain entities."""

    @staticmethod
    def get_meeting_highlights(
        db: Session,
        meeting_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> HighlightListResponse:
        """
        Retrieves highlights generated for a specific meeting.

        Args:
            db: Active synchronous database session.
            meeting_id: Unique UUID of the meeting.
            user_id: Optional user UUID filter.

        Returns:
            HighlightListResponse schema.

        Raises:
            MeetingNotFoundError: If the meeting does not exist.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Get meeting highlights failed: meeting {meeting_id} not found")
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        query = db.query(Highlight).filter(Highlight.meeting_id == meeting_id)
        target_user_id = user_id or meeting.user_id

        if user_id is not None:
            query = query.filter(Highlight.user_id == user_id)

        highlights = query.order_by(Highlight.created_at.desc()).all()

        return HighlightListResponse(
            meeting_id=meeting_id,
            user_id=target_user_id,
            highlights=[HighlightResponse.model_validate(h) for h in highlights],
        )

    @staticmethod
    def get_user_highlights(
        db: Session,
        user_id: UUID,
    ) -> HighlightListResponse:
        """
        Retrieves all highlights relevant to a user across all meetings.

        Args:
            db: Active synchronous database session.
            user_id: Unique UUID of the user.

        Returns:
            HighlightListResponse schema.

        Raises:
            UserNotFoundError: If the user does not exist.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"Get user highlights failed: user {user_id} not found")
            raise UserNotFoundError(
                f"User with id '{user_id}' not found.",
                details={"user_id": str(user_id)},
            )

        highlights = (
            db.query(Highlight)
            .filter(Highlight.user_id == user_id)
            .order_by(Highlight.created_at.desc())
            .all()
        )

        return HighlightListResponse(
            meeting_id=None,
            user_id=user_id,
            highlights=[HighlightResponse.model_validate(h) for h in highlights],
        )

    @staticmethod
    def create_highlight(
        db: Session,
        highlight_in: HighlightCreate,
    ) -> HighlightResponse:
        """
        Persists a single highlight item (invoked during extraction/confirmation).

        Args:
            db: Active synchronous database session.
            highlight_in: Validated highlight creation payload.

        Returns:
            HighlightResponse schema.

        Raises:
            MeetingNotFoundError: If the parent meeting does not exist.
            UserNotFoundError: If the target user does not exist.
        """
        meeting = db.query(Meeting).filter(Meeting.id == highlight_in.meeting_id).first()
        if not meeting:
            raise MeetingNotFoundError(
                f"Meeting with id '{highlight_in.meeting_id}' not found.",
                details={"meeting_id": str(highlight_in.meeting_id)},
            )

        user = db.query(User).filter(User.id == highlight_in.user_id).first()
        if not user:
            raise UserNotFoundError(
                f"User with id '{highlight_in.user_id}' not found.",
                details={"user_id": str(highlight_in.user_id)},
            )

        highlight = Highlight(
            meeting_id=highlight_in.meeting_id,
            user_id=highlight_in.user_id,
            content=highlight_in.content.strip(),
        )
        db.add(highlight)
        try:
            db.commit()
            db.refresh(highlight)
            logger.info(f"Persisted highlight {highlight.id} for meeting {highlight.meeting_id}")
        except Exception as exc:
            db.rollback()
            logger.error(f"Error persisting highlight: {exc}")
            raise

        return HighlightResponse.model_validate(highlight)

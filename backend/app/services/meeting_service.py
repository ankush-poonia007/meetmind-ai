"""
Meeting service for MeetMind AI.

Handles meeting lifecycle: creation, retrieval, list views, detail with participants,
and cascading deletion. Enforces user/meeting ownership boundaries and deterministic
title placeholder strategy.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.constants import InputFormat
from app.core.exceptions import InvalidOwnershipError, MeetingNotFoundError, UserNotFoundError
from app.core.logging import get_logger
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.user import User
from app.schemas.meeting import (
    MeetingCreate,
    MeetingDetail,
    MeetingListItem,
    MeetingResponse,
    ParticipantInfo,
)

logger = get_logger(__name__)

# Approved deterministic title placeholder strategy
TITLE_PLACEHOLDER = "Processing Transcript..."


class MeetingService:
    """Service layer managing Meeting domain entities and form-first creation."""

    @staticmethod
    def create_meeting(
        db: Session,
        meeting_in: MeetingCreate,
        submitter_name: Optional[str] = None,
        submitter_role: Optional[str] = None,
    ) -> MeetingResponse:
        """
        Creates a new meeting record with deterministic title placeholder
        and initializes the submitting user's participant entry.

        Args:
            db: Active synchronous database session.
            meeting_in: Validated meeting creation payload.
            submitter_name: Submitter's display name (defaults to User.name).
            submitter_role: Submitter's meeting role if specified in form.

        Returns:
            MeetingResponse schema.

        Raises:
            UserNotFoundError: If the specified user_id does not exist.
        """
        logger.info(f"Creating meeting for user {meeting_in.user_id}")

        # Validate user existence
        user = db.query(User).filter(User.id == meeting_in.user_id).first()
        if not user:
            logger.warning(f"Meeting creation rejected: user {meeting_in.user_id} not found")
            raise UserNotFoundError(
                f"User with id '{meeting_in.user_id}' not found.",
                details={"user_id": str(meeting_in.user_id)},
            )

        # Title placeholder strategy: use provided title or deterministic placeholder
        title = (
            meeting_in.title.strip()
            if meeting_in.title and meeting_in.title.strip()
            else TITLE_PLACEHOLDER
        )

        input_fmt = (
            meeting_in.input_format.value
            if hasattr(meeting_in.input_format, "value")
            else str(meeting_in.input_format)
        )

        meeting = Meeting(
            user_id=meeting_in.user_id,
            title=title,
            organization=meeting_in.organization,
            meeting_date=meeting_in.meeting_date,
            meeting_time=meeting_in.meeting_time,
            raw_transcript=meeting_in.raw_transcript,
            input_format=input_fmt,
            pinecone_namespace=None,
        )
        db.add(meeting)

        try:
            db.flush()  # Populate meeting.id for participant relationship

            # Create submitter participant
            participant_name = (
                submitter_name.strip()
                if submitter_name and submitter_name.strip()
                else user.name
            )
            participant = MeetingParticipant(
                meeting_id=meeting.id,
                name=participant_name,
                role=submitter_role,
                is_current_user=True,
            )
            db.add(participant)

            db.commit()
            db.refresh(meeting)
        except Exception as exc:
            db.rollback()
            logger.error(f"Error creating meeting for user {meeting_in.user_id}: {exc}")
            raise

        logger.info(f"Successfully created meeting {meeting.id} ('{meeting.title}')")
        return MeetingResponse.model_validate(meeting)

    @staticmethod
    def get_meetings_for_user(db: Session, user_id: UUID) -> list[MeetingListItem]:
        """
        Retrieves lightweight meeting summaries for a specific user,
        ordered by meeting_date descending, then created_at descending.

        Args:
            db: Active synchronous database session.
            user_id: Unique UUID of the owning user.

        Returns:
            List of MeetingListItem schemas.

        Raises:
            UserNotFoundError: If the user does not exist.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"Query meetings failed: user {user_id} not found")
            raise UserNotFoundError(
                f"User with id '{user_id}' not found.",
                details={"user_id": str(user_id)},
            )

        meetings = (
            db.query(Meeting)
            .filter(Meeting.user_id == user_id)
            .order_by(Meeting.meeting_date.desc(), Meeting.created_at.desc())
            .all()
        )
        return [MeetingListItem.model_validate(m) for m in meetings]

    @staticmethod
    def get_meeting_detail(
        db: Session,
        meeting_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> MeetingDetail:
        """
        Retrieves complete meeting detail including detected participants.
        Optionally enforces user ownership.

        Args:
            db: Active synchronous database session.
            meeting_id: Unique UUID of the meeting.
            user_id: Optional UUID of requesting user to enforce data isolation.

        Returns:
            MeetingDetail schema with populated participants list.

        Raises:
            MeetingNotFoundError: If the meeting does not exist.
            InvalidOwnershipError: If user_id is provided and does not match meeting owner.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Meeting not found with id {meeting_id}")
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        if user_id is not None and meeting.user_id != user_id:
            logger.warning(
                f"Ownership violation: user {user_id} attempted access to meeting {meeting_id} owned by {meeting.user_id}"
            )
            raise InvalidOwnershipError(
                f"Meeting with id '{meeting_id}' does not belong to user '{user_id}'.",
                details={"meeting_id": str(meeting_id), "user_id": str(user_id)},
            )

        participants = (
            db.query(MeetingParticipant)
            .filter(MeetingParticipant.meeting_id == meeting_id)
            .all()
        )

        return MeetingDetail(
            id=meeting.id,
            user_id=meeting.user_id,
            title=meeting.title,
            organization=meeting.organization,
            meeting_date=meeting.meeting_date,
            meeting_time=meeting.meeting_time,
            raw_transcript=meeting.raw_transcript,
            input_format=InputFormat(meeting.input_format),
            pinecone_namespace=meeting.pinecone_namespace,
            created_at=meeting.created_at,
            participants=[ParticipantInfo.model_validate(p) for p in participants],
        )

    @staticmethod
    def delete_meeting(
        db: Session,
        meeting_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> None:
        """
        Deletes a meeting and triggers database cascades for participants,
        tasks, highlights, chat messages, and chunks.

        Args:
            db: Active synchronous database session.
            meeting_id: Unique UUID of the meeting to delete.
            user_id: Optional UUID of requesting user to enforce data isolation.

        Raises:
            MeetingNotFoundError: If the meeting does not exist.
            InvalidOwnershipError: If user_id is provided and does not match meeting owner.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Delete failed: meeting {meeting_id} not found")
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        if user_id is not None and meeting.user_id != user_id:
            logger.warning(
                f"Delete ownership violation: user {user_id} attempted to delete meeting {meeting_id}"
            )
            raise InvalidOwnershipError(
                f"Meeting with id '{meeting_id}' does not belong to user '{user_id}'.",
                details={"meeting_id": str(meeting_id), "user_id": str(user_id)},
            )

        try:
            db.delete(meeting)
            db.commit()
            logger.info(f"Deleted meeting {meeting_id} and cascaded dependent records")
        except Exception as exc:
            db.rollback()
            logger.error(f"Error deleting meeting {meeting_id}: {exc}")
            raise

    @staticmethod
    def update_meeting_title(
        db: Session,
        meeting_id: UUID,
        title: str,
    ) -> MeetingResponse:
        """
        Updates the meeting title (invoked by Ingestion Agent after title generation).

        Args:
            db: Active synchronous database session.
            meeting_id: Unique UUID of the meeting.
            title: Final generated title.

        Returns:
            Updated MeetingResponse.

        Raises:
            MeetingNotFoundError: If the meeting does not exist.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        meeting.title = title.strip()
        try:
            db.commit()
            db.refresh(meeting)
        except Exception as exc:
            db.rollback()
            logger.error(f"Error updating title for meeting {meeting_id}: {exc}")
            raise

        logger.info(f"Updated meeting {meeting_id} title to: '{meeting.title}'")
        return MeetingResponse.model_validate(meeting)

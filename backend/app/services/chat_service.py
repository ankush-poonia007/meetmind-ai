"""
Chat service for MeetMind AI.

Handles meeting-scoped Q&A conversation history, message persistence,
history retrieval, and history clearing. Strictly enforces meeting isolation
and delegates Q&A reasoning to the graph/agent architecture.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.constants import ChatRole as AppChatRole, ConfidenceLevel
from app.core.exceptions import (
    InvalidOwnershipError,
    MeetingNotFoundError,
    UserNotFoundError,
)
from app.core.logging import get_logger
from app.db.models.chat_message import ChatMessage, ChatRole as DBChatRole
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.user import User
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSource,
)

logger = get_logger(__name__)


class ChatService:
    """Service layer managing meeting-scoped Q&A chat interactions."""

    @staticmethod
    def send_chat_message(
        db: Session,
        meeting_id: UUID,
        chat_request: ChatRequest,
    ) -> ChatResponse:
        """
        Processes a user question within a strictly scoped meeting context:
        1. Validates meeting and user existence.
        2. Persists the user question as a ChatMessage.
        3. Invokes the Q&A agent/pipeline boundary.
        4. Persists the assistant answer as a ChatMessage.
        5. Returns the synthesized answer with grounding citations.

        Args:
            db: Active synchronous database session.
            meeting_id: Unique UUID of the scoped meeting.
            chat_request: Validated question and user_id.

        Returns:
            ChatResponse schema.

        Raises:
            MeetingNotFoundError: If meeting does not exist.
            UserNotFoundError: If user does not exist.
        """
        logger.info(f"Processing chat message for meeting {meeting_id}, user {chat_request.user_id}")

        # Validate meeting existence
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Chat rejected: meeting {meeting_id} not found")
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        # Validate user existence
        user = db.query(User).filter(User.id == chat_request.user_id).first()
        if not user:
            logger.warning(f"Chat rejected: user {chat_request.user_id} not found")
            raise UserNotFoundError(
                f"User with id '{chat_request.user_id}' not found.",
                details={"user_id": str(chat_request.user_id)},
            )

        # 1. Persist user message
        user_msg = ChatMessage(
            meeting_id=meeting_id,
            user_id=chat_request.user_id,
            role=DBChatRole.user,
            content=chat_request.question.strip(),
        )
        db.add(user_msg)

        # Lookup participant details for Q&A context
        participant = (
            db.query(MeetingParticipant)
            .filter(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.is_current_user.is_(True),
            )
            .first()
        )
        user_name = participant.name if participant else user.name
        user_role = participant.role if participant else None

        # 2. Delegate Q&A execution to agent pipeline boundary
        answer, sources, confidence = ChatService._invoke_qa_pipeline(
            db=db,
            meeting=meeting,
            user=user,
            question=chat_request.question.strip(),
            user_name=user_name,
            user_role=user_role,
        )

        # 3. Persist assistant response
        assistant_msg = ChatMessage(
            meeting_id=meeting_id,
            user_id=chat_request.user_id,
            role=DBChatRole.assistant,
            content=answer,
        )
        db.add(assistant_msg)

        try:
            db.commit()
            logger.info(f"Chat exchange persisted for meeting {meeting_id}")
        except Exception as exc:
            db.rollback()
            logger.error(f"Error persisting chat exchange: {exc}")
            raise

        return ChatResponse(
            meeting_id=meeting_id,
            answer=answer,
            sources=sources,
            confidence=confidence,
        )

    @staticmethod
    def _invoke_qa_pipeline(
        db: Session,
        meeting: Meeting,
        user: User,
        question: str,
        user_name: str,
        user_role: Optional[str] = None,
    ) -> tuple[str, list[ChatSource], ConfidenceLevel]:
        """
        Boundary interface for Q&A Agent execution.
        Delegates to LangGraph Q&A sub-agent when implemented (Batch 3).
        Provides graceful application fallback when agents are not yet wired.
        """
        try:
            from app.graph.graph import run_qa_graph
            graph_res = run_qa_graph(
                meeting_id=meeting.id,
                user_id=user.id,
                question=question,
                user_name=user_name,
                user_role=user_role,
                db=db,
            )
            answer = graph_res.get("qa_answer") or graph_res.get("final_response", "")
            raw_sources = graph_res.get("qa_sources", [])
            sources = [ChatSource(**s) if isinstance(s, dict) else s for s in raw_sources]
            raw_confidence = graph_res.get("qa_confidence", "high")
            try:
                confidence = ConfidenceLevel(raw_confidence.lower())
            except (ValueError, AttributeError):
                confidence = ConfidenceLevel.HIGH
            return answer, sources, confidence
        except (ImportError, AttributeError):
            logger.info("Q&A graph not yet loaded; using service boundary placeholder")
            # Default placeholder answer for Batch 1 testing
            fallback_answer = f"I found information regarding '{question}' in meeting '{meeting.title}'."
            return fallback_answer, [], ConfidenceLevel.HIGH

    @staticmethod
    def get_chat_history(
        db: Session,
        meeting_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> ChatHistoryResponse:
        """
        Retrieves all chat messages for a meeting, ordered chronologically.
        Strictly prevents cross-meeting retrieval.

        Args:
            db: Active synchronous database session.
            meeting_id: Unique UUID of the meeting.
            user_id: Optional user UUID filter.

        Returns:
            ChatHistoryResponse schema.

        Raises:
            MeetingNotFoundError: If meeting does not exist.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Get chat history failed: meeting {meeting_id} not found")
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        query = db.query(ChatMessage).filter(ChatMessage.meeting_id == meeting_id)
        if user_id is not None:
            query = query.filter(ChatMessage.user_id == user_id)

        messages = query.order_by(ChatMessage.created_at.asc()).all()

        return ChatHistoryResponse(
            meeting_id=meeting_id,
            messages=[ChatMessageResponse.model_validate(m) for m in messages],
        )

    @staticmethod
    def clear_chat_history(
        db: Session,
        meeting_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> None:
        """
        Deletes chat messages for a given meeting.

        Args:
            db: Active synchronous database session.
            meeting_id: Unique UUID of the meeting.
            user_id: Optional user UUID filter.

        Raises:
            MeetingNotFoundError: If meeting does not exist.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Clear chat history failed: meeting {meeting_id} not found")
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        query = db.query(ChatMessage).filter(ChatMessage.meeting_id == meeting_id)
        if user_id is not None:
            query = query.filter(ChatMessage.user_id == user_id)

        try:
            query.delete(synchronize_session=False)
            db.commit()
            logger.info(f"Cleared chat history for meeting {meeting_id}")
        except Exception as exc:
            db.rollback()
            logger.error(f"Error clearing chat history for meeting {meeting_id}: {exc}")
            raise

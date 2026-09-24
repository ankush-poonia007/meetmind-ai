"""
Chat API router for MeetMind AI.

Exposes meeting-scoped Q&A chat endpoints: send message, retrieve history,
and clear history. Strictly enforces meeting isolation.
Delegates entirely to ChatService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.chat_service import ChatService

router = APIRouter()


@router.post(
    "/{meeting_id}/message",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send chat message",
    description="Submits a question to the meeting-scoped Q&A pipeline, persists conversation, and returns grounded response.",
)
def send_chat_message(
    meeting_id: UUID,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Sends question to meeting Q&A pipeline."""
    return ChatService.send_chat_message(db=db, meeting_id=meeting_id, chat_request=chat_request)


@router.get(
    "/{meeting_id}/history",
    response_model=ChatHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chat history",
    description="Retrieves chronological conversation history for a specific meeting.",
)
def get_chat_history(
    meeting_id: UUID,
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    """Retrieves chat history for a meeting."""
    return ChatService.get_chat_history(db=db, meeting_id=meeting_id)


@router.delete(
    "/{meeting_id}/history",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear chat history",
    description="Deletes all conversation messages for a specific meeting.",
)
def clear_chat_history(
    meeting_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    """Clears chat messages for a meeting."""
    ChatService.clear_chat_history(db=db, meeting_id=meeting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

"""
Pydantic contracts for Meeting-Scoped Chat (Q&A) domain.

Defines schemas for questions, answers, source attribution,
and conversation history aligned with the locked Gate 1 database schema.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ChatRole, ConfidenceLevel


# ── Source Attribution ───────────────────────────────────────────────────────

class ChatSource(BaseModel):
    """Retrieved chunk source citation accompanying an answer."""
    speaker: Optional[str] = Field(None, description="Speaker name associated with chunk")
    timestamp: Optional[str] = Field(None, description="Transcript timestamp of excerpt")
    excerpt: str = Field(..., description="Verbatim transcript excerpt")


# ── Chat Messages ────────────────────────────────────────────────────────────

class ChatMessageBase(BaseModel):
    """Base chat message content."""
    content: str = Field(..., min_length=1, description="Message text")


class ChatMessageCreate(ChatMessageBase):
    """Payload to create and persist a chat message."""
    meeting_id: UUID = Field(..., description="Associated meeting identifier")
    user_id: UUID = Field(..., description="Message author or owner")
    role: ChatRole = Field(ChatRole.USER, description="Message role: user or assistant")


class ChatMessageResponse(ChatMessageBase):
    """Standard API response for a persisted chat message."""
    id: UUID = Field(..., description="Unique message identifier")
    meeting_id: UUID = Field(..., description="Associated meeting identifier")
    user_id: UUID = Field(..., description="Message author or owner")
    role: ChatRole = Field(..., description="Message role")
    created_at: datetime = Field(..., description="Message timestamp")

    model_config = ConfigDict(from_attributes=True)


# ── High-Level Q&A Interactions ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Payload for submitting a question to the Q&A pipeline (POST /api/v1/chat/{meeting_id}/message)."""
    question: str = Field(..., min_length=1, description="Natural language question about the meeting")
    user_id: UUID = Field(..., description="User submitting question")


class ChatResponse(BaseModel):
    """Response returned from the Q&A Agent."""
    meeting_id: UUID = Field(..., description="Meeting identifier")
    answer: str = Field(..., description="AI-generated answer")
    sources: list[ChatSource] = Field(default_factory=list, description="Grounding citations")
    confidence: ConfidenceLevel = Field(ConfidenceLevel.HIGH, description="Answer confidence")


class ChatHistoryResponse(BaseModel):
    """History of messages for a meeting chat (GET /api/v1/chat/{meeting_id}/history)."""
    meeting_id: UUID = Field(..., description="Meeting identifier")
    messages: list[ChatMessageResponse] = Field(default_factory=list, description="Ordered conversation history")


# Convenience alias
ChatMessageRead = ChatMessageResponse

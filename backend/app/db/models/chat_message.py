"""
ChatMessage model.

Persists meeting-scoped Q&A conversation history between the user
and the Q&A Agent.  Ordered by created_at for sequential retrieval.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.base import Base


class ChatRole(str, enum.Enum):
    """Locked role values for chat messages — do not extend."""
    user = "user"
    assistant = "assistant"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    # ── Composite indexes ──────────────────────────────────────────────────
    # Supports the Q&A Agent's "last 5 messages" retrieval pattern.
    __table_args__ = (
        Index(
            "ix_chat_messages_meeting_id_user_id_created_at",
            "meeting_id",
            "user_id",
            "created_at",
        ),
    )

    # ── Primary Key ────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ── Foreign Keys ───────────────────────────────────────────────────────
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Columns ────────────────────────────────────────────────────────────
    role: Mapped[ChatRole] = mapped_column(
        Enum(ChatRole, name="chat_role", create_type=True),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship(  # noqa: F821
        "Meeting",
        back_populates="chat_messages",
        lazy="select",
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="chat_messages",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<ChatMessage id={self.id!s} role={self.role}"
            f" meeting_id={self.meeting_id!s}>"
        )

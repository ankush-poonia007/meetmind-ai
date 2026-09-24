"""
Meeting model.

Stores a meeting and its original transcript.
Acts as the parent for participants, tasks, highlights,
chat messages, and transcript chunks.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.base import Base


class Meeting(Base):
    __tablename__ = "meetings"

    # ── Primary Key ────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ── Foreign Keys ───────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Columns ────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String, nullable=False)

    # organization and meeting_time are included per final locked schema.
    organization: Mapped[str | None] = mapped_column(String, nullable=True)

    meeting_date: Mapped[date] = mapped_column(Date, nullable=False)

    meeting_time: Mapped[str | None] = mapped_column(String, nullable=True)

    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False)

    input_format: Mapped[str] = mapped_column(String, nullable=False)

    # Nullable until the Ingestion Agent sets the Pinecone namespace.
    pinecone_namespace: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="meetings",
        lazy="select",
    )

    participants: Mapped[list["MeetingParticipant"]] = relationship(  # noqa: F821
        "MeetingParticipant",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="select",
    )

    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="select",
    )

    highlights: Mapped[list["Highlight"]] = relationship(  # noqa: F821
        "Highlight",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="select",
    )

    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        "ChatMessage",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="select",
    )

    transcript_chunks: Mapped[list["TranscriptChunk"]] = relationship(  # noqa: F821
        "TranscriptChunk",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Meeting id={self.id!s} title={self.title!r}>"

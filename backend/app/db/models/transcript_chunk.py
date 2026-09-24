"""
TranscriptChunk model.

Stores the PostgreSQL representation of meeting transcript chunks
used by BM25 retrieval and linking Pinecone vector IDs back to
structured chunk metadata.

pinecone_vector_id MUST remain nullable — the chunk row can be
created before its Pinecone vector upsert succeeds.
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TranscriptChunkType(str, enum.Enum):
    """Locked chunk type values — do not extend."""
    dialogue = "dialogue"
    decision = "decision"
    task_mention = "task_mention"


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    # ── Indexes ────────────────────────────────────────────────────────────
    # meeting_id index supports meeting-scoped BM25 retrieval.
    __table_args__ = (
        Index("ix_transcript_chunks_meeting_id", "meeting_id"),
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

    # ── Columns ────────────────────────────────────────────────────────────
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    speaker_name: Mapped[str | None] = mapped_column(String, nullable=True)

    speaker_role: Mapped[str | None] = mapped_column(String, nullable=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    timestamp: Mapped[str | None] = mapped_column(String, nullable=True)

    chunk_type: Mapped[TranscriptChunkType | None] = mapped_column(
        Enum(TranscriptChunkType, name="transcript_chunk_type", create_type=True),
        nullable=True,
    )

    involves_user: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # Nullable — chunk can exist before Pinecone vector is created.
    pinecone_vector_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship(  # noqa: F821
        "Meeting",
        back_populates="transcript_chunks",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<TranscriptChunk id={self.id!s} meeting_id={self.meeting_id!s}"
            f" chunk_index={self.chunk_index} chunk_type={self.chunk_type}>"
        )

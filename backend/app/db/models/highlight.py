"""
Highlight model.

Stores important meeting announcements, decisions, and context
that are relevant to the identified user but are not personal tasks.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.base import Base


class Highlight(Base):
    __tablename__ = "highlights"

    # ── Composite indexes ──────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_highlights_meeting_id_user_id", "meeting_id", "user_id"),
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
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship(  # noqa: F821
        "Meeting",
        back_populates="highlights",
        lazy="select",
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="highlights",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Highlight id={self.id!s} meeting_id={self.meeting_id!s}>"

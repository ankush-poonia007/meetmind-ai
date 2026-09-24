"""
MeetingParticipant model.

Stores participants detected in a meeting transcript.
The is_current_user flag identifies the submitting user
among all detected participants.

NOTE: No user_id FK — participants are identified by name/role match,
not by a users table reference.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

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
        index=True,
    )

    # ── Columns ────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String, nullable=False)

    role: Mapped[str | None] = mapped_column(String, nullable=True)

    is_current_user: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # ── Relationships ──────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship(  # noqa: F821
        "Meeting",
        back_populates="participants",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<MeetingParticipant id={self.id!s} name={self.name!r}"
            f" is_current_user={self.is_current_user}>"
        )

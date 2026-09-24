"""
User model.

Represents the current MeetMind user identity and email address.
One user can own many meetings, tasks, highlights, and chat messages.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # ── Primary Key ────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ── Columns ────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String, nullable=False)

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    meetings: Mapped[list["Meeting"]] = relationship(  # noqa: F821
        "Meeting",
        back_populates="user",
        lazy="select",
    )

    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task",
        back_populates="user",
        lazy="select",
    )

    highlights: Mapped[list["Highlight"]] = relationship(  # noqa: F821
        "Highlight",
        back_populates="user",
        lazy="select",
    )

    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        "ChatMessage",
        back_populates="user",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!s} email={self.email!r}>"

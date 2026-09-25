"""
Task model.

Stores tasks confirmed by the user during the Confirmation Agent step.
Supports deadline monitoring, priority filtering, and alert state tracking.
"""

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import DateTime

from app.db.base import Base


class TaskPriority(str, enum.Enum):
    """Locked priority values — do not extend."""
    high = "high"
    medium = "medium"
    low = "low"


class TaskStatus(str, enum.Enum):
    """Locked status values — do not extend."""
    pending = "pending"
    complete = "complete"


class Task(Base):
    __tablename__ = "tasks"

    # ── Composite indexes ──────────────────────────────────────────────────
    # Defined at table level so Alembic includes them in autogeneration.
    __table_args__ = (
        Index("ix_tasks_user_id_status_deadline", "user_id", "status", "deadline"),
        Index("ix_tasks_meeting_id", "meeting_id"),
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
    title: Mapped[str] = mapped_column(String, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    priority: Mapped[TaskPriority | None] = mapped_column(
        Enum(TaskPriority, name="task_priority", create_type=True),
        nullable=True,
    )

    # MUST be nullable — Extraction Agent may not find a deadline.
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @validates("deadline")
    def validate_deadline(self, key: str, value: Any) -> Any:
        from app.core.utils import normalize_deadline
        return normalize_deadline(value)

    @property
    def due_at(self) -> datetime | None:
        """Alias for deadline to support due_at property references."""
        return self.deadline

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_type=True),
        nullable=False,
        default=TaskStatus.pending,
        server_default="pending",
    )

    alert_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    meeting: Mapped["Meeting"] = relationship(  # noqa: F821
        "Meeting",
        back_populates="tasks",
        lazy="select",
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="tasks",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Task id={self.id!s} title={self.title!r}"
            f" status={self.status} priority={self.priority}>"
        )

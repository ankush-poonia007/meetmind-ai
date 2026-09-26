"""
UserCredentials model for MeetMind AI.

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.4 — Authentication & Database Foundation

Stores password hashes and credential metadata in a dedicated table,
strictly separating authentication secrets from user identity.
Enforces an explicit one-to-one relationship with the users table.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.db.base import Base


class UserCredentials(Base):
    __tablename__ = "user_credentials"

    # ── Primary Key & Foreign Key (1:1 with users) ──────────────────────────
    # Using user_id as both primary key and unique foreign key guarantees
    # an unambiguous, database-enforced 1:1 relationship with the users table.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # ── Columns ────────────────────────────────────────────────────────────
    # Argon2id hashes are typically ~96 characters; String(255) provides safe headroom.
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="credentials",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<UserCredentials user_id={self.user_id!s}>"

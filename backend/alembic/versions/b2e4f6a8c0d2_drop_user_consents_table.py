"""drop user_consents table

Revision ID: b2e4f6a8c0d2
Revises: a4f8d1c2b3e5
Create Date: 2026-09-26 07:30:00.000000

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Task: Simplify Authentication by Removing the Consent Policy System

Changes:
1. Drop indexes on `user_consents` table:
   - `ix_user_consents_user_id_consent_type`
   - `ix_user_consents_user_id`
2. Drop `user_consents` table.

Downgrade:
Recreates the `user_consents` table and its indexes as defined in revision a4f8d1c2b3e5.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2e4f6a8c0d2"
down_revision: Union[str, None] = "a4f8d1c2b3e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Drop indexes on user_consents ───────────────────────────────────
    op.drop_index("ix_user_consents_user_id_consent_type", table_name="user_consents")
    op.drop_index("ix_user_consents_user_id", table_name="user_consents")

    # ── 2. Drop user_consents table ────────────────────────────────────────
    op.drop_table("user_consents")


def downgrade() -> None:
    # ── Recreate user_consents table ───────────────────────────────────────
    op.create_table(
        "user_consents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "consent_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "granted",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "policy_version",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])
    op.create_index(
        "ix_user_consents_user_id_consent_type",
        "user_consents",
        ["user_id", "consent_type"],
    )

"""user auth and consent foundation

Revision ID: e8c9b1d2e3f4
Revises: 7a82b9c01d2e
Create Date: 2026-09-26 07:00:00.000000

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.4 — Authentication & Database Foundation

Changes:
1. Extend `users` table with optional profile fields:
   - `first_name` (VARCHAR(100), nullable)
   - `last_name` (VARCHAR(100), nullable)
   - `mobile_number` (VARCHAR(25), nullable, non-unique, indexed)
2. Create `user_credentials` table (1:1 with `users`):
   - `user_id` (UUID PK, FK -> users.id, ON DELETE CASCADE)
   - `password_hash` (VARCHAR(255), not null)
   - `created_at` (TIMESTAMPTZ, default now())
   - `updated_at` (TIMESTAMPTZ, default now())
3. Create `user_consents` table:
   - `id` (UUID PK)
   - `user_id` (UUID FK -> users.id, ON DELETE CASCADE)
   - `consent_type` (VARCHAR(50), not null)
   - `granted` (BOOLEAN, not null)
   - `policy_version` (VARCHAR(50), not null)
   - `ip_address` (VARCHAR(45), nullable)
   - `user_agent` (VARCHAR(500), nullable)
   - `created_at` (TIMESTAMPTZ, default now())
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e8c9b1d2e3f4"
down_revision: Union[str, None] = "7a82b9c01d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Extend users table ──────────────────────────────────────────────
    op.add_column("users", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("mobile_number", sa.String(length=25), nullable=True))
    op.create_index("ix_users_mobile_number", "users", ["mobile_number"], unique=False)

    # ── 2. Create user_credentials table ───────────────────────────────────
    op.create_table(
        "user_credentials",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── 3. Create user_consents table ──────────────────────────────────────
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
            server_default="terms_and_privacy",
            nullable=False,
        ),
        sa.Column(
            "granted",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "policy_version",
            sa.String(length=50),
            server_default="v1.0",
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


def downgrade() -> None:
    # ── 3. Drop user_consents table ────────────────────────────────────────
    op.drop_index("ix_user_consents_user_id_consent_type", table_name="user_consents")
    op.drop_index("ix_user_consents_user_id", table_name="user_consents")
    op.drop_table("user_consents")

    # ── 2. Drop user_credentials table ─────────────────────────────────────
    op.drop_table("user_credentials")

    # ── 1. Revert users table extension ────────────────────────────────────
    op.drop_index("ix_users_mobile_number", table_name="users")
    op.drop_column("users", "mobile_number")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")

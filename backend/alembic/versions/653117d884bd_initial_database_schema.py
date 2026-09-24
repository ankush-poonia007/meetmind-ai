"""initial database schema

Revision ID: 653117d884bd
Revises:
Create Date: 2026-09-24

Creates all seven MeetMind AI application tables with:
- PostgreSQL ENUM types (task_priority, task_status, chat_role, transcript_chunk_type)
- UUID primary keys (Python-generated via uuid.uuid4)
- Timezone-aware TIMESTAMP WITH TIME ZONE columns with server-side now() defaults
- Required foreign key constraints with ON DELETE CASCADE / RESTRICT behavior
- UNIQUE constraint on users.email
- Required application indexes
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "653117d884bd"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── PostgreSQL ENUM types ────────────────────────────────────────────
    # Created before the tables that reference them.
    task_priority = postgresql.ENUM(
        "high", "medium", "low",
        name="task_priority",
        create_type=False,
    )
    task_priority.create(op.get_bind(), checkfirst=True)

    task_status = postgresql.ENUM(
        "pending", "complete",
        name="task_status",
        create_type=False,
    )
    task_status.create(op.get_bind(), checkfirst=True)

    chat_role = postgresql.ENUM(
        "user", "assistant",
        name="chat_role",
        create_type=False,
    )
    chat_role.create(op.get_bind(), checkfirst=True)

    transcript_chunk_type = postgresql.ENUM(
        "dialogue", "decision", "task_mention",
        name="transcript_chunk_type",
        create_type=False,
    )
    transcript_chunk_type.create(op.get_bind(), checkfirst=True)

    # ── TABLE: users ─────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── TABLE: meetings ──────────────────────────────────────────────────
    op.create_table(
        "meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("organization", sa.String(), nullable=True),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("meeting_time", sa.String(), nullable=True),
        sa.Column("raw_transcript", sa.Text(), nullable=False),
        sa.Column("input_format", sa.String(), nullable=False),
        sa.Column("pinecone_namespace", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meetings_user_id", "meetings", ["user_id"])

    # ── TABLE: meeting_participants ───────────────────────────────────────
    op.create_table(
        "meeting_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column(
            "is_current_user",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"], ["meetings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meeting_participants_meeting_id",
        "meeting_participants",
        ["meeting_id"],
    )

    # ── TABLE: tasks ─────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "high", "medium", "low", name="task_priority", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "complete", name="task_status", create_type=False
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "alert_sent",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"], ["meetings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tasks_user_id_status_deadline",
        "tasks",
        ["user_id", "status", "deadline"],
    )
    op.create_index("ix_tasks_meeting_id", "tasks", ["meeting_id"])

    # ── TABLE: highlights ────────────────────────────────────────────────
    op.create_table(
        "highlights",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"], ["meetings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_highlights_meeting_id_user_id",
        "highlights",
        ["meeting_id", "user_id"],
    )

    # ── TABLE: chat_messages ─────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "user", "assistant", name="chat_role", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"], ["meetings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_messages_meeting_id_user_id_created_at",
        "chat_messages",
        ["meeting_id", "user_id", "created_at"],
    )

    # ── TABLE: transcript_chunks ─────────────────────────────────────────
    op.create_table(
        "transcript_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("speaker_name", sa.String(), nullable=True),
        sa.Column("speaker_role", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.String(), nullable=True),
        sa.Column(
            "chunk_type",
            postgresql.ENUM(
                "dialogue",
                "decision",
                "task_mention",
                name="transcript_chunk_type",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "involves_user",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("pinecone_vector_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["meeting_id"], ["meetings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transcript_chunks_meeting_id",
        "transcript_chunks",
        ["meeting_id"],
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order to respect FK constraints.
    op.drop_table("transcript_chunks")
    op.drop_index(
        "ix_chat_messages_meeting_id_user_id_created_at",
        table_name="chat_messages",
    )
    op.drop_table("chat_messages")
    op.drop_index("ix_highlights_meeting_id_user_id", table_name="highlights")
    op.drop_table("highlights")
    op.drop_index("ix_tasks_meeting_id", table_name="tasks")
    op.drop_index("ix_tasks_user_id_status_deadline", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index(
        "ix_meeting_participants_meeting_id",
        table_name="meeting_participants",
    )
    op.drop_table("meeting_participants")
    op.drop_index("ix_meetings_user_id", table_name="meetings")
    op.drop_table("meetings")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    # Drop ENUM types after all tables that reference them are gone.
    op.execute("DROP TYPE IF EXISTS transcript_chunk_type")
    op.execute("DROP TYPE IF EXISTS chat_role")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS task_priority")

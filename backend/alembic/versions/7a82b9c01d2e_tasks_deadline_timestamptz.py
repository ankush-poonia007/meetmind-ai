"""Tasks deadline to TIMESTAMPTZ.

Revision ID: 7a82b9c01d2e
Revises: 653117d884bd
Create Date: 2026-09-25 16:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a82b9c01d2e"
down_revision: Union[str, None] = "653117d884bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "tasks",
        "deadline",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.Date(),
        existing_nullable=True,
        postgresql_using="deadline::timestamp with time zone",
    )


def downgrade() -> None:
    op.alter_column(
        "tasks",
        "deadline",
        type_=sa.Date(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="deadline::date",
    )

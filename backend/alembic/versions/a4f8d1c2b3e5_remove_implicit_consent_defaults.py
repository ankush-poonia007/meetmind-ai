"""remove implicit consent defaults

Revision ID: a4f8d1c2b3e5
Revises: e8c9b1d2e3f4
Create Date: 2026-09-26 07:15:00.000000

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.4 — Consent Corrections

Changes:
1. Drop server_default on `user_consents.granted` so that an explicit decision
   (True or False) is strictly required and never assumed.
2. Drop server_default on `user_consents.consent_type` so that the specific purpose
   (data_use or model_enhancement) is explicitly required.
3. Drop server_default on `user_consents.policy_version` so that policy versioning
   is explicitly recorded without silent assignment.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4f8d1c2b3e5"
down_revision: Union[str, None] = "e8c9b1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop server defaults on user_consents columns so explicit decisions are required
    op.alter_column("user_consents", "granted", server_default=None)
    op.alter_column("user_consents", "consent_type", server_default=None)
    op.alter_column("user_consents", "policy_version", server_default=None)


def downgrade() -> None:
    # Restore previous server defaults if downgraded
    op.alter_column("user_consents", "policy_version", server_default="v1.0")
    op.alter_column("user_consents", "consent_type", server_default="terms_and_privacy")
    op.alter_column("user_consents", "granted", server_default="true")

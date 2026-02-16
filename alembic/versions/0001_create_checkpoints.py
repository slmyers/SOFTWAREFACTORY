"""Create checkpoints table

Revision ID: 0001
Revises:
Create Date: 2026-02-16

Issue #5: AgentState + checkpointing

Creates the `checkpoints` table for versioned checkpoint persistence:
- id: UUID primary key
- thread_id: indexed text for checkpoint grouping
- version: integer version number per thread_id
- state: JSONB blob containing full AgentState
- created_at: timestamp when checkpoint was created
- updated_at: timestamp when checkpoint was last updated
- Unique index on (thread_id, version) for fast lookups
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "checkpoints",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("thread_id", sa.Text(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Create unique index on (thread_id, version) for fast lookups and to ensure no duplicate versions
    op.create_index(
        "ix_checkpoints_thread_id_version",
        "checkpoints",
        ["thread_id", "version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_checkpoints_thread_id_version", table_name="checkpoints")
    op.drop_table("checkpoints")

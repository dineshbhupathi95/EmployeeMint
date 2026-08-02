"""Add created_by to AI assistant tables

Revision ID: 011
Revises: 010
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("ai_configs", "ai_documents", "ai_chunks", "ai_conversations"):
        op.add_column(
            table,
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        )


def downgrade() -> None:
    for table in ("ai_conversations", "ai_chunks", "ai_documents", "ai_configs"):
        op.drop_column(table, "created_by")

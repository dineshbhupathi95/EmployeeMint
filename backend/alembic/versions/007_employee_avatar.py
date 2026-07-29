"""Add employee avatar_path

Revision ID: 007
Revises: 006
Create Date: 2026-07-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("avatar_path", sa.String(length=500), nullable=True))
    op.add_column("employees", sa.Column("avatar_content_type", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "avatar_content_type")
    op.drop_column("employees", "avatar_path")

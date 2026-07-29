"""Add show_on_dashboard to announcements

Revision ID: 006
Revises: 005
Create Date: 2026-07-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "announcements",
        sa.Column(
            "show_on_dashboard",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("announcements", "show_on_dashboard")

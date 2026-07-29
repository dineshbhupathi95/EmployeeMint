"""Tenant organization logo for nav branding

Revision ID: 009
Revises: 008
Create Date: 2026-07-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("logo_path", sa.String(length=500), nullable=True))
    op.add_column("tenants", sa.Column("logo_content_type", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "logo_content_type")
    op.drop_column("tenants", "logo_path")

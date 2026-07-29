"""Employee compensation / my pay

Revision ID: 004
Revises: 003
Create Date: 2026-07-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_compensation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ctc", sa.String(length=100), nullable=True),
        sa.Column("ctc_annual", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("designation", sa.String(length=255), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("gross_monthly", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("net_monthly", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("earnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("deductions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="admin"),
        sa.Column("offer_letter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_letter_id"], ["offer_letters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "employee_id", name="uq_comp_tenant_employee"),
    )
    op.create_index(
        op.f("ix_employee_compensation_employee_id"),
        "employee_compensation",
        ["employee_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_employee_compensation_tenant_id"),
        "employee_compensation",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("employee_compensation")

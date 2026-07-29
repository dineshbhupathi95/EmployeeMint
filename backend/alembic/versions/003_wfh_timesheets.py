"""WFH requests and timesheets

Revision ID: 003
Revises: 002
Create Date: 2026-07-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wfh_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "employee_id", "request_date", name="uq_wfh_employee_date"),
    )
    op.create_index(op.f("ix_wfh_requests_employee_id"), "wfh_requests", ["employee_id"], unique=False)
    op.create_index(op.f("ix_wfh_requests_request_date"), "wfh_requests", ["request_date"], unique=False)
    op.create_index(op.f("ix_wfh_requests_status"), "wfh_requests", ["status"], unique=False)
    op.create_index(op.f("ix_wfh_requests_tenant_id"), "wfh_requests", ["tenant_id"], unique=False)

    op.create_table(
        "timesheet_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_timesheet_entries_employee_id"), "timesheet_entries", ["employee_id"], unique=False)
    op.create_index(op.f("ix_timesheet_entries_work_date"), "timesheet_entries", ["work_date"], unique=False)
    op.create_index(op.f("ix_timesheet_entries_status"), "timesheet_entries", ["status"], unique=False)
    op.create_index(op.f("ix_timesheet_entries_tenant_id"), "timesheet_entries", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_table("timesheet_entries")
    op.drop_table("wfh_requests")

"""Payroll runs, lines, and employee bank accounts

Revision ID: 012
Revises: 011
Create Date: 2026-08-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_bank_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_holder_name", sa.String(length=200), nullable=False),
        sa.Column("account_number", sa.String(length=50), nullable=False),
        sa.Column("ifsc_code", sa.String(length=20), nullable=False),
        sa.Column("bank_name", sa.String(length=200), nullable=False),
        sa.Column("branch_name", sa.String(length=200), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "employee_id", name="uq_bank_account_tenant_employee"),
    )
    op.create_index("ix_employee_bank_accounts_employee_id", "employee_bank_accounts", ["employee_id"])
    op.create_index("ix_employee_bank_accounts_tenant_id", "employee_bank_accounts", ["tenant_id"])

    op.create_table(
        "payroll_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("finance_notes", sa.Text(), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.Date(), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.Date(), nullable=True),
        sa.Column("total_gross", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("total_net", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
        sa.Column("employee_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "month", "year", name="uq_payroll_run_period"),
    )
    op.create_index("ix_payroll_runs_status", "payroll_runs", ["status"])
    op.create_index("ix_payroll_runs_tenant_id", "payroll_runs", ["tenant_id"])

    op.create_table(
        "payroll_run_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payroll_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_code", sa.String(length=50), nullable=False),
        sa.Column("employee_name", sa.String(length=200), nullable=False),
        sa.Column("base_gross", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("base_deductions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("lop_days", sa.Numeric(precision=5, scale=1), nullable=False, server_default="0"),
        sa.Column("lop_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("bonus", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("other_earnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("other_deductions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("gross_pay", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("total_deductions", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("net_pay", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("leave_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("bank_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("payment_status", sa.String(length=30), nullable=True),
        sa.Column("payment_reference", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_run_id"], ["payroll_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payroll_run_id", "employee_id", name="uq_payroll_line_run_employee"),
    )
    op.create_index("ix_payroll_run_lines_employee_id", "payroll_run_lines", ["employee_id"])
    op.create_index("ix_payroll_run_lines_payroll_run_id", "payroll_run_lines", ["payroll_run_id"])
    op.create_index("ix_payroll_run_lines_tenant_id", "payroll_run_lines", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("payroll_run_lines")
    op.drop_table("payroll_runs")
    op.drop_table("employee_bank_accounts")

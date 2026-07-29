"""Module tables

Revision ID: 002
Revises: 001
Create Date: 2026-07-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "request_type", name="uq_workflows_tenant_type"),
    )
    op.create_index(op.f("ix_approval_workflows_request_type"), "approval_workflows", ["request_type"], unique=False)
    op.create_index(op.f("ix_approval_workflows_tenant_id"), "approval_workflows", ["tenant_id"], unique=False)

    op.create_table(
        "approval_workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("approver_rule", sa.String(length=50), nullable=False),
        sa.Column("approver_value", sa.String(length=255), nullable=True),
        sa.Column("condition_field", sa.String(length=100), nullable=True),
        sa.Column("condition_operator", sa.String(length=20), nullable=True),
        sa.Column("condition_value", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["approval_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("requester_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_step_order", sa.Integer(), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approval_requests_request_type"), "approval_requests", ["request_type"], unique=False)
    op.create_index(op.f("ix_approval_requests_requester_user_id"), "approval_requests", ["requester_user_id"], unique=False)
    op.create_index(op.f("ix_approval_requests_status"), "approval_requests", ["status"], unique=False)
    op.create_index(op.f("ix_approval_requests_tenant_id"), "approval_requests", ["tenant_id"], unique=False)

    op.create_table(
        "approval_request_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["approval_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_approval_request_steps_approver_user_id"),
        "approval_request_steps",
        ["approver_user_id"],
        unique=False,
    )

    op.create_table(
        "leave_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("annual_quota", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("is_paid", sa.Boolean(), nullable=False),
        sa.Column("requires_document", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_leave_types_tenant_code"),
    )
    op.create_index(op.f("ix_leave_types_tenant_id"), "leave_types", ["tenant_id"], unique=False)

    op.create_table(
        "leave_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("leave_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("allocated", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("used", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("pending", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_type_id"], ["leave_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "employee_id", "leave_type_id", "year", name="uq_leave_balance"),
    )
    op.create_index(op.f("ix_leave_balances_employee_id"), "leave_balances", ["employee_id"], unique=False)
    op.create_index(op.f("ix_leave_balances_tenant_id"), "leave_balances", ["tenant_id"], unique=False)

    op.create_table(
        "leave_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("leave_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_half_day", sa.Boolean(), nullable=False),
        sa.Column("half_day_period", sa.String(length=20), nullable=True),
        sa.Column("days", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_type_id"], ["leave_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leave_requests_employee_id"), "leave_requests", ["employee_id"], unique=False)
    op.create_index(op.f("ix_leave_requests_status"), "leave_requests", ["status"], unique=False)
    op.create_index(op.f("ix_leave_requests_tenant_id"), "leave_requests", ["tenant_id"], unique=False)

    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("check_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "employee_id", "date", name="uq_attendance_employee_date"),
    )
    op.create_index(op.f("ix_attendance_records_date"), "attendance_records", ["date"], unique=False)
    op.create_index(op.f("ix_attendance_records_employee_id"), "attendance_records", ["employee_id"], unique=False)
    op.create_index(op.f("ix_attendance_records_tenant_id"), "attendance_records", ["tenant_id"], unique=False)

    op.create_table(
        "reimbursement_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("max_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_reimbursement_cat_tenant"),
    )
    op.create_index(op.f("ix_reimbursement_categories_tenant_id"), "reimbursement_categories", ["tenant_id"], unique=False)

    op.create_table(
        "payslips",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("gross_pay", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("net_pay", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("earnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deductions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payslips_employee_id"), "payslips", ["employee_id"], unique=False)
    op.create_index(op.f("ix_payslips_tenant_id"), "payslips", ["tenant_id"], unique=False)

    op.create_table(
        "reimbursement_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("receipt_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["reimbursement_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reimbursement_claims_employee_id"), "reimbursement_claims", ["employee_id"], unique=False)
    op.create_index(op.f("ix_reimbursement_claims_status"), "reimbursement_claims", ["status"], unique=False)
    op.create_index(op.f("ix_reimbursement_claims_tenant_id"), "reimbursement_claims", ["tenant_id"], unique=False)

    op.create_table(
        "holidays",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_optional", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_holidays_date"), "holidays", ["date"], unique=False)
    op.create_index(op.f("ix_holidays_tenant_id"), "holidays", ["tenant_id"], unique=False)

    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_announcements_tenant_id"), "announcements", ["tenant_id"], unique=False)

    op.create_table(
        "onboarding_checklists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_onboarding_checklists_tenant_id"), "onboarding_checklists", ["tenant_id"], unique=False)

    op.create_table(
        "onboarding_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["checklist_id"], ["onboarding_checklists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_onboarding_tasks_employee_id"), "onboarding_tasks", ["employee_id"], unique=False)
    op.create_index(op.f("ix_onboarding_tasks_tenant_id"), "onboarding_tasks", ["tenant_id"], unique=False)

    op.create_table(
        "exit_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exit_type", sa.String(length=30), nullable=False),
        sa.Column("resignation_date", sa.Date(), nullable=False),
        sa.Column("last_working_date", sa.Date(), nullable=False),
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
    )
    op.create_index(op.f("ix_exit_requests_employee_id"), "exit_requests", ["employee_id"], unique=False)
    op.create_index(op.f("ix_exit_requests_status"), "exit_requests", ["status"], unique=False)
    op.create_index(op.f("ix_exit_requests_tenant_id"), "exit_requests", ["tenant_id"], unique=False)

    op.create_table(
        "offer_letter_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_offer_letter_templates_tenant_id"), "offer_letter_templates", ["tenant_id"], unique=False)

    op.create_table(
        "offer_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("candidate_name", sa.String(length=255), nullable=False),
        sa.Column("candidate_email", sa.String(length=255), nullable=False),
        sa.Column("designation", sa.String(length=255), nullable=True),
        sa.Column("ctc", sa.String(length=100), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["offer_letter_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_offer_letters_status"), "offer_letters", ["status"], unique=False)
    op.create_index(op.f("ix_offer_letters_tenant_id"), "offer_letters", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_table("offer_letters")
    op.drop_table("offer_letter_templates")
    op.drop_table("exit_requests")
    op.drop_table("onboarding_tasks")
    op.drop_table("onboarding_checklists")
    op.drop_table("announcements")
    op.drop_table("holidays")
    op.drop_table("reimbursement_claims")
    op.drop_table("payslips")
    op.drop_table("reimbursement_categories")
    op.drop_table("attendance_records")
    op.drop_table("leave_requests")
    op.drop_table("leave_balances")
    op.drop_table("leave_types")
    op.drop_table("approval_request_steps")
    op.drop_table("approval_requests")
    op.drop_table("approval_workflow_steps")
    op.drop_table("approval_workflows")

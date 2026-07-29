"""Employee personal, academic, and work history details

Revision ID: 008
Revises: 007
Create Date: 2026-07-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("gender", sa.String(length=30), nullable=True))
    op.add_column("employees", sa.Column("marital_status", sa.String(length=30), nullable=True))
    op.add_column("employees", sa.Column("blood_group", sa.String(length=10), nullable=True))
    op.add_column("employees", sa.Column("nationality", sa.String(length=100), nullable=True))
    op.add_column("employees", sa.Column("personal_email", sa.String(length=255), nullable=True))
    op.add_column("employees", sa.Column("father_name", sa.String(length=200), nullable=True))
    op.add_column("employees", sa.Column("emergency_contact_name", sa.String(length=200), nullable=True))
    op.add_column("employees", sa.Column("emergency_contact_phone", sa.String(length=50), nullable=True))
    op.add_column("employees", sa.Column("emergency_contact_relation", sa.String(length=100), nullable=True))
    op.add_column("employees", sa.Column("current_address", sa.Text(), nullable=True))
    op.add_column("employees", sa.Column("permanent_address", sa.Text(), nullable=True))
    op.add_column("employees", sa.Column("pan_number", sa.String(length=20), nullable=True))
    op.add_column("employees", sa.Column("aadhaar_number", sa.String(length=20), nullable=True))
    op.add_column("employees", sa.Column("passport_number", sa.String(length=50), nullable=True))
    op.add_column(
        "employees",
        sa.Column("background_verification_status", sa.String(length=30), nullable=True),
    )
    op.add_column("employees", sa.Column("background_verification_notes", sa.Text(), nullable=True))

    op.create_table(
        "employee_educations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("degree", sa.String(length=200), nullable=False),
        sa.Column("institution", sa.String(length=255), nullable=False),
        sa.Column("field_of_study", sa.String(length=200), nullable=True),
        sa.Column("year_of_passing", sa.Integer(), nullable=True),
        sa.Column("grade_or_percentage", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employee_educations_employee_id"), "employee_educations", ["employee_id"])
    op.create_index(op.f("ix_employee_educations_tenant_id"), "employee_educations", ["tenant_id"])

    op.create_table(
        "employee_work_experiences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("designation", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("last_drawn_salary", sa.String(length=50), nullable=True),
        sa.Column("reason_for_leaving", sa.String(length=255), nullable=True),
        sa.Column("responsibilities", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_employee_work_experiences_employee_id"), "employee_work_experiences", ["employee_id"]
    )
    op.create_index(
        op.f("ix_employee_work_experiences_tenant_id"), "employee_work_experiences", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_table("employee_work_experiences")
    op.drop_table("employee_educations")
    for col in (
        "background_verification_notes",
        "background_verification_status",
        "passport_number",
        "aadhaar_number",
        "pan_number",
        "permanent_address",
        "current_address",
        "emergency_contact_relation",
        "emergency_contact_phone",
        "emergency_contact_name",
        "father_name",
        "personal_email",
        "nationality",
        "blood_group",
        "marital_status",
        "gender",
    ):
        op.drop_column("employees", col)

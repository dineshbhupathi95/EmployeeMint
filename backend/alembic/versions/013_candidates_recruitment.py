"""Candidates and recruitment offer links

Revision ID: 013
Revises: 012
Create Date: 2026-08-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="new"),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("applied_for_designation", sa.String(length=255), nullable=True),
        sa.Column("expected_ctc", sa.String(length=100), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        sa.Column("current_company", sa.String(length=255), nullable=True),
        sa.Column("current_designation", sa.String(length=255), nullable=True),
        sa.Column("total_experience_years", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("resume_file_path", sa.String(length=500), nullable=True),
        sa.Column("resume_file_name", sa.String(length=255), nullable=True),
        sa.Column("resume_content_type", sa.String(length=100), nullable=True),
        sa.Column("resume_text", sa.Text(), nullable=True),
        sa.Column("resume_parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parsed_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_candidates_tenant_email"),
    )
    op.create_index("ix_candidates_email", "candidates", ["email"])
    op.create_index("ix_candidates_status", "candidates", ["status"])
    op.create_index("ix_candidates_tenant_id", "candidates", ["tenant_id"])

    op.add_column("offer_letters", sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("offer_letters", sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("offer_letters", sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_offer_letters_candidate_id", "offer_letters", "candidates", ["candidate_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_offer_letters_employee_id", "offer_letters", "employees", ["employee_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_offer_letters_candidate_id", "offer_letters", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_offer_letters_candidate_id", table_name="offer_letters")
    op.drop_constraint("fk_offer_letters_employee_id", "offer_letters", type_="foreignkey")
    op.drop_constraint("fk_offer_letters_candidate_id", "offer_letters", type_="foreignkey")
    op.drop_column("offer_letters", "accepted_at")
    op.drop_column("offer_letters", "employee_id")
    op.drop_column("offer_letters", "candidate_id")
    op.drop_table("candidates")

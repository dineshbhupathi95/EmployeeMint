import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.platform import TenantScopedMixin


class Payslip(Base, TenantScopedMixin):
    __tablename__ = "payslips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    earnings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    deductions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ReimbursementCategory(Base, TenantScopedMixin):
    __tablename__ = "reimbursement_categories"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_reimbursement_cat_tenant"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ReimbursementClaim(Base, TenantScopedMixin):
    __tablename__ = "reimbursement_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reimbursement_categories.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)


class EmployeeBankAccount(Base, TenantScopedMixin):
    __tablename__ = "employee_bank_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "employee_id", name="uq_bank_account_tenant_employee"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


class PayrollRun(Base, TenantScopedMixin):
    __tablename__ = "payroll_runs"
    __table_args__ = (UniqueConstraint("tenant_id", "month", "year", name="uq_payroll_run_period"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    finance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_gross: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total_net: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PayrollRunLine(Base, TenantScopedMixin):
    __tablename__ = "payroll_run_lines"
    __table_args__ = (UniqueConstraint("payroll_run_id", "employee_id", name="uq_payroll_line_run_employee"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payroll_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False)
    employee_name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_gross: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    base_deductions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    lop_days: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=0, nullable=False)
    lop_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    other_earnings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    other_deductions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    leave_summary: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    bank_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    payment_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmployeeCompensation(Base, TenantScopedMixin):
    __tablename__ = "employee_compensation"
    __table_args__ = (UniqueConstraint("tenant_id", "employee_id", name="uq_comp_tenant_employee"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ctc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ctc_annual: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gross_monthly: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    net_monthly: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    earnings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    deductions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="admin", nullable=False)
    offer_letter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offer_letters.id", ondelete="SET NULL"), nullable=True
    )

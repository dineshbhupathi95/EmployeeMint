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

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.platform import TenantScopedMixin


class LeaveType(Base, TenantScopedMixin):
    __tablename__ = "leave_types"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_leave_types_tenant_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    annual_quota: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=0, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LeaveBalance(Base, TenantScopedMixin):
    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "leave_type_id", "year", name="uq_leave_balance"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=0, nullable=False)
    used: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=0, nullable=False)
    pending: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=0, nullable=False)


class LeaveRequest(Base, TenantScopedMixin):
    __tablename__ = "leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_half_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    half_day_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    days: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)

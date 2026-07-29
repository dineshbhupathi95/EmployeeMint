import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.platform import TenantScopedMixin


class AttendanceRecord(Base, TenantScopedMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "date", name="uq_attendance_employee_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), default="in_office", nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="web", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="present", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

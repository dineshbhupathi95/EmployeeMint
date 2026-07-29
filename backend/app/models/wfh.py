import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.platform import TenantScopedMixin


class WfhRequest(Base, TenantScopedMixin):
    __tablename__ = "wfh_requests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "request_date", name="uq_wfh_employee_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)

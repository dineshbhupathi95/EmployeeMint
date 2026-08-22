import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.platform import TenantScopedMixin


class Candidate(Base, TenantScopedMixin):
    __tablename__ = "candidates"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_candidates_tenant_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="new", nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    applied_for_designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_ctc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_designation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_experience_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)

    resume_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resume_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parsed_profile: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    hired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

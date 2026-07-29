import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.platform import TenantScopedMixin


class ApprovalWorkflow(Base, TenantScopedMixin):
    __tablename__ = "approval_workflows"
    __table_args__ = (UniqueConstraint("tenant_id", "request_type", name="uq_workflows_tenant_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    steps: Mapped[list["ApprovalWorkflowStep"]] = relationship(
        back_populates="workflow", order_by="ApprovalWorkflowStep.step_order"
    )


class ApprovalWorkflowStep(Base):
    __tablename__ = "approval_workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_workflows.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_rule: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    condition_field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    condition_operator: Mapped[str | None] = mapped_column(String(20), nullable=True)
    condition_value: Mapped[str | None] = mapped_column(String(255), nullable=True)

    workflow: Mapped["ApprovalWorkflow"] = relationship(back_populates="steps")


class ApprovalRequest(Base, TenantScopedMixin):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    requester_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    requester_employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    current_step_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    steps: Mapped[list["ApprovalRequestStep"]] = relationship(
        back_populates="request", order_by="ApprovalRequestStep.step_order"
    )


class ApprovalRequestStep(Base):
    __tablename__ = "approval_request_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    request: Mapped["ApprovalRequest"] = relationship(back_populates="steps")

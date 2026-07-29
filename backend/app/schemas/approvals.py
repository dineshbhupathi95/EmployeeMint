import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ApprovalStepResponse(BaseModel):
    id: uuid.UUID
    step_order: int
    approver_user_id: uuid.UUID | None
    status: str
    comments: str | None
    acted_at: datetime | None


class ApprovalRequestResponse(BaseModel):
    id: uuid.UUID
    request_type: str
    requester_user_id: uuid.UUID
    requester_employee_id: uuid.UUID | None
    requester_name: str | None = None
    status: str
    payload: dict[str, Any]
    reference_id: uuid.UUID | None
    current_step_order: int
    created_at: datetime
    steps: list[ApprovalStepResponse] = []


class ApprovalActionRequest(BaseModel):
    comments: str | None = None

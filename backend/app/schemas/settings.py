import uuid
from datetime import date as Date, datetime

from pydantic import BaseModel, Field


class HolidayCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date: Date
    is_optional: bool = False


class HolidayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    date: Date | None = None
    is_optional: bool | None = None


class HolidayResponse(BaseModel):
    id: uuid.UUID
    name: str
    date: Date
    is_optional: bool
    model_config = {"from_attributes": True}


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    is_pinned: bool = False
    show_on_dashboard: bool = True


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    is_pinned: bool | None = None
    show_on_dashboard: bool | None = None


class AnnouncementResponse(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    is_pinned: bool
    show_on_dashboard: bool = True
    created_at: datetime
    model_config = {"from_attributes": True}


class LeaveTypeCreate(BaseModel):
    name: str
    code: str
    annual_quota: float = 0
    is_paid: bool = True
    requires_document: bool = False


class LeaveTypeUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    annual_quota: float | None = None
    is_paid: bool | None = None
    requires_document: bool | None = None
    is_active: bool | None = None


class WorkflowStepSchema(BaseModel):
    step_order: int
    approver_rule: str
    approver_value: str | None = None


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    name: str
    request_type: str
    is_active: bool
    steps: list[WorkflowStepSchema] = []

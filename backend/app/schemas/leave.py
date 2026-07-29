import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LeaveTypeResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    annual_quota: Decimal
    is_paid: bool
    requires_document: bool
    model_config = {"from_attributes": True}


class LeaveBalanceResponse(BaseModel):
    leave_type_id: uuid.UUID
    leave_type_name: str | None = None
    leave_type_code: str | None = None
    allocated: Decimal
    used: Decimal
    pending: Decimal
    available: Decimal


class LeaveApplyRequest(BaseModel):
    leave_type_id: uuid.UUID
    start_date: date
    end_date: date
    is_half_day: bool = False
    half_day_period: str | None = None
    reason: str | None = None


class LeaveUpdateRequest(BaseModel):
    leave_type_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_half_day: bool | None = None
    half_day_period: str | None = None
    reason: str | None = None


class LeaveRequestResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    leave_type_id: uuid.UUID
    start_date: date
    end_date: date
    is_half_day: bool
    days: Decimal
    reason: str | None
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}

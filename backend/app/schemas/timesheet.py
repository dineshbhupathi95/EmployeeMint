import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TimesheetEntryCreate(BaseModel):
    work_date: date
    hours: Decimal = Field(gt=0, le=24)
    description: str = Field(min_length=1, max_length=500)


class TimesheetEntryUpdate(BaseModel):
    work_date: date | None = None
    hours: Decimal | None = Field(default=None, gt=0, le=24)
    description: str | None = Field(default=None, min_length=1, max_length=500)


class TimesheetEntryResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    work_date: date
    hours: Decimal
    description: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}

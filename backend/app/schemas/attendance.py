import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    mode: str = Field(default="in_office", pattern=r"^(in_office|remote|wfh)$")


class AttendanceResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    date: date
    check_in: datetime | None
    check_out: datetime | None
    mode: str
    status: str
    model_config = {"from_attributes": True}


class RegularizeRequest(BaseModel):
    date: date
    mode: str = Field(default="in_office", pattern=r"^(in_office|remote|wfh)$")
    check_in_time: time | None = None
    check_out_time: time | None = None
    reason: str = Field(min_length=3, max_length=500)


class WfhRequestCreate(BaseModel):
    request_date: date
    reason: str | None = Field(default=None, max_length=500)


class WfhRequestResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    request_date: date
    reason: str | None
    status: str
    model_config = {"from_attributes": True}


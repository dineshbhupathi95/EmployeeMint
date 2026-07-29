import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.validators import AuthEmail


class EmployeeCodePreview(BaseModel):
    employee_code: str


class EmployeeCreate(BaseModel):
    employee_code: str | None = Field(default=None, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: AuthEmail
    password: str = Field(min_length=8)
    work_email: AuthEmail | None = None
    phone: str | None = None
    date_of_joining: date | None = None
    department_id: uuid.UUID | None = None
    designation_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    reports_to_employee_id: uuid.UUID | None = None
    role_ids: list[uuid.UUID] = []
    leave_type_ids: list[uuid.UUID] = []


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    work_email: AuthEmail | None = None
    phone: str | None = None
    date_of_joining: date | None = None
    department_id: uuid.UUID | None = None
    designation_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    reports_to_employee_id: uuid.UUID | None = None
    employment_status: str | None = None
    role_ids: list[uuid.UUID] | None = None
    leave_type_ids: list[uuid.UUID] | None = None


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    work_email: str | None
    phone: str | None
    date_of_joining: date | None
    department_id: uuid.UUID | None
    designation_id: uuid.UUID | None
    location_id: uuid.UUID | None
    reports_to_employee_id: uuid.UUID | None
    employment_status: str
    user_id: uuid.UUID | None
    role_ids: list[uuid.UUID] = []
    leave_type_ids: list[uuid.UUID] = []

    model_config = {"from_attributes": True}

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class TeamMemberResponse(EmployeeResponse):
    checked_in_today: bool = False
    checked_out_today: bool = False
    check_in_time: datetime | None = None
    attendance_mode: str | None = None
    relation: str = "reportee"  # reportee | peer
    manager_name: str | None = None

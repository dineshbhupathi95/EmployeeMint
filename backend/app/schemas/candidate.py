import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.validators import AuthEmail


class CandidateCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: AuthEmail
    phone: str | None = Field(default=None, max_length=50)
    status: str = Field(default="new", max_length=30)
    source: str | None = Field(default=None, max_length=50)
    applied_for_designation: str | None = Field(default=None, max_length=255)
    expected_ctc: str | None = Field(default=None, max_length=100)
    notice_period_days: int | None = None
    current_company: str | None = Field(default=None, max_length=255)
    current_designation: str | None = Field(default=None, max_length=255)
    total_experience_years: Decimal | None = None
    applied_at: date | None = None
    notes: str | None = None
    parsed_profile: dict | None = None


class CandidateUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: AuthEmail | None = None
    phone: str | None = None
    status: str | None = Field(default=None, max_length=30)
    source: str | None = None
    applied_for_designation: str | None = None
    expected_ctc: str | None = None
    notice_period_days: int | None = None
    current_company: str | None = None
    current_designation: str | None = None
    total_experience_years: Decimal | None = None
    notes: str | None = None
    rejection_reason: str | None = None


class CandidateResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    status: str
    source: str | None
    applied_for_designation: str | None
    expected_ctc: str | None
    notice_period_days: int | None
    current_company: str | None
    current_designation: str | None
    total_experience_years: Decimal | None
    resume_file_name: str | None
    has_resume: bool = False
    parsed_profile: dict
    employee_id: uuid.UUID | None
    hired_at: datetime | None
    applied_at: date | None
    notes: str | None
    rejection_reason: str | None
    created_at: datetime
    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, c) -> "CandidateResponse":
        base = cls.model_validate(c)
        return base.model_copy(update={"has_resume": bool(c.resume_file_path)})


class CandidateOfferResponse(BaseModel):
    id: uuid.UUID
    status: str
    designation: str | None
    ctc: str | None
    joining_date: date | None
    has_pdf: bool
    employee_id: uuid.UUID | None
    accepted_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class CreateOfferForCandidate(BaseModel):
    template_id: uuid.UUID
    designation: str | None = None
    ctc: str | None = None
    joining_date: date | None = None


class AcceptOfferRequest(BaseModel):
    password: str = Field(min_length=8)
    department_id: uuid.UUID | None = None
    designation_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    reports_to_employee_id: uuid.UUID | None = None
    date_of_joining: date | None = None
    role_ids: list[uuid.UUID] = Field(default_factory=list)
    leave_type_ids: list[uuid.UUID] = Field(default_factory=list)
    start_onboarding: bool = True


class ResumeParseResponse(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    current_company: str | None = None
    current_designation: str | None = None
    total_experience_years: float | None = None
    parsed_profile: dict = Field(default_factory=dict)
    resume_text_length: int = 0
    parse_warning: str | None = None

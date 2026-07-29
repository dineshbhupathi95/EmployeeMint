import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PayslipResponse(BaseModel):
    id: uuid.UUID
    month: int
    year: int
    gross_pay: Decimal
    net_pay: Decimal
    earnings: dict
    deductions: dict
    model_config = {"from_attributes": True}


class ReimbursementCategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    model_config = {"from_attributes": True}


class ReimbursementSubmitRequest(BaseModel):
    category_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    expense_date: date
    description: str | None = None


class ReimbursementClaimResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    amount: Decimal
    expense_date: date
    description: str | None
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class CompensationResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    ctc: str | None
    ctc_annual: Decimal | None
    designation: str | None
    joining_date: date | None
    gross_monthly: Decimal | None
    net_monthly: Decimal | None
    earnings: dict
    deductions: dict
    source: str
    offer_letter_id: uuid.UUID | None
    model_config = {"from_attributes": True}


class CompensationUpsertRequest(BaseModel):
    ctc: str = Field(min_length=1, max_length=100)
    designation: str | None = Field(default=None, max_length=255)
    joining_date: date | None = None
    gross_monthly: Decimal | None = Field(default=None, gt=0)
    net_monthly: Decimal | None = Field(default=None, gt=0)
    earnings: dict | None = None
    deductions: dict | None = None


class MyPayResponse(BaseModel):
    configured: bool
    compensation: CompensationResponse | None = None
    payslip_count: int = 0
    message: str | None = None

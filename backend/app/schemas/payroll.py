import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PayrollSettingsResponse(BaseModel):
    working_days_per_month: int = 30
    hr_roles: list[str] = Field(default_factory=lambda: ["HR Admin", "HR Executive"])
    finance_roles: list[str] = Field(default_factory=lambda: ["Finance Admin"])
    admin_roles: list[str] = Field(default_factory=lambda: ["Org Admin"])


class PayrollSettingsUpdate(BaseModel):
    working_days_per_month: int | None = Field(default=None, ge=20, le=31)
    hr_roles: list[str] | None = None
    finance_roles: list[str] | None = None
    admin_roles: list[str] | None = None


class PayrollRunCreate(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2020, le=2100)
    notes: str | None = None


class PayrollRunLineUpdate(BaseModel):
    lop_days: Decimal | None = Field(default=None, ge=0)
    bonus: Decimal | None = Field(default=None, ge=0)
    other_earnings: dict | None = None
    other_deductions: dict | None = None
    notes: str | None = None


class PayrollRunLineResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_code: str
    employee_name: str
    base_gross: Decimal
    base_deductions: dict
    lop_days: Decimal
    lop_amount: Decimal
    bonus: Decimal
    other_earnings: dict
    other_deductions: dict
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    leave_summary: dict
    bank_snapshot: dict
    payment_status: str | None
    payment_reference: str | None
    notes: str | None
    model_config = {"from_attributes": True}


class PayrollRunResponse(BaseModel):
    id: uuid.UUID
    month: int
    year: int
    status: str
    notes: str | None
    finance_notes: str | None
    submitted_at: date | None
    approved_at: date | None
    total_gross: Decimal
    total_net: Decimal
    employee_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


class PayrollRunDetailResponse(PayrollRunResponse):
    lines: list[PayrollRunLineResponse] = Field(default_factory=list)


class PayrollRejectRequest(BaseModel):
    finance_notes: str = Field(min_length=1, max_length=2000)


class BankAccountResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    account_holder_name: str
    account_number: str
    ifsc_code: str
    bank_name: str
    branch_name: str | None
    model_config = {"from_attributes": True}


class BankAccountUpsert(BaseModel):
    account_holder_name: str = Field(min_length=1, max_length=200)
    account_number: str = Field(min_length=1, max_length=50)
    ifsc_code: str = Field(min_length=1, max_length=20)
    bank_name: str = Field(min_length=1, max_length=200)
    branch_name: str | None = Field(default=None, max_length=200)


class PayslipResponse(BaseModel):
    id: uuid.UUID
    month: int
    year: int
    gross_pay: Decimal
    net_pay: Decimal
    earnings: dict
    deductions: dict
    file_url: str | None = None
    has_pdf: bool = False
    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_payslip(cls, slip) -> "PayslipResponse":
        return cls(
            id=slip.id,
            month=slip.month,
            year=slip.year,
            gross_pay=slip.gross_pay,
            net_pay=slip.net_pay,
            earnings=slip.earnings,
            deductions=slip.deductions,
            file_url=slip.file_url,
            has_pdf=bool(slip.file_url),
        )

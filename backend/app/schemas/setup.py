from pydantic import BaseModel, Field


class CompanyProfileSetup(BaseModel):
    timezone: str = Field(min_length=1, max_length=50)
    currency: str = Field(min_length=3, max_length=3)
    country: str = Field(min_length=2, max_length=100)
    fiscal_year_start_month: int = Field(ge=1, le=12, default=4)


class WorkingDaysSetup(BaseModel):
    monday: bool = True
    tuesday: bool = True
    wednesday: bool = True
    thursday: bool = True
    friday: bool = True
    saturday: bool = False
    sunday: bool = False


class SetupProgressResponse(BaseModel):
    is_setup_complete: bool
    steps: dict[str, bool]
    company_profile: CompanyProfileSetup | None = None
    working_days: WorkingDaysSetup | None = None


class SetupCompleteResponse(BaseModel):
    is_setup_complete: bool
    message: str

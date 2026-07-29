import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.validators import AuthEmail


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: str = "starter"
    max_employees: int = Field(default=100, ge=1)
    admin_email: AuthEmail
    admin_password: str = Field(min_length=8)
    admin_first_name: str = Field(min_length=1, max_length=100)
    admin_last_name: str = Field(min_length=1, max_length=100)


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    plan: str | None = None
    max_employees: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    is_setup_complete: bool | None = None
    enabled_modules: dict | None = None


class TenantAdminResponse(BaseModel):
    user_id: uuid.UUID
    employee_id: uuid.UUID | None
    email: str
    first_name: str | None
    last_name: str | None
    is_active: bool
    last_login_at: datetime | None
    role_name: str = "Org Admin"

    model_config = {"from_attributes": True}


class TenantAdminUpdate(BaseModel):
    email: AuthEmail | None = None
    password: str | None = Field(default=None, min_length=8)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    custom_domain: str | None
    plan: str
    max_employees: int
    is_active: bool
    is_setup_complete: bool
    enabled_modules: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantDetailResponse(TenantResponse):
    updated_at: datetime
    employee_count: int = 0
    admins: list[TenantAdminResponse] = []

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.validators import AuthEmail


class LoginRequest(BaseModel):
    email: AuthEmail
    password: str = Field(min_length=8)
    tenant_slug: str | None = None


class PlatformLoginRequest(BaseModel):
    email: AuthEmail
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    id: uuid.UUID
    email: str
    tenant_id: uuid.UUID | None = None
    tenant_slug: str | None = None
    employee_id: uuid.UUID | None = None
    employee_code: str | None = None
    full_name: str | None = None
    phone: str | None = None
    work_email: str | None = None
    has_avatar: bool = False
    permissions: list[str] = []
    is_platform_admin: bool = False
    is_setup_complete: bool = True
    is_impersonation: bool = False

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    work_email: AuthEmail | None = None


class AuthResponse(BaseModel):
    tokens: TokenResponse
    user: UserInfo

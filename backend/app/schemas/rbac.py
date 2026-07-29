import uuid

from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    module: str
    description: str | None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    permission_codes: list[str] = []


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    permission_codes: list[str] | None = None


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionResponse] = []

    model_config = {"from_attributes": True}


class RolePermissionMatrix(BaseModel):
    permissions: list[PermissionResponse]
    roles: list[RoleResponse]

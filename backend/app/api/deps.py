import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import tenant_id_var, user_id_var
from app.core.security import verify_token
from app.middleware.tenant import set_rls_tenant
from app.models import PlatformAdmin, Tenant, User

security_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: uuid.UUID
    email: str
    tenant_id: uuid.UUID | None
    tenant_slug: str | None
    employee_id: uuid.UUID | None
    permissions: list[str]
    is_platform_admin: bool = False
    is_impersonation: bool = False


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser | None:
    if not credentials:
        return None

    payload = verify_token(credentials.credentials, "access")
    if not payload:
        return None

    subject = payload.get("sub")
    if not subject:
        return None

    if payload.get("is_platform_admin"):
        result = await db.execute(select(PlatformAdmin).where(PlatformAdmin.id == uuid.UUID(subject)))
        admin = result.scalar_one_or_none()
        if not admin or not admin.is_active:
            return None
        user_id_var.set(str(admin.id))
        return CurrentUser(
            id=admin.id,
            email=admin.email,
            tenant_id=None,
            tenant_slug=None,
            employee_id=None,
            permissions=["platform.*"],
            is_platform_admin=True,
        )

    tenant_id = payload.get("tenant_id")
    if tenant_id:
        await set_rls_tenant(db, uuid.UUID(tenant_id))
        tenant_id_var.set(tenant_id)

    result = await db.execute(
        select(User)
        .options(selectinload(User.employee), selectinload(User.user_roles))
        .where(User.id == uuid.UUID(subject))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    user_id_var.set(str(user.id))

    tenant_slug = None
    is_setup_complete = True
    if user.tenant_id:
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        if tenant:
            tenant_slug = tenant.slug
            is_setup_complete = tenant.is_setup_complete

    permissions = payload.get("permissions", [])

    return CurrentUser(
        id=user.id,
        email=user.email,
        tenant_id=user.tenant_id,
        tenant_slug=tenant_slug,
        employee_id=user.employee.id if user.employee else None,
        permissions=permissions,
        is_impersonation=user.is_platform_impersonation,
    )


async def get_current_user(
    current_user: CurrentUser | None = Depends(get_current_user_optional),
) -> CurrentUser:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Not authenticated"}},
        )
    return current_user


def _has_permission(current_user: CurrentUser, permission: str) -> bool:
    if current_user.is_platform_admin and permission.startswith("platform."):
        return True
    if permission in current_user.permissions or "*" in current_user.permissions:
        return True
    module = permission.rsplit(".", 1)[0]
    return f"{module}.*" in current_user.permissions


def require_permission(permission: str):
    async def checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if _has_permission(current_user, permission):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": f"Missing permission: {permission}"}},
        )

    return checker


def require_any_permission(*permissions: str):
    async def checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if any(_has_permission(current_user, p) for p in permissions):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Missing required permission"}},
        )

    return checker


async def get_platform_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Platform admin access required"}},
        )
    return current_user

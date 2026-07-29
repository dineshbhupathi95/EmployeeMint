from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, get_current_user
from app.core.database import get_db
from app.core.security import verify_token
from app.models import Tenant, User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    PlatformLoginRequest,
    ProfileUpdateRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserInfo,
)
from app.services.auth_service import AuthService
from app.services.avatar_service import AvatarService

router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()
avatar_service = AvatarService()


@router.post("/platform/login", response_model=AuthResponse)
async def platform_login(data: PlatformLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.login_platform(db, data.email, data.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}},
        )
    return result


@router.post("/login", response_model=AuthResponse)
async def tenant_login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.login_tenant(db, data.email, data.password, data.tenant_slug)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email, password, or tenant"}},
        )
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_token(data.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid refresh token"}},
        )

    from uuid import UUID

    user_id = UUID(payload["sub"])
    is_platform = payload.get("is_platform_admin", False)
    tokens = await auth_service.refresh_tokens(db, user_id, is_platform)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "User not found or inactive"}},
        )
    return tokens


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_platform_admin:
        return UserInfo(
            id=current_user.id,
            email=current_user.email,
            permissions=current_user.permissions,
            is_platform_admin=True,
        )

    result = await db.execute(
        select(User).options(selectinload(User.employee)).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found"}})

    tenant = None
    if user.tenant_id:
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = tenant_result.scalar_one_or_none()

    return await auth_service.get_me(db, user, tenant)


@router.patch("/me", response_model=UserInfo)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_platform_admin:
        raise HTTPException(status_code=400, detail={"error": {"code": "NOT_ALLOWED", "message": "Platform admins cannot update profile here"}})
    result = await db.execute(
        select(User).options(selectinload(User.employee)).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found"}})
    try:
        return await auth_service.update_profile(db, user, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


async def _load_user_with_employee(db: AsyncSession, user_id) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.employee)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "User not found"}})
    return user


@router.post("/me/avatar", response_model=UserInfo)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_platform_admin:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NOT_ALLOWED", "message": "Platform admins cannot upload avatar here"}},
        )
    user = await _load_user_with_employee(db, current_user.id)
    if not user.employee:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}},
        )
    content = await file.read()
    try:
        await avatar_service.save(
            db,
            employee=user.employee,
            file_name=file.filename or "avatar.jpg",
            content_type=file.content_type,
            content=content,
        )
        await db.flush()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    except OSError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION", "message": f"Could not save avatar: {e}"}},
        ) from e

    tenant = None
    if user.tenant_id:
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = tenant_result.scalar_one_or_none()
    return await auth_service.get_me(db, user, tenant)


@router.get("/me/avatar")
async def get_avatar(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_platform_admin:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "No avatar"}})
    user = await _load_user_with_employee(db, current_user.id)
    emp = user.employee
    if not emp or not emp.avatar_path:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "No avatar"}})
    path = avatar_service.absolute_path(emp.avatar_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Avatar file missing"}})
    return FileResponse(
        path,
        media_type=emp.avatar_content_type or "image/jpeg",
        content_disposition_type="inline",
    )


@router.delete("/me/avatar", response_model=UserInfo)
async def delete_avatar(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_platform_admin:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NOT_ALLOWED", "message": "Platform admins cannot update avatar here"}},
        )
    user = await _load_user_with_employee(db, current_user.id)
    if not user.employee:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}},
        )
    await avatar_service.clear(db, user.employee)
    tenant = None
    if user.tenant_id:
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = tenant_result.scalar_one_or_none()
    return await auth_service.get_me(db, user, tenant)

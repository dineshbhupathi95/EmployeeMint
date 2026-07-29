import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions_seed import DEFAULT_ENABLED_MODULES
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.middleware.tenant import set_rls_tenant
from app.models import Employee, PlatformAdmin, Tenant, User
from app.schemas.auth import AuthResponse, TokenResponse, UserInfo
from app.services.rbac_service import RBACService


class AuthService:
    def __init__(self) -> None:
        self.rbac = RBACService()

    async def login_platform(
        self, db: AsyncSession, email: str, password: str
    ) -> AuthResponse | None:
        result = await db.execute(select(PlatformAdmin).where(PlatformAdmin.email == email))
        admin = result.scalar_one_or_none()
        if not admin or not admin.is_active or not verify_password(password, admin.password_hash):
            return None

        tokens = TokenResponse(
            access_token=create_access_token(
                str(admin.id),
                extra_claims={"is_platform_admin": True, "permissions": ["platform.*"]},
            ),
            refresh_token=create_refresh_token(str(admin.id)),
        )
        user_info = UserInfo(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name,
            permissions=["platform.*"],
            is_platform_admin=True,
        )
        return AuthResponse(tokens=tokens, user=user_info)

    async def login_tenant(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        tenant_slug: str | None = None,
    ) -> AuthResponse | None:
        tenant: Tenant | None = None
        if tenant_slug:
            result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active.is_(True)))
            tenant = result.scalar_one_or_none()
            if not tenant:
                return None
            await set_rls_tenant(db, tenant.id)

        query = (
            select(User)
            .options(selectinload(User.employee))
            .where(User.email == email, User.is_active.is_(True))
        )
        if tenant:
            query = query.where(User.tenant_id == tenant.id)

        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            return None

        if not tenant:
            result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
            tenant = result.scalar_one_or_none()

        await set_rls_tenant(db, user.tenant_id)
        permissions = await self.rbac.get_user_permissions(db, user.id)

        full_name = None
        employee_id = None
        if user.employee:
            full_name = f"{user.employee.first_name} {user.employee.last_name}"
            employee_id = user.employee.id

        tokens = TokenResponse(
            access_token=create_access_token(
                str(user.id),
                extra_claims={
                    "tenant_id": str(user.tenant_id),
                    "permissions": permissions,
                },
            ),
            refresh_token=create_refresh_token(str(user.id)),
        )
        user_info = UserInfo(
            id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
            tenant_slug=tenant.slug if tenant else None,
            tenant_name=tenant.name if tenant else None,
            has_logo=bool(tenant and tenant.logo_path),
            employee_id=employee_id,
            employee_code=user.employee.employee_code if user.employee else None,
            full_name=full_name,
            phone=user.employee.phone if user.employee else None,
            work_email=user.employee.work_email if user.employee else None,
            has_avatar=bool(user.employee and user.employee.avatar_path),
            permissions=permissions,
            is_setup_complete=tenant.is_setup_complete if tenant else True,
            is_impersonation=user.is_platform_impersonation,
        )
        return AuthResponse(tokens=tokens, user=user_info)

    async def refresh_tokens(self, db: AsyncSession, user_id: uuid.UUID, is_platform: bool) -> TokenResponse | None:
        if is_platform:
            result = await db.execute(select(PlatformAdmin).where(PlatformAdmin.id == user_id))
            admin = result.scalar_one_or_none()
            if not admin or not admin.is_active:
                return None
            return TokenResponse(
                access_token=create_access_token(
                    str(admin.id),
                    extra_claims={"is_platform_admin": True, "permissions": ["platform.*"]},
                ),
                refresh_token=create_refresh_token(str(admin.id)),
            )

        result = await db.execute(
            select(User).options(selectinload(User.employee)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None

        await set_rls_tenant(db, user.tenant_id)
        permissions = await self.rbac.get_user_permissions(db, user.id)
        return TokenResponse(
            access_token=create_access_token(
                str(user.id),
                extra_claims={"tenant_id": str(user.tenant_id), "permissions": permissions},
            ),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def get_me(self, db: AsyncSession, user: User, tenant: Tenant | None) -> UserInfo:
        permissions = await self.rbac.get_user_permissions(db, user.id)
        full_name = None
        employee_id = None
        if user.employee:
            full_name = f"{user.employee.first_name} {user.employee.last_name}"
            employee_id = user.employee.id
        return UserInfo(
            id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
            tenant_slug=tenant.slug if tenant else None,
            tenant_name=tenant.name if tenant else None,
            has_logo=bool(tenant and tenant.logo_path),
            employee_id=employee_id,
            employee_code=user.employee.employee_code if user.employee else None,
            full_name=full_name,
            phone=user.employee.phone if user.employee else None,
            work_email=user.employee.work_email if user.employee else None,
            has_avatar=bool(user.employee and user.employee.avatar_path),
            permissions=permissions,
            is_setup_complete=tenant.is_setup_complete if tenant else True,
            is_impersonation=user.is_platform_impersonation,
        )

    async def update_profile(
        self, db: AsyncSession, user: User, data: "ProfileUpdateRequest"
    ) -> UserInfo:
        from app.schemas.auth import ProfileUpdateRequest

        if not user.employee:
            raise ValueError("No employee profile linked to this account")

        update = data.model_dump(exclude_unset=True)
        if "first_name" in update:
            user.employee.first_name = update["first_name"]
        if "last_name" in update:
            user.employee.last_name = update["last_name"]
        if "phone" in update:
            user.employee.phone = update["phone"]
        if "work_email" in update:
            user.employee.work_email = update["work_email"]
        await db.flush()

        tenant = None
        if user.tenant_id:
            result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
            tenant = result.scalar_one_or_none()
        return await self.get_me(db, user, tenant)

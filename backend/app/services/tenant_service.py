import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions_seed import DEFAULT_ENABLED_MODULES
from app.core.tenant_defaults import seed_tenant_defaults
from app.core.security import hash_password
from app.models import Employee, Role, Tenant, User, UserRole
from app.schemas.tenant import TenantAdminResponse, TenantAdminUpdate, TenantCreate, TenantDetailResponse
from app.services.employee_service import EmployeeService
from app.services.rbac_service import RBACService


class TenantService:
    def __init__(self) -> None:
        self.rbac = RBACService()
        self.employees = EmployeeService()

    async def create_tenant(self, db: AsyncSession, data: TenantCreate) -> Tenant:
        existing = await db.execute(select(Tenant).where(Tenant.slug == data.slug))
        if existing.scalar_one_or_none():
            raise ValueError(f"Tenant slug '{data.slug}' already exists")

        tenant = Tenant(
            name=data.name,
            slug=data.slug,
            plan=data.plan,
            max_employees=data.max_employees,
            enabled_modules=DEFAULT_ENABLED_MODULES.copy(),
        )
        db.add(tenant)
        await db.flush()

        roles = await self.rbac.seed_tenant_roles(db, tenant.id)
        org_admin_role = roles["Org Admin"]

        user = User(
            tenant_id=tenant.id,
            email=data.admin_email,
            password_hash=hash_password(data.admin_password),
        )
        db.add(user)
        await db.flush()

        employee_code = await self.employees.generate_employee_code(db, tenant.id, tenant.slug)
        employee = Employee(
            tenant_id=tenant.id,
            user_id=user.id,
            employee_code=employee_code,
            first_name=data.admin_first_name,
            last_name=data.admin_last_name,
            work_email=data.admin_email,
            created_by=user.id,
        )
        db.add(employee)
        await self.rbac.assign_role(db, user.id, org_admin_role.id)
        await seed_tenant_defaults(db, tenant.id, user.id)
        await db.flush()
        return tenant

    async def list_tenants(
        self, db: AsyncSession, page: int = 1, page_size: int = 20
    ) -> tuple[list[Tenant], int]:
        count_result = await db.execute(select(func.count()).select_from(Tenant))
        total = count_result.scalar_one()

        result = await db.execute(
            select(Tenant)
            .order_by(Tenant.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_by_id(self, db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Tenant | None:
        result = await db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def get_org_admins(self, db: AsyncSession, tenant_id: uuid.UUID) -> list[TenantAdminResponse]:
        result = await db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .options(selectinload(User.employee))
            .where(
                User.tenant_id == tenant_id,
                User.is_deleted.is_(False),
                Role.name == "Org Admin",
            )
            .order_by(User.created_at)
        )
        admins: list[TenantAdminResponse] = []
        for user in result.scalars().unique().all():
            employee = user.employee
            admins.append(
                TenantAdminResponse(
                    user_id=user.id,
                    employee_id=employee.id if employee else None,
                    email=user.email,
                    first_name=employee.first_name if employee else None,
                    last_name=employee.last_name if employee else None,
                    is_active=user.is_active,
                    last_login_at=user.last_login_at,
                )
            )
        return admins

    async def get_employee_count(self, db: AsyncSession, tenant_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(Employee)
            .where(Employee.tenant_id == tenant_id, Employee.is_deleted.is_(False))
        )
        return result.scalar_one()

    async def get_tenant_detail(self, db: AsyncSession, tenant_id: uuid.UUID) -> TenantDetailResponse | None:
        tenant = await self.get_by_id(db, tenant_id)
        if not tenant:
            return None
        admins = await self.get_org_admins(db, tenant_id)
        employee_count = await self.get_employee_count(db, tenant_id)
        return TenantDetailResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            custom_domain=tenant.custom_domain,
            plan=tenant.plan,
            max_employees=tenant.max_employees,
            is_active=tenant.is_active,
            is_setup_complete=tenant.is_setup_complete,
            enabled_modules=tenant.enabled_modules,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            employee_count=employee_count,
            admins=admins,
        )

    async def update_tenant(self, db: AsyncSession, tenant: Tenant, update_data: dict) -> Tenant:
        for field, value in update_data.items():
            setattr(tenant, field, value)
        await db.flush()
        return tenant

    async def update_org_admin(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: TenantAdminUpdate,
    ) -> TenantAdminResponse | None:
        result = await db.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .options(selectinload(User.employee))
            .where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.is_deleted.is_(False),
                Role.name == "Org Admin",
            )
        )
        user = result.scalars().unique().first()
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=True)
        password = update_data.pop("password", None)
        first_name = update_data.pop("first_name", None)
        last_name = update_data.pop("last_name", None)

        if "email" in update_data:
            existing = await db.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.email == update_data["email"],
                    User.id != user_id,
                    User.is_deleted.is_(False),
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError("Another user with this email already exists in the tenant")

        for field, value in update_data.items():
            setattr(user, field, value)

        if password:
            user.password_hash = hash_password(password)

        if user.employee and (first_name is not None or last_name is not None):
            if first_name is not None:
                user.employee.first_name = first_name
            if last_name is not None:
                user.employee.last_name = last_name
            if "email" in update_data:
                user.employee.work_email = update_data["email"]

        await db.flush()

        employee = user.employee
        return TenantAdminResponse(
            user_id=user.id,
            employee_id=employee.id if employee else None,
            email=user.email,
            first_name=employee.first_name if employee else None,
            last_name=employee.last_name if employee else None,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
        )

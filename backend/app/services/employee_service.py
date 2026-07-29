import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models import Employee, Tenant, User, UserRole
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services.rbac_service import RBACService


class EmployeeService:
    def __init__(self) -> None:
        self.rbac = RBACService()

    async def generate_employee_code(
        self, db: AsyncSession, tenant_id: uuid.UUID, tenant_slug: str
    ) -> str:
        prefix = f"{tenant_slug.upper()}-"
        result = await db.execute(
            select(Employee.employee_code).where(
                Employee.tenant_id == tenant_id,
                Employee.is_deleted.is_(False),
                Employee.employee_code.like(f"{prefix}%"),
            )
        )
        max_num = 0
        for (code,) in result.all():
            suffix = code[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
        return f"{prefix}{max_num + 1:03d}"

    async def create(
        self, db: AsyncSession, tenant_id: uuid.UUID, data: EmployeeCreate, created_by: uuid.UUID
    ) -> Employee:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")

        employee_code = data.employee_code or await self.generate_employee_code(db, tenant_id, tenant.slug)

        if data.reports_to_employee_id:
            manager = await self.get_by_id(db, tenant_id, data.reports_to_employee_id)
            if not manager:
                raise ValueError("Reporting manager not found")

        user = User(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=hash_password(data.password),
            created_by=created_by,
        )
        db.add(user)
        await db.flush()

        employee = Employee(
            tenant_id=tenant_id,
            user_id=user.id,
            employee_code=employee_code,
            first_name=data.first_name,
            last_name=data.last_name,
            work_email=data.work_email or data.email,
            phone=data.phone,
            date_of_joining=data.date_of_joining,
            department_id=data.department_id,
            designation_id=data.designation_id,
            location_id=data.location_id,
            reports_to_employee_id=data.reports_to_employee_id,
            created_by=created_by,
        )
        db.add(employee)

        for role_id in data.role_ids:
            await self.rbac.assign_role(db, user.id, role_id)

        await db.flush()

        from app.services.finance_service import FinanceService
        from app.services.leave_service import LeaveService

        await FinanceService().try_sync_offer_for_new_employee(db, tenant_id, employee, created_by)
        await LeaveService().sync_employee_leave_types(
            db,
            tenant_id=tenant_id,
            employee_id=employee.id,
            leave_type_ids=data.leave_type_ids,
            created_by=created_by,
        )
        await db.flush()
        return employee

    async def list_employees(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Employee], int]:
        base = select(Employee).where(Employee.tenant_id == tenant_id, Employee.is_deleted.is_(False))
        count_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()

        result = await db.execute(
            base.order_by(Employee.first_name, Employee.last_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_by_id(self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID) -> Employee | None:
        result = await db.execute(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
                Employee.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_reportees(
        self, db: AsyncSession, tenant_id: uuid.UUID, manager_employee_id: uuid.UUID
    ) -> list[Employee]:
        """Return all direct and indirect reportees under a manager."""
        result = await db.execute(
            select(Employee).where(
                Employee.tenant_id == tenant_id,
                Employee.is_deleted.is_(False),
            )
        )
        employees = list(result.scalars().all())
        by_manager: dict[uuid.UUID | None, list[Employee]] = {}
        for emp in employees:
            by_manager.setdefault(emp.reports_to_employee_id, []).append(emp)

        reportees: list[Employee] = []
        stack = list(by_manager.get(manager_employee_id, []))
        while stack:
            emp = stack.pop()
            reportees.append(emp)
            stack.extend(by_manager.get(emp.id, []))
        reportees.sort(key=lambda e: (e.first_name, e.last_name))
        return reportees

    async def get_peers_under_manager(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> list[Employee]:
        """Return coworkers who report to the same manager (excludes self)."""
        me = await self.get_by_id(db, tenant_id, employee_id)
        if not me or not me.reports_to_employee_id:
            return []
        result = await db.execute(
            select(Employee).where(
                Employee.tenant_id == tenant_id,
                Employee.is_deleted.is_(False),
                Employee.reports_to_employee_id == me.reports_to_employee_id,
                Employee.id != employee_id,
            ).order_by(Employee.first_name, Employee.last_name)
        )
        return list(result.scalars().all())

    async def get_my_team(
        self, db: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID
    ) -> tuple[list[Employee], str]:
        """Reportees first; if none, peers under the same manager."""
        reportees = await self.get_all_reportees(db, tenant_id, employee_id)
        if reportees:
            return reportees, "reportees"
        peers = await self.get_peers_under_manager(db, tenant_id, employee_id)
        return peers, "peers"

    async def update(
        self, db: AsyncSession, employee: Employee, data: EmployeeUpdate
    ) -> Employee:
        update_data = data.model_dump(exclude_unset=True)
        role_ids = update_data.pop("role_ids", None)
        leave_type_ids = update_data.pop("leave_type_ids", None)
        reports_to = update_data.get("reports_to_employee_id")
        if reports_to is not None and reports_to == employee.id:
            raise ValueError("Employee cannot report to themselves")
        if reports_to:
            manager = await self.get_by_id(db, employee.tenant_id, reports_to)
            if not manager:
                raise ValueError("Reporting manager not found")
        for field, value in update_data.items():
            setattr(employee, field, value)
        if role_ids is not None and employee.user_id:
            await self.rbac.set_user_roles(db, employee.user_id, role_ids)
        if leave_type_ids is not None:
            from app.services.leave_service import LeaveService

            await LeaveService().sync_employee_leave_types(
                db,
                tenant_id=employee.tenant_id,
                employee_id=employee.id,
                leave_type_ids=leave_type_ids,
            )
        await db.flush()
        return employee

    async def to_response(self, db: AsyncSession, employee: Employee) -> EmployeeResponse:
        role_ids: list[uuid.UUID] = []
        if employee.user_id:
            role_ids = await self.rbac.get_user_role_ids(db, employee.user_id)
        from app.services.leave_service import LeaveService

        leave_type_ids = await LeaveService().get_assigned_leave_type_ids(
            db, employee.tenant_id, employee.id
        )
        return EmployeeResponse.model_validate(employee).model_copy(
            update={"role_ids": role_ids, "leave_type_ids": leave_type_ids}
        )

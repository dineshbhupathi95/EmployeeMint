from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, get_current_user, require_any_permission, require_permission
from app.core.database import get_db
from app.models import Permission, Role, RolePermission, Tenant, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.employee import EmployeeCodePreview, EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.schemas.rbac import RoleCreate, RolePermissionMatrix, RoleResponse, RoleUpdate
from app.services.employee_service import EmployeeService
from app.services.rbac_service import RBACService

router = APIRouter(tags=["organization"])
employee_service = EmployeeService()
rbac_service = RBACService()


@router.get("/employees", response_model=PaginatedResponse[EmployeeResponse])
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.view.all")),
):
    employees, total = await employee_service.list_employees(
        db, current_user.tenant_id, page, page_size
    )
    items = [await employee_service.to_response(db, e) for e in employees]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/employees/next-code", response_model=EmployeeCodePreview)
async def preview_next_employee_code(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.create")),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Tenant not found"}})
    code = await employee_service.generate_employee_code(db, current_user.tenant_id, tenant.slug)
    return EmployeeCodePreview(employee_code=code)


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.create")),
):
    try:
        employee = await employee_service.create(db, current_user.tenant_id, data, current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
        ) from exc
    return await employee_service.to_response(db, employee)


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    employee = await employee_service.get_by_id(db, current_user.tenant_id, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found"}})

    can_view_all = "employee.view.all" in current_user.permissions
    can_view_own = "employee.view.own" in current_user.permissions and current_user.employee_id == employee_id
    can_view_team = "employee.view.team" in current_user.permissions

    if not (can_view_all or can_view_own or can_view_team):
        raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Access denied"}})

    return await employee_service.to_response(db, employee)


@router.patch("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.edit.all")),
):
    employee = await employee_service.get_by_id(db, current_user.tenant_id, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found"}})
    try:
        employee = await employee_service.update(db, employee, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
        ) from exc
    return await employee_service.to_response(db, employee)


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("org.manage_roles", "employee.create")),
):
    return (await rbac_service.get_role_matrix(db, current_user.tenant_id)).roles


@router.get("/roles/matrix", response_model=RolePermissionMatrix)
async def get_role_matrix(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("org.manage_roles")),
):
    return await rbac_service.get_role_matrix(db, current_user.tenant_id)


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("org.manage_roles")),
):
    role = Role(
        tenant_id=current_user.tenant_id,
        name=data.name,
        description=data.description,
        is_system=False,
        created_by=current_user.id,
    )
    db.add(role)
    await db.flush()

    if data.permission_codes:
        result = await db.execute(select(Permission).where(Permission.code.in_(data.permission_codes)))
        for perm in result.scalars().all():
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    await db.flush()

    matrix = await rbac_service.get_role_matrix(db, current_user.tenant_id)
    for r in matrix.roles:
        if r.id == role.id:
            return r
    raise HTTPException(status_code=500, detail={"error": {"code": "INTERNAL", "message": "Role creation failed"}})


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("org.manage_roles")),
):
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.role_permissions))
        .where(Role.id == role_id, Role.tenant_id == current_user.tenant_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Role not found"}})

    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description

    if data.permission_codes is not None:
        for rp in list(role.role_permissions):
            await db.delete(rp)
        result = await db.execute(select(Permission).where(Permission.code.in_(data.permission_codes)))
        for perm in result.scalars().all():
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await db.flush()
    matrix = await rbac_service.get_role_matrix(db, current_user.tenant_id)
    for r in matrix.roles:
        if r.id == role.id:
            return r
    raise HTTPException(status_code=500, detail={"error": {"code": "INTERNAL", "message": "Role update failed"}})

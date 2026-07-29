from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_permission
from app.core.database import get_db
from app.models import AttendanceRecord
from app.schemas.employee import TeamMemberResponse
from app.services.dashboard_service import DashboardService, OrganizationService
from app.services.employee_service import EmployeeService

router = APIRouter(tags=["organization"])
dashboard_service = DashboardService()
org_service = OrganizationService()
employee_service = EmployeeService()


@router.get("/dashboard/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("dashboard.view")),
):
    return await dashboard_service.get_summary(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        employee_id=current_user.employee_id,
        permissions=current_user.permissions,
    )


@router.get("/organization/tree")
async def org_tree(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("org.view")),
):
    return await org_service.get_org_tree(db, current_user.tenant_id)


@router.get("/my-team", response_model=list[TeamMemberResponse])
async def my_team(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("employee.view.team")),
):
    if not current_user.employee_id:
        return []
    reportees = await employee_service.get_all_reportees(
        db, current_user.tenant_id, current_user.employee_id
    )
    if not reportees:
        return []

    today = date.today()
    att_result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.tenant_id == current_user.tenant_id,
            AttendanceRecord.employee_id.in_([e.id for e in reportees]),
            AttendanceRecord.date == today,
        )
    )
    attendance_by_employee = {r.employee_id: r for r in att_result.scalars().all()}

    members: list[TeamMemberResponse] = []
    for employee in reportees:
        base = await employee_service.to_response(db, employee)
        record = attendance_by_employee.get(employee.id)
        members.append(
            TeamMemberResponse(
                **base.model_dump(),
                checked_in_today=record.check_in is not None if record else False,
                checked_out_today=record.check_out is not None if record else False,
                check_in_time=record.check_in if record else None,
                attendance_mode=record.mode if record else None,
            )
        )
    return members

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.database import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.timesheet import TimesheetEntryCreate, TimesheetEntryResponse, TimesheetEntryUpdate
from app.services.timesheet_service import TimesheetService

router = APIRouter(prefix="/timesheets", tags=["timesheets"])
timesheet_service = TimesheetService()


@router.get("", response_model=PaginatedResponse[TimesheetEntryResponse])
async def list_timesheets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("timesheet.submit")),
):
    if not current_user.employee_id:
        return PaginatedResponse.create([], 0, page, page_size)
    items, total = await timesheet_service.list_entries(
        db, current_user.tenant_id, current_user.employee_id, page, page_size
    )
    return PaginatedResponse.create(
        [TimesheetEntryResponse.model_validate(i) for i in items], total, page, page_size
    )


@router.post("", response_model=TimesheetEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet_entry(
    data: TimesheetEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("timesheet.submit")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    entry = await timesheet_service.create_entry(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=current_user.employee_id,
        user_id=current_user.id,
        work_date=data.work_date,
        hours=data.hours,
        description=data.description,
    )
    return TimesheetEntryResponse.model_validate(entry)


@router.patch("/{entry_id}", response_model=TimesheetEntryResponse)
async def update_timesheet_entry(
    entry_id: uuid.UUID,
    data: TimesheetEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("timesheet.submit")),
):
    entry = await timesheet_service.get_by_id(db, current_user.tenant_id, entry_id)
    if not entry or entry.employee_id != current_user.employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Entry not found"}})
    try:
        entry = await timesheet_service.update_entry(db, entry, **data.model_dump(exclude_unset=True))
        return TimesheetEntryResponse.model_validate(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/{entry_id}/submit", response_model=TimesheetEntryResponse)
async def submit_timesheet_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("timesheet.submit")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    try:
        entry = await timesheet_service.submit_entry(
            db,
            tenant_id=current_user.tenant_id,
            employee_id=current_user.employee_id,
            user_id=current_user.id,
            entry_id=entry_id,
        )
        return TimesheetEntryResponse.model_validate(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e

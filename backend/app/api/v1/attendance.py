from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_permission
from app.core.database import get_db
from app.schemas.attendance import (
    AttendanceResponse,
    CheckInRequest,
    RegularizeRequest,
    WfhRequestCreate,
    WfhRequestResponse,
)
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["attendance"])
attendance_service = AttendanceService()


@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    data: CheckInRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("attendance.mark.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    try:
        record = await attendance_service.check_in(
            db,
            tenant_id=current_user.tenant_id,
            employee_id=current_user.employee_id,
            mode=data.mode,
            user_id=current_user.id,
        )
        return AttendanceResponse.model_validate(record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("attendance.mark.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    try:
        record = await attendance_service.check_out(db, current_user.tenant_id, current_user.employee_id)
        return AttendanceResponse.model_validate(record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/my", response_model=list[AttendanceResponse])
async def my_attendance(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("attendance.mark.own")),
):
    if not current_user.employee_id:
        return []
    records = await attendance_service.get_month(
        db, current_user.tenant_id, current_user.employee_id, year, month
    )
    return [AttendanceResponse.model_validate(r) for r in records]


@router.post("/regularize", response_model=AttendanceResponse)
async def regularize_attendance(
    data: RegularizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("attendance.mark.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    try:
        record = await attendance_service.regularize(
            db,
            tenant_id=current_user.tenant_id,
            employee_id=current_user.employee_id,
            user_id=current_user.id,
            target_date=data.date,
            mode=data.mode,
            check_in_time=data.check_in_time,
            check_out_time=data.check_out_time,
            reason=data.reason,
        )
        return AttendanceResponse.model_validate(record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/wfh-requests", response_model=WfhRequestResponse, status_code=201)
async def create_wfh_request(
    data: WfhRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("attendance.mark.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    try:
        wfh = await attendance_service.request_wfh(
            db,
            tenant_id=current_user.tenant_id,
            employee_id=current_user.employee_id,
            user_id=current_user.id,
            request_date=data.request_date,
            reason=data.reason,
        )
        return WfhRequestResponse.model_validate(wfh)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/wfh-requests", response_model=list[WfhRequestResponse])
async def list_wfh_requests(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("attendance.mark.own")),
):
    if not current_user.employee_id:
        return []
    items = await attendance_service.list_wfh_requests(
        db, current_user.tenant_id, current_user.employee_id
    )
    return [WfhRequestResponse.model_validate(i) for i in items]


@router.get("/team/today", response_model=list[AttendanceResponse])
async def team_attendance_today(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("attendance.view.team")),
):
    if not current_user.employee_id:
        return []
    records = await attendance_service.team_today(
        db, current_user.tenant_id, current_user.employee_id
    )
    return [AttendanceResponse.model_validate(r) for r in records]

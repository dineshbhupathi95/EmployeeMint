import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_permission
from app.core.database import get_db
from app.models import ApprovalRequest, ApprovalRequestStep, LeaveType
from app.schemas.approvals import ApprovalActionRequest, ApprovalRequestResponse, ApprovalStepResponse
from app.schemas.common import PaginatedResponse
from app.schemas.leave import (
    LeaveApplyRequest,
    LeaveBalanceResponse,
    LeaveRequestResponse,
    LeaveTypeResponse,
    LeaveUpdateRequest,
)
from app.services.finance_service import FinanceService
from app.services.leave_service import LeaveService
from app.services.workflow_service import WorkflowService

router = APIRouter(tags=["leave"])
leave_service = LeaveService()
workflow_service = WorkflowService()
finance_service = FinanceService()


@router.get("/leave/types", response_model=list[LeaveTypeResponse])
async def list_leave_types(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    types = await leave_service.list_types(db, current_user.tenant_id)
    return [LeaveTypeResponse.model_validate(t) for t in types]


@router.get("/leave/balances", response_model=list[LeaveBalanceResponse])
async def get_my_balances(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("leave.view.own")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    balances = await leave_service.get_balances(db, current_user.tenant_id, current_user.employee_id)
    types = await leave_service.list_types(db, current_user.tenant_id)
    type_map = {t.id: t for t in types}
    return [
        LeaveBalanceResponse(
            leave_type_id=b.leave_type_id,
            leave_type_name=type_map[b.leave_type_id].name if b.leave_type_id in type_map else None,
            leave_type_code=type_map[b.leave_type_id].code if b.leave_type_id in type_map else None,
            allocated=b.allocated,
            used=b.used,
            pending=b.pending,
            available=b.allocated - b.used - b.pending,
        )
        for b in balances
    ]


@router.post("/leave/requests", response_model=LeaveRequestResponse, status_code=201)
async def apply_leave(
    data: LeaveApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("leave.apply")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    try:
        req = await leave_service.apply_leave(
            db,
            tenant_id=current_user.tenant_id,
            employee_id=current_user.employee_id,
            user_id=current_user.id,
            leave_type_id=data.leave_type_id,
            start_date=data.start_date,
            end_date=data.end_date,
            is_half_day=data.is_half_day,
            half_day_period=data.half_day_period,
            reason=data.reason,
        )
        return LeaveRequestResponse.model_validate(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/leave/requests", response_model=PaginatedResponse[LeaveRequestResponse])
async def list_leave_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    employee_id = None
    if "leave.view.all" not in current_user.permissions:
        if "leave.view.own" in current_user.permissions:
            employee_id = current_user.employee_id
        else:
            raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Access denied"}})
    items, total = await leave_service.list_requests(
        db, current_user.tenant_id, employee_id, status, page, page_size
    )
    return PaginatedResponse.create(
        [LeaveRequestResponse.model_validate(i) for i in items], total, page, page_size
    )


@router.patch("/leave/requests/{request_id}", response_model=LeaveRequestResponse)
async def update_leave_request(
    request_id: uuid.UUID,
    data: LeaveUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("leave.apply")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    try:
        req = await leave_service.update_request(
            db,
            tenant_id=current_user.tenant_id,
            employee_id=current_user.employee_id,
            user_id=current_user.id,
            request_id=request_id,
            **data.model_dump(exclude_unset=True),
        )
        return LeaveRequestResponse.model_validate(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e

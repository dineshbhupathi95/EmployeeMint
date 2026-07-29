from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, require_permission
from app.core.database import get_db
from app.models import ApprovalRequest, ApprovalRequestStep, Employee
from app.schemas.approvals import ApprovalActionRequest, ApprovalRequestResponse, ApprovalStepResponse
from app.services.finance_service import FinanceService
from app.services.leave_service import LeaveService
from app.services.timesheet_service import TimesheetService
from app.services.workflow_service import WorkflowService
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/approvals", tags=["approvals"])
workflow_service = WorkflowService()
leave_service = LeaveService()
finance_service = FinanceService()
timesheet_service = TimesheetService()
attendance_service = AttendanceService()


async def _requester_name(db: AsyncSession, employee_id: UUID | None) -> str | None:
    if not employee_id:
        return None
    emp = await db.get(Employee, employee_id)
    if not emp:
        return None
    return f"{emp.first_name} {emp.last_name}"


def _to_response(req: ApprovalRequest, requester_name: str | None = None) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=req.id,
        request_type=req.request_type,
        requester_user_id=req.requester_user_id,
        requester_employee_id=req.requester_employee_id,
        requester_name=requester_name,
        status=req.status,
        payload=req.payload,
        reference_id=req.reference_id,
        current_step_order=req.current_step_order,
        created_at=req.created_at,
        steps=[
            ApprovalStepResponse(
                id=s.id,
                step_order=s.step_order,
                approver_user_id=s.approver_user_id,
                status=s.status,
                comments=s.comments,
                acted_at=s.acted_at,
            )
            for s in req.steps
        ],
    )


@router.get("/inbox", response_model=list[ApprovalRequestResponse])
async def approval_inbox(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("approvals.view")),
):
    pending = await workflow_service.get_pending_for_user(db, current_user.id, current_user.tenant_id)
    responses: list[ApprovalRequestResponse] = []
    for req in pending:
        name = await _requester_name(db, req.requester_employee_id)
        responses.append(_to_response(req, name))
    return responses


@router.get("/history", response_model=list[ApprovalRequestResponse])
async def approval_history(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("approvals.view")),
):
    result = await db.execute(
        select(ApprovalRequest)
        .options(selectinload(ApprovalRequest.steps))
        .where(
            ApprovalRequest.tenant_id == current_user.tenant_id,
            ApprovalRequest.status.in_(["approved", "rejected"]),
        )
        .order_by(ApprovalRequest.updated_at.desc())
        .limit(50)
    )
    requests = list(result.scalars().all())
    responses: list[ApprovalRequestResponse] = []
    for req in requests:
        name = await _requester_name(db, req.requester_employee_id)
        responses.append(_to_response(req, name))
    return responses


async def _sync_reference_status(db: AsyncSession, request: ApprovalRequest) -> None:
    if not request.reference_id:
        return
    approved = request.status == "approved"
    if request.request_type == "leave":
        await leave_service.update_status_on_approval(db, request.reference_id, approved)
    elif request.request_type == "reimbursement":
        await finance_service.update_claim_status(db, request.reference_id, approved)
    elif request.request_type == "wfh":
        await attendance_service.update_wfh_status(db, request.reference_id, approved)
    elif request.request_type == "timesheet":
        await timesheet_service.update_status_on_approval(db, request.reference_id, approved)


@router.post("/steps/{step_id}/approve", response_model=ApprovalRequestResponse)
async def approve_step(
    step_id: UUID,
    data: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("approvals.action")),
):
    try:
        request = await workflow_service.act_on_step(
            db, step_id=step_id, actor_user_id=current_user.id, action="approved", comments=data.comments
        )
        await _sync_reference_status(db, request)
        result = await db.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.steps))
            .where(ApprovalRequest.id == request.id)
        )
        req = result.scalar_one()
        name = await _requester_name(db, req.requester_employee_id)
        return _to_response(req, name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/steps/{step_id}/reject", response_model=ApprovalRequestResponse)
async def reject_step(
    step_id: UUID,
    data: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("approvals.action")),
):
    if not data.comments:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION", "message": "Rejection comment is required"}},
        )
    try:
        request = await workflow_service.act_on_step(
            db, step_id=step_id, actor_user_id=current_user.id, action="rejected", comments=data.comments
        )
        await _sync_reference_status(db, request)
        result = await db.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.steps))
            .where(ApprovalRequest.id == request.id)
        )
        req = result.scalar_one()
        name = await _requester_name(db, req.requester_employee_id)
        return _to_response(req, name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e

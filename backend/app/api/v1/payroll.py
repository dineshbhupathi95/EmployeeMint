import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_any_permission, require_permission
from app.core.database import get_db
from app.schemas.payroll import (
    BankAccountResponse,
    BankAccountUpsert,
    PayrollRejectRequest,
    PayrollRunCreate,
    PayrollRunDetailResponse,
    PayrollRunLineResponse,
    PayrollRunLineUpdate,
    PayrollRunResponse,
    PayrollSettingsResponse,
    PayrollSettingsUpdate,
)
from app.services.payroll_service import PayrollService

router = APIRouter(prefix="/payroll", tags=["payroll"])
payroll_service = PayrollService()


def _run_response(run) -> PayrollRunResponse:
    return PayrollRunResponse.model_validate(run)


def _run_detail(run, lines) -> PayrollRunDetailResponse:
    base = PayrollRunResponse.model_validate(run)
    return PayrollRunDetailResponse(
        **base.model_dump(),
        lines=[PayrollRunLineResponse.model_validate(l) for l in lines],
    )


@router.get("/settings", response_model=PayrollSettingsResponse)
async def get_payroll_settings(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("settings.manage", "payroll.draft", "payroll.approve")),
):
    settings = await payroll_service.get_settings(db, current_user.tenant_id)
    return PayrollSettingsResponse(**settings)


@router.put("/settings", response_model=PayrollSettingsResponse)
async def update_payroll_settings(
    data: PayrollSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings.manage")),
):
    current = await payroll_service.get_settings(db, current_user.tenant_id)
    updates = data.model_dump(exclude_unset=True)
    merged = {**current, **updates}
    result = await payroll_service.upsert_settings(
        db, current_user.tenant_id, merged, current_user.id
    )
    return PayrollSettingsResponse(**result)


@router.get("/runs", response_model=list[PayrollRunResponse])
async def list_payroll_runs(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_permission("payroll.draft", "payroll.approve", "payroll.view.all")
    ),
):
    runs = await payroll_service.list_runs(db, current_user.tenant_id, status)
    return [_run_response(r) for r in runs]


@router.post("/runs", response_model=PayrollRunDetailResponse, status_code=201)
async def create_payroll_run(
    data: PayrollRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("payroll.draft", "payroll.process")),
):
    try:
        run = await payroll_service.create_draft(
            db,
            tenant_id=current_user.tenant_id,
            month=data.month,
            year=data.year,
            user_id=current_user.id,
            notes=data.notes,
        )
        lines = await payroll_service._get_lines(db, run.id)
        return _run_detail(run, lines)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/runs/{run_id}", response_model=PayrollRunDetailResponse)
async def get_payroll_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_permission("payroll.draft", "payroll.approve", "payroll.view.all")
    ),
):
    run = await payroll_service.get_run(db, current_user.tenant_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Payroll run not found"}})
    lines = await payroll_service._get_lines(db, run_id)
    return _run_detail(run, lines)


@router.post("/runs/{run_id}/refresh", response_model=PayrollRunDetailResponse)
async def refresh_payroll_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("payroll.draft", "payroll.process")),
):
    try:
        run = await payroll_service.refresh_draft_lines(
            db, tenant_id=current_user.tenant_id, run_id=run_id
        )
        lines = await payroll_service._get_lines(db, run_id)
        return _run_detail(run, lines)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.patch("/runs/{run_id}/lines/{line_id}", response_model=PayrollRunLineResponse)
async def update_payroll_line(
    run_id: uuid.UUID,
    line_id: uuid.UUID,
    data: PayrollRunLineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("payroll.draft", "payroll.process")),
):
    try:
        line = await payroll_service.update_line(
            db,
            tenant_id=current_user.tenant_id,
            run_id=run_id,
            line_id=line_id,
            updates=data.model_dump(exclude_unset=True),
        )
        return PayrollRunLineResponse.model_validate(line)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/runs/{run_id}/submit", response_model=PayrollRunResponse)
async def submit_payroll_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.submit")),
):
    try:
        run = await payroll_service.submit_for_review(
            db, tenant_id=current_user.tenant_id, run_id=run_id, user_id=current_user.id
        )
        return _run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/runs/{run_id}/approve", response_model=PayrollRunResponse)
async def approve_payroll_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.approve")),
):
    try:
        run = await payroll_service.approve(
            db, tenant_id=current_user.tenant_id, run_id=run_id, user_id=current_user.id
        )
        return _run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/runs/{run_id}/reject", response_model=PayrollRunResponse)
async def reject_payroll_run(
    run_id: uuid.UUID,
    data: PayrollRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.approve")),
):
    try:
        run = await payroll_service.reject(
            db,
            tenant_id=current_user.tenant_id,
            run_id=run_id,
            user_id=current_user.id,
            finance_notes=data.finance_notes,
        )
        return _run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/runs/{run_id}/export")
async def export_payroll_batch(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.export")),
):
    try:
        content, filename = await payroll_service.export_bank_excel(
            db, current_user.tenant_id, run_id
        )
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/runs/{run_id}/upload-payment")
async def upload_payment_status(
    run_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.import")),
):
    content = await file.read()
    try:
        updated = await payroll_service.import_payment_status(
            db, current_user.tenant_id, run_id, content
        )
        return {"updated": updated, "message": f"Updated payment status for {updated} employees"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/runs/{run_id}/finalize", response_model=PayrollRunResponse)
async def finalize_payroll_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.finalize")),
):
    try:
        run = await payroll_service.finalize(
            db, tenant_id=current_user.tenant_id, run_id=run_id, user_id=current_user.id
        )
        return _run_response(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/bank-account", response_model=BankAccountResponse | None)
async def my_bank_account(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.employee_id:
        return None
    bank = await payroll_service.get_bank_account(
        db, current_user.tenant_id, current_user.employee_id
    )
    return BankAccountResponse.model_validate(bank) if bank else None


@router.put("/bank-account", response_model=BankAccountResponse)
async def upsert_my_bank_account(
    data: BankAccountUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    bank = await payroll_service.upsert_bank_account(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=current_user.employee_id,
        user_id=current_user.id,
        **data.model_dump(),
    )
    return BankAccountResponse.model_validate(bank)


@router.get("/bank-account/{employee_id}", response_model=BankAccountResponse | None)
async def get_employee_bank_account(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("payroll.draft", "payroll.view.all")),
):
    bank = await payroll_service.get_bank_account(db, current_user.tenant_id, employee_id)
    return BankAccountResponse.model_validate(bank) if bank else None

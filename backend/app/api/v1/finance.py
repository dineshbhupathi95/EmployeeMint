import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_any_permission, require_permission
from app.core.database import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.finance import (
    CompensationResponse,
    CompensationUpsertRequest,
    MyPayResponse,
    PayslipResponse,
    ReimbursementCategoryResponse,
    ReimbursementClaimResponse,
    ReimbursementSubmitRequest,
    TaxPreviewRequest,
)
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])
finance_service = FinanceService()


def _compensation_response(comp) -> CompensationResponse:
    enriched = finance_service.enrichment_for_compensation(comp)
    base = CompensationResponse.model_validate(comp)
    return base.model_copy(
        update={
            "earnings": enriched["earnings"],
            "deductions": {k: v for k, v in enriched["deductions"].items() if k != "tax_regime"},
            "gross_monthly": enriched["gross_monthly"],
            "net_monthly": enriched["net_monthly"],
            "tax_computation": enriched["tax_computation"],
        }
    )


@router.get("/my-pay", response_model=MyPayResponse)
async def my_pay(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.view.own")),
):
    if not current_user.employee_id:
        return MyPayResponse(
            configured=False,
            message="No employee profile linked to your account.",
        )

    comp = await finance_service.get_compensation(
        db, current_user.tenant_id, current_user.employee_id
    )
    payslips = await finance_service.list_payslips(
        db, current_user.tenant_id, current_user.employee_id
    )

    if not comp:
        return MyPayResponse(
            configured=False,
            payslip_count=len(payslips),
            message=(
                "Pay details not configured yet. HR will set up your compensation manually "
                "or it will appear automatically when your offer letter is released (matching your email)."
            ),
        )

    response_comp = _compensation_response(comp)
    return MyPayResponse(
        configured=True,
        compensation=response_comp,
        payslip_count=len(payslips),
        tax_computation=response_comp.tax_computation,
    )


@router.get("/compensation/{employee_id}", response_model=CompensationResponse)
async def get_employee_compensation(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.view.all")),
):
    comp = await finance_service.get_compensation(db, current_user.tenant_id, employee_id)
    if not comp:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Compensation not configured for this employee"}},
        )
    return _compensation_response(comp)


@router.put("/compensation/{employee_id}", response_model=CompensationResponse)
async def configure_employee_compensation(
    employee_id: uuid.UUID,
    data: CompensationUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.process")),
):
    comp = await finance_service.upsert_compensation(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=employee_id,
        user_id=current_user.id,
        ctc=data.ctc,
        designation=data.designation,
        joining_date=data.joining_date,
        source="admin",
        tax_regime=data.tax_regime,
        earnings=data.earnings,
        deductions=data.deductions,
        gross_monthly=data.gross_monthly,
        net_monthly=data.net_monthly,
    )
    return _compensation_response(comp)


@router.post("/tax-preview")
async def tax_preview(
    data: TaxPreviewRequest,
    current_user: CurrentUser = Depends(require_any_permission("payroll.view.own", "payroll.process")),
):
    """Preview automatic tax + net pay for a CTC."""
    return finance_service.compute_pay_from_ctc(data.ctc, tax_regime=data.tax_regime)


@router.get("/payslips", response_model=list[PayslipResponse])
async def my_payslips(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("payroll.view.own")),
):
    if not current_user.employee_id:
        return []
    slips = await finance_service.list_payslips(db, current_user.tenant_id, current_user.employee_id)
    return [PayslipResponse.model_validate(s) for s in slips]


@router.get("/reimbursements/categories", response_model=list[ReimbursementCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    cats = await finance_service.list_categories(db, current_user.tenant_id)
    return [ReimbursementCategoryResponse.model_validate(c) for c in cats]


@router.post("/reimbursements", response_model=ReimbursementClaimResponse, status_code=201)
async def submit_reimbursement(
    data: ReimbursementSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reimbursement.submit")),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    claim = await finance_service.submit_reimbursement(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=current_user.employee_id,
        user_id=current_user.id,
        category_id=data.category_id,
        amount=data.amount,
        expense_date=data.expense_date,
        description=data.description,
    )
    return ReimbursementClaimResponse.model_validate(claim)


@router.get("/reimbursements", response_model=PaginatedResponse[ReimbursementClaimResponse])
async def list_reimbursements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    employee_id = current_user.employee_id
    if "reimbursement.approve" in current_user.permissions or "payroll.view.all" in current_user.permissions:
        employee_id = None
    elif "reimbursement.submit" not in current_user.permissions:
        raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Access denied"}})
    items, total = await finance_service.list_claims(
        db, current_user.tenant_id, employee_id, page, page_size
    )
    return PaginatedResponse.create(
        [ReimbursementClaimResponse.model_validate(i) for i in items], total, page, page_size
    )

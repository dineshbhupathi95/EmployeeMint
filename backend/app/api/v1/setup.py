from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.core.database import get_db
from app.models import Tenant
from app.schemas.setup import (
    CompanyProfileSetup,
    SetupCompleteResponse,
    SetupProgressResponse,
    WorkingDaysSetup,
)
from app.services.setup_service import SetupService

router = APIRouter(prefix="/setup", tags=["setup"])
setup_service = SetupService()


async def _get_tenant(db: AsyncSession, tenant_id) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Tenant not found"}},
        )
    return tenant


@router.get("/progress", response_model=SetupProgressResponse)
async def get_setup_progress(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant = await _get_tenant(db, current_user.tenant_id)
    return await setup_service.get_progress(db, tenant)


@router.put("/profile", response_model=CompanyProfileSetup)
async def save_company_profile(
    data: CompanyProfileSetup,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await setup_service.save_company_profile(
        db, current_user.tenant_id, data, current_user.id
    )


@router.put("/working-days", response_model=WorkingDaysSetup)
async def save_working_days(
    data: WorkingDaysSetup,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        return await setup_service.save_working_days(
            db, current_user.tenant_id, data, current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
        ) from e


@router.post("/complete", response_model=SetupCompleteResponse)
async def complete_setup(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    tenant = await _get_tenant(db, current_user.tenant_id)
    try:
        await setup_service.complete_setup(db, tenant)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "SETUP_INCOMPLETE", "message": str(e)}},
        ) from e
    return SetupCompleteResponse(
        is_setup_complete=True,
        message="Setup completed successfully. Welcome to EmployeeMint!",
    )

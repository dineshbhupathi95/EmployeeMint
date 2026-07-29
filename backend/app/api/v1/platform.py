from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_platform_admin
from app.core.database import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.tenant import (
    TenantAdminResponse,
    TenantAdminUpdate,
    TenantCreate,
    TenantDetailResponse,
    TenantResponse,
    TenantUpdate,
)
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/platform/tenants", tags=["platform-tenants"])
tenant_service = TenantService()


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_platform_admin),
):
    try:
        tenant = await tenant_service.create_tenant(db, data)
        return TenantResponse.model_validate(tenant)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "CONFLICT", "message": str(e)}},
        ) from e


@router.get("", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_platform_admin),
):
    tenants, total = await tenant_service.list_tenants(db, page, page_size)
    items = [TenantResponse.model_validate(t) for t in tenants]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_platform_admin),
):
    tenant = await tenant_service.get_tenant_detail(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Tenant not found"}},
        )
    return tenant


@router.patch("/{tenant_id}", response_model=TenantDetailResponse)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_platform_admin),
):
    tenant = await tenant_service.get_by_id(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Tenant not found"}},
        )
    update_data = data.model_dump(exclude_unset=True)
    await tenant_service.update_tenant(db, tenant, update_data)
    detail = await tenant_service.get_tenant_detail(db, tenant_id)
    assert detail is not None
    return detail


@router.patch("/{tenant_id}/admins/{user_id}", response_model=TenantAdminResponse)
async def update_tenant_admin(
    tenant_id: UUID,
    user_id: UUID,
    data: TenantAdminUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_platform_admin),
):
    try:
        admin = await tenant_service.update_org_admin(db, tenant_id, user_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "CONFLICT", "message": str(e)}},
        ) from e

    if not admin:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Org admin not found"}},
        )
    return admin

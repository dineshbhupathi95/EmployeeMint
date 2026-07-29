from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, get_current_user, require_any_permission, require_permission
from app.core.database import get_db
from app.models import Announcement, ApprovalWorkflow, Holiday, LeaveType, Notification, Tenant
from app.schemas.leave import LeaveTypeResponse
from app.schemas.settings import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
    BrandingResponse,
    BrandingUpdate,
    HolidayCreate,
    HolidayResponse,
    HolidayUpdate,
    LeaveTypeCreate,
    LeaveTypeUpdate,
    WorkflowResponse,
    WorkflowStepSchema,
)
from app.services.branding_service import BrandingService
from app.services.dashboard_service import NotificationService, OrganizationService

router = APIRouter(prefix="/settings", tags=["settings"])
notification_service = NotificationService()
org_service = OrganizationService()
branding_service = BrandingService()


@router.get("/branding", response_model=BrandingResponse)
async def get_branding(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_TENANT", "message": "No tenant"}})
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Tenant not found"}})
    return BrandingResponse(name=tenant.name, slug=tenant.slug, has_logo=bool(tenant.logo_path))


@router.put("/branding", response_model=BrandingResponse)
async def update_branding(
    data: BrandingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("settings.manage", "org.manage")),
):
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Tenant not found"}})
    try:
        await branding_service.update_name(db, tenant, data.name)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    await db.refresh(tenant)
    return BrandingResponse(name=tenant.name, slug=tenant.slug, has_logo=bool(tenant.logo_path))


@router.post("/branding/logo", response_model=BrandingResponse)
async def upload_branding_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("settings.manage", "org.manage")),
):
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Tenant not found"}})
    content = await file.read()
    try:
        await branding_service.save_logo(
            db,
            tenant=tenant,
            file_name=file.filename or "logo",
            content_type=file.content_type,
            content=content,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    await db.refresh(tenant)
    return BrandingResponse(name=tenant.name, slug=tenant.slug, has_logo=bool(tenant.logo_path))


@router.get("/branding/logo")
async def get_branding_logo(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_TENANT", "message": "No tenant"}})
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.logo_path:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Logo not found"}})
    path = branding_service.absolute_path(tenant.logo_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Logo file missing"}})
    return FileResponse(
        path,
        media_type=tenant.logo_content_type or "image/png",
        filename=path.name,
        content_disposition_type="inline",
    )


@router.delete("/branding/logo", response_model=BrandingResponse)
async def delete_branding_logo(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_permission("settings.manage", "org.manage")),
):
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Tenant not found"}})
    await branding_service.delete_logo(db, tenant)
    await db.commit()
    await db.refresh(tenant)
    return BrandingResponse(name=tenant.name, slug=tenant.slug, has_logo=False)


@router.get("/holidays", response_model=list[HolidayResponse])
async def list_holidays(
    year: int = Query(default_factory=lambda: date.today().year),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    holidays = await org_service.list_holidays(db, current_user.tenant_id, year)
    return [HolidayResponse.model_validate(h) for h in holidays]


@router.post("/holidays", response_model=HolidayResponse, status_code=201)
async def create_holiday(
    data: HolidayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings.manage")),
):
    holiday = Holiday(
        tenant_id=current_user.tenant_id,
        name=data.name,
        date=data.date,
        is_optional=data.is_optional,
        created_by=current_user.id,
    )
    db.add(holiday)
    await db.flush()
    return HolidayResponse.model_validate(holiday)


@router.patch("/holidays/{holiday_id}", response_model=HolidayResponse)
async def update_holiday(
    holiday_id: UUID,
    data: HolidayUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings.manage")),
):
    result = await db.execute(
        select(Holiday).where(Holiday.id == holiday_id, Holiday.tenant_id == current_user.tenant_id)
    )
    holiday = result.scalar_one_or_none()
    if not holiday:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Holiday not found"}})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(holiday, field, value)
    await db.flush()
    return HolidayResponse.model_validate(holiday)


@router.get("/leave-types", response_model=list[LeaveTypeResponse])
async def settings_leave_types(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("leave.manage")),
):
    result = await db.execute(
        select(LeaveType).where(LeaveType.tenant_id == current_user.tenant_id, LeaveType.is_deleted.is_(False))
    )
    return [LeaveTypeResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/leave-types", response_model=LeaveTypeResponse, status_code=201)
async def create_leave_type(
    data: LeaveTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("leave.manage")),
):
    lt = LeaveType(
        tenant_id=current_user.tenant_id,
        name=data.name,
        code=data.code,
        annual_quota=data.annual_quota,
        is_paid=data.is_paid,
        requires_document=data.requires_document,
        created_by=current_user.id,
    )
    db.add(lt)
    await db.flush()
    return LeaveTypeResponse.model_validate(lt)


@router.patch("/leave-types/{leave_type_id}", response_model=LeaveTypeResponse)
async def update_leave_type(
    leave_type_id: UUID,
    data: LeaveTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("leave.manage")),
):
    result = await db.execute(
        select(LeaveType).where(LeaveType.id == leave_type_id, LeaveType.tenant_id == current_user.tenant_id)
    )
    lt = result.scalar_one_or_none()
    if not lt:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Leave type not found"}})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lt, field, value)
    await db.flush()
    return LeaveTypeResponse.model_validate(lt)


@router.get("/workflows", response_model=list[WorkflowResponse])
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("workflows.manage")),
):
    result = await db.execute(
        select(ApprovalWorkflow)
        .options(selectinload(ApprovalWorkflow.steps))
        .where(ApprovalWorkflow.tenant_id == current_user.tenant_id, ApprovalWorkflow.is_deleted.is_(False))
    )
    workflows = []
    for wf in result.scalars().all():
        workflows.append(
            WorkflowResponse(
                id=wf.id,
                name=wf.name,
                request_type=wf.request_type,
                is_active=wf.is_active,
                steps=[
                    WorkflowStepSchema(
                        step_order=s.step_order,
                        approver_rule=s.approver_rule,
                        approver_value=s.approver_value,
                    )
                    for s in wf.steps
                ],
            )
        )
    return workflows


@router.get("/announcements", response_model=list[AnnouncementResponse])
async def list_announcements(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(Announcement)
        .where(Announcement.tenant_id == current_user.tenant_id, Announcement.is_deleted.is_(False))
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .limit(20)
    )
    return [AnnouncementResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/announcements", response_model=AnnouncementResponse, status_code=201)
async def create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings.manage")),
):
    ann = Announcement(
        tenant_id=current_user.tenant_id,
        title=data.title,
        body=data.body,
        is_pinned=data.is_pinned,
        show_on_dashboard=data.show_on_dashboard,
        author_user_id=current_user.id,
        created_by=current_user.id,
    )
    db.add(ann)
    await db.flush()
    return AnnouncementResponse.model_validate(ann)


@router.patch("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: UUID,
    data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("settings.manage")),
):
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id, Announcement.tenant_id == current_user.tenant_id
        )
    )
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Announcement not found"}})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ann, field, value)
    await db.flush()
    return AnnouncementResponse.model_validate(ann)


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    notes = await notification_service.list_for_user(
        db, current_user.tenant_id, current_user.id, unread_only
    )
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "body": n.body,
            "is_read": n.is_read,
            "notification_type": n.notification_type,
            "metadata": n.metadata_ or {},
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from uuid import UUID

    await notification_service.mark_read(db, UUID(notification_id), current_user.id)
    return {"ok": True}


@router.get("/notifications/unread-count")
async def unread_notification_count(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    count = await notification_service.unread_count(db, current_user.tenant_id, current_user.id)
    return {"count": count}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.tenant_id == current_user.tenant_id,
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
            Notification.is_deleted.is_(False),
        )
    )
    from datetime import UTC, datetime

    for note in result.scalars().all():
        note.is_read = True
        note.read_at = datetime.now(UTC)
    await db.flush()
    return {"ok": True}

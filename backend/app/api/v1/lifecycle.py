import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_permission
from app.core.database import get_db
from app.models import OfferLetter, Tenant
from app.services.lifecycle_service import DEFAULT_TEMPLATE_BODY, LifecycleService

router = APIRouter(tags=["hr-lifecycle"])
lifecycle_service = LifecycleService()


class OfferLetterCreate(BaseModel):
    template_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    designation: str | None = None
    ctc: str | None = None
    joining_date: date | None = None


class OfferTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    body_html: str = Field(min_length=1)
    is_active: bool = True


class OfferTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    body_html: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class OnboardingTaskCreate(BaseModel):
    employee_id: uuid.UUID
    title: str
    description: str | None = None
    due_date: date | None = None


class OnboardingTaskUpdate(BaseModel):
    status: str | None = None
    title: str | None = None
    due_date: date | None = None


class ExitRequestCreate(BaseModel):
    exit_type: str = "resignation"
    resignation_date: date
    last_working_date: date
    reason: str | None = None


# ── Templates ──────────────────────────────────────────────


@router.get("/offer-letter-templates")
async def list_offer_templates(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    return await lifecycle_service.list_templates(db, current_user.tenant_id)


@router.post("/offer-letter-templates", status_code=201)
async def create_offer_template(
    data: OfferTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    try:
        template = await lifecycle_service.create_template(
            db,
            current_user.tenant_id,
            current_user.id,
            name=data.name,
            body_html=data.body_html,
            is_active=data.is_active,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {
        "id": str(template.id),
        "name": template.name,
        "body_html": template.body_html,
        "is_active": template.is_active,
    }


@router.post("/offer-letter-templates/upload", status_code=201)
async def upload_offer_template(
    name: str = Form(...),
    file: UploadFile = File(...),
    is_active: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    filename = (file.filename or "").lower()
    allowed = (".html", ".htm", ".txt", ".md")
    if not any(filename.endswith(ext) for ext in allowed):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION",
                    "message": "Upload .html, .htm, .txt, or .md files only",
                }
            },
        )
    raw = await file.read()
    if len(raw) > 500_000:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION", "message": "File too large (max 500KB)"}},
        )
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION", "message": "File must be UTF-8 text"}},
        ) from e
    if not body.strip():
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION", "message": "Uploaded file is empty"}},
        )
    try:
        template = await lifecycle_service.create_template(
            db,
            current_user.tenant_id,
            current_user.id,
            name=name,
            body_html=body,
            is_active=is_active,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {
        "id": str(template.id),
        "name": template.name,
        "body_html": template.body_html,
        "is_active": template.is_active,
        "message": "Template uploaded successfully",
    }


@router.patch("/offer-letter-templates/{template_id}")
async def update_offer_template(
    template_id: uuid.UUID,
    data: OfferTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    try:
        template = await lifecycle_service.update_template(
            db,
            current_user.tenant_id,
            template_id,
            name=data.name,
            body_html=data.body_html,
            is_active=data.is_active,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {
        "id": str(template.id),
        "name": template.name,
        "body_html": template.body_html,
        "is_active": template.is_active,
    }


@router.delete("/offer-letter-templates/{template_id}", status_code=204)
async def delete_offer_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    try:
        await lifecycle_service.delete_template(db, current_user.tenant_id, template_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/offer-letter-templates/sample-body")
async def sample_template_body(
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    return {
        "body_html": DEFAULT_TEMPLATE_BODY,
        "placeholders": [
            "candidate_name",
            "candidate_email",
            "designation",
            "ctc",
            "joining_date",
            "company_name",
            "date",
        ],
    }


# ── Offer letters ──────────────────────────────────────────


@router.get("/offer-letters")
async def list_offer_letters(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    return await lifecycle_service.list_offers(db, current_user.tenant_id)


@router.post("/offer-letters", status_code=201)
async def create_offer_letter(
    data: OfferLetterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    try:
        letter = await lifecycle_service.create_offer(
            db,
            current_user.tenant_id,
            current_user.id,
            template_id=data.template_id,
            candidate_name=data.candidate_name,
            candidate_email=data.candidate_email,
            designation=data.designation,
            ctc=data.ctc,
            joining_date=data.joining_date,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {"id": str(letter.id), "status": letter.status, "template_id": str(letter.template_id)}


@router.post("/offer-letters/{offer_id}/generate-pdf")
async def generate_offer_pdf(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    try:
        letter, pdf_bytes = await lifecycle_service.generate_offer_pdf(
            db, current_user.tenant_id, offer_id
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e

    filename = f"offer-{letter.candidate_name.replace(' ', '-').lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Offer-Status": letter.status,
        },
    )


@router.get("/offer-letters/{offer_id}/pdf")
async def download_offer_pdf(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    result = await db.execute(
        select(OfferLetter).where(
            OfferLetter.id == offer_id,
            OfferLetter.tenant_id == current_user.tenant_id,
            OfferLetter.is_deleted.is_(False),
        )
    )
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Offer not found"}})
    if letter.status == "draft":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION", "message": "Generate PDF first"}},
        )

    template_body = None
    template_name = None
    if letter.template_id:
        template = await lifecycle_service._get_template(db, current_user.tenant_id, letter.template_id)
        if template:
            template_body = template.body_html
            template_name = template.name

    tenant = await db.get(Tenant, current_user.tenant_id)
    company_name = tenant.name if tenant else "Your Company"
    pdf_bytes = lifecycle_service._build_offer_pdf(letter, company_name, template_body, template_name)
    filename = f"offer-{letter.candidate_name.replace(' ', '-').lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/offer-letters/{offer_id}/release")
async def release_offer_letter(
    offer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offer_letter.generate")),
):
    try:
        letter = await lifecycle_service.release_offer(db, current_user.tenant_id, offer_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {
        "id": str(letter.id),
        "status": letter.status,
        "message": f"Offer released to {letter.candidate_email}. Pay details synced if employee email matches.",
    }


# ── Onboarding / Offboarding ───────────────────────────────


@router.get("/onboarding/my-tasks")
async def my_onboarding_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.employee_id:
        return []
    return await lifecycle_service.list_my_onboarding_tasks(
        db, current_user.tenant_id, current_user.employee_id
    )


@router.patch("/onboarding/my-tasks/{task_id}")
async def complete_my_onboarding_task(
    task_id: uuid.UUID,
    data: OnboardingTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    if not data.status:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": "status is required"}})
    try:
        task = await lifecycle_service.update_my_onboarding_task(
            db,
            current_user.tenant_id,
            current_user.employee_id,
            task_id,
            status=data.status,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {"id": str(task.id), "status": task.status}


@router.get("/onboarding/tasks")
async def list_onboarding_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("onboarding.manage")),
):
    return await lifecycle_service.list_onboarding_tasks(db, current_user.tenant_id)


@router.post("/onboarding/tasks", status_code=201)
async def create_onboarding_task(
    data: OnboardingTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("onboarding.manage")),
):
    try:
        task = await lifecycle_service.create_onboarding_task(
            db,
            current_user.tenant_id,
            current_user.id,
            employee_id=data.employee_id,
            title=data.title,
            description=data.description,
            due_date=data.due_date,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {"id": str(task.id), "status": task.status}


@router.post("/onboarding/start/{employee_id}", status_code=201)
async def start_onboarding(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("onboarding.manage")),
):
    try:
        tasks = await lifecycle_service.start_onboarding(
            db, current_user.tenant_id, current_user.id, employee_id
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {"created": len(tasks), "message": f"Started onboarding with {len(tasks)} tasks"}


@router.patch("/onboarding/tasks/{task_id}")
async def update_onboarding_task(
    task_id: uuid.UUID,
    data: OnboardingTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("onboarding.manage")),
):
    try:
        task = await lifecycle_service.update_onboarding_task(
            db,
            current_user.tenant_id,
            task_id,
            status=data.status,
            title=data.title,
            due_date=data.due_date,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {"id": str(task.id), "status": task.status}


@router.get("/offboarding/requests")
async def list_exit_requests(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offboarding.manage")),
):
    from app.models import ExitRequest

    result = await db.execute(
        select(ExitRequest).where(
            ExitRequest.tenant_id == current_user.tenant_id, ExitRequest.is_deleted.is_(False)
        )
    )
    return [
        {
            "id": str(e.id),
            "exit_type": e.exit_type,
            "status": e.status,
            "last_working_date": str(e.last_working_date),
        }
        for e in result.scalars().all()
    ]


@router.post("/offboarding/requests", status_code=201)
async def create_exit_request(
    data: ExitRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("offboarding.manage")),
):
    from app.models import ExitRequest

    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    req = ExitRequest(
        tenant_id=current_user.tenant_id,
        employee_id=current_user.employee_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(req)
    await db.commit()
    return {"id": str(req.id), "status": req.status}

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_any_permission, require_permission
from app.core.database import get_db
from app.schemas.candidate import (
    AcceptOfferRequest,
    CandidateCreate,
    CandidateOfferResponse,
    CandidateResponse,
    CandidateUpdate,
    CreateOfferForCandidate,
    ResumeParseResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.candidate_service import CandidateService

router = APIRouter(prefix="/candidates", tags=["recruitment"])
candidate_service = CandidateService()


@router.get("", response_model=PaginatedResponse[CandidateResponse])
async def list_candidates(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("recruitment.view")),
):
    items, total = await candidate_service.list_candidates(
        db, current_user.tenant_id, status=status, page=page, page_size=page_size
    )
    return PaginatedResponse.create(
        [CandidateResponse.from_model(c) for c in items], total, page, page_size
    )


@router.post("", response_model=CandidateResponse, status_code=201)
async def create_candidate(
    data: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("recruitment.manage")),
):
    try:
        candidate = await candidate_service.create(
            db, current_user.tenant_id, current_user.id, data
        )
        return CandidateResponse.from_model(candidate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/parse-resume", response_model=ResumeParseResponse)
async def parse_resume_preview(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permission("recruitment.manage")),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION", "message": "Choose a resume file to upload"}},
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION", "message": "Uploaded file is empty"}},
        )
    try:
        parsed = await candidate_service.parse_resume_preview(file.filename, content)
        return ResumeParseResponse(**parsed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "PARSE_FAILED", "message": f"Could not parse resume: {e}"}},
        ) from e


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("recruitment.view")),
):
    candidate = await candidate_service.get(db, current_user.tenant_id, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Candidate not found"}})
    return CandidateResponse.from_model(candidate)


@router.patch("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: uuid.UUID,
    data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("recruitment.manage")),
):
    try:
        candidate = await candidate_service.update(db, current_user.tenant_id, candidate_id, data)
        return CandidateResponse.from_model(candidate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/{candidate_id}/resume", response_model=CandidateResponse)
async def upload_candidate_resume(
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("recruitment.manage")),
):
    content = await file.read()
    try:
        candidate, _ = await candidate_service.upload_resume(
            db,
            current_user.tenant_id,
            candidate_id,
            filename=file.filename or "resume.pdf",
            content=content,
            content_type=file.content_type,
        )
        return CandidateResponse.from_model(candidate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/{candidate_id}/resume")
async def download_candidate_resume(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("recruitment.view")),
):
    candidate = await candidate_service.get(db, current_user.tenant_id, candidate_id)
    if not candidate or not candidate.resume_file_path:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Resume not found"}})
    return FileResponse(
        candidate.resume_file_path,
        filename=candidate.resume_file_name or "resume.pdf",
        media_type=candidate.resume_content_type or "application/octet-stream",
    )


@router.get("/{candidate_id}/offers", response_model=list[CandidateOfferResponse])
async def list_candidate_offers(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("recruitment.view")),
):
    offers = await candidate_service.list_offers(db, current_user.tenant_id, candidate_id)
    return [
        CandidateOfferResponse(
            id=o.id,
            status=o.status,
            designation=o.designation,
            ctc=o.ctc,
            joining_date=o.joining_date,
            has_pdf=o.status in ("pdf_ready", "released", "accepted"),
            employee_id=o.employee_id,
            accepted_at=o.accepted_at,
            created_at=o.created_at,
        )
        for o in offers
    ]


@router.post("/{candidate_id}/offers", status_code=201)
async def create_candidate_offer(
    candidate_id: uuid.UUID,
    data: CreateOfferForCandidate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_permission("recruitment.manage", "offer_letter.generate")
    ),
):
    try:
        offer = await candidate_service.create_offer_for_candidate(
            db,
            current_user.tenant_id,
            current_user.id,
            candidate_id,
            template_id=data.template_id,
            designation=data.designation,
            ctc=data.ctc,
            joining_date=data.joining_date,
        )
        return {"id": str(offer.id), "status": offer.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.post("/{candidate_id}/offers/{offer_id}/accept")
async def accept_candidate_offer(
    candidate_id: uuid.UUID,
    offer_id: uuid.UUID,
    data: AcceptOfferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_permission("recruitment.manage", "employee.create")
    ),
):
    try:
        result = await candidate_service.accept_offer(
            db,
            current_user.tenant_id,
            candidate_id,
            offer_id,
            current_user.id,
            data,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e

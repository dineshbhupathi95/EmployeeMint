import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_permission
from app.core.database import get_db
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
document_service = DocumentService()


@router.get("/types")
async def list_document_types(
    current_user: CurrentUser = Depends(get_current_user),
):
    return document_service.list_required_types()


@router.get("/my")
async def list_my_documents(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.employee_id:
        return []
    docs = await document_service.list_documents(db, current_user.tenant_id, current_user.employee_id)
    return [
        {
            "id": str(d.id),
            "document_type": d.document_type,
            "title": d.title,
            "file_name": d.file_name,
            "content_type": d.content_type,
            "file_size": d.file_size,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.post("/my", status_code=201)
async def upload_my_document(
    document_type: str = Form(...),
    title: str | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    content = await file.read()
    try:
        doc = await document_service.upload(
            db,
            tenant_id=current_user.tenant_id,
            employee_id=current_user.employee_id,
            user_id=current_user.id,
            document_type=document_type,
            title=title,
            file_name=file.filename or "document",
            content_type=file.content_type,
            content=content,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e
    return {
        "id": str(doc.id),
        "document_type": doc.document_type,
        "title": doc.title,
        "file_name": doc.file_name,
        "status": doc.status,
        "message": "Document uploaded. Related onboarding tasks marked complete when applicable.",
    }


@router.get("/my/{document_id}/download")
async def download_my_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    doc = await document_service.get_document(db, current_user.tenant_id, document_id)
    if not doc or doc.employee_id != current_user.employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Document not found"}})
    path = document_service.absolute_path(doc)
    if not path.exists():
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "File missing on server"}})
    media = doc.content_type or "application/octet-stream"
    # inline so browsers / iframes can preview PDFs and images
    return FileResponse(
        path,
        filename=doc.file_name,
        media_type=media,
        content_disposition_type="inline",
    )


@router.delete("/my/{document_id}", status_code=204)
async def delete_my_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "NO_EMPLOYEE", "message": "No employee profile"}})
    doc = await document_service.get_document(db, current_user.tenant_id, document_id)
    if not doc or doc.employee_id != current_user.employee_id:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Document not found"}})
    try:
        await document_service.delete_document(db, current_user.tenant_id, document_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "VALIDATION", "message": str(e)}}) from e


@router.get("/employee/{employee_id}")
async def list_employee_documents(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("onboarding.manage")),
):
    docs = await document_service.list_documents(db, current_user.tenant_id, employee_id)
    return [
        {
            "id": str(d.id),
            "document_type": d.document_type,
            "title": d.title,
            "file_name": d.file_name,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]

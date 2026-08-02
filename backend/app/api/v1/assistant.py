from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_any_permission
from app.core.database import get_db
from app.services.assistant_service import assistant_service
from app.services.policy_file_extract import extract_policy_text

router = APIRouter(prefix="/assistant", tags=["assistant"])

manage_ai = require_any_permission("assistant.manage", "settings.manage")


def _require_tenant(user: CurrentUser) -> CurrentUser:
    if not user.tenant_id or user.is_platform_admin:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN", "message": "Tenant user required"}},
        )
    return user


class AiConfigUpdate(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    embedding_model: str | None = None
    api_key: str | None = None
    is_enabled: bool | None = None


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: UUID | None = None


@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    cfg = await assistant_service.get_or_create_config(db, current_user.tenant_id)
    await db.commit()
    return assistant_service.config_public(cfg)


@router.put("/config")
async def update_config(
    body: AiConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    cfg = await assistant_service.update_config(
        db,
        current_user.tenant_id,
        provider=body.provider,
        base_url=body.base_url,
        model_name=body.model_name,
        embedding_model=body.embedding_model,
        api_key=body.api_key,
        is_enabled=body.is_enabled,
    )
    await db.commit()
    return assistant_service.config_public(cfg)


@router.post("/config/test")
async def test_config(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    try:
        result = await assistant_service.test_connection(db, current_user.tenant_id)
        await db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "AI_ERROR", "message": str(e)}})


@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    docs = await assistant_service.list_documents(db, current_user.tenant_id)
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "source_type": d.source_type,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }
        for d in docs
    ]


@router.post("/documents", status_code=201)
async def create_document(
    body: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    try:
        doc = await assistant_service.create_document(
            db, current_user.tenant_id, title=body.title, content=body.content
        )
        await db.commit()
        return {
            "id": str(doc.id),
            "title": doc.title,
            "source_type": doc.source_type,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "AI_ERROR", "message": str(e)}})


@router.post("/documents/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    """Upload a policy file (.txt, .md, .csv, .pdf). Content textarea not required."""
    try:
        raw = await file.read()
        if not raw:
            raise ValueError("Uploaded file is empty")
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("File too large (max 8 MB)")
        text = extract_policy_text(file.filename or "document.txt", raw)
        doc_title = (title or "").strip() or (file.filename or "Uploaded policy").rsplit(".", 1)[0]
        doc = await assistant_service.create_document(
            db,
            current_user.tenant_id,
            title=doc_title[:255],
            content=text,
            source_type="upload",
        )
        await db.commit()
        return {
            "id": str(doc.id),
            "title": doc.title,
            "source_type": doc.source_type,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "AI_ERROR", "message": str(e)}})


@router.post("/documents/{doc_id}/reindex")
async def reindex_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    try:
        doc = await assistant_service.reindex_document(db, current_user.tenant_id, doc_id)
        await db.commit()
        return {"id": str(doc.id), "status": doc.status, "chunk_count": doc.chunk_count}
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "AI_ERROR", "message": str(e)}})


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    try:
        await assistant_service.delete_document(db, current_user.tenant_id, doc_id)
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "AI_ERROR", "message": str(e)}})


@router.post("/sync")
async def sync_company_data(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(manage_ai),
):
    try:
        result = await assistant_service.sync_company_data(db, current_user.tenant_id)
        await db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "AI_ERROR", "message": str(e)}})


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_tenant(current_user)
    items = await assistant_service.list_conversations(db, current_user.tenant_id, current_user.id)
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in items
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_tenant(current_user)
    conv = await assistant_service.get_conversation(
        db, current_user.tenant_id, current_user.id, conversation_id
    )
    if not conv:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Not found"}})
    return {
        "id": str(conv.id),
        "title": conv.title,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "sources": m.sources or [],
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in (conv.messages or [])
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_tenant(current_user)
    try:
        await assistant_service.delete_conversation(
            db, current_user.tenant_id, current_user.id, conversation_id
        )
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "AI_ERROR", "message": str(e)}})


@router.post("/chat")
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_tenant(current_user)
    try:
        result = await assistant_service.chat(
            db,
            current_user.tenant_id,
            user_id=current_user.id,
            employee_id=current_user.employee_id,
            permissions=current_user.permissions,
            message=body.message,
            conversation_id=body.conversation_id,
        )
        await db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "AI_ERROR", "message": str(e)}})
